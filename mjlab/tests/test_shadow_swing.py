"""Stage 5 Drill 2: shadow swing at a ghost ball (episode routing, no contact, reward, recovery, metrics)."""

import pytest
import torch


def test_student_swing_task_config():
    import mjlab.tasks  # noqa: F401
    from mjlab.tasks.registry import load_env_cfg, load_rl_cfg

    from picklebot_mj.feeds import FAMILY_NAMES
    from picklebot_mj.tasks import TASK_FOOTWORK_WIDE, TASK_STUDENT_SWING

    c, f2 = load_env_cfg(TASK_STUDENT_SWING), load_env_cfg(TASK_FOOTWORK_WIDE)
    b = c.actions["ball"]
    assert b.move_prob == 0.25 and b.swing_prob == 0.5
    from picklebot_mj.feeds import REACH_FAMILIES, STAGE4_FAMILIES
    w = dict(zip(FAMILY_NAMES, b.swing_mix.vector()))  # Stage 5 families; the Stage 5C court families are not used
    assert all(w[f] > 0 for f in STAGE4_FAMILIES + REACH_FAMILIES) and len(w) == len(FAMILY_NAMES)
    assert "shadow_swing" in c.rewards and "move_arrival" in c.rewards
    for g in ("actor", "critic"):  # the student's inputs are unchanged
        assert list(c.observations[g].terms) == list(f2.observations[g].terms)
    rl = load_rl_cfg(TASK_STUDENT_SWING)
    assert tuple(rl.actor.hidden_dims) == (1024, 512, 256) and rl.algorithm.class_name.endswith(":RegPPO")


@pytest.mark.skipif(not torch.cuda.is_available(), reason="needs CUDA (mujoco_warp)")
def test_ghost_ball_swing_reward_and_recovery():
    from mjlab.envs import ManagerBasedRlEnv

    from picklebot_mj.feeds import FAMILY_NAMES, FeedMix
    from picklebot_mj.tasks.return_stand import return_stand_env_cfg
    from picklebot_mj.tasks.shadow_swing import FAR, RECOVER_S, WINDOW_MAX_S

    n = 32
    cfg = return_stand_env_cfg(targets=True, start_box=True, recovery=True, free_feet=True, swing_prob=1.0,
                               swing_mix=FeedMix({f: 1.0 for f in FAMILY_NAMES}))
    cfg.scene.num_envs = n
    cfg.actions["ball"].compile_ball = False
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    t = env.action_manager.get_term("ball")
    sh = t.shadow
    assert sh.swing_ep.all() and t.tallied.all()  # every episode is a swing episode, never tallied
    p = torch.zeros(n, 3, device="cuda")
    assert torch.allclose(sh.paddle_for_sim(p)[:, 2], torch.full((n,), FAR, device="cuda"))  # out of the ball sim
    # A perfect swing: paddle exactly at the ball after the bounce, moving 3 m/s toward the net, feet still.
    sh.bounced[:] = True
    t.ball.pos[:, 2] = 0.8
    vel = torch.zeros(n, 3, device="cuda")
    vel[:, 0] = 3.0
    no = torch.zeros(n, dtype=torch.bool, device="cuda")
    sh.step(0.005, no, t.ball.pos.clone(), vel, torch.zeros(n, device="cuda"))
    assert torch.allclose(sh.dmin, torch.zeros(n, device="cuda"))
    sh.elapsed[:] = WINDOW_MAX_S + 1.0  # close the window
    sh.step(0.005, no, t.ball.pos.clone() + 5.0, vel, torch.zeros(n, device="cuda"))
    r = sh.consume()
    assert torch.allclose(r, torch.ones(n, device="cuda"), atol=1e-5)
    assert t.hit_done.all() and torch.allclose(t.refeed_timer, torch.full((n,), RECOVER_S, device="cuda"))
    assert float(sh.stats["swings"].sum()) == n and float(sh.stats["within"].sum()) == n
    assert torch.equal(sh.consume(), torch.zeros(n, device="cuda"))  # one-shot
    # The real environment runs with ghost balls: no paddle contact is ever tallied.
    ep0 = int(t.ep["episodes"])
    for _ in range(40):
        env.step(torch.zeros(n, 29, device="cuda"))
    assert int(t.ep["episodes"]) == ep0


@pytest.mark.skipif(not torch.cuda.is_available(), reason="needs CUDA (mujoco_warp)")
def test_hint_shown_until_the_swing_then_true_recovery_spot_and_blowup_guard():
    from mjlab.envs import ManagerBasedRlEnv

    from picklebot_mj.feeds import FAMILY_NAMES, FeedMix
    from picklebot_mj.tasks.return_stand import blew_up, return_stand_env_cfg
    from picklebot_mj.tasks.shadow_swing import WINDOW_MAX_S

    n = 32
    cfg = return_stand_env_cfg(targets=True, start_box=True, recovery=True, free_feet=True, swing_prob=1.0,
                               swing_mix=FeedMix({f: 1.0 for f in FAMILY_NAMES}), swing_hint=True,
                               blowup_guard=True)
    cfg.scene.num_envs = n
    cfg.actions["ball"].compile_ball = False
    assert "blew_up" in cfg.terminations
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    t = env.action_manager.get_term("ball")
    sh = t.shadow
    hint = t.recover_xy.clone()
    assert not torch.allclose(hint, sh.recover_true)  # the spot input shows the interception hint, not recovery
    # Close every window: the spot input returns to the true recovery spot.
    sh.elapsed[:] = WINDOW_MAX_S + 1.0
    no = torch.zeros(n, dtype=torch.bool, device="cuda")
    z = torch.zeros(n, 3, device="cuda")
    sh.step(0.005, no, t.ball.pos.clone(), z, torch.zeros(n, device="cuda"))
    assert torch.allclose(t.recover_xy, sh.recover_true)
    # Blow-up guard: an impossible base speed terminates.
    assert not blew_up(env).any()
    vel = torch.zeros(n, 6, device="cuda")
    vel[:, 0] = 20.0
    env.scene["robot"].write_root_link_velocity_to_sim(vel)
    env.sim.forward()
    assert blew_up(env).all()


def test_histogram_bins_are_nan_safe():
    """Regression (S-D2 crash at iteration 953): a NaN from a simulation blow-up became a negative index."""
    from picklebot_mj.tasks.shadow_swing import D_BIN, D_BINS

    d = torch.tensor([float("nan"), float("inf"), -1.0, 0.1])
    b = (d.nan_to_num(nan=1e3, posinf=1e3, neginf=0.0) / D_BIN).clamp(0, D_BINS - 1).long()
    assert int(b.min()) >= 0 and int(b.max()) <= D_BINS - 1



@pytest.mark.skipif(not torch.cuda.is_available(), reason="needs CUDA (mujoco_warp)")
def test_follow_hint_rewards_walking_toward_the_hint_until_the_bounce():
    from mjlab.envs import ManagerBasedRlEnv

    from picklebot_mj.feeds import FAMILY_NAMES, FeedMix
    from picklebot_mj.tasks.move_drill import _walk_mask
    from picklebot_mj.tasks.return_stand import return_stand_env_cfg

    n = 32
    cfg = return_stand_env_cfg(targets=True, start_box=True, recovery=True, free_feet=True, move_prob=0.25,
                               swing_prob=0.75, swing_mix=FeedMix({f: 1.0 for f in FAMILY_NAMES}), swing_hint=True,
                               blowup_guard=True, swing_follow_hint=True)
    cfg.scene.num_envs = n
    cfg.actions["ball"].compile_ball = False
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    t = env.action_manager.get_term("ball")
    m = _walk_mask(t.drill).bool()
    assert torch.equal(m, t.drill.move_ep | t.shadow.swing_ep)  # every episode walks before the first bounce
    t.shadow.bounced[:] = True
    assert torch.equal(_walk_mask(t.drill).bool(), t.drill.move_ep)  # after the bounce: swing, not walk

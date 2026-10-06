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
    assert all(w > 0 for w in b.swing_mix.vector()) and len(b.swing_mix.vector()) == len(FAMILY_NAMES)
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

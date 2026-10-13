"""Stage 5B H4: the Drill 3 executor acting through the frozen latent controller (Picklebot-Latent-Drill3-G1)."""

from pathlib import Path

import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
LATENT = ROOT / "artifacts" / "train" / "latent" / "latent-07" / "latent_10651.pt"
needs = pytest.mark.skipif(not (torch.cuda.is_available() and LATENT.exists()),
                           reason="needs CUDA and the H1 latent controller")


@needs
def test_h4_task_uses_the_latent_action_space_and_no_posture_rewards():
    import mjlab.tasks  # noqa: F401
    from mjlab.asset_zoo.robots import G1_ACTION_SCALE
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.tasks.registry import load_env_cfg

    from picklebot_mj.tasks.latent_reach import controller_proprio

    cfg = load_env_cfg("Picklebot-Latent-Drill3-G1")
    assert list(cfg.actions) == ["latent", "ball"]  # the ball term runs after the joint targets are set
    assert cfg.actions["latent"].lam == 1.0
    assert cfg.actions["latent"].scale == G1_ACTION_SCALE  # the scale the decoder was trained with
    assert "pose" not in cfg.rewards and "ready_stance" not in cfg.rewards and "style" not in cfg.rewards
    assert "latent_l2" in cfg.rewards and "legal_return" in cfg.rewards
    assert cfg.rewards["action_rate_l2"].weight == -0.01  # H3's weight for the raw latent action
    cfg.scene.num_envs = 16
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    assert env.action_manager.total_action_dim == 35
    term = env.action_manager.get_term("latent")
    for _ in range(60):
        obs, rew, *_ = env.step(0.5 * torch.randn(16, 35, device="cuda"))
        assert torch.isfinite(rew).all() and torch.isfinite(obs["actor"]).all()
    # The controller sees the same proprioception it was trained on (decoder output as its last action).
    p = controller_proprio(env.scene["robot"], env.scene["robot/imu_lin_vel"], env.scene["robot/imu_ang_vel"],
                           term._target_ids, term.dec)
    assert p.shape == (16, 93) and torch.isfinite(p).all()
    env.close()


@needs
def test_zero_action_follows_the_prior_mean_and_stands():
    """a = 0 gives z = mu_p and no wrist residual: the controller's own default must keep the robot up for 2 s."""
    import mjlab.tasks  # noqa: F401
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.tasks.registry import load_env_cfg

    cfg = load_env_cfg("Picklebot-Latent-Drill3-G1")
    cfg.scene.num_envs = 32
    cfg.actions["ball"].move_prob, cfg.actions["ball"].swing_prob = 0.0, 0.0
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    robot = env.scene["robot"]
    torso = list(robot.body_names).index("torso_link")
    for _ in range(100):
        env.step(torch.zeros(32, 35, device="cuda"))
    assert (robot.data.body_link_pos_w[:, torso, 2] > 0.6).float().mean() > 0.9
    env.close()


def test_return_quality_rewards_balls_sent_over_the_net():
    from picklebot_mj.tasks.return_stand import return_quality

    pos = torch.tensor([[-6.0, 0.0, 0.8]] * 4)
    vel = torch.tensor([[8.0, 0.0, 4.0],    # fast, clears the net (1.04 m at x = 0)
                        [8.0, 0.0, -3.0],   # fast, into the net
                        [-2.0, 0.0, 3.0],   # away from the net
                        [5.0, 0.0, 6.5]])   # slower, high: clears (1.54 m at x = 0)
    q = return_quality(pos, vel)
    assert q[0] == 1.0
    assert q[1] == 0.5
    assert q[2] == 0.0
    assert torch.isclose(q[3], torch.tensor(0.5 * 5.0 / 6.0 + 0.5))


@needs
def test_shaped_task_reads_shaping_before_legal_return():
    import mjlab.tasks  # noqa: F401
    from mjlab.tasks.registry import load_env_cfg

    cfg = load_env_cfg("Picklebot-Latent-Drill3-Shaped-G1")
    keys = list(cfg.rewards)
    assert keys[-1] == "legal_return" and "return_shaping" in keys


def test_low_entropy_variant_changes_only_the_entropy_coefficient():
    import mjlab.tasks  # noqa: F401
    from dataclasses import asdict

    from mjlab.tasks.registry import load_rl_cfg

    base = asdict(load_rl_cfg("Picklebot-Latent-Drill3-Shaped-G1"))
    low = asdict(load_rl_cfg("Picklebot-Latent-Drill3-Shaped-LowEnt-G1"))
    assert low["algorithm"]["entropy_coef"] == 0.001
    low["algorithm"]["entropy_coef"] = base["algorithm"]["entropy_coef"]
    assert low == base


@needs
def test_half_hint_shows_the_hint_on_about_half_the_real_feeds():
    import mjlab.tasks  # noqa: F401
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.tasks.registry import load_env_cfg

    cfg = load_env_cfg("Picklebot-Latent-Drill3-HalfHint-G1")
    assert cfg.actions["ball"].hit_hint and cfg.actions["ball"].hit_hint_prob == 0.5
    cfg.actions["ball"].move_prob, cfg.actions["ball"].swing_prob = 0.0, 0.0  # real-ball feeds only
    cfg.scene.num_envs = 512
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    share = env.action_manager.get_term("ball").hit_hint_on.float().mean().item()
    assert 0.4 < share < 0.6
    env.close()


@needs
def test_forehand_only_hint_puts_backhand_balls_on_the_forehand_side():
    import mjlab.tasks  # noqa: F401
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.tasks.registry import load_env_cfg

    from picklebot_mj.feeds import FeedMix
    from picklebot_mj.tasks.shadow_swing import predict_intercept, stance_spot

    spots = {}
    for task in ("Picklebot-Latent-Drill3-FewHint-G1", "Picklebot-Latent-Drill3-FhHint-G1"):
        cfg = load_env_cfg(task)
        ball = cfg.actions["ball"]
        ball.move_prob, ball.swing_prob, ball.hit_hint_prob = 0.0, 0.0, 1.0
        ball.feed_mix, ball.adaptive_curriculum = FeedMix({"backhand": 1.0}), False
        ball.feed_anchor = "start"
        cfg.events["reset_base"].params["pose_range"] = {"x": (0.0, 0.0), "y": (0.0, 0.0), "yaw": (0.0, 0.0)}
        cfg.scene.num_envs = 64
        env = ManagerBasedRlEnv(cfg, device="cuda")
        env.reset()
        term = env.action_manager.get_term("ball")
        _, yi = predict_intercept(term.ball.pos, term.ball.vel, term.family, "top")
        spots[task] = (stance_spot(term, True)[:, 1] - yi).median().item()  # spot y minus ball y
        env.close()
    assert spots["Picklebot-Latent-Drill3-FewHint-G1"] < 0  # backhand: stand to the ball's right
    assert spots["Picklebot-Latent-Drill3-FhHint-G1"] > 0  # forehand side: stand to the ball's left


@needs
def test_spot_progress_rewards_moving_toward_the_spot_only_when_it_is_to_be_followed():
    import mjlab.tasks  # noqa: F401
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.tasks.registry import load_env_cfg

    from picklebot_mj.tasks.return_stand import spot_progress

    cfg = load_env_cfg("Picklebot-Latent-Drill3-Progress-G1")
    assert list(cfg.rewards)[-1] == "legal_return" and cfg.rewards["spot_progress"].weight == 1.0
    cfg.actions["ball"].move_prob, cfg.actions["ball"].swing_prob = 0.0, 0.0
    cfg.actions["ball"].hit_hint_prob = 0.5
    cfg.scene.num_envs = 64
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    term = env.action_manager.get_term("ball")
    robot = env.scene["robot"]
    term.recover_xy[:] = term.pelvis_xy() + torch.tensor([0.0, 1.0], device="cuda")  # spot 1 m to the left
    v = torch.zeros(64, 6, device="cuda")
    v[:, 1] = 0.6  # moving left, toward the spot
    robot.write_root_link_velocity_to_sim(v)
    env.sim.forward()
    r = spot_progress(env)
    hinted, free = term.hit_hint_on & ~term.hit_done, ~term.hit_hint_on & ~term.hit_done
    assert hinted.any() and free.any()
    assert torch.allclose(r[hinted], torch.full_like(r[hinted], 0.6), atol=0.05)
    assert (r[free] == 0).all()  # un-hinted approach: the ball must be read, no spot pull
    env.close()


@needs
def test_move_mix_keeps_sixty_percent_real_balls():
    import mjlab.tasks  # noqa: F401
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.tasks.registry import load_env_cfg

    cfg = load_env_cfg("Picklebot-Latent-Drill3-MoveMix-G1")
    cfg.scene.num_envs = 2048
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    t = env.action_manager.get_term("ball")
    move, swing = t.drill.move_ep.float().mean().item(), t.shadow.swing_ep.float().mean().item()
    assert abs(move - 0.35) < 0.04 and abs(swing - 0.05) < 0.02 and abs(1 - move - swing - 0.6) < 0.05
    env.close()


@needs
def test_stance_progress_pulls_toward_the_forehand_side_stance_on_unhinted_feeds():
    import mjlab.tasks  # noqa: F401
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.tasks.registry import load_env_cfg

    from picklebot_mj.feeds import FeedMix
    from picklebot_mj.tasks.return_stand import stance_progress

    cfg = load_env_cfg("Picklebot-Latent-Drill3-Footwork-G1")
    assert list(cfg.rewards)[-1] == "legal_return" and "stance_progress" in cfg.rewards
    b = cfg.actions["ball"]
    b.move_prob, b.swing_prob, b.hit_hint_prob, b.adaptive_curriculum = 0.0, 0.0, 0.5, False
    b.feed_mix = FeedMix({"backhand": 1.0})
    cfg.scene.num_envs = 64
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    t = env.action_manager.get_term("ball")
    robot = env.scene["robot"]
    to = t.stance_xy - t.pelvis_xy()
    assert (to[:, 1] > 0.5).float().mean() > 0.9  # backhand ball, forehand-side stance: step left
    v = torch.zeros(64, 6, device="cuda")
    v[:, :2] = 0.5 * to / to.norm(dim=-1, keepdim=True)
    robot.write_root_link_velocity_to_sim(v)
    env.sim.forward()
    r = stance_progress(env)
    free, hinted = ~t.hit_hint_on, t.hit_hint_on
    assert free.any() and hinted.any()
    assert torch.allclose(r[free], torch.full_like(r[free], 0.5), atol=0.05)
    assert (r[hinted] == 0).all()
    env.close()


def test_fall_penalty_variant_adds_only_the_fall_term():
    import mjlab.tasks  # noqa: F401
    from mjlab.tasks.registry import load_env_cfg

    base = load_env_cfg("Picklebot-Latent-Drill3-Footwork-G1")
    pen = load_env_cfg("Picklebot-Latent-Drill3-FallPen-G1")
    assert set(pen.rewards) - set(base.rewards) == {"fall"} and pen.rewards["fall"].weight == -50.0
    assert list(pen.rewards)[-1] == "legal_return"


def test_net_margin_requires_clearance_above_the_tape():
    from picklebot_mj.tasks.return_stand import return_quality

    pos = torch.tensor([[-6.0, 0.0, 0.8]])
    vel = torch.tensor([[8.0, 0.0, 4.0]])  # 1.04 m at x = 0: clears the 0.914 m tape by about 0.09 m
    assert return_quality(pos, vel)[0] == 1.0
    assert return_quality(pos, vel, margin=0.3)[0] == 0.5  # within the margin: speed half only


def test_margin_task_changes_only_the_shaping_margin():
    import mjlab.tasks  # noqa: F401
    from mjlab.tasks.registry import load_env_cfg

    base = load_env_cfg("Picklebot-Latent-Drill3-LP-Top-G1")
    m = load_env_cfg("Picklebot-Latent-Drill3-Margin-G1")
    assert m.rewards["return_shaping"].params == {"margin": 0.3}
    assert set(m.rewards) == set(base.rewards)


@needs
def test_net_clearance_rewards_the_real_crossing_once():
    import mjlab.tasks  # noqa: F401
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.tasks.registry import load_env_cfg

    from picklebot_mj.tasks.return_stand import net_clearance

    cfg = load_env_cfg("Picklebot-Latent-Drill3-NetReal-G1")
    assert list(cfg.rewards)[-1] == "legal_return" and "net_clearance" in cfg.rewards
    cfg.scene.num_envs = 8
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    t = env.action_manager.get_term("ball")
    t.cross_now[:4] = True
    t.cross_clear[:] = torch.tensor([0.6, 0.15, -0.05, 0.3, 0.6, 0.6, 0.6, 0.6], device="cuda")
    r = net_clearance(env, margin=0.3)
    assert torch.allclose(r, torch.tensor([1.0, 0.5, 0.0, 1.0, 0, 0, 0, 0], device="cuda"))
    t.consume_step_events()
    assert not t.cross_now.any()
    env.close()


@needs
def test_prior_nll_is_the_latent_distance_from_the_prior_mean():
    import mjlab.tasks  # noqa: F401
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.tasks.registry import load_env_cfg

    from picklebot_mj.tasks.latent_reach import latent_prior_nll

    cfg = load_env_cfg("Picklebot-Latent-Drill3-Prior-G1")
    assert cfg.rewards["latent_prior"].weight == -0.01 and list(cfg.rewards)[-1] == "legal_return"
    cfg.scene.num_envs = 4
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    a = torch.zeros(4, 35, device="cuda")
    a[1, :32] = 100.0  # saturated: every latent dim at lam * 1 from the prior mean
    a[2, 32:] = 5.0  # wrist residual only: no latent cost
    env.step(a)
    p = latent_prior_nll(env)
    assert torch.allclose(p, torch.tensor([0.0, 32.0, 0.0, 0.0], device="cuda"), atol=1e-4)
    env.close()

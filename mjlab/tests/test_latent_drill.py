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

"""Stage 5B H3: latent action term and the paddle-reach task (picklebot_mj/tasks/latent_reach.py)."""

from pathlib import Path

import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
MOTION = ROOT / "artifacts" / "motion" / "tracking" / "tennis-lafan2.npz"
LATENT = ROOT / "artifacts" / "train" / "latent" / "latent-07" / "latent_10651.pt"
needs = pytest.mark.skipif(not (torch.cuda.is_available() and MOTION.exists() and LATENT.exists()),
                           reason="needs CUDA, the motion file and the H1 latent controller")


@needs
def test_controller_proprio_matches_the_tracking_observation():
    import mjlab.tasks  # noqa: F401
    from mjlab.envs import ManagerBasedRlEnv

    from picklebot_mj.latent import GOAL_DIM
    from picklebot_mj.tasks.latent_reach import controller_proprio
    from picklebot_mj.tasks.tracking import paddle_tracking_env_cfg

    cfg = paddle_tracking_env_cfg(str(MOTION))
    cfg.scene.num_envs = 16
    cfg.observations["actor"].enable_corruption = False
    env = ManagerBasedRlEnv(cfg, device="cuda")
    obs, _ = env.reset()
    term = env.action_manager.get_term("joint_pos")
    for _ in range(5):
        obs, *_ = env.step(0.3 * torch.randn(16, env.action_manager.total_action_dim, device="cuda"))
    mine = controller_proprio(env.scene["robot"], env.scene["robot/imu_lin_vel"], env.scene["robot/imu_ang_vel"],
                              term.target_ids, env.action_manager.action)
    assert torch.allclose(mine, obs["actor"][:, GOAL_DIM:], atol=1e-5)
    env.close()


@needs
def test_reach_task_runs_and_tallies_target_windows():
    import mjlab.tasks  # noqa: F401
    from mjlab.envs import ManagerBasedRlEnv

    from picklebot_mj.tasks.latent_reach import latent_reach_env_cfg

    cfg = latent_reach_env_cfg(str(LATENT), str(MOTION))
    cfg.scene.num_envs = 32
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    assert env.action_manager.total_action_dim == 35
    cmd = env.command_manager.get_term("reach")
    for _ in range(110):  # > one 2 s window at 50 Hz
        obs, rew, *_ = env.step(torch.zeros(32, 35, device="cuda"))
        assert torch.isfinite(rew).all()
    assert cmd.tally["windows"] >= 32
    assert 0 <= cmd.tally["paddle_reached"] <= cmd.tally["windows"]
    assert obs["actor"].shape[1] == 3 + 3 + 3 + 29 + 29 + 35 + 9
    env.close()


@needs
def test_extension_rewards_are_finite_and_progress_has_the_right_sign():
    import mjlab.tasks  # noqa: F401
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.tasks.registry import load_env_cfg

    from picklebot_mj.tasks.latent_reach import latent_action_l2, root_progress

    cfg = load_env_cfg("Picklebot-Latent-Reach-E2-G1")
    cfg.scene.num_envs = 16
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    env.step(torch.ones(16, 35, device="cuda"))
    assert torch.allclose(latent_action_l2(env), torch.full((16,), 32.0, device="cuda"))
    cmd = env.command_manager.get_term("reach")
    robot = env.scene["robot"]
    to = cmd.root_target - robot.data.root_link_pos_w[:, :2]
    p = root_progress(env)
    assert torch.isfinite(p).all() and (p.abs() <= 1.0).all()
    # Moving straight at the target scores positive, away negative (velocity written into the sim state).
    v = torch.zeros(16, 6, device="cuda")
    v[:, :2] = 0.5 * to / to.norm(dim=-1, keepdim=True)
    robot.write_root_link_velocity_to_sim(v)
    env.sim.forward()
    far = to.norm(dim=-1) > 0.05
    assert (root_progress(env)[far] > 0.3).all()
    env.close()

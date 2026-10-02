"""Stage 2 task: registration, build, ball/rules plumbing (GPU) and seed ranges."""

import pytest
import torch

from picklebot_mj import seeds


def test_command_stays_zero():
    """Regression (run return-stand-01): the inherited velocity curriculum widened the command."""
    from picklebot_mj.tasks.return_stand import return_stand_env_cfg

    cfg = return_stand_env_cfg()
    assert "command_vel" not in cfg.curriculum
    r = cfg.commands["twist"].ranges
    assert r.lin_vel_x == (0.0, 0.0) and r.lin_vel_y == (0.0, 0.0) and r.ang_vel_z == (0.0, 0.0)
    assert cfg.commands["twist"].rel_standing_envs == 1.0 and not cfg.commands["twist"].heading_command


def test_rally_end_is_a_time_out_not_a_termination():
    """Regression (run lateral-a01): terminating on rally end taught the policy to avoid ending rallies."""
    from picklebot_mj.tasks.return_stand import EPISODE_S, return_stand_env_cfg

    cfg = return_stand_env_cfg()
    assert cfg.terminations["drill_over"].time_out is True
    assert cfg.terminations["fell_over"].time_out is False  # a fall is still a real failure
    assert cfg.episode_length_s == EPISODE_S >= 4.0


def test_seed_ranges_disjoint():
    seeds.check_disjoint()
    assert min(seeds.FINAL_SEEDS) > max(seeds.DEV_EVAL_SEEDS) > max(seeds.TRAIN_SEEDS)


@pytest.mark.skipif(not torch.cuda.is_available(), reason="needs CUDA (mujoco_warp)")
def test_task_builds_and_runs():
    import mjlab.tasks  # noqa: F401
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.tasks.registry import list_tasks, load_env_cfg

    from picklebot_mj.tasks import TASK_RETURN_STAND

    assert TASK_RETURN_STAND in list_tasks()
    cfg = load_env_cfg(TASK_RETURN_STAND)
    cfg.scene.num_envs = 8
    env = ManagerBasedRlEnv(cfg, device="cuda")
    obs, _ = env.reset()
    term = env.action_manager.get_term("ball")
    assert term.action_dim == 0 and env.action_manager.total_action_dim == 29
    from picklebot_mj.rules import Phase

    p0 = term.ball.pos.clone()
    assert (term.rules.phase == Phase.SERVE_FLIGHT).all()  # receive context: must bounce
    act = torch.zeros(8, 29, device="cuda")
    bounced = torch.zeros(8, dtype=torch.bool, device="cuda")
    for _ in range(45):  # 0.9 s: every feed bounces (flight time <= 0.95 s) unless the env resets
        env.step(act)
        bounced |= term.rules.bounced
    assert not torch.equal(p0, term.ball.pos)
    assert bounced.float().mean() >= 0.5  # the rules engine registers the feed bounce
    bid = env.scene["ball"].indexing.mocap_id
    assert torch.allclose(env.sim.data.mocap_pos[:, bid], term.ball.pos + env.scene.env_origins, atol=1e-5)

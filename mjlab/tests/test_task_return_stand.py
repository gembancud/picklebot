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


def test_rally_end_does_not_end_the_episode():
    """Regressions: lateral-a01 (rally end = termination -> lobs that outlast the episode) and
    lateral-a02 (rally end = bootstrapped time-out -> critic divergence). Now a feeding machine."""
    from picklebot_mj.tasks.return_stand import EPISODE_S, return_stand_env_cfg

    cfg = return_stand_env_cfg()
    assert "drill_over" not in cfg.terminations
    assert cfg.terminations["fell_over"].time_out is False
    assert cfg.episode_length_s == EPISODE_S >= 8.0


@pytest.mark.skipif(not torch.cuda.is_available(), reason="needs CUDA (mujoco_warp)")
def test_feeding_machine_refeeds_after_delay():
    import mjlab.tasks  # noqa: F401
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.tasks.registry import load_env_cfg

    from picklebot_mj.rules import Fault, Phase
    from picklebot_mj.tasks import TASK_RETURN_STAND

    cfg = load_env_cfg(TASK_RETURN_STAND)
    cfg.scene.num_envs = 8
    cfg.actions["ball"].compile_ball = False
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    term = env.action_manager.get_term("ball")
    act = torch.zeros(8, 29, device="cuda")
    env.step(act)
    ep0 = int(term.ep["episodes"])
    term.rules.fail(torch.ones(8, dtype=torch.bool, device="cuda"), torch.zeros(8, dtype=torch.long, device="cuda"),
                    Fault.LOST)  # end every rally now
    env.step(act)  # rally over -> tallied, countdown starts
    assert int(term.ep["episodes"]) - ep0 == 8 and term.tallied.all()
    assert (term.refeed_timer > 0).all()
    for _ in range(int(0.45 / env.step_dt)):
        env.step(act)
    assert int(term.ep["episodes"]) - ep0 == 8  # still waiting (< 0.5 s), nothing double-counted
    for _ in range(int(0.1 / env.step_dt) + 1):
        env.step(act)
    fresh = term.rules.phase == Phase.SERVE_FLIGHT
    assert fresh.float().mean() >= 0.5  # new balls in flight (envs that fell meanwhile were reset instead)
    assert not term.tallied[fresh].any()


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

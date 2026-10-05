"""Stage 5 stance release: no stand-still rewards, walking leg tolerances, foot terms gated on motion."""

import pytest
import torch


def test_free_feet_config():
    from picklebot_mj.tasks import footwork_rewards as fr
    from picklebot_mj.tasks.return_stand import return_stand_env_cfg

    base, free = return_stand_env_cfg(), return_stand_env_cfg(free_feet=True)
    assert "track_linear_velocity" in base.rewards and "track_angular_velocity" in base.rewards
    assert "track_linear_velocity" not in free.rewards and "track_angular_velocity" not in free.rewards
    std = free.rewards["pose"].params["std_standing"]
    assert std[r".*knee.*"] == 0.35 and std[r".*hip_pitch.*"] == 0.3
    assert std[r"right_.*(shoulder|elbow|wrist).*"] == 3.0  # hitting arm still free
    for name, func in fr.GATED.items():
        term = free.rewards[name]
        assert term.func is func and term.weight == base.rewards[name].weight
        assert "command_name" not in term.params and term.params["speed_threshold"] == fr.SPEED_THRESHOLD
    # Balance and ball terms untouched; only the two tracking terms are gone.
    assert set(base.rewards) - set(free.rewards) == {"track_linear_velocity", "track_angular_velocity"}
    assert free.terminations["fell_over"].time_out is False


@pytest.mark.skipif(not torch.cuda.is_available(), reason="needs CUDA (mujoco_warp)")
def test_foot_costs_follow_actual_base_motion():
    """Note: a zero action falls in ~1.25 s in every variant (standing, start box, free feet): rewards do not
    change the dynamics, so stance release is verified on the reward terms, not on a zero-action rollout."""
    from mjlab.envs import ManagerBasedRlEnv

    from picklebot_mj.tasks.footwork_rewards import base_moving
    from picklebot_mj.tasks.return_stand import return_stand_env_cfg

    n = 16
    cfg = return_stand_env_cfg(targets=True, start_box=True, recovery=True, free_feet=True)
    cfg.scene.num_envs = n
    cfg.actions["ball"].compile_ball = False
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    assert base_moving(env).sum() == 0  # at rest after reset: foot-quality costs are off
    # Base motion alone: no remaining reward term is a function of base speed at a fixed pose.
    rm = env.reward_manager
    still = {k: rm._term_cfgs[i].func for i, k in enumerate(rm._term_names)}
    assert not any(k.startswith("track_") for k in still)
    robot = env.scene["robot"]
    vel = torch.zeros(n, 6, device="cuda")
    vel[:, 0] = 0.8  # 0.8 m/s forward
    robot.write_root_link_velocity_to_sim(vel)
    env.sim.forward()  # refresh derived body velocities
    assert base_moving(env).all()  # moving: foot-quality costs now apply to the steps

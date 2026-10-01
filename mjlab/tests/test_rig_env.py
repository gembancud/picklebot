"""GPU smoke test: analytic ball + scripted paddle inside an mjlab env (D-039 integration)."""

import pytest
import torch

pytestmark = pytest.mark.skipif(not torch.cuda.is_available(), reason="needs CUDA (mujoco_warp)")


def test_rig_hits_and_lands_over_net():
    from picklebot_mj import court
    from picklebot_mj.rig_env import PickleballRigEnv, rig_env_cfg

    env = PickleballRigEnv(rig_env_cfg(num_envs=32), device="cuda", seed=1)
    env.reset()
    act = torch.zeros(32, 0, device="cuda")
    for _ in range(int(2 * 3.0 / env.step_dt) + 2):  # two full episodes
        env.step(act)
    s = env.outcome_summary()
    assert s["episodes"] >= 64
    assert s["paddle_hit_rate"] == 1.0
    assert s["landed_rate"] == 1.0
    assert s["in_far_court_rate"] >= 0.75
    assert s["landing_x_min"] > 0.0  # every first landing is past the net
    # Mocap poses written to sim match the analytic state (env 0, court-local + origin).
    bid = env.scene["ball"].indexing.mocap_id
    expected = env.ball.pos[0] + env.scene.env_origins[0]
    assert torch.allclose(env.sim.data.mocap_pos[0, bid], expected, atol=1e-5)
    assert court.HALF_LENGTH > 0

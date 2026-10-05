"""Stage 5 recovery command: observation layout, reward gating, sampling and the error metric."""

import pytest
import torch


def test_recovery_terms_appended_last():
    from picklebot_mj.tasks.return_stand import return_stand_env_cfg

    aim = return_stand_env_cfg(targets=True, start_box=True)
    rec = return_stand_env_cfg(targets=True, start_box=True, recovery=True)
    for g in ("actor", "critic"):
        names = list(rec.observations[g].terms)
        assert names[-2:] == ["court_pose", "recovery"] and names[:-2] == list(aim.observations[g].terms)
    assert rec.actions["ball"].recovery and not aim.actions["ball"].recovery
    r = list(rec.rewards)
    assert "recovery" in r and "recovery" not in aim.rewards
    assert r.index("recovery") < r.index("legal_return")


@pytest.mark.skipif(not torch.cuda.is_available(), reason="needs CUDA (mujoco_warp)")
def test_recovery_reward_gating_sampling_and_metric():
    from mjlab.envs import ManagerBasedRlEnv

    from picklebot_mj.tasks.return_stand import (RECOVERY_BOX, court_pose_obs, recovery_obs, recovery_reward,
                                                 return_stand_env_cfg)

    n = 32
    cfg = return_stand_env_cfg(targets=True, start_box=True, recovery=True)
    cfg.scene.num_envs = n
    cfg.actions["ball"].compile_ball = False
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    act = torch.zeros(n, 29, device="cuda")
    env.step(act)
    t = env.action_manager.get_term("ball")
    # Spots sampled inside the training box, and different across envs.
    (x0, x1), (y0, y1) = RECOVERY_BOX
    assert ((t.recover_xy[:, 0] >= x0) & (t.recover_xy[:, 0] <= x1)).all()
    assert ((t.recover_xy[:, 1] >= y0) & (t.recover_xy[:, 1] <= y1)).all()
    assert float(t.recover_xy[:, 1].std()) > 0.3
    # Never before the hit.
    assert not t.hit_done.any()
    assert torch.equal(recovery_reward(env), torch.zeros(n, device="cuda"))
    # After a hit, standing on the spot pays ~1 and the relative observation is ~0.
    t.recover_xy = t.pelvis_xy().clone()
    t.hit_done[:] = True
    assert torch.allclose(recovery_reward(env), torch.ones(n, device="cuda"), atol=1e-4)
    assert recovery_obs(env).abs().max() < 1e-4
    pose = court_pose_obs(env)
    assert pose.shape == (n, 4) and torch.allclose(pose[:, 2:].norm(dim=-1), torch.ones(n, device="cuda"), atol=1e-4)
    # The metric scores hit feeds at the next launch; misses are not scored.
    t.recover_hist.zero_()
    t.hit_done[n // 2:] = False
    fire = torch.ones(n, dtype=torch.bool, device="cuda")
    t._refeed(fire)
    assert int(t.recover_hist.sum()) == n // 2 and int(t.recover_hist[0]) == n // 2
    assert not t.hit_done.any()  # cleared for the new feed


def test_wide_shaping_is_the_only_f2_change():
    """Run F2 changes only the distance-shaping range (stage5-run-f1.md)."""
    import mjlab.tasks  # noqa: F401
    from mjlab.tasks.registry import load_env_cfg

    from picklebot_mj.tasks import TASK_FOOTWORK, TASK_FOOTWORK_WIDE
    from picklebot_mj.tasks.return_stand import RECOVERY_STD, WIDE_SHAPING_STD

    f1, f2 = load_env_cfg(TASK_FOOTWORK), load_env_cfg(TASK_FOOTWORK_WIDE)
    assert set(f2.rewards) - set(f1.rewards) == {"approach_far"} and set(f1.rewards) <= set(f2.rewards)
    far = f2.rewards["approach_far"]
    assert far.func is f1.rewards["approach_ball"].func and far.params["std"] == WIDE_SHAPING_STD == 1.5
    assert f1.rewards["recovery"].params["std"] == RECOVERY_STD and f2.rewards["recovery"].params["std"] == 1.5
    for k in f1.rewards:
        if k != "recovery":
            assert f1.rewards[k].weight == f2.rewards[k].weight
    for g in ("actor", "critic"):
        assert list(f1.observations[g].terms) == list(f2.observations[g].terms)

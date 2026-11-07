"""D-235: launcher courts inside the drill-reset rally task play the court read's own episodes (GPU)."""
from pathlib import Path

import pytest
import torch

BASE = (Path(__file__).resolve().parents[1] / "artifacts" / "train" / "logs" / "picklebot_return_stand"
        / "2026-10-31_18-24-20_s5c-d1-fw1bS" / "model_32854.pt")
TASK = "Picklebot-Rally22b-FastMove-DrillReset-Launch-G1"


def test_launch_courts_are_off_by_default_and_on_in_the_task():
    import mjlab.tasks  # noqa: F401
    import picklebot_mj.tasks.footwork_specialist as fs
    from mjlab.tasks.registry import load_env_cfg
    assert getattr(load_env_cfg("Picklebot-Latent-Court-Res-G1").actions["ball"], "pair_launch_court_frac", 0.0) == 0.0
    assert getattr(load_env_cfg(fs.TASK_RALLY_FASTMOVE_DR).actions["ball"], "pair_launch_court_frac", 0.0) == 0.0
    cfg = load_env_cfg(TASK)
    b = cfg.actions["ball"]
    assert b.pair_launch_court_frac == 0.25 and b.pair_drill_court_frac == 0.5 and b.pair_drill_reset
    assert cfg.terminations["launch_time_out"].time_out


@pytest.mark.skipif(not torch.cuda.is_available(), reason="needs CUDA")
def test_launch_courts_feed_their_own_robots_and_never_rally(monkeypatch):
    if not BASE.exists():
        pytest.skip("needs the d1 base")
    monkeypatch.setenv("PICKLEBOT_RES_BASE", str(BASE))
    monkeypatch.setenv("PICKLEBOT_LAM_R", "2")
    import mjlab.tasks  # noqa: F401
    import picklebot_mj.tasks.footwork_specialist  # noqa: F401
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.tasks.registry import load_env_cfg
    cfg = load_env_cfg(TASK)
    cfg.scene.num_envs = 64
    b = cfg.actions["ball"]
    b.court_feed_prob, b.recovery_mode, b.refeed_delay_s = 1.0, "fixed", 0.5
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    t = env.action_manager.get_term("ball")
    le, h = t.launch_env, t.pairs.h
    court = torch.arange(64, device=t.device) % h
    assert int(le.sum()) == 16 and bool((le == ((court >= 8) & (court < 16))).all())
    assert bool((t.drill_scale[le] == 0).all()) and bool((t.drill_scale[court < 8] == 2).all())
    assert int(t.pairs.solo.sum()) == 8
    seen = {"lfire": 0, "not_court": 0, "anch": 0, "rec_out": 0, "busy": 0}
    from picklebot_mj.tasks.return_stand import RECOVERY_BOX
    orig = t._refeed

    def refeed(fire):
        seen["lfire"] += int((fire & le).sum())
        orig(fire)
        f = fire & le
        seen["not_court"] += int((f & ~t.court_feed).sum())  # pelvis-anchored court feeds (the court read's feed)
        seen["anch"] += int((f & t._court_anch).sum())
        r = t.recover_xy[f]
        (x0, x1), (y0, y1) = RECOVERY_BOX
        seen["rec_out"] += int(((r[:, 0] < x0) | (r[:, 0] > x1) | (r[:, 1] < y0) | (r[:, 1] > y1)).sum())

    t._refeed = refeed
    act = torch.zeros(env.num_envs, env.action_manager.total_action_dim, device=env.device)
    with torch.inference_mode():
        for _ in range(450):  # 9 s: every launcher robot's first episode has ended
            env.step(act)
            seen["busy"] += int((t.drill.move_ep & le).sum()) + int((t.shadow.swing_ep & le).sum())
    summ = t.launch_summary()["launch_courts"]
    started = t.pairs.started.clone()
    env.close()
    assert summ["envs"] == 16 and summ["episodes_falls"][0] >= 16, summ
    assert seen["lfire"] > 0 and seen["not_court"] == seen["anch"] == seen["rec_out"] == seen["busy"] == 0, seen
    assert summ["other_falls"] >= 0 and summ["step"] > 0, summ
    assert not bool(started[8:16].any())


def test_left_back_task_only_changes_the_move_sector_weights():
    import dataclasses
    import mjlab.tasks  # noqa: F401
    import picklebot_mj.tasks.footwork_specialist as fs
    from mjlab.tasks.registry import load_env_cfg
    a = dataclasses.asdict(load_env_cfg(TASK).actions["ball"])
    b = dataclasses.asdict(load_env_cfg(fs.TASK_RALLY_FASTMOVE_DR_LAUNCH_LB).actions["ball"])
    assert {k for k in a if a[k] != b[k]} == {"move_sector_weights"}
    assert tuple(b["move_sector_weights"]) == (1.0, 1.0, 2.0, 2.0, 2.0, 1.0, 1.0, 1.0)
    assert b["adaptive_curriculum"] is False  # the weights hold during training


def test_left_back3_task_only_changes_the_weights():
    import dataclasses
    import mjlab.tasks  # noqa: F401
    import picklebot_mj.tasks.footwork_specialist as fs
    from mjlab.tasks.registry import load_env_cfg
    a = dataclasses.asdict(load_env_cfg(TASK).actions["ball"])
    b = dataclasses.asdict(load_env_cfg(fs.TASK_RALLY_FASTMOVE_DR_LAUNCH_LB3).actions["ball"])
    assert {k for k in a if a[k] != b[k]} == {"move_sector_weights"}
    assert tuple(b["move_sector_weights"]) == (1.0, 1.0, 3.0, 3.0, 3.0, 1.0, 1.0, 1.0)


def test_half_reset_task_only_changes_the_reset_share():
    import dataclasses
    import mjlab.tasks  # noqa: F401
    import picklebot_mj.tasks.footwork_specialist as fs
    from mjlab.tasks.registry import load_env_cfg
    a = dataclasses.asdict(load_env_cfg(TASK).actions["ball"])
    b = dataclasses.asdict(load_env_cfg(fs.TASK_RALLY_FASTMOVE_DR_LAUNCH_HALF).actions["ball"])
    assert {k for k in a if a[k] != b[k]} == {"pair_drill_reset_frac"}
    assert a["pair_drill_reset_frac"] == 1.0 and b["pair_drill_reset_frac"] == 0.5
    assert getattr(load_env_cfg("Picklebot-Latent-Court-Res-G1").actions["ball"], "pair_drill_reset_frac", 1.0) == 1.0


@pytest.mark.skipif(not torch.cuda.is_available(), reason="needs CUDA")
def test_half_reset_places_only_on_odd_live_courts(monkeypatch):
    if not BASE.exists():
        pytest.skip("needs the d1 base")
    monkeypatch.setenv("PICKLEBOT_RES_BASE", str(BASE))
    monkeypatch.setenv("PICKLEBOT_LAM_R", "2")
    import mjlab.tasks  # noqa: F401
    import picklebot_mj.tasks.footwork_specialist as fs
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.tasks.registry import load_env_cfg
    cfg = load_env_cfg(fs.TASK_RALLY_FASTMOVE_DR_LAUNCH_HALF)
    cfg.scene.num_envs = 64
    b = cfg.actions["ball"]
    b.court_feed_prob, b.recovery_mode, b.refeed_delay_s = 1.0, "fixed", 0.5
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    t = env.action_manager.get_term("ball")
    h = t.pairs.h
    court = torch.arange(h, device=t.device)
    live = (t.drill_scale[:h] == 0) & ~t.pairs.solo
    assert bool((t._reset_court == (live & (court % 2 == 1))).all()) and int(t._reset_court.sum()) == 8
    assert bool((t.pairs.sub == (live & (court % 2 == 0))).all())
    act = torch.zeros(env.num_envs, env.action_manager.total_action_dim, device=env.device)
    with torch.inference_mode():
        for _ in range(900):
            env.step(act)
    s = t.launch_summary()
    sub_n, all_n = sum(s["len_hist_sub"]), int(t.pairs.len_hist_group[0].sum())
    env.close()
    assert s["drill_places"] > 0 and s["drill_places_off"] == 0, s
    assert 0 < sub_n < all_n, (sub_n, all_n)



def test_cap_court_mask_caps_only_masked_courts():
    """D-242: with cap_court set, the rally_cap-th shot ends the rally on masked courts only."""
    from picklebot_mj.pairs import PairCourts
    pc = PairCourts(4, "cpu", handoff="crossing", rally_cap=2)  # courts 0 (envs 0, 2) and 1 (envs 1, 3)
    pc.cap_court = torch.tensor([True, False])
    pc.court_dead[:] = False
    pc.started[:] = True
    z = torch.zeros(4, dtype=torch.bool)
    recv = []
    for cross in ([True, True, False, False], [False, False, True, True], [True, True, False, False]):
        _, r = pc.step(z, z, z, torch.tensor(cross), 0.02, 0.5)
        recv.append(r.clone())
    # shot 1 is handed over on both courts; shot 2 (the cap) only on the uncapped court 1, which rallies on
    assert recv[0].tolist() == [False, False, True, True]
    assert recv[1].tolist() == [False, True, False, False]


@pytest.mark.skipif(not torch.cuda.is_available(), reason="needs CUDA")
def test_cap_reset_only_wires_the_reset_half(monkeypatch):
    if not BASE.exists():
        pytest.skip("needs the d1 base")
    monkeypatch.setenv("PICKLEBOT_RES_BASE", str(BASE))
    monkeypatch.setenv("PICKLEBOT_LAM_R", "2")
    import mjlab.tasks  # noqa: F401
    import picklebot_mj.tasks.footwork_specialist as fs
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.tasks.registry import load_env_cfg
    assert getattr(load_env_cfg(fs.TASK_RALLY_FASTMOVE_DR_LAUNCH_HALF).actions["ball"], "pair_rally_cap_reset_only") is False
    cfg = load_env_cfg(fs.TASK_RALLY_FASTMOVE_DR_LAUNCH_HALF)
    cfg.scene.num_envs = 64
    b = cfg.actions["ball"]
    b.pair_rally_cap, b.pair_rally_cap_reset_only = 8, True
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    t = env.action_manager.get_term("ball")
    ok = bool((t.pairs.cap_court == t._reset_court).all()) and int(t.pairs.cap_court.sum()) == 8
    env.close()
    assert ok

"""D-252: the call-and-set test drill (tasks/call_set.py) and its lines (callset_rule.py)."""
import math
from pathlib import Path

import pytest
import torch

BASE = (Path(__file__).resolve().parents[1] / "artifacts" / "train" / "logs" / "picklebot_return_stand"
        / "2026-10-31_18-24-20_s5c-d1-fw1bS" / "model_32854.pt")


def test_deadline_formula():
    from picklebot_mj.tasks import call_set as cs
    d = torch.tensor([2.0, 3.0, 1.0])
    assert torch.allclose(cs.deadline(d), torch.tensor([1.3, 1.7, 0.9]))
    assert torch.allclose(cs.deadline(d, 1.5), 0.5 + d / 1.5)


def test_cells_and_contact_side():
    from picklebot_mj.tasks import call_set as cs
    ct = torch.tensor([0, 1, 2, 3])
    fh = torch.tensor([True, False, True, False])
    early = torch.tensor([False, True, False, True])
    assert cs.cell_index(ct, fh, early).tolist() == [0, 7, 8, 15]
    S = torch.zeros(2, 2)
    C = cs.contact_point(S, torch.tensor([True, False]))
    assert C[0, 1] < 0 < C[1, 1]  # forehand on the robot's right (-y), backhand on its left
    assert (C[:, 0] > 0).all()  # ahead of the stance spot (toward the net)


def test_ball_path_hits_contact_at_T_after_one_bounce():
    from picklebot_mj.ball import BALL_RADIUS
    from picklebot_mj.tasks import call_set as cs
    C = torch.tensor([[-6.0, 1.0, 0.9], [-4.0, -2.0, 0.9]])
    L = torch.tensor([[3.0, 0.5, 1.0], [5.0, -1.0, 1.0]])
    T = torch.tensor([1.3, 0.9])
    p, v = cs.ball_path(L, C, T, T)
    assert torch.allclose(p, C, atol=1e-4)
    p0, _ = cs.ball_path(L, C, T, torch.zeros(2))
    assert torch.allclose(p0, L, atol=1e-5)
    tb = T - cs.AFTER_BOUNCE_S
    pb, _ = cs.ball_path(L, C, T, tb - 1e-4)
    assert torch.allclose(pb[:, 2], torch.full((2,), BALL_RADIUS), atol=2e-3)
    es = torch.linspace(0, 1, 50)
    for i in range(2):  # never below the court
        z = torch.stack([cs.ball_path(L[i:i + 1], C[i:i + 1], T[i:i + 1], e.view(1) * T[i])[0][0, 2] for e in es])
        assert (z >= BALL_RADIUS - 1e-3).all()


def test_judge_each_condition_fails_alone():
    from picklebot_mj.tasks import call_set as cs
    good = dict(speed_avg=torch.tensor([0.1]), feet_z=torch.tensor([[0.05, 0.06]]), tilt=torch.tensor([0.1]),
                paddle_fwd=torch.tensor([0.4]), paddle_lat=torch.tensor([-0.2]), paddle_z=torch.tensor([1.0]),
                ball_lat=torch.tensor([-0.5]), ball_dist=torch.tensor([0.6]), forehand=torch.tensor([True]))
    s, r, h = cs.judge(**good)
    assert bool(s) and bool(r) and bool(h)
    for k, bad, which in (("speed_avg", 0.4, 0), ("feet_z", [[0.05, 0.2]], 0), ("tilt", math.radians(25), 0),
                          ("paddle_z", 1.3, 1), ("paddle_fwd", 0.6, 1), ("paddle_lat", 0.0, 1),
                          ("ball_dist", 0.9, 2), ("ball_lat", 0.3, 2)):
        x = dict(good)
        x[k] = torch.tensor(bad if isinstance(bad, list) else [bad])
        out = cs.judge(**x)
        assert [bool(o) for o in out] == [i != which for i in range(3)], k
    x = dict(good, forehand=torch.tensor([False]))  # the backhand mirror: the same pose is on the wrong side
    s, r, h = cs.judge(**x)
    assert bool(s) and not bool(r) and not bool(h)
    x = dict(good, forehand=torch.tensor([False]), paddle_lat=torch.tensor([0.2]), ball_lat=torch.tensor([0.5]))
    assert all(bool(o) for o in cs.judge(**x))


def test_rule_read_and_target_lines():
    from picklebot_mj import callset_rule as cr
    n = 16
    c = {k: [0] * n for k in ("issued", "judged", "passed", "set", "ready", "reach", "fell", "censored", "reversed",
                              "start_n", "ladder_n")}
    c["start_sum"] = [0.0] * n
    for i in range(n):
        c["issued"][i] = c["judged"][i] = 300
        c["passed"][i] = 255 if i < 12 else 200  # 'short' (type 3) at 0.667
        c["set"][i] = c["ready"][i] = c["reach"][i] = 280
        c["start_n"][i], c["start_sum"][i] = 300, 150.0
        c["ladder_n"][i] = 300
    c["ladder"] = [[100] * n, [200] * n, [250] * n]
    c["chains"] = [800, 790]
    c["meta"] = {"paces": [1.5, 2.0, 2.5]}
    r = cr.read(c)
    assert r["judged"] == 4800 and abs(r["start_s"] - 0.5) < 1e-9
    ok, lines = cr.target_lines(r)
    assert not ok and lines[-1] == "TARGET-LINES NOT MET"  # short below 0.70
    c["passed"] = [255] * n
    ok, _ = cr.target_lines(cr.read(c))
    assert ok  # 0.85, Wilson low about 0.84
    lo, hi = cr.wilson(80, 100)
    assert 0.70 < lo < 0.80 < hi
    assert cr.pool([c, c])["judged"][0] == 600


def test_task_only_swaps_the_drill():
    import dataclasses
    import mjlab.tasks  # noqa: F401
    import picklebot_mj.tasks.footwork_specialist as fs
    from mjlab.tasks.registry import load_env_cfg
    a = dataclasses.asdict(load_env_cfg(fs.TASK_FW_RALLY_MEASURE).actions["ball"])
    b = dataclasses.asdict(load_env_cfg(fs.TASK_FW_CALLSET).actions["ball"])
    assert {k for k in a if a[k] != b[k]} == {"call_set"} and b["call_set"] is True


@pytest.mark.skipif(not torch.cuda.is_available(), reason="needs CUDA")
def test_call_drill_runs_on_the_rally_composite(monkeypatch):
    if not BASE.exists():
        pytest.skip("needs the d1 base")
    monkeypatch.setenv("PICKLEBOT_RES_BASE", str(BASE))
    monkeypatch.setenv("PICKLEBOT_LAM_R", "2")
    import mjlab.tasks  # noqa: F401
    import picklebot_mj.tasks.footwork_specialist as fs
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.tasks.registry import load_env_cfg
    from picklebot_mj import callset_rule as cr
    from picklebot_mj.tasks.call_set import CallSetDrill
    cfg = load_env_cfg(fs.TASK_FW_CALLSET)
    cfg.scene.num_envs = 64
    cfg.actions["ball"].move_prob = 1.0
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    t = env.action_manager.get_term("ball")
    dr = t.drill
    assert isinstance(dr, CallSetDrill)
    act = torch.zeros(env.num_envs, env.action_manager.total_action_dim, device=env.device)
    seen_fly = False
    with torch.inference_mode():
        for i in range(1500):  # 30 s
            env.step(act)
            if i % 50 == 0 and bool(dr.pending.any()):
                z = t.ball.pos[dr.pending, 2]
                seen_fly |= bool((z > 0.3).any())
    c = dr.counters()
    env.close()
    r = cr.read(c)
    assert sum(c["issued"]) > 200 and r["judged"] > 100, (sum(c["issued"]), r["judged"])
    assert seen_fly
    assert 0.15 < r["early_share"] < 0.5, r["early_share"]
    shares = [v["judged"] / r["judged"] for v in r["types"].values()]
    assert min(shares) > 0.1, shares
    assert sum(c["reversed"]) < sum(c["issued"])

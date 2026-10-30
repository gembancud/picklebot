"""Body-speed test (tasks/body_speed.py FastMoveDrill, picklebot_mj/bodyspeed_rule.py, task Teacher-Move-Fast25).
CPU only: the drill runs against test_agility's fake term."""

import dataclasses
import os
import sys

import torch

sys.path.insert(0, os.path.dirname(__file__))
from test_agility import FakeTerm  # noqa: E402

from picklebot_mj import bodyspeed_rule as bsr  # noqa: E402

BOX = ((-10.4, -2.4), (-5.5, 5.5))


def _drill(n=256, **kw):
    from picklebot_mj.tasks.body_speed import FastMoveDrill
    t = FakeTerm(n, xy=(-6.4, 0.0))
    dr = FastMoveDrill(t, 1.0, seed=5, cmd_max_speed=2.5, dist_range=(3.0, 5.0), spot_box=BOX, **kw)
    dr.reset(torch.arange(n))
    return t, dr


def test_command_cap_gain_and_braking_radius():
    from picklebot_mj.tasks import move_drill as md
    t, dr = _drill(4)
    assert abs(dr.gain - 3.0) < 1e-9 and abs(dr.cap / dr.gain - md.CMD_MAX_SPEED / md.CMD_GAIN) < 1e-9
    for d, want in ((4.0, 2.5), (0.5, 1.5), (0.1, 0.3)):
        t.recover_xy = torch.tensor([[-6.4 + d, 0.0]] * 4)
        v, wz = dr.command()
        assert torch.allclose(v.norm(dim=-1), torch.full((4,), want), atol=1e-5)
        assert torch.allclose(wz, torch.zeros(4))


def test_spots_are_3_to_5_m_inside_the_wide_box():
    t, dr = _drill(512)
    d = (t.recover_xy - t.pelvis_xy()).norm(dim=-1)
    assert (d <= 5.0 + 1e-4).all() and (d >= 2.99).float().mean() > 0.95
    lo, hi = torch.tensor([BOX[0][0], BOX[1][0]]), torch.tensor([BOX[0][1], BOX[1][1]])
    assert ((t.recover_xy >= lo - 1e-5) & (t.recover_xy <= hi + 1e-5)).all()
    assert set(dr.sector.tolist()) == set(range(8)) and dr.live.all()


def test_sustained_speed_peak_booking_falls_and_censoring():
    n = 8
    t, dr = _drill(n)
    t.recover_xy = torch.tensor([[-2.4, 0.0]] * n)  # 4 m toward the net
    data = t._entity.data
    data.root_link_lin_vel_w[:, 0] = torch.tensor([2.0, 2.0, 1.0, 1.0, 0.0, 0.0, 2.0, 2.0])
    for _ in range(4 * 60):  # 60 control steps (1.2 s) at constant speed
        dr.update(0.005)
    assert dr.cnt.tolist() == [60] * n and torch.allclose(dr.best[:6], torch.tensor([2.0, 2.0, 1.0, 1.0, 0.0, 0.0]),
                                                          atol=1e-4)
    # envs 0-5 time out (booked); 6 falls, 7 is censored by the episode limit
    dr.limit[:6] = 0.0
    dr.update(0.005)
    c = dr.counters()
    assert sum(c["booked"]) == 6 and sum(c["timed_out"]) == 6
    h = torch.tensor(c["best_hist"]).sum(0)
    assert int(h[20]) + int(h[19]) == 2 and int(h[10]) + int(h[9]) == 2 and int(h[0]) == 2
    p = torch.tensor(c["peak_hist"]).sum(0)
    assert int(p[20]) + int(p[19]) == 2
    t._env.common_step_counter = 10
    t.fell[:] = torch.tensor([False] * 6 + [True, False])
    dr.reset(torch.tensor([6, 7]))
    c = dr.counters()
    assert sum(c["fell"]) == 1 and sum(c["censored"]) == 1 and sum(c["booked"]) == 6


def _counters(sp, arrival=0.95, cen=0):
    c = {k: [0] * 8 for k in ("arrived", "timed_out", "fell", "censored", "booked", "issued", "ready")}
    c["best_hist"] = [[0] * 50 for _ in range(8)]
    c["peak_hist"] = [[0] * 50 for _ in range(8)]
    for i in range(8):
        c["arrived"][i] = round(100 * arrival)
        c["timed_out"][i] = 100 - c["arrived"][i]
        c["censored"][i] = cen
        c["booked"][i] = 100
        c["best_hist"][i][int(round(sp[i] / 0.1))] = 100
    return c


def test_rule_routes():
    ok = [2.2, 2.0, 2.0, 1.9, 1.9, 1.9, 2.0, 2.0]
    assert bsr.route(_counters(ok), 3.0, [])["verdict"] == "BODY-OK"
    assert bsr.route(_counters(ok), 5.0, [])["verdict"] == "MIXED"  # falls
    assert bsr.route(_counters(ok, arrival=0.85), 3.0, [])["verdict"] == "MIXED"
    lim = [2.2, 1.5, 1.2, 1.0, 1.0, 1.0, 1.5, 1.5]
    assert bsr.route(_counters(lim), 3.0, [])["verdict"] == "BODY-LIMIT"
    assert bsr.route(_counters([2.2, 1.5, 1.5, 1.0, 1.0, 1.0, 1.5, 1.5]), 3.0, [])["verdict"] == "MIXED"
    assert bsr.route(_counters([1.6] + ok[1:]), 3.0, [])["verdict"] == "VOID"  # positive control
    assert bsr.route(_counters(ok, cen=20), 3.0, [])["verdict"] == "VOID"  # 20 / 120 censored
    r = bsr.route(_counters(ok), 3.0, ["move_cmd_max_speed"])
    assert r["verdict"] == "VOID" and len(r["lines"]) == 10 and all("PASS" in x or "FAIL" in x for x in r["lines"])
    s = bsr.sectors(_counters(ok))
    assert abs(s[4]["sustained_p50"] - 1.95) < 1e-6 and s[0]["arrival"] == 0.95


def test_fast25_task_differs_from_teacher_move_only_in_the_drill_fields():
    import mjlab.tasks  # noqa: F401
    from mjlab.tasks.registry import load_env_cfg, load_rl_cfg, load_runner_cls

    import picklebot_mj.tasks.agility as ag
    for play in (False, True):
        src, a = load_env_cfg(ag.SRC_TEACHER, play=play), load_env_cfg(ag.TASK_TEACHER_MOVE_FAST25, play=play)
        sb, ab = src.actions["ball"], a.actions["ball"]
        assert [f.name for f in dataclasses.fields(sb) if getattr(sb, f.name) != getattr(ab, f.name)] == []
        extra = {f.name for f in dataclasses.fields(ab)} - {f.name for f in dataclasses.fields(sb)}
        changed = sorted(k for k in extra if getattr(ab, k) != getattr(ag.AgilityBallActionCfg, k, None))
        assert changed == ["move_cmd_max_speed", "move_dist_range", "move_spot_box"], changed
        assert ab.move_cmd_max_speed == 2.5 and ab.move_dist_range == (3.0, 5.0) and ab.move_prob == 1.0
        assert [k for k in src.actions if k != "ball" and src.actions[k] != a.actions[k]] == []
        for g in src.observations:
            assert list(src.observations[g].terms) == list(a.observations[g].terms)
        assert [k for k in src.rewards if src.rewards[k].func is not a.rewards[k].func
                or src.rewards[k].weight != a.rewards[k].weight or src.rewards[k].params != a.rewards[k].params] == []
        assert list(src.terminations) == list(a.terminations) and src.decimation == a.decimation
    assert load_env_cfg(ag.SRC_TEACHER).episode_length_s == 8.0
    assert load_env_cfg(ag.TASK_TEACHER_MOVE_FAST25).episode_length_s == 60.0
    assert load_env_cfg(ag.TASK_TEACHER_MOVE_FAST25, play=True).episode_length_s == load_env_cfg(ag.SRC_TEACHER, play=True).episode_length_s
    assert load_runner_cls(ag.TASK_TEACHER_MOVE_FAST25) is load_runner_cls(ag.SRC_TEACHER)
    assert load_rl_cfg(ag.TASK_TEACHER_MOVE_FAST25) == load_rl_cfg(ag.SRC_TEACHER)

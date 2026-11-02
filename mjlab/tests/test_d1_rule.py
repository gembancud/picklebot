from picklebot_mj import d1_rule as dr
from picklebot_mj.bodyspeed_rule import SPEED_BIN


def _drill(speed, first_s=1.0, falls=0, arrived=100, censored=0):
    n_bins = 50
    hist = [[0] * n_bins for _ in range(8)]
    for i in range(8):
        hist[i][int(round(speed[i] / SPEED_BIN))] = 10
    fs = [[0] * 80 for _ in range(8)]
    for i in range(8):
        fs[i][int(first_s / 0.05)] = 10
    c = {"arrived": [arrived] * 8, "timed_out": [0] * 8, "fell": [falls] * 8, "censored": [censored] * 8,
         "booked": [10] * 8, "best_hist": hist, "peak_hist": hist, "first_step_hist": fs, "first_step_bin_s": 0.05,
         "settled": [50] * 8}
    return {"move_drill": {"footwork": c}, "robot_falls": falls * 8, "envs": 1000, "sim_seconds": 100}


def test_teacher_check():
    fast, slow = _drill([2.0] * 8), _drill([1.2] * 8)
    assert dr.teacher_check(fast, slow)[0] == "TEACHER-OK"
    assert dr.teacher_check(_drill([1.5] * 8), slow)[0] == "TEACHER-SLOW"  # under 1.6
    assert dr.teacher_check(_drill([1.7] * 8), _drill([1.6] * 8))[0] == "TEACHER-SLOW"  # gain under 0.3


def test_kick_kill():
    rows = [{"mse_move": 0.05, "mse_hit": 0.0009}] * 359
    assert dr.kick_kill(rows) is None
    assert dr.kick_kill(rows + rows[:1])[0] == "CONTINUE"
    assert dr.kick_kill([{"mse_move": 0.2, "mse_hit": 0.0009}] * 360)[0] == "KILL-NO-FIT"
    assert dr.kick_kill([{"mse_move": 0.05, "mse_hit": 0.002}] * 360)[0] == "KILL-HIT-INTERFERE"


def test_agility_verdict():
    spec = [{"sustained_p50": 2.0}] * 8
    parent = _drill([1.3] * 8, first_s=1.2, falls=1)
    v, _ = dr.agility_verdict(_drill([1.8] * 8, first_s=1.0, falls=1), parent, spec)
    assert v == "AGILE"
    assert dr.agility_verdict(_drill([1.8] * 8, first_s=1.5, falls=1), parent, spec)[0] == "MIXED"  # slower off the mark
    assert dr.agility_verdict(_drill([1.3] * 8, falls=1), parent, spec)[0] == "CAP-HELD"
    assert dr.agility_verdict(_drill([1.8] * 8, falls=3), parent, spec)[0] == "INVALID"


def test_retention_and_base():
    p = {"main": 0.80, "cells": 42, "families": {"a": 0.9, "b": 0.8}, "style": 4.0, "falls_court": 0.036, "falls_move": 0.0099}
    ok = dict(p, main=0.785, cells=40, families={"a": 0.86, "b": 0.8}, style=4.15, falls_court=0.046, falls_move=0.01)
    assert dr.retention(ok, p)[0] == "RETAINS"
    for k, v in (("main", 0.779), ("cells", 39), ("families", {"a": 0.84, "b": 0.8}), ("style", 4.16),
                 ("falls_court", 0.047), ("falls_move", 0.011)):
        assert dr.retention(dict(ok, **{k: v}), p)[0] == "REJECTED", k
    assert dr.base_verdict("AGILE", "RETAINS") == "BASE-PASS"
    assert dr.base_verdict("MIXED", "RETAINS") == "BASE-PASS"
    assert dr.base_verdict("MIXED", "REJECTED") == "REJECTED"
    assert dr.base_verdict("CAP-HELD", "RETAINS") == "CAP-HELD"


def test_premise_check():
    walker = _drill([0.8] * 8, first_s=1.75)
    assert dr.premise_check(_drill([1.0] * 8, first_s=1.4), walker)[0] == "PREMISE-OK"
    assert dr.premise_check(_drill([1.0] * 8, first_s=1.6), walker)[0] == "PREMISE-FAIL"  # only 0.15 s quicker
    assert dr.premise_check(_drill([1.0] * 8, first_s=1.4, censored=30), walker)[0] == "PREMISE-FAIL"  # validity


def test_stage2_kill_lines():
    """D-194: the literal reference (22b 30100-30199) never kills 22b's own continuation from model_30200 (every
    20-iteration window of 30201-30600); synthetic hitting / falls breaches do."""
    import os
    log = "artifacts/train/rally-22b-readcfg.log"
    assert dr.s2_window_verdict(1.6, 0.70, 1.574, 0.7549) == "KILL-NO-HIT"
    assert dr.s2_window_verdict(3.2, 0.76, 1.574, 0.7549) == "KILL-UNSTABLE"
    assert dr.s2_window_verdict(3.1, 0.71, 1.574, 0.7549) == "CONTINUE"
    if not os.path.exists(log):  # git-ignored training log
        import pytest
        pytest.skip("22b training log not present")
    b = dr.log_blocks(log)
    f0, l0 = dr.window_stats(b, dr.S2_REF_ITERS, 12288)
    assert abs(f0 - 1.574) < 0.01 and abs(l0 - 0.7549) < 0.001
    for lo in range(30201, 30600, 20):
        f1, l1 = dr.window_stats(b, range(lo, lo + 20), 12288)
        assert dr.s2_window_verdict(f1, l1, f0, l0) == "CONTINUE", (lo, f1, l1)


def test_stage3_speed_lines():
    spec = [{"sustained_p50": 2.0}] * 8
    z = _drill([1.6] * 8, first_s=1.3, falls=1)
    assert dr.s3_speed_kill(_drill([1.5] * 8, falls=1), z)[0] == "CONTINUE"
    assert dr.s3_speed_kill(_drill([1.4] * 8, falls=1), z)[0] == "KILL-SLOWED"
    assert dr.s3_speed_kill(_drill([1.6] * 8, falls=3), z)[0] == "KILL-NO-ARRIVE"
    assert dr.s3_agility_kept(_drill([1.6] * 8, first_s=1.3), z, spec)[0] == "AGILE-KEPT"
    assert dr.s3_agility_kept(_drill([1.5] * 8, first_s=1.3), z, spec)[0] == "SPEED-LOST"  # R_LB 0.75 < 0.80 - 0.03
    assert dr.s3_agility_kept(_drill([1.6] * 8, first_s=1.5), z, spec)[0] == "SPEED-LOST"  # first step 0.2 s slower


def test_stage4_dose_events_and_verdicts():
    rows = [{"step": 0, "ready": [0.0, 0, 0, 0.0]}, {"step": 480, "ready": [0.1 * 2000, 2000, 0, 0.01 * 2000]}]  # mean 0.1
    rows += [{"step": 340 * 24, "ready": [400.0, 4000, 0, 40.0]},
             {"step": 360 * 24, "ready": [400.0 + 0.3 * 2000, 6000, 0, 40.0 + 0.09 * 2000]}]
    assert dr.s4_dose_kill(rows)[0] == "CONTINUE"  # 0.3 per event late vs 0.1 early
    flat = rows[:3] + [{"step": 360 * 24, "ready": [400.0 + 0.1 * 2000, 6000, 0, 40.0 + 0.01 * 2000]}]
    assert dr.s4_dose_kill(flat)[0] == "KILL-NO-DOSE"
    par = [{"step": 100 * 24, "feeder": 0}, {"step": 300 * 24, "feeder": 1000}]
    assert dr.s4_events_kill([{"step": 100 * 24, "feeder": 0}, {"step": 300 * 24, "feeder": 1090}], par)[0] == "CONTINUE"
    assert dr.s4_events_kill([{"step": 100 * 24, "feeder": 0}, {"step": 300 * 24, "feeder": 1200}], par)[0] == "KILL-EVENTS"
    v = dr.s4_verdict
    assert v(False, True, True, True, None, True, True, True, True) == "READY-PASS"
    assert v(False, True, True, True, False, True, True, True, True) == "READY-TIME"
    assert v(False, True, True, True, True, False, False, True, True) == "READY-F"
    assert v(False, True, False, True, True, True, True, True, True) == "NO-DOSE"
    assert v(False, True, True, False, None, False, False, True, True) == "READY-FAIL"
    assert v(True, True, True, True, True, True, True, True, True) == "KILL"


def test_stage4_windows_follow_the_resumed_step_counter():
    start = 31399
    off = start * 24
    rows = [{"step": off, "ready": [0.0, 0, 0, 0.0]}, {"step": off + 480, "ready": [200.0, 2000, 0, 20.0]}]
    rows += [{"step": off + 340 * 24, "ready": [400.0, 4000, 0, 40.0]}, {"step": off + 360 * 24, "ready": [1000.0, 6000, 0, 220.0]}]
    assert dr.s4_dose_kill(rows, start)[0] == "CONTINUE"
    cp = [{"step": off + 100 * 24, "feeder": 0}, {"step": off + 300 * 24, "feeder": 1000}]
    pp = [{"step": 30200 * 24 + 100 * 24, "feeder": 0}, {"step": 30200 * 24 + 300 * 24, "feeder": 1000}]
    assert dr.s4_events_kill(cp, pp, start, 30200)[0] == "CONTINUE"


def test_windows_use_existing_rows_and_report_no_data():
    """D-200 addendum: rows at +21, +31, ... (as d1s4's ready log) give a +1-20 window from the first rows that exist; a
    window with too few events is NO-DATA, never a kill."""
    start = 31399
    off = start * 24
    rows = [{"step": off + it * 24, "ready": [0.3 * 1500 * k, 1500 * k, 0, 0.09 * 1500 * k]} for k, it in enumerate(range(21, 400, 10), 1)]
    v, _ = dr.s4_dose_kill(rows, start)
    assert v == "KILL-NO-DOSE"  # flat mean 0.3: windows found from existing rows, the line itself fails
    few = [{"step": off + it * 24, "ready": [0.3 * 10 * k, 10 * k, 0, 0.09 * 10 * k]} for k, it in enumerate(range(21, 400, 10), 1)]
    assert dr.s4_dose_kill(few, start)[0] == "NO-DATA"
    cp = [{"step": off + it * 24, "feeder": 10 * it} for it in (101, 201, 301, 401)]
    pp = [{"step": 30200 * 24 + it * 24, "feeder": 10 * it} for it in (100, 200, 300)]
    assert dr.s4_events_kill(cp, pp, start, 30200)[0] == "CONTINUE"
    assert dr.s4_events_kill([], pp, start, 30200)[0] == "NO-DATA"


def test_stage5_share_bin_and_verdicts(tmp_path):
    import json
    start, pstart = 31399, 30200
    cr = [{"step": (start + it) * 24, "split": [[3000 * k, 7000 * k], [0, 0]]} for k, it in enumerate((101, 201, 301, 401))]
    pr = [{"step": (pstart + it) * 24, "split": [[2000 * k, 8000 * k], [0, 0]]} for k, it in enumerate((100, 200, 300))]
    assert dr.s5_share_kill(cr, pr, start, pstart)[0] == "CONTINUE"  # 0.30 vs 0.20
    low = [{"step": r["step"], "split": [[2100 * k, 7900 * k], [0, 0]]} for k, r in enumerate(cr)]
    assert dr.s5_share_kill(low, pr, start, pstart)[0] == "KILL-NO-SHARE"
    assert dr.s5_share_kill([], pr, start, pstart)[0] == "NO-DATA"

    def log(path, legal_rate):
        with open(path, "w") as f:
            for k in range(5):
                f.write(json.dumps({"step": 240 * k, "launch": {"outcome_feeds_legal": [[300 * k, int(300 * k * legal_rate)], [0, 0], [0, 0]]}}) + "\n")
    log(tmp_path / "c.jsonl", 0.75)
    log(tmp_path / "p.jsonl", 0.65)
    assert dr.f_bin(str(tmp_path / "c.jsonl"), str(tmp_path / "p.jsonl"))[0]
    log(tmp_path / "c.jsonl", 0.68)
    assert not dr.f_bin(str(tmp_path / "c.jsonl"), str(tmp_path / "p.jsonl"))[0]
    v = dr.s5_verdict
    assert v(True, False, None, True, True, True, True, True, True) == "MIX"
    assert v(True, True, False, True, True, True, True, True, True) == "MORE-TIME"
    assert v(True, True, None, True, True, True, True, True, True) == "CAP-PASS"
    assert v(True, True, True, False, False, True, True, True, True) == "CAP-F"
    assert v(False, True, None, False, False, True, True, True, True) == "CAP-FAIL"


def test_stage6_farm_dose_and_verdicts(tmp_path):
    import json
    start, pstart = 31399, 30200
    cr = [{"step": (start + it) * 24, "rallies": 10000 * k, "shots": 17000 * k} for k, it in enumerate((101, 201, 301, 401))]
    pr = [{"step": (pstart + it) * 24, "rallies": 10000 * k, "shots": 18000 * k} for k, it in enumerate((100, 200, 300))]
    assert dr.s6_farm_kill(cr, pr, start, pstart)[0] == "CONTINUE"  # 1.7 vs 1.8 (>= 1.62)
    short = [{"step": r["step"], "rallies": r["rallies"], "shots": 15000 * k} for k, r in enumerate(cr)]
    assert dr.s6_farm_kill(short, pr, start, pstart)[0] == "KILL-FARM"  # 1.5 < 1.62
    assert dr.s6_farm_kill([], pr, start, pstart)[0] == "NO-DATA"
    var = lambda v, d: {"pelvis_speed": {"p50": v}, "recover_dist": {"p50": d}}  # noqa: E731
    assert dr.s6_dose(var(0.20, 0.9), var(0.28, 0.9))[0]
    assert dr.s6_dose(var(0.28, 0.75), var(0.28, 0.9))[0]
    assert not dr.s6_dose(var(0.25, 0.85), var(0.28, 0.9))[0]
    assert not dr.s6_dose(var(None, 0.5), var(0.28, 0.9))[0]
    p = tmp_path / "parked.jsonl"
    p.write_text(json.dumps({"step": 240, "parked": [20.0, 40.0, 100.0, 12.0]}) + "\n")
    assert "paid steps 40 of 100" in dr.parked_paid(str(p))
    v = dr.s6_verdict
    assert v(False, True, True, True, None, True, True, True, True, True, True) == "NO-DOSE"
    assert v(True, False, True, True, None, True, True, True, True, True, True) == "GUARD-BREACH"
    assert v(True, True, True, False, None, True, True, True, True, True, True) == "MIX"
    assert v(True, True, True, True, False, True, True, True, True, True, True) == "MORE-TIME"
    assert v(True, True, True, True, None, True, True, True, True, True, True) == "PARK-PASS"
    assert v(True, True, True, True, None, False, False, True, True, True, True) == "PARK-F"
    assert v(True, True, False, True, None, False, False, True, True, True, True) == "PARK-FAIL"


def test_stage7_use_and_verdicts():
    var = lambda v, d: {"pelvis_speed": {"p50": v}, "recover_dist": {"p50": d}}  # noqa: E731
    parent, child = var(0.28, 0.90), var(0.20, 0.88)  # DOSE on speed only
    assert dr.s7_use(child, parent, var(0.25, 0.80))[0]  # takes back 0.05 / 0.08 of the speed gain
    assert not dr.s7_use(child, parent, var(0.22, 0.95))[0]  # 0.25 of it; distance had no DOSE
    assert not dr.s7_use(var(0.27, 0.9), parent, var(0.28, 0.9))[0]  # no DOSE at all
    v = dr.s7_verdict
    assert v(False, True, True, True, True, None, True, True, True, True, True, True) == "NO-DOSE"
    assert v(True, False, True, True, True, None, True, True, True, True, True, True) == "NO-USE"
    assert v(True, True, False, True, True, None, True, True, True, True, True, True) == "GUARD-BREACH"
    assert v(True, True, True, True, True, None, True, True, True, True, True, True) == "OBS-PASS"
    assert v(True, True, True, True, True, None, False, False, True, True, True, True) == "OBS-F"
    assert v(True, True, True, False, True, None, False, False, True, True, True, True) == "OBS-FAIL"


def test_open_hazards_reproduce_p5_open():
    import json
    import os
    import sys
    path = "results/d1s6-parent-pairs.json"
    if not os.path.exists(path):
        return
    sys.path.insert(0, "scripts")
    import rally_check as rc
    p = json.load(open(path))["pairs"]
    hz = dr.open_hazards(p)
    assert abs(hz[0] - 0.383) < 0.002 and abs(hz[1] - 0.287) < 0.002
    surv = 1.0
    for x in hz:
        surv *= 1 - x
    assert abs(surv - rc.p5_open(p)[0]) < 0.002


def test_diag68_matched_failure_and_route_shapes():
    # k = 1 fails 0.5 in bin 0 and 0.1 in bin 1; k >= 3 balls sit 10 / 90 -> matched 0.14
    assert abs(dr.matched_failure([100, 100], [50, 90], [10, 90]) - 0.14) < 1e-9
    assert dr.matched_failure([0, 0], [0, 0], [5, 5]) is None
    from picklebot_mj import ballidx_rule as br
    from picklebot_mj.tasks.ball_index import SPLIT_VARS
    import random
    rnd = random.Random(0)
    rows = br.N_KBINS * 40 * 2  # groups x k bins x distance bins
    c = {"split": {}, "split_legal": {}}
    for name, lo, w, nb in SPLIT_VARS:
        h = [[0] * (nb + 1) for _ in range(rows)]
        lg = [[0] * (nb + 1) for _ in range(rows)]
        for k in range(br.N_KBINS):
            for d in range(*br.MATCHED_BAND):
                r = k * 40 + d
                for b in range(nb):
                    n = rnd.randint(5, 20)
                    fail = 0.3 if k == 0 else 0.03
                    h[r][b] = n
                    lg[r][b] = int(round(n * (1 - fail)))
        c["split"][name], c["split_legal"][name] = h, lg
    v, lines = dr.diag68_route(c)
    assert v == "NEITHER" and len(lines) == 6  # flat failure inside each k: no state gap, nothing explained by the ball


def test_pool_reads_and_mean_shift(tmp_path):
    import json
    for i, (c, n) in enumerate(((0.5, 100), (0.7, 300))):
        json.dump({"per_family": {"fast": {"contact": c, "episodes": n}}}, open(tmp_path / f"p{i}.json", "w"))
        json.dump({"directions": {"left": {"contact": c, "feeds": n}, "back": {"contact": c, "feeds": n}}}, open(tmp_path / f"d{i}.json", "w"))
    pf, pd = dr.pool_reads([str(tmp_path / "p0.json"), str(tmp_path / "p1.json")], [str(tmp_path / "d0.json"), str(tmp_path / "d1.json")])
    assert abs(pf["per_family"]["fast"]["contact"] - 0.65) < 1e-9 and pf["per_family"]["fast"]["episodes"] == 400
    assert abs(pd["directions"]["left"]["contact"] - 0.65) < 1e-9 and pd["directions"]["back"]["feeds"] == 400
    assert abs(dr.mean_family_shift({"a": {"contact": 0.4}, "b": {"contact": 0.5}}, {"a": {"contact": 0.45}, "b": {"contact": 0.5}}) + 0.025) < 1e-9


def test_sum_counters():
    a = {"split": {"x": [[1, 2], [3, 4]]}, "n": 5, "meta": "m"}
    b = {"split": {"x": [[10, 20], [30, 40]]}, "n": 1, "meta": "m"}
    assert dr.sum_counters(a, b) == {"split": {"x": [[11, 22], [33, 44]]}, "n": 6, "meta": "m"}

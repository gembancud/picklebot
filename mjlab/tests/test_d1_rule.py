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


def test_stage8_climb_lines_and_verdicts():
    start = 31399
    rows = [{"step": (start + it) * 24, "idlerec": [0.30 * 2000 * k + (0.08 * 2000 if it >= 300 else 0) * 0, 2000 * k, 0, 0]}
            for k, it in enumerate((0, 60, 300, 360))]
    assert dr.s8_climb_kill(rows, start)[0] == "KILL-NO-CLIMB"  # flat 0.30
    rows2 = [{"step": r["step"], "idlerec": [0.30 * 2000 * k if k < 3 else 0.30 * 2000 * 2 + 0.40 * 2000, 2000 * k, 0, 0]}
             for k, r in enumerate(rows)]
    assert dr.s8_climb_kill(rows2, start)[0] == "CONTINUE"  # 0.30 -> 0.40
    assert dr.s8_climb_kill([], start)[0] == "NO-DATA"
    st = lambda d, f1, f3=0.03, n=2000: {"recover_dist": d, "pelvis_speed": 0.2, "k1_n": n, "k1_fail": f1, "k3_fail": f3}  # noqa: E731
    L = dr.s8_lines(st(0.55, 0.14), st(0.70, 0.18), st(0.68, 0.18))
    assert L == {"invalid": False, "dose": True, "hazard": True}
    assert not dr.s8_lines(st(0.62, 0.14), st(0.70, 0.18), st(0.68, 0.18))["dose"]
    assert not dr.s8_lines(st(0.55, 0.16), st(0.70, 0.18), st(0.68, 0.18))["hazard"]
    assert dr.s8_lines(st(0.55, 0.14, n=900), st(0.70, 0.18), st(0.68, 0.18))["invalid"]
    v = dr.s8_verdict
    assert [v(True, 1, 1, 1, 1), v(0, 0, 1, 1, 1), v(0, 1, 0, 1, 1), v(0, 1, 1, 0, 1), v(0, 1, 1, 1, 0), v(0, 1, 1, 1, 1)] == \
        ["INVALID", "NO-DOSE", "NO-HAZARD", "GUARD-BREACH", "P5-LOSS", "REC-PASS"]


def test_k1_state_reads_the_parent_diag68_counters():
    import os
    if not os.path.exists("results/diag68-r05.jsonl"):
        return
    from picklebot_mj import agility_rule as ar
    c = dr.sum_counters(ar.window(ar.read_rows("results/diag68-r05.jsonl"), "ballidx", 0.5, 1.0),
                        ar.window(ar.read_rows("results/diag68-r05b.jsonl"), "ballidx", 0.5, 1.0))
    s = dr.k1_state(c)
    assert s["k1_n"] == 1917 and 0.3 < s["recover_dist"] < 1.2 and 0.1 < s["k1_fail"] < 0.3 and s["k3_fail"] < 0.06


def test_pooled_pairs_and_drift_verdict(tmp_path):
    import json
    for i, (fl, f) in enumerate(((60, 100), (70, 100))):
        json.dump({"pairs": {"court_counts": [[0, 0, f, fl]], "len_hist": [5, 0, 0, 0, 0, 1], "open_len_hist": [0, 0, 0, 0, 0, 4]}},
                  open(tmp_path / f"p{i}.json", "w"))
    q = dr.pooled_pairs([str(tmp_path / "p0.json"), str(tmp_path / "p1.json")])
    assert abs(q["feeder"] - 0.65) < 1e-9 and abs(q["p5"] - 10 / 20) < 1e-9
    v = dr.drift_verdict
    assert v(False, 0.0, 0.6, 0.6, 0.4, 0.4) == "STILL-DRIFT" and v(True, -0.021, 0.6, 0.6, 0.4, 0.4) == "STILL-DRIFT"
    assert v(True, -0.005, 0.60, 0.605, 0.40, 0.405) == "FIXED"
    assert v(True, -0.015, 0.60, 0.60, 0.40, 0.40) == "PARTIAL" and v(True, 0.0, 0.58, 0.60, 0.40, 0.40) == "PARTIAL"


def test_gain_line_mechanism_and_route(tmp_path):
    import json

    def pairs(path, p5_k, n=100, ready=0.2, falls=1):
        json.dump({"pairs": {"court_counts": [[0, 0, 10, 6]], "len_hist": [n - p5_k, 0, 0, 0, 0, p5_k], "open_len_hist": [0] * 6},
                   "ready": {"ready": ready, "feeds_scored": 100}, "rally_endings": {"WRONG_SIDE": 2, "OUT": 8},
                   "falls": falls, "hits": 1000, "recovery": {"error_median_m": 0.3}}, open(path, "w"))
    c, p = [], []
    for i, (kc, kp) in enumerate(((42, 40), (43, 41), (41, 39), (44, 42))):
        pairs(tmp_path / f"c{i}.json", kc); pairs(tmp_path / f"p{i}.json", kp)
        c.append(str(tmp_path / f"c{i}.json")); p.append(str(tmp_path / f"p{i}.json"))
    assert dr.gain_line(c, p)[0]  # +2 points on every seed
    assert not dr.gain_line(p, c)[0]
    m = dr.mechanism(c)
    assert abs(m["ready"] - 0.2) < 1e-9 and abs(m["falls_per_1000_hits"] - 1.0) < 1e-9 and abs(m["wrong_side_share"] - 0.2) < 1e-9
    r = dr.anchor_route
    assert [r("FIXED", True), r("FIXED", False), r("STILL-DRIFT", True), r("STILL-DRIFT", False), r("PARTIAL", True)] == \
        ["CONFIRM", "HELD-NO-GAIN", "TRADE-OFF", "STILL-DRIFT", "PARTIAL"]


def test_replicated():
    assert dr.replicated(True, {"ready": 0.30, "falls_per_1000_hits": 1.0})
    assert not dr.replicated(False, {"ready": 0.30, "falls_per_1000_hits": 1.0})
    assert not dr.replicated(True, {"ready": 0.20, "falls_per_1000_hits": 1.0})
    assert not dr.replicated(True, {"ready": 0.30, "falls_per_1000_hits": 1.5})


def test_gain2_and_seed_estimate(tmp_path):
    import json

    def pairs(path, k, n=2000):
        json.dump({"pairs": {"court_counts": [[0, 0, 10, 6]], "len_hist": [n - k, 0, 0, 0, 0, k], "open_len_hist": [0] * 6}},
                  open(path, "w"))
    c, r = [], []
    for i, (kc, kr) in enumerate(((860, 800), (870, 800), (850, 800), (880, 800))):  # +3.0 .. +4.0 points
        pairs(tmp_path / f"c{i}.json", kc); pairs(tmp_path / f"r{i}.json", kr)
        c.append(str(tmp_path / f"c{i}.json")); r.append(str(tmp_path / f"r{i}.json"))
    ok, diff, lo, _ = dr.gain2(c, r)
    assert ok and abs(diff - 0.0325) < 1e-9 and lo > 0
    ok, diff, lo, _ = dr.gain2(r, c)
    assert not ok and diff < 0
    assert "over 3 training seeds" in dr.seed_estimate([0.021, 0.0145, 0.01])


def test_lev76_hazard_lines_and_candidate(tmp_path):
    import json

    def pairs(path, h, oh, f=100, fl=60):
        json.dump({"pairs": {"court_counts": [[0, 0, f, fl]], "len_hist": h, "open_len_hist": oh}}, open(path, "w"))
    pairs(tmp_path / "r.json", [40, 30, 5, 1, 0, 0], [0, 0, 0, 0, 0, 24])   # h0 0.40, h1 0.50
    pairs(tmp_path / "c.json", [36, 28, 5, 1, 0, 0], [0, 0, 0, 0, 0, 30])   # h0 0.36, h1 0.4375
    q = dr.pooled_hazards([str(tmp_path / "r.json")])
    assert abs(q["h"][0] - 0.40) < 1e-9 and abs(q["h"][1] - 0.50) < 1e-9 and abs(q["open2"] - 0.30) < 1e-9
    assert abs(q["late"] - 1 / 25) < 1e-9
    ok, lines = dr.lever_lines([str(tmp_path / "c.json")], [str(tmp_path / "r.json")])
    assert ok and lines[0].endswith("True")  # open2 0.36 vs 0.30
    assert not dr.lever_lines([str(tmp_path / "r.json")], [str(tmp_path / "c.json")])[0]
    pairs(tmp_path / "low.json", [36, 28, 5, 1, 0, 0], [0, 0, 0, 0, 0, 30], fl=55)  # feeder 0.55 vs 0.60
    assert not dr.lever_lines([str(tmp_path / "low.json")], [str(tmp_path / "r.json")])[0]
    assert [dr.lev76_candidate(*a) for a in ((True, True), (False, True), (True, False), (False, False))] == ["K", "K", "C2", "none"]


def test_fast4_check():
    def ag(sus, fs, st, arr=0.97, falls=0.2, fc=0.02):
        return {"falls": falls, "worst_arrival": arr, "fallen_censored_share": fc, "sustained_p50": sus,
                "first_step_p50": fs, "settled": st, "peak_p50": sus}
    w = ag([2.0] * 6, [1.2] * 6, [0.3] * 6)
    t = ag([2.2] * 6, [1.1] * 6, [0.35] * 6, falls=0.15)
    assert dr.fast4_check(t, w)[0] == "D1B-OK"
    assert dr.fast4_check(ag([2.05] * 6, [1.1] * 6, [0.35] * 6, falls=0.15), w)[0] == "TEACHER-NOT-READY"  # +0.05 only
    assert dr.fast4_check(ag([2.2] * 6, [1.3] * 6, [0.35] * 6, falls=0.15), w)[0] == "TEACHER-NOT-READY"  # slower first step
    assert dr.fast4_check(ag([2.2] * 6, [1.1] * 6, [0.29] * 6, falls=0.15), w)[0] == "TEACHER-NOT-READY"  # settles less
    assert dr.fast4_check(ag([2.2] * 6, [1.1] * 6, [0.35] * 6, arr=0.94, falls=0.15), w)[0] == "TEACHER-NOT-READY"
    assert dr.fast4_check(ag([2.2] * 6, [1.1] * 6, [0.35] * 6, falls=0.3), w)[0] == "TEACHER-NOT-READY"  # more falls


def test_rec78_lines(tmp_path):
    import json

    def pairs(path, h, oh, f=100, fl=60):
        json.dump({"pairs": {"court_counts": [[0, 0, f, fl]], "len_hist": h, "open_len_hist": oh}}, open(path, "w"))
    pairs(tmp_path / "r.json", [40, 30, 5, 1, 0, 0], [0, 0, 0, 0, 0, 24])   # h1 0.50
    pairs(tmp_path / "c.json", [40, 25, 5, 1, 0, 0], [0, 0, 0, 0, 0, 29])   # h1 25/60
    ok, lines = dr.rec78_lines([str(tmp_path / "c.json")], [str(tmp_path / "r.json")])
    assert ok and lines[0].endswith("True")
    assert not dr.rec78_lines([str(tmp_path / "r.json")], [str(tmp_path / "c.json")])[0]
    s34, s5 = dr.late_splits([str(tmp_path / "r.json")])
    assert abs(s34 - 1 / 25) < 1e-9 and s5 == 0.0


def test_cfs79_lines(tmp_path):
    import json

    def pairs(path, h, oh, f=100, fl=60):
        json.dump({"pairs": {"court_counts": [[0, 0, f, fl]], "len_hist": h, "open_len_hist": oh}}, open(path, "w"))
    pairs(tmp_path / "r.json", [40, 30, 5, 1, 0, 0], [0, 0, 0, 0, 0, 24])   # h0 0.40
    pairs(tmp_path / "c.json", [35, 30, 5, 1, 0, 0], [0, 0, 0, 0, 0, 29])   # h0 0.35
    ok, lines = dr.cfs79_lines([str(tmp_path / "c.json")], [str(tmp_path / "r.json")])
    assert ok and lines[0].startswith("H0") and lines[0].endswith("True")
    assert not dr.cfs79_lines([str(tmp_path / "r.json")], [str(tmp_path / "c.json")])[0]


def test_dist_route():
    restart = [[300, 260], [300, 255], [300, 250], [300, 220], [300, 200], [300, 180], [900, 450]]  # near 0.85, far 0.50
    assert dr.dist_route(restart)[0] == "RESTART-BINDS"
    shot = [[300, 210], [300, 200], [300, 210], [300, 200], [300, 190], [300, 180], [900, 450]]  # near 0.69
    assert dr.dist_route(shot)[0] == "SHOT-BINDS"
    mid = [[300, 240], [300, 230], [300, 235], [300, 220], [300, 200], [300, 180], [900, 600]]  # near 0.78
    assert dr.dist_route(mid)[0] == "PANEL"
    lo, hi = dr.wilson(50, 100)
    assert abs(lo - 0.4038) < 1e-3 and abs(hi - 0.5962) < 1e-3


def test_cut81_kills():
    def row(it, feeds, hands, far, near, cf, cl):
        return {"step": it * dr.STEPS_PER_IT, "split": [[feeds, hands], [0, 0]],
                "launch": {"d_hist": [[near, 0, 0, 0, 0, 0, far]], "outcome_after_cut": [cf, cl]}}
    start = 32598
    ok = [row(start + 30, 0, 0, 0, 0, 0, 0), row(start + 90, 0, 0, 0, 0, 2000, 1400),
          row(start + 300, 1000, 1000, 1000, 1000, 2000, 1400), row(start + 360, 3000, 6000, 2000, 1500, 2500, 1700)]
    v = [x[0] for x in dr.cut81_kills(ok, start)]
    assert v == ["CONTINUE", "CONTINUE", "CONTINUE"], v
    bad = [row(start + 30, 0, 0, 0, 0, 0, 0), row(start + 90, 0, 0, 0, 0, 2000, 1900),
           row(start + 300, 1000, 1000, 1000, 1000, 2000, 1900), row(start + 360, 1500, 15000, 1200, 2800, 2500, 2300)]
    v = [x[0] for x in dr.cut81_kills(bad, start)]
    assert v == ["KILL-NO-SHARE", "KILL-NO-DOSE", "KILL-EASY"], v
    assert all(x[0] == "NO-DATA" for x in dr.cut81_kills([], start))


def test_spawn_route():
    first = [10, 10, 10, 100, 100, 270, 500]          # off-spot 0.50 of 1,000
    full = [30, 30, 30, 400, 400, 810, 800]            # second half: 300 of 2,000 = 0.15
    assert dr.spawn_route(first, full)[0] == "SPAWN-BINDS"
    full_mid = [20, 20, 20, 200, 200, 540, 1000]       # second half: 500 of 1,000 = 0.50
    assert dr.spawn_route(first, full_mid)[0] == "MID-BINDS"
    full_mix = [20, 20, 20, 300, 300, 640, 900]        # second half: 400 of 1,300 = 0.31 but first 0.50 -> spawn
    assert dr.spawn_route(first, full_mix)[0] == "SPAWN-BINDS"
    full_none = [20, 20, 20, 400, 400, 640, 700]       # second 400 / 1,200 = 0.33
    assert dr.spawn_route([10, 10, 10, 200, 200, 270, 300], full_none)[0] == "PANEL"  # first 0.30 (< 0.45), second 0.33 (< 0.45)


def test_spawn_route_invalid_split():
    first = [10, 10, 10, 100, 100, 270, 500]
    assert dr.spawn_route(first, [9, 10, 10, 101, 100, 269, 499])[0] == "INVALID-SPLIT"  # second half about 0


def test_court_conv_and_ep24_dose(tmp_path):
    import json
    cc = [[0, 0, 1, 1]] * 26 + [[0, 0, 2, 1]] * 37 + [[0, 0, 3, 1]] * 37   # q0 0.26
    json.dump({"pairs": {"court_counts": cc}}, open(tmp_path / "p.json", "w"))
    q = dr.court_conv([str(tmp_path / "p.json")])
    assert abs(q["q0"] - 0.26) < 1e-9 and abs(q["q1"] - 74 / 111) < 1e-9 and q["courts"] == 100

    def row(it, reset, other):
        return {"step": it * dr.STEPS_PER_IT, "launch": {"outcome_by_d": [[other, 0]] + [[0, 0]] * 6 + [[reset, 0]]}}
    rows = [row(32598, 0, 0), row(32598 + 160, 500, 1500)]
    assert dr.ep24_dose_kill(rows, 0, 160, 32598)[0] == "CONTINUE"    # 0.25
    rows = [row(32598, 0, 0), row(32598 + 160, 100, 1900)]
    assert dr.ep24_dose_kill(rows, 0, 160, 32598)[0] == "KILL-NO-DOSE"  # 0.05
    assert dr.ep24_dose_kill([], 0, 160, 32598)[0] == "NO-DATA"


def test_reset_dose_reproduces_the_logged_values():
    import json
    import os
    p = "results/ep82-smoke-share.jsonl"
    if not os.path.exists(p):
        import pytest
        pytest.skip("needs the D-219 smoke log")
    rows = [json.loads(x) for x in open(p)]
    s, r, n = dr.reset_dose(rows, 20, 140, 32598, 1024)
    assert abs(s - 0.4306) < 1e-3 and abs(r - 0.03879) < 1e-4 and n > 1000
    assert dr.reset_dose_kill(rows, 20, 140, 32598, 1024)[0] == "CONTINUE"
    assert dr.reset_dose_kill(rows, 0, 160, 32598, 1024)[0] == "NO-DATA"  # D-219's window: no row at +182


def test_reset_dose_kill_lines():
    def row(it, res, fire):
        return {"step": it * dr.STEPS_PER_IT, "end_reasons": [[0, 0, res, 0], [0, 0, 0, 0]], "split": [[fire, 0], [0, 0]]}
    low = [row(32598 + 20, 0, 0), row(32598 + 140, 300, 2000)]  # share 0.15
    assert dr.reset_dose_kill(low, 20, 140, 32598, 1024)[0] == "KILL-NO-DOSE"


def _fs_row(it, left, back, start=16600, pay=0.0, issued=0):
    h = [[0] * 80 for _ in range(8)]
    for i, xs in ((dr.LEFT, left), (dr.BACK, back)):
        for b, n in xs:
            h[i][b] = n
    return {"step": (start + it) * dr.STEPS_PER_IT,
            "move": {"first_step_hist": h, "first_step_bin_s": 0.05, "first_pay_sum": [pay] * 8, "issued": [issued] * 8}}


def test_quick_kill_lines():
    def cum(rows):
        out, acc = [], None
        for it, l, b in rows:
            r = _fs_row(it, l, b)
            if acc is not None:
                for i in (dr.LEFT, dr.BACK):
                    r["move"]["first_step_hist"][i] = [x + y for x, y in zip(r["move"]["first_step_hist"][i], acc[i])]
            acc = r["move"]["first_step_hist"]
            out.append(r)
        return out
    base = [(0, [], []), (100, [(27, 300)], [(28, 300)]), (400, [(27, 900)], [(28, 900)])]
    fast = cum(base + [(450, [(24, 300)], [(25, 300)])])      # 1.375 -> 1.225 / 1.425 -> 1.275: 0.15 faster
    assert dr.quick_kill(fast, 16600)[0] == "CONTINUE"
    slow = cum(base + [(450, [(26, 300)], [(25, 300)])])      # left only 0.05 faster
    assert dr.quick_kill(slow, 16600)[0] == "KILL-NO-START"
    assert dr.quick_kill(cum(base), 16600)[0] == "NO-DATA"    # no row at +450
    few = cum([(0, [], []), (100, [(27, 50)], [(28, 50)]), (400, [], []), (450, [(24, 50)], [(25, 50)])])
    assert dr.quick_kill(few, 16600)[0] == "NO-DATA"          # < 200 samples


def test_quick_check_lines():
    w = {"falls": 0.02, "worst_arrival": 0.97, "fallen_censored_share": 0.05, "settled": [0.3] * 8,
         "first_step_p50": [1.375] * 8, "sustained_p50": [1.0] * 8}
    t = dict(w, falls=0.01, worst_arrival=0.98, settled=[0.35] * 8, first_step_p50=[1.125] * 8)
    assert dr.quick_check(t, w)[0] == "QUICK-OK"              # exactly - 0.25
    assert dr.quick_check(dict(t, first_step_p50=[1.175] * 8), w)[0] == "QUICK-FAIL"
    assert dr.quick_check(dict(t, falls=0.03), w)[0] == "QUICK-FAIL"
    assert dr.quick_check(dict(t, settled=[0.2] * 8), w)[0] == "QUICK-FAIL"
    assert dr.quick_check(dict(t, worst_arrival=0.7), w)[0] == "INVALID"


def test_quick_kill_reads_the_fast4_log_as_flat():
    import json
    import os
    p = "results/fwfast4-train.jsonl"
    if not os.path.exists(p):
        import pytest
        pytest.skip("needs the D-191 training log")
    rows = [json.loads(x) for x in open(p)]
    v, line = dr.quick_kill(rows, 16600)
    assert v == "KILL-NO-START", line   # Fast4's first step held at 1.33-1.38 s


def _h1_read(tmp_path, name, near0, near1, far0, h1_len=None):
    import json
    o = [[[0, 0] for _ in range(8)] for _ in range(2)]
    o[0][1], o[1][1], o[0][6] = near0, near1, far0
    own = [sum(x[0] for c in o for x in c), sum(x[1] for c in o for x in c)]
    n0 = sum(x[0] for x in o[0])
    l0 = sum(x[1] for x in o[0])
    lh = h1_len or [0, n0 - l0, l0, 0, 0, 0, 0]  # rallies ending at 1 = first hand-off misses; the rest end at 2
    p = tmp_path / name
    json.dump({"pairs": {"handoff_by_d": o, "court_counts": [own + [0, 0]], "len_hist": [0] * 1 + lh[1:],
                         "open_len_hist": [0] * len(lh)}}, open(p, "w"))
    return str(p)


def test_h1_route_lines(tmp_path):
    ball = _h1_read(tmp_path, "b.json", [1000, 800], [3000, 2700], [1000, 300])  # 0.80 vs 0.90
    assert dr.h1_route([ball])[0] == "BALL"
    pos = _h1_read(tmp_path, "p.json", [1000, 880], [3000, 2700], [1500, 450])  # 0.88 vs 0.90, far 0.6
    assert dr.h1_route([pos])[0] == "POSITION"
    mixed = _h1_read(tmp_path, "m.json", [1000, 880], [3000, 2700], [300, 90])  # gap ok but far share low
    assert dr.h1_route([mixed])[0] == "MIXED"
    few = _h1_read(tmp_path, "f.json", [100, 80], [3000, 2700], [100, 30])
    assert dr.h1_route([few])[0] == "INVALID-SPLIT"
    ok, line = dr.h1_recon([ball])
    assert ok, line

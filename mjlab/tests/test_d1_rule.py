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

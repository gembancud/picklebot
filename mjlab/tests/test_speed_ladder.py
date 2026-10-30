"""Supervised speed ladder helpers (scripts/motion/speed_ladder.py, D-175): speed bins, heading-frame direction,
window stats, clip-name parsing and the coded rule in its registered order. CPU only, no simulator."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

spec = importlib.util.spec_from_file_location(
    "speed_ladder", Path(__file__).resolve().parents[1] / "scripts" / "motion" / "speed_ladder.py")
sl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sl)


def _quat_yaw(yaw, n):
    q = np.zeros((n, 4))
    q[:, 0], q[:, 3] = np.cos(yaw / 2), np.sin(yaw / 2)
    return q


def test_speed_bins_match_d175():
    assert sl.speed_bin(0.3) == sl.speed_bin(1.0) == "<=1.0"
    assert sl.speed_bin(1.01) == sl.speed_bin(1.49) == "1.0-1.5"
    assert sl.speed_bin(1.5) == sl.speed_bin(1.99) == "1.5-2.0"
    assert sl.speed_bin(2.0) == sl.speed_bin(3.7) == ">=2.0"


@pytest.mark.parametrize("yaw", [0.0, 0.7, -2.0, 3.0])
@pytest.mark.parametrize("local, name", [((1, 0), "forward"), ((0, 1), "left"), ((-1, 0), "back"), ((0, -1), "right")])
def test_direction_is_in_the_heading_frame(yaw, local, name):
    n = 20
    c, s = np.cos(yaw), np.sin(yaw)
    vw = np.zeros((n, 3))
    vw[:, 0] = 2.5 * (c * local[0] - s * local[1])
    vw[:, 1] = 2.5 * (s * local[0] + c * local[1])
    st = sl.window_stats(vw, _quat_yaw(yaw, n))
    assert st["direction"] == name and st["purity"] == 1.0
    assert st["ref_p50"] == pytest.approx(2.5) and st["bin"] == ">=2.0"


def test_window_direction_is_the_dominant_sector_and_ignores_standing_frames():
    n = 100
    vw = np.zeros((n, 3))
    vw[:60, 1] = 1.2  # left (yaw 0)
    vw[60:90, 1] = -1.2  # right
    vw[90:, 0] = 0.05  # standing (below MOVING_MPS): no direction
    st = sl.window_stats(vw, _quat_yaw(0.0, n))
    assert st["direction"] == "left" and st["purity"] == pytest.approx(60 / 90)
    assert st["ref_p50"] == pytest.approx(1.2) and st["bin"] == "1.0-1.5"


def test_clip_names():
    assert sl.parse_clip("Neutral_SW_train_mirror_x2.5") == ("SW_train_mirror", 2.5)
    assert sl.parse_clip("Neutral_BW_ref_x1") == ("BW_ref", 1.0)
    assert sl.gait_of("SR_ref_mirror") == "SR"


def test_coded_rule_order_and_thresholds():
    ok = dict(h0_x1=1.0, lat_x1=1.0, n_fast=10)
    assert sl.coded_rule(**ok, h0_fast=0.95, lat_fast=0.92, cov5_fast=0.85)[1] == "SELECTION"
    assert sl.coded_rule(**ok, h0_fast=0.95, lat_fast=0.92, cov5_fast=0.79)[1] == "OTHER"
    assert sl.coded_rule(**ok, h0_fast=0.90, lat_fast=0.69, cov5_fast=0.9)[1] == "DECODER"
    assert sl.coded_rule(**ok, h0_fast=0.69, lat_fast=0.69, cov5_fast=0.9)[1] == "BODY?"
    assert sl.coded_rule(**ok, h0_fast=0.80, lat_fast=0.80, cov5_fast=0.9)[1] == "OTHER"
    # VOID comes first: either checkpoint < 95 % at x1, whatever the fast windows say.
    assert sl.coded_rule(h0_x1=0.949, lat_x1=1.0, n_fast=10, h0_fast=1, lat_fast=1, cov5_fast=1)[1] == "VOID"
    assert sl.coded_rule(h0_x1=1.0, lat_x1=0.94, n_fast=10, h0_fast=1, lat_fast=1, cov5_fast=1)[1] == "VOID"
    assert sl.coded_rule(h0_x1=0.95, lat_x1=0.95, n_fast=10, h0_fast=1, lat_fast=1, cov5_fast=1)[1] == "SELECTION"
    lines, v = sl.coded_rule(h0_x1=1.0, lat_x1=1.0, n_fast=0, h0_fast=float("nan"), lat_fast=float("nan"),
                             cov5_fast=float("nan"))
    assert v == "UNDEFINED"
    lines, _ = sl.coded_rule(**ok, h0_fast=0.95, lat_fast=0.92, cov5_fast=0.85)
    assert any(">=  90.0 %" in x and "92.0 %" in x for x in lines)  # every line prints value, sign and threshold


def test_rule_inputs_use_left_back_fast_windows_only():
    def row(f, d, v, h0, lat, cov5):
        return {"factor": f, "direction": d, "ref_p50": v, "h0_success": h0, "lat_success": lat, "cov5": cov5,
                "cov2": cov5}
    rows = [row(1.0, "left", 0.4, 1.0, 1.0, 1.0), row(1.0, "forward", 0.6, 0.0, 1.0, 1.0),
            row(4.0, "back", 2.1, 0.5, 0.25, 0.5), row(4.0, "forward", 2.5, 1.0, 1.0, 1.0),
            row(3.0, "left", 1.9, 1.0, 1.0, 1.0)]
    inp = sl.rule_inputs(rows)
    assert inp["n_fast"] == 1 and inp["h0_fast"] == 0.5 and inp["lat_fast"] == 0.25 and inp["cov5_fast"] == 0.5
    assert inp["h0_x1"] == 0.5 and inp["lat_x1"] == 1.0

"""Travel check rule (picklebot_mj/travel_rule.py, D-184)."""

from picklebot_mj import travel_rule as tr


def _read(ratio, ref_speed=1.2, slip=0.1, friction=1.0, units=20, reps=4, vel=None, clip="fwfast_x"):
    per_clip = [{"clip": clip, "ref_pelvis_speed": ref_speed, "pelvis_speed": ref_speed * (vel if vel is not None else ratio)}
                for _ in range(units)]
    per_env = [{"unit": k, "clip": clip, "disp_robot": 4.0 * ratio, "disp_ref": 4.0, "disp_robot_1s": ratio,
                "disp_ref_1s": 1.0, "stance_slip_mps": slip, "foot_friction": friction, "success": True}
               for k in range(units) for _ in range(reps)]
    return {"per_clip": per_clip, "per_env": per_env}


def test_stats_and_instrument():
    s = tr.read_stats(_read(0.54))
    assert abs(s["D"] - 0.54) < 1e-9 and abs(s["TR"] - 0.54) < 1e-9 and s["instrument_ok"] and s["envs"] == 80
    assert not tr.read_stats(_read(0.54, vel=0.40))["instrument_ok"]
    assert tr.read_stats(_read(0.54, ref_speed=0.8))["envs"] == 0  # no FAST units


def test_routes():
    s = tr.read_stats
    assert tr.route(s(_read(0.95)), s(_read(0.93)), None)[0] == "TRAVEL-OK"
    assert tr.route(s(_read(0.95)), s(_read(0.70)), None)[0] == "DECODER-GAP"
    assert tr.route(s(_read(0.85)), s(_read(0.85)), None)[0] == "MIXED"
    v, sub, _ = tr.route(s(_read(0.54)), s(_read(0.55)), s(_read(0.95, clip="walk1_subject1")))
    assert (v, sub) == ("TRAVEL-GAP", "COVERAGE")
    v, sub, _ = tr.route(s(_read(0.54)), s(_read(0.55)), s(_read(0.55, clip="walk1_subject1")))
    assert (v, sub) == ("TRAVEL-GAP", "OBJECTIVE")
    assert tr.route(s(_read(0.54, vel=0.4)), s(_read(0.55)), None)[0] == "INSTRUMENT"


def test_contact_needs_high_friction_bin_ok():
    h0 = _read(0.54, slip=0.3)
    for i, e in enumerate(h0["per_env"]):  # high-friction envs travel fully
        if i % 2 == 0:
            e["foot_friction"], e["disp_robot"] = 1.0, 3.8
        else:
            e["foot_friction"] = 0.4
    s = tr.read_stats(h0)
    s["D"], s["instrument_ok"] = 0.6, True  # force D below GAP; the mixed construction trips the instrument check
    assert tr.route(s, tr.read_stats(_read(0.55)), None)[0] == "CONTACT"

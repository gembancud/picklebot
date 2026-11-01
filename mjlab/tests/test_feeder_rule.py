"""D-198 feeder-ball split rule (picklebot_mj/feeder_rule.py) on synthetic counters."""

from picklebot_mj import feeder_rule as fr
from picklebot_mj.tasks.ball_index import SPLIT_VARS, STATE_VARS

DB = 40


def _counters(k0_contact, k3_contact, k0_balls=1000, k3_balls=4000, state_fail=None):
    """Feeder balls at distance bin 4 (1.0-1.25 m, in the matched band), all forward; k >= 3 likewise.
    state_fail: {var: (fail_low_tercile, fail_high_tercile)} spread over two variable bins."""
    cells = 2 * 3 * 5
    c = {"dist": [[0] * DB for _ in range(cells)], "dist_contact": [[0] * DB for _ in range(cells)]}
    k3 = (0 * 3 + 2) * 5 + 0
    c["dist"][k3][4] = k3_balls
    c["dist_contact"][k3][4] = int(k3_contact * k3_balls)
    f = {k: [0] * 10 for k in ("balls", "contact", "legal", "fell", "early")}
    f.update({k: [0, 0] for k in ("received", "void", "censored")})
    f.update({k: [[0] * DB for _ in range(10)] for k in ("dist", "dist_legal", "dist_contact")})
    f["balls"][0], f["contact"][0], f["legal"][0] = k0_balls, int(k0_contact * k0_balls), int(0.9 * k0_contact * k0_balls)
    f["dist"][0][4], f["dist_contact"][0][4] = k0_balls, int(k0_contact * k0_balls)
    f["dist_legal"][0][4] = f["legal"][0]
    nb = {name: n for name, _, _, n in SPLIT_VARS}
    f["split"], f["split_legal"] = {}, {}
    for name in STATE_VARS:
        h = [[0] * (nb[name] + 1) for _ in range(2 * DB)]
        hl = [[0] * (nb[name] + 1) for _ in range(2 * DB)]
        lo, hi = (state_fail or {}).get(name, (0.3, 0.3))
        for b, (n, fail) in ((1, (k0_balls // 3, lo)), (5, (k0_balls // 3, 0.3)), (9, (k0_balls - 2 * (k0_balls // 3), hi))):
            h[4][b], hl[4][b] = n, int(n * (1 - fail))
        f["split"][name], f["split_legal"][name] = h, hl
    c["feeder"] = f
    return c


def test_state_shot_other_invalid():
    st = {"pelvis_speed": (0.10, 0.40)}
    assert fr.route(_counters(0.70, 0.97, state_fail=st), _counters(0.71, 0.97, state_fail=st))["verdict"] == "FEED-STATE"
    assert fr.route(_counters(0.70, 0.97), _counters(0.71, 0.97))["verdict"] == "FEED-OTHER"  # big gap, no state variable
    assert fr.route(_counters(0.94, 0.97), _counters(0.94, 0.97))["verdict"] == "FEED-SHOT"
    assert fr.route(_counters(0.70, 0.97, k0_balls=500), _counters(0.70, 0.97))["verdict"] == "INVALID"
    assert fr.route(_counters(0.70, 0.97), _counters(0.70, 0.97), valid=False)["verdict"] == "INVALID"


def test_noise_arm_blocks_a_gap_it_does_not_reproduce():
    st = {"pelvis_speed": (0.10, 0.40)}
    # C's gap 0.27; C2's gap 0.05: noise 2 x 0.22 = 0.44 > 0.27 -> not big -> not STATE (and not within 0.05 -> OTHER)
    assert fr.route(_counters(0.70, 0.97, state_fail=st), _counters(0.92, 0.97, state_fail=st))["verdict"] == "FEED-OTHER"

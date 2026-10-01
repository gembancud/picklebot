"""Bisect the ball-court damping ratio per timestep to hit the official drop band centre.

Contact model: solref = (2*dt, dampratio), MuJoCo default solimp. The sweep in
bounce_sweep.py showed this family is monotonic in dampratio (COR decreases
smoothly), unlike longer time constants. Target: first rebound apex (ball top)
0.813 m, the centre of the official 0.762-0.864 m band, from a 1.981 m drop (ball-bottom datum).

Usage: python scripts/calibrate_court_bounce.py
"""

from bounce_sweep import drop  # noqa: E402

from picklebot_mj.court import BALL_CONTACT_SOLIMP

TARGET = 0.813


def calibrate(dt, lo, hi, iters=30):
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        r = drop(dt, (2 * dt, mid), BALL_CONTACT_SOLIMP)
        if r["apex_top"] > TARGET:  # too bouncy -> more damping
            lo = mid
        else:
            hi = mid
    r = drop(dt, (2 * dt, 0.5 * (lo + hi)), BALL_CONTACT_SOLIMP)
    return 0.5 * (lo + hi), r


if __name__ == "__main__":
    for dt, lo, hi in ((0.005, 0.15, 0.175), (0.002, 0.375, 0.425), (0.001, 0.275, 0.325)):
        dr, r = calibrate(dt, lo, hi)
        print(f"dt={dt}: dampratio={dr:.5f} apex_top={r['apex_top']} cor={r['cor']} "
              f"pen={r['penetration_mm']}mm contact={r['contact_ms']}ms gain={r['energy_gain']}")

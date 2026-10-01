"""Sweep ball-floor contact parameters for the official drop test.

Official compliance drop (PHASE1B spec section 5): release from 1.981 m, first
rebound apex (top of ball) 0.762-0.864 m. Datum choice, recorded in the output:
ball *bottom* at 1.981 m, so the centre starts at 1.981 + r. Aerodynamics on.

Measurements per configuration: rebound apex (top of ball), normal coefficient of
restitution (exit/entry vertical speed at contact boundaries), max penetration,
contact duration, contact episodes before lift-off (chatter), energy gain.

Usage: python scripts/bounce_sweep.py [out.json]
"""

from __future__ import annotations

import json
import sys

import mujoco
import numpy as np
import torch

from picklebot_mj import ball

DROP_BOTTOM = 1.981
APEX_TOP_RANGE = (0.762, 0.864)
SOLIMPS = {"default": [0.9, 0.95, 0.001, 0.5, 2.0], "stiff": [0.95, 0.99, 0.001, 0.5, 2.0]}


def build(dt, solref, solimp, friction=(0.3, 0.3, 0.005, 0.0001, 0.0001)):
    spec = mujoco.MjSpec()
    spec.option.timestep = dt
    spec.option.integrator = mujoco.mjtIntegrator.mjINT_IMPLICITFAST
    spec.worldbody.add_geom(name="floor", type=mujoco.mjtGeom.mjGEOM_PLANE, size=[5, 5, 0.1])
    ball.add_ball(spec.worldbody, pos=[0, 0, DROP_BOTTOM + ball.BALL_RADIUS])
    spec.add_exclude(bodyname1="world", bodyname2="ball")
    spec.add_pair(geomname1="floor", geomname2="ball_geom", condim=3,
                  solref=list(solref), solimp=list(solimp), friction=list(friction))
    return spec.compile()


def drop(dt, solref, solimp, aero=True, duration=1.6, vel0=(0.0, 0.0, 0.0), spin0=(0.0, 0.0, 0.0)):
    m = build(dt, solref, solimp)
    d = mujoco.MjData(m)
    d.qvel[0:3] = vel0
    d.qvel[3:6] = spin0
    bid = m.body("ball").id
    res = np.zeros(6)
    in_contact, episodes, contact_steps = False, 0, 0
    v_in = v_out = None
    min_z, apex, left = 1e9, None, False
    e0 = None
    vin_vec = vout_vec = w_out = None
    for _ in range(int(duration / dt)):
        mujoco.mj_forward(m, d)
        mujoco.mj_objectVelocity(m, d, mujoco.mjtObj.mjOBJ_BODY, bid, res, 0)
        if aero:
            d.xfrc_applied[bid] = ball.ball_wrench(torch.tensor(res[3:].copy()), torch.tensor(res[:3].copy())).numpy()
        touching = d.ncon > 0
        if touching and not in_contact:
            episodes += 1
            if v_in is None:
                v_in, vin_vec = -d.qvel[2], d.qvel[:3].copy()
                e0 = 0.5 * ball.BALL_MASS * float(d.qvel[:3] @ d.qvel[:3]) + ball.BALL_MASS * 9.81 * d.qpos[2]
        if not touching and in_contact and v_out is None and d.qvel[2] > 0:
            v_out, vout_vec, w_out = d.qvel[2], d.qvel[:3].copy(), res[:3].copy()
        if touching:
            contact_steps += 1 if episodes == 1 else 0
        in_contact = touching
        min_z = min(min_z, d.qpos[2])
        if v_out is not None and not left:
            left = True
        if left and apex is None and d.qvel[2] < 0 and not touching:
            apex = d.qpos[2]
        mujoco.mj_step(m, d)
    if v_in is None:
        return None
    apex_top = (apex if apex is not None else ball.BALL_RADIUS) + ball.BALL_RADIUS
    e_apex = ball.BALL_MASS * 9.81 * (apex_top - ball.BALL_RADIUS)
    return dict(
        dt=dt, solref=list(solref), solimp=list(solimp),
        apex_top=round(float(apex_top), 4),
        cor=round(float(v_out / v_in), 4) if v_out else 0.0,
        v_in=round(float(v_in), 3),
        penetration_mm=round(float(ball.BALL_RADIUS - min_z) * 1000, 2),
        contact_ms=round(contact_steps * dt * 1000, 2),
        chatter=episodes > 1 and v_out is None,
        energy_gain=bool(apex is not None and e_apex > e0 + 1e-9),
        vin=None if vin_vec is None else vin_vec.round(3).tolist(),
        vout=None if vout_vec is None else vout_vec.round(3).tolist(),
        w_out=None if w_out is None else np.round(w_out, 2).tolist(),
    )


def main():
    rows = []
    for dt in (0.005, 0.002, 0.001, 0.0005):
        for mult in (2, 4, 8):
            tc = mult * dt
            for sname, si in SOLIMPS.items():
                for dr in np.round(np.arange(0.05, 0.61, 0.025), 3):
                    r = drop(dt, (tc, float(dr)), si)
                    if r:
                        r.update(tc_mult=mult, solimp_name=sname)
                        rows.append(r)
    ok = [r for r in rows if APEX_TOP_RANGE[0] <= r["apex_top"] <= APEX_TOP_RANGE[1] and not r["energy_gain"]]
    out = dict(datum="ball bottom at 1.981 m (centre 1.981 + r); apex measured at ball top",
               target_apex_top=APEX_TOP_RANGE, rows=rows, passing=ok)
    json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else "artifacts/stage1/bounce_sweep.json", "w"), indent=1)
    for r in ok:
        print({k: r[k] for k in ("dt", "tc_mult", "solimp_name", "solref", "apex_top", "cor", "penetration_mm", "contact_ms")})
    print(f"{len(ok)} / {len(rows)} configurations within the official apex band")


if __name__ == "__main__":
    main()

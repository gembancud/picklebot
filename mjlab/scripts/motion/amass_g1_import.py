"""Import the G1-retargeted AMASS footwork subset as tracking CSVs (fast-footwork motion prior data, D-178).

The source (scripts/motion/fetch_amass_g1.py; fleaven/Retargeted_AMASS_for_robotics) is already G1 joint space:
[T, 36] = root xyz, root quat xyzw, 29 joints in the GMR / LAFAN CSV order. Its root height is relative (pelvis z near
0), so this:
- resamples each clip from its source rate (the number before `_jpos` in the file name) to 30 fps (linear joints and
  root position, slerp root rotation);
- replays it on the paddle G1's capsule model (artifacts/motion/lafan-g1/g1_capsules.xml) and shifts it so the lowest
  ankle over the clip sits at the standing ankle height (tennis_retarget.ground_shift's rule);
- writes CSV (xyzw, as lafan_retarget.py) plus a per-clip JSON with the checks below.

There is no human skeleton here, so the IK position-error test of lafan_retarget.py cannot be applied. **Acceptance
rule** (frozen before any clip was converted):
- clip name not stairs / seesaw / push / displace / tilt / jump / kick / crawl / lie / sit (not floor footwork);
- 1.0 s or longer at 30 fps;
- no single joint within 2 deg of its limit in more than 25 % of frames (100STYLE SR failed at 33-45 % ankle roll);
- both feet's contact-frame skate median <= 0.15 m/s (LAFAN1's accepted clips: 0.06-0.14);
- grounded: the per-frame lowest ankle is within 0.10 m of the standing height in >= 95 % of frames (no climbing,
  no relative-height drift);
- self-collision is checked afterwards on the accepted set with penetration_check.py (reported, not filtered here).
The data stays under the git-ignored artifacts/motion/ (AMASS licence: non-commercial research, no redistribution).

Usage (picklebot-mj venv; the raw directory is data only, nothing in it is executed):
    python -I scripts/motion/amass_g1_import.py --src artifacts/motion/amass-g1-raw --out artifacts/motion/amass-g1
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import mujoco as mj
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp

FPS = 30
MODEL_XML = Path(__file__).resolve().parents[2] / "artifacts" / "motion" / "lafan-g1" / "g1_capsules.xml"
STAND_ANKLE_Z = 0.036  # as tennis_retarget.STAND_ANKLE_Z
EXCLUDE = re.compile(r"stair|seesaw|push|displace|tilt|jump|kick|crawl|lie|sit|chair|yoga|kendo|vault|bench|rope|dance"
                     r"|chacha|xinjiang|catwalk|moonwalk|tiptoe|stomp|hop|pose|pick|throw|punch", re.I)
MIN_SECONDS = 1.0
LIMIT_FRAC_MAX = 0.25
SKATE_MAX = 0.15
GROUND_TOL_M, GROUND_FRAC_MIN = 0.10, 0.95


def src_fps(path: Path) -> int:
    m = re.search(r"_(\d+)_jpos\.npy$", path.name)
    if not m:
        raise ValueError(f"no frame rate in {path.name}")
    return int(m.group(1))


def resample(a: np.ndarray, fps_in: int) -> np.ndarray:
    t_in = np.arange(len(a)) / fps_in
    t = np.arange(0.0, t_in[-1] + 1e-9, 1.0 / FPS)
    pos = np.stack([np.interp(t, t_in, a[:, i]) for i in range(3)], axis=1)
    rot = Slerp(t_in, R.from_quat(a[:, 3:7]))(t).as_quat()  # xyzw
    joints = np.stack([np.interp(t, t_in, a[:, i]) for i in range(7, 36)], axis=1)
    return np.concatenate([pos, rot, joints], axis=1)


def to_qpos(c: np.ndarray) -> np.ndarray:
    return np.concatenate([c[:, :3], c[:, [6, 3, 4, 5]], c[:, 7:]], axis=1)  # xyzw -> wxyz


def check(model, qs):
    data = mj.MjData(model)
    feet = [model.body("left_ankle_roll_link").id, model.body("right_ankle_roll_link").id]
    fz, fxy = [], []
    for q in qs:
        data.qpos[:] = q
        mj.mj_kinematics(model, data)
        fz.append(data.xpos[feet, 2].copy())
        fxy.append(data.xpos[feet, :2].copy())
    fz, fxy = np.array(fz), np.array(fxy)
    lo, hi = model.jnt_range[1:, 0], model.jnt_range[1:, 1]
    j = qs[:, 7:]
    at = np.minimum(j - lo, hi - j) < np.deg2rad(2)
    names = [mj.mj_id2name(model, mj.mjtObj.mjOBJ_JOINT, k) for k in range(1, model.njnt)]
    out = {"frames": int(len(qs)), "fps": FPS, "seconds": round(len(qs) / FPS, 2),
           "joint_limit_frac_frames": round(float(at.any(axis=1).mean()), 3),
           "joint_limit_frac_max": round(float(at.mean(axis=0).max()), 3),
           "joints_at_limit": {n: round(float(at[:, i].mean()), 3) for i, n in enumerate(names) if at[:, i].mean() > 0.05}}
    for k, side in enumerate(("left", "right")):
        z = fz[:, k]
        sp = np.r_[0, np.linalg.norm(np.diff(fxy[:, k], axis=0), axis=1) * FPS]
        low = z < z.min() + 0.03
        out[f"{side}_skate_median_mps"] = round(float(np.median(sp[low])), 3)
    out["grounded_frac"] = round(float((fz.min(axis=1) - STAND_ANKLE_Z < GROUND_TOL_M).mean()), 3)
    v = np.r_[0, np.linalg.norm(np.diff(qs[:, :2], axis=0), axis=1) * FPS]
    out["root_path_m"] = round(float(v.sum() / FPS), 1)
    out["root_speed_p50_mps"] = round(float(np.percentile(v, 50)), 2)
    out["root_speed_p90_mps"] = round(float(np.percentile(v, 90)), 2)
    # travel direction relative to the pelvis heading (x forward, y left), over moving frames
    yaw = R.from_quat(np.concatenate([qs[:, 4:7], qs[:, 3:4]], axis=1)).as_euler("zyx")[:, 0]
    d = np.diff(qs[:, :2], axis=0) * FPS
    c, s = np.cos(-yaw[:-1]), np.sin(-yaw[:-1])
    loc = np.stack([c * d[:, 0] - s * d[:, 1], s * d[:, 0] + c * d[:, 1]], axis=1)
    mv = np.linalg.norm(loc, axis=1) > 0.5
    ang = np.degrees(np.arctan2(loc[mv, 1], loc[mv, 0]))
    out["moving_frames_frac"] = round(float(mv.mean()), 3)
    out["dir_frac"] = {"forward": round(float((np.abs(ang) <= 45).mean()), 3) if mv.any() else 0.0,
                       "left": round(float(((ang > 45) & (ang < 135)).mean()), 3) if mv.any() else 0.0,
                       "back": round(float((np.abs(ang) >= 135).mean()), 3) if mv.any() else 0.0,
                       "right": round(float(((ang < -45) & (ang > -135)).mean()), 3) if mv.any() else 0.0}
    fast = np.linalg.norm(loc, axis=1) > 1.5
    out["fast_lateral_back_s"] = round(float((fast & (np.abs(np.degrees(np.arctan2(loc[:, 1], loc[:, 0]))) > 45)).sum()
                                             / FPS), 2)
    return out


def accept(stem, rep):
    why = []
    if EXCLUDE.search(re.sub(r"_(poses|stageii)_\d+_jpos$", "", stem)):  # the clip's own name only ("Transitions" holds "sit")
        why.append("excluded name")
    if rep["seconds"] < MIN_SECONDS:
        why.append("short")
    if rep["joint_limit_frac_max"] > LIMIT_FRAC_MAX:
        why.append("joint limit")
    if max(rep["left_skate_median_mps"], rep["right_skate_median_mps"]) > SKATE_MAX:
        why.append("skate")
    if rep["grounded_frac"] < GROUND_FRAC_MIN:
        why.append("not grounded")
    return not why, why


def clip_name(src: Path, path: Path) -> str:
    rel = path.relative_to(src / "g1").with_suffix("")
    return re.sub(r"[^A-Za-z0-9]+", "_", str(rel)).strip("_")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    src, out = Path(a.src), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    model = mj.MjModel.from_xml_path(str(MODEL_XML))
    assert model.nq == 36, model.nq
    reports = []
    for p in sorted((src / "g1").rglob("*.npy")):
        name = clip_name(src, p)
        try:
            raw = np.load(p, allow_pickle=False)
            assert raw.ndim == 2 and raw.shape[1] == 36 and np.isfinite(raw).all(), raw.shape
            c = resample(raw.astype(np.float64), src_fps(p))
            qs = to_qpos(c)
            data = mj.MjData(model)
            low = np.inf
            for q in qs:
                data.qpos[:] = q
                mj.mj_kinematics(model, data)
                low = min(low, float(data.xpos[[model.body("left_ankle_roll_link").id,
                                                 model.body("right_ankle_roll_link").id], 2].min()))
            qs[:, 2] -= low - STAND_ANKLE_Z
            c[:, 2] = qs[:, 2]
            rep = {"source": str(p.relative_to(src)), "source_fps": src_fps(p), **check(model, qs)}
        except Exception as e:  # one bad clip must not stop the batch
            rep = {"source": str(p.relative_to(src)), "error": f"{type(e).__name__}: {e}", "seconds": 0}
            reports.append({**rep, "name": name, "accepted": False, "reject": ["error"]})
            continue
        ok, why = accept(p.stem, rep)
        rep.update(name=name, accepted=ok, reject=why)
        if ok:
            np.savetxt(out / f"{name}.csv", c, delimiter=",")
        (out / f"{name}.json").write_text(json.dumps(rep, indent=1))
        reports.append(rep)
    acc = [r for r in reports if r["accepted"]]
    (out / "accepted.json").write_text(json.dumps(sorted(r["name"] for r in acc), indent=1))
    summ = {"clips": len(reports), "accepted": len(acc), "accepted_seconds": round(sum(r["seconds"] for r in acc), 1),
            "rejects": {}, "accepted_fast_lateral_back_s": round(sum(r["fast_lateral_back_s"] for r in acc), 1)}
    for r in reports:
        for w in r["reject"]:
            summ["rejects"][w] = summ["rejects"].get(w, 0) + 1
    (out / "summary.json").write_text(json.dumps(summ, indent=1))
    print(json.dumps(summ))


if __name__ == "__main__":
    main()

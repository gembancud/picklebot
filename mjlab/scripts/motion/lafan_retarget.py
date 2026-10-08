"""Retarget LAFAN1 locomotion BVH to the paddle G1 (Stage 5B footwork style data, D-047).

Uses GMR's own LAFAN1 -> G1 mapping (ik_configs/bvh_lafan1_to_g1.json, LAFAN1 loader) with this project's pipeline
from tennis_retarget.py:
- the IK runs on GMR's G1 with the paddle G1's capsules and paddle (capsule_model_xml), with self-collision avoidance
  (arms vs body, hand vs hand, paddle vs body; the paddle has no orientation target here);
- warm start at the human's pose, feet grounded, the same checks and an acceptance filter.
LAFAN1 is 30 fps; CSVs are written at 30 fps (convert with csv_to_npz_local.py --input-fps 30).

LAFAN1 is CC BY-NC-ND 4.0: everything this writes stays under the git-ignored artifacts/motion/.

Usage (GMR venv):
    python scripts/motion/lafan_retarget.py BVH [BVH ...] --out artifacts/motion/lafan-g1 [--max-seconds S]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tennis_retarget as tr  # noqa: E402  (also installs the mink 1.3 shim)
from general_motion_retargeting import GeneralMotionRetargeting as GMR  # noqa: E402
from general_motion_retargeting import params as gmr_params  # noqa: E402
from general_motion_retargeting.utils.lafan1 import load_bvh_file  # noqa: E402

FPS = 30
# Bodies with a position target in GMR's LAFAN1 config whose origin is at the human joint they follow (hip_yaw and
# shoulder_yaw sit 10-27 cm from the hip/shoulder joint, so they are left out of the error measure).
ERR_BODIES = {"pelvis": "Hips", "left_knee_link": "LeftLeg", "right_knee_link": "RightLeg",
              "left_ankle_roll_link": "LeftFootMod", "right_ankle_roll_link": "RightFootMod",
              "left_elbow_link": "LeftForeArm", "right_elbow_link": "RightForeArm",
              "left_wrist_yaw_link": "LeftHand", "right_wrist_yaw_link": "RightHand"}
ACCEPT_MEDIAN_M, ACCEPT_P95_M = 0.08, 0.20  # as tennis (retarget_summary.py)


def make_retargeter(out: Path, height: float):
    gmr_params.ROBOT_XML_DICT["unitree_g1"] = tr.capsule_model_xml(out / "g1_capsules.xml")
    rt = GMR(src_human="bvh_lafan1", tgt_robot="unitree_g1", actual_human_height=height, verbose=False)
    rt.ik_limits.extend(tr.collision_limit(rt.model))
    return rt


def warm_start(rt, frame, iters=50):
    rt.update_targets(frame)
    pos, quat = rt.scaled_human_data["Hips"]
    q = np.zeros(rt.model.nq)
    q[0:3], q[3:7] = pos, quat
    rt.configuration.update(q)
    for _ in range(iters):
        rt.retarget(frame)


def retarget_clip(path: Path, out: Path, max_seconds):
    frames, height = load_bvh_file(str(path), format="lafan1")
    if max_seconds:
        frames = frames[: int(max_seconds * FPS)]
    rt = make_retargeter(out, height)
    warm_start(rt, frames[0])
    qs, errs, pos_err = [], [], []
    for f in frames:
        qs.append(rt.retarget(f))
        errs.append(rt.error2())
        robot = np.array([rt.configuration.data.xpos[rt.model.body(b).id] for b in ERR_BODIES])
        target = np.array([rt.scaled_human_data[h][0] for h in ERR_BODIES.values()])
        pos_err.append(np.linalg.norm(robot - target, axis=1))
    qs = np.array(qs)
    qs[:, 2] -= tr.ground_shift(rt.model, qs)
    csv = np.concatenate([qs[:, :3], qs[:, [4, 5, 6, 3]], qs[:, 7:]], axis=1)  # wxyz -> xyzw
    np.savetxt(out / f"{path.stem}.csv", csv, delimiter=",")
    for f in frames:  # tr.checks reads the hands under the tennis skeleton's names
        f["LeftWrist"], f["RightWrist"] = f["LeftHand"], f["RightHand"]
    rep = {"source": path.name, "human_height_m": round(float(height), 3), **tr.checks(rt.model, qs, errs, frames, FPS)}
    pe = np.array(pos_err)
    rep["pos_err_median_m"] = round(float(np.median(pe)), 4)
    rep["pos_err_p95_m"] = round(float(np.percentile(pe, 95)), 4)
    rep["pos_err_by_body_median_m"] = {b: round(float(np.median(pe[:, i])), 3) for i, b in enumerate(ERR_BODIES)}
    root = qs[:, :2]
    rep["root_path_m"] = round(float(np.linalg.norm(np.diff(root, axis=0), axis=1).sum()), 1)
    rep["root_speed_p90_mps"] = round(float(np.percentile(np.linalg.norm(np.diff(root, axis=0), axis=1) * FPS, 90)), 2)
    rep["accepted"] = rep["pos_err_median_m"] <= ACCEPT_MEDIAN_M and rep["pos_err_p95_m"] <= ACCEPT_P95_M
    (out / f"{path.stem}.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: rep[k] for k in ("source", "seconds", "pos_err_median_m", "pos_err_p95_m", "accepted",
                                          "root_path_m", "joint_limit_frac_frames")}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bvh", nargs="+")
    ap.add_argument("--out", default="artifacts/motion/lafan-g1")
    ap.add_argument("--max-seconds", type=float, default=None)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    failed = []
    for p in map(Path, args.bvh):
        try:
            retarget_clip(p, out, args.max_seconds)
        except Exception as e:  # one bad clip must not stop the batch
            failed.append(p.name)
            print(json.dumps({"source": p.name, "error": f"{type(e).__name__}: {e}"}))
    accepted = sorted(json.loads(j.read_text())["source"][:-4] for j in out.glob("*.json")
                      if j.name != "accepted.json" and isinstance(json.loads(j.read_text()), dict)
                      and json.loads(j.read_text()).get("accepted"))
    (out / "accepted.json").write_text(json.dumps(accepted, indent=1))
    if failed:
        print("failed:", failed)


if __name__ == "__main__":
    main()

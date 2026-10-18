"""Retarget the filtered 100STYLE clips to the paddle G1 (Stage 5E footwork style data, D-101).

**Filter rule and split** (frozen before extraction): `results/stage5e-style-reference.md`.
- Neutral style; FW, BW, SW and SR content.
- Frames inside 100STYLE's Frame_Cuts.csv range.
- The first 70 % of each clip is the training part; the last 30 % is the held-out reference slice.

**Pipeline.** It is that of `lafan_retarget.py`: GMR IK on the paddle G1's capsule model with self-collision limits, a
warm start, the same checks and acceptance thresholds. The joint map is GMR's LAFAN1 -> G1 table, with the 100STYLE
joints renamed onto the LAFAN1 names:
- Hips -> Hips; Chest4 -> Spine2;
- Hip -> UpLeg, Knee -> Leg, Ankle -> FootMod;
- Shoulder -> Arm, Elbow -> ForeArm, Wrist -> Hand.

**Rotation offsets.** These are computed, not copied. 100STYLE's rest pose (all channels zero) is a T-pose facing +Z
with every joint frame equal to the BVH frame. After the Y-up -> Z-up conversion of GMR's BVH loader, every human
joint's world orientation at rest is the conversion rotation q_c, and the human faces world -y. GMR's target for a
robot body is (human orientation) * (offset). Each offset is therefore q_c^-1 * R_b, where R_b is that body's world
orientation with the G1 in a T-pose turned to face -y:
- arms abducted level;
- elbows straight;
- every other joint at zero.

100STYLE is 60 fps; clips are resampled to 30 fps (every second frame) and written as CSV at 30 fps (convert with
csv_to_npz_local.py --input-fps 30). Outputs stay in the git-ignored artifacts/motion/.

Usage (GMR venv):
    python scripts/motion/style100_retarget.py --src artifacts/motion/100style/100STYLE --out artifacts/motion/style100-g1
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import mujoco as mj
import numpy as np
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lafan_retarget as lr  # noqa: E402
import tennis_retarget as tr  # noqa: E402  (also installs the mink 1.3 shim)
from general_motion_retargeting import GeneralMotionRetargeting as GMR  # noqa: E402
from general_motion_retargeting import params as gmr_params  # noqa: E402
import general_motion_retargeting.utils.lafan_vendor.utils as bvh_utils  # noqa: E402
from general_motion_retargeting.utils.lafan_vendor.extract import read_bvh  # noqa: E402

STYLE = "Neutral"
KEEP = ("FW", "BW", "SW", "SR")
TRAIN_SHARE = 0.7
FPS_IN, FPS = 60, 30
HEIGHT = 1.75
RENAME = {"Hips": "Hips", "Chest4": "Spine2",
          "LeftHip": "LeftUpLeg", "RightHip": "RightUpLeg", "LeftKnee": "LeftLeg", "RightKnee": "RightLeg",
          "LeftAnkle": "LeftFootMod", "RightAnkle": "RightFootMod",
          "LeftShoulder": "LeftArm", "RightShoulder": "RightArm", "LeftElbow": "LeftForeArm",
          "RightElbow": "RightForeArm", "LeftWrist": "LeftHand", "RightWrist": "RightHand"}
Y_UP_TO_Z_UP = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]])  # as GMR's BVH loader


def frame_cuts(src: Path) -> dict[str, tuple[int, int]]:
    with open(src / "Frame_Cuts.csv") as f:
        row = next(r for r in csv.DictReader(f) if r["STYLE_NAME"] == STYLE)
    return {c: (int(row[f"{c}_START"]), int(row[f"{c}_STOP"])) for c in KEEP}


def load_frames(path: Path, start: int, stop: int) -> list[dict]:
    """Human frames {LAFAN1 name: [pos (m, z-up), quat wxyz]} for BVH frames start..stop, at 30 fps."""
    data = read_bvh(str(path))
    gq, gp = bvh_utils.quat_fk(data.quats, data.pos, data.parents)
    qc = R.from_matrix(Y_UP_TO_Z_UP).as_quat(scalar_first=True)
    idx = {b: i for i, b in enumerate(data.bones)}
    frames = []
    for t in range(start, min(stop, gp.shape[0]), FPS_IN // FPS):
        f = {}
        for src, dst in RENAME.items():
            i = idx[src]
            f[dst] = [gp[t, i] @ Y_UP_TO_Z_UP.T / 100.0, bvh_utils.quat_mul(qc, gq[t, i])]
        frames.append(f)
    return frames


def tpose_offsets(model: mj.MjModel, bodies: list[str]) -> dict[str, list[float]]:
    """Rotation offset (wxyz) per robot body: q_c^-1 * (body orientation in the G1 T-pose facing -y)."""
    data = mj.MjData(model)
    q = np.zeros(model.nq)
    q[3:7] = R.from_euler("z", -90, degrees=True).as_quat(scalar_first=True)  # face world -y, as the human
    jadr = lambda name: model.jnt_qposadr[model.joint(name).id]

    def wrist_reach(qq):
        data.qpos[:] = qq
        mj.mj_kinematics(model, data)
        out = {}
        for s in ("left", "right"):
            sh = data.xpos[model.body(f"{s}_shoulder_roll_link").id]
            wr = data.xpos[model.body(f"{s}_wrist_yaw_link").id]
            out[s] = (abs(wr[2] - sh[2]), np.linalg.norm(wr[:2] - sh[:2]))
        return out

    for s in ("left", "right"):  # shoulder roll and elbow that put each arm level and straight
        best = None
        for roll in np.linspace(-np.pi / 2, np.pi / 2, 181):
            for elbow in np.linspace(-1.0, 2.0, 61):
                qq = q.copy()
                qq[jadr(f"{s}_shoulder_roll_joint")], qq[jadr(f"{s}_elbow_joint")] = roll, elbow
                dz, dxy = wrist_reach(qq)[s]
                score = dxy - 3.0 * dz
                if best is None or score > best[0]:
                    best = (score, roll, elbow)
        q[jadr(f"{s}_shoulder_roll_joint")], q[jadr(f"{s}_elbow_joint")] = best[1], best[2]
    data.qpos[:] = q
    mj.mj_kinematics(model, data)
    qc_inv = R.from_matrix(Y_UP_TO_Z_UP).inv()
    return {b: (qc_inv * R.from_matrix(data.xmat[model.body(b).id].reshape(3, 3))).as_quat(scalar_first=True).tolist()
            for b in bodies}


def write_config(out: Path, model: mj.MjModel) -> Path:
    base = Path(gmr_params.IK_CONFIG_DICT["bvh_lafan1"]["unitree_g1"])
    cfg = json.loads(base.read_text())
    bodies = sorted(set(cfg["ik_match_table1"]) | set(cfg["ik_match_table2"]))
    off = tpose_offsets(model, bodies)
    for t in ("ik_match_table1", "ik_match_table2"):
        for b, entry in cfg[t].items():
            entry[4] = off[b]
    path = out / "bvh_100style_to_g1.json"
    path.write_text(json.dumps(cfg, indent=1))
    gmr_params.IK_CONFIG_DICT["bvh_100style"] = {"unitree_g1": path}
    return path


def retarget_part(name: str, frames: list[dict], out: Path, rt) -> dict:
    lr.warm_start(rt, frames[0])
    qs, errs, pos_err = [], [], []
    for f in frames:
        qs.append(rt.retarget(f))
        errs.append(rt.error2())
        robot = np.array([rt.configuration.data.xpos[rt.model.body(b).id] for b in lr.ERR_BODIES])
        target = np.array([rt.scaled_human_data[h][0] for h in lr.ERR_BODIES.values()])
        pos_err.append(np.linalg.norm(robot - target, axis=1))
    qs = np.array(qs)
    qs[:, 2] -= tr.ground_shift(rt.model, qs)
    csv_ = np.concatenate([qs[:, :3], qs[:, [4, 5, 6, 3]], qs[:, 7:]], axis=1)  # wxyz -> xyzw
    np.savetxt(out / f"{name}.csv", csv_, delimiter=",")
    for f in frames:  # tr.checks reads the hands under the tennis skeleton's names
        f["LeftWrist"], f["RightWrist"] = f["LeftHand"], f["RightHand"]
    rep = {"source": name, **tr.checks(rt.model, qs, errs, frames, FPS)}
    pe = np.array(pos_err)
    rep["pos_err_median_m"] = round(float(np.median(pe)), 4)
    rep["pos_err_p95_m"] = round(float(np.percentile(pe, 95)), 4)
    rep["pos_err_by_body_median_m"] = {b: round(float(np.median(pe[:, i])), 3) for i, b in enumerate(lr.ERR_BODIES)}
    # D-101 foot checks: sliding while a foot is down, and ground contact (feet neither through nor floating above it).
    data = mj.MjData(rt.model)
    sole = []
    for q in qs:
        data.qpos[:] = q
        mj.mj_kinematics(rt.model, data)
        sole.append(min(data.xpos[rt.model.body(f"{s}_ankle_roll_link").id, 2] for s in ("left", "right")))
    sole = np.array(sole)
    rep["skate_median_mps"] = max(rep["left_skate_median_mps"], rep["right_skate_median_mps"])
    rep["penetration_max_m"] = round(float(max(0.0, sole.min() - np.percentile(sole, 1))), 4)
    rep["lower_ankle_above_its_p1_median_m"] = round(float(np.median(sole - np.percentile(sole, 1))), 4)
    root = qs[:, :2]
    step = np.linalg.norm(np.diff(root, axis=0), axis=1)
    rep["root_path_m"] = round(float(step.sum()), 1)
    rep["root_speed_median_mps"] = round(float(np.median(step) * FPS), 2)
    rep["root_speed_p90_mps"] = round(float(np.percentile(step * FPS, 90)), 2)
    rep["accepted"] = bool(rep["pos_err_median_m"] <= lr.ACCEPT_MEDIAN_M and rep["pos_err_p95_m"] <= lr.ACCEPT_P95_M
                           and rep["skate_median_mps"] <= 0.10 and rep["penetration_max_m"] <= 0.02)
    (out / f"{name}.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: rep[k] for k in ("source", "seconds", "pos_err_median_m", "pos_err_p95_m", "skate_median_mps",
                                          "root_speed_median_mps", "accepted", "joint_limit_frac_frames")}))
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="artifacts/motion/100style/100STYLE")
    ap.add_argument("--out", default="artifacts/motion/style100-g1")
    ap.add_argument("--max-seconds", type=float, default=None, help="checks only: cut each part")
    args = ap.parse_args()
    src, out = Path(args.src), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    model = mj.MjModel.from_xml_path(str(tr.capsule_model_xml(out / "g1_capsules.xml")))
    print("config:", write_config(out, model))
    gmr_params.ROBOT_XML_DICT["unitree_g1"] = tr.capsule_model_xml(out / "g1_capsules.xml")
    cuts = frame_cuts(src)
    reports = []
    for c in KEEP:
        a, b = cuts[c]
        frames = load_frames(src / STYLE / f"{STYLE}_{c}.bvh", a, b)
        k = int(round(TRAIN_SHARE * len(frames)))
        for part, fr in (("train", frames[:k]), ("ref", frames[k:])):
            if args.max_seconds:
                fr = fr[: int(args.max_seconds * FPS)]
            rt = GMR(src_human="bvh_100style", tgt_robot="unitree_g1", actual_human_height=HEIGHT, verbose=False)
            rt.ik_limits.extend(tr.collision_limit(rt.model))
            reports.append(retarget_part(f"{STYLE}_{c}_{part}", fr, out, rt))
    (out / "accepted.json").write_text(json.dumps(sorted(r["source"] for r in reports if r["accepted"]), indent=1))
    (out / "summary.json").write_text(json.dumps(reports, indent=1))


if __name__ == "__main__":
    main()

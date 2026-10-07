"""Retarget Tennis-MoCap BVH (OptiTrack Arena skeleton) to the G1 with GMR (Stage 5B, D-046).

GMR ships no mapping for this skeleton, so the IK config is built here from the two rest poses:
the human T-pose (all BVH rotations zero) and a G1 T-pose (TPOSE). For every mapped body:
    target = q_human * offset,   offset = Q0^-1 * H * R_tpose
Q0 turns BVH Y-up into Z-up, H turns the human's facing (-y) into the robot's (+x), and R_tpose is the link's
world rotation in the G1 T-pose. Per-bone scales come from the same two poses (scale_table).

Runs in the GMR venv (~/envs/gmr):
    python scripts/motion/tennis_retarget.py BVH [BVH ...] --out artifacts/motion/retargeted [--fps 50]
Writes per clip: <name>.csv (mjlab layout: base xyz, base quat xyzw, 29 joints in GMR/G1 order) and
<name>.json (checks: joint-limit hits, foot height/skate, IK residuals, right-wrist speed, handedness).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from pathlib import Path

import mink
import mujoco as mj
import numpy as np
from scipy.spatial.transform import Rotation as R

from general_motion_retargeting import GeneralMotionRetargeting as GMR
from general_motion_retargeting import params as gmr_params
import general_motion_retargeting.utils.lafan_vendor.utils as lafan_utils
from general_motion_retargeting.utils.lafan_vendor.extract import read_bvh

# GMR calls mink.solve_ik(cfg, tasks, dt, solver, damping, ik_limits) positionally, but mink 1.3 inserted
# `safety_break` before `limits`: the limits list lands in safety_break (truthy -> float round-off at a joint limit
# raises) and `limits` falls back to mink's default. Re-route it.
_solve_ik = mink.solve_ik


def _solve_ik_compat(configuration, tasks, dt, solver, damping=1e-12, safety_break=False, limits=None, **kw):
    if not isinstance(safety_break, bool):
        safety_break, limits = False, safety_break
    return _solve_ik(configuration, tasks, dt, solver, damping, safety_break=safety_break, limits=limits, **kw)


mink.solve_ik = _solve_ik_compat

Q0 = R.from_matrix(np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], dtype=float))  # BVH Y-up -> Z-up
H = R.from_euler("z", -90, degrees=True)  # robot +x -> human facing (-y after Q0)
G1_XML = gmr_params.ROBOT_XML_DICT["unitree_g1"]

# Human bones sit at the joints, so positions map to the G1 link whose origin is that joint (hip_roll_link,
# shoulder_roll_link, elbow_link, wrist_roll_link); the pelvis is offset up from the hip centre (pelvis_above_hips).
# Thigh and upper-arm rotations need the yaw links, so those bones also drive the yaw link through an alias
# "<bone>~rot" (GMR allows one task per human bone).
# robot body -> (human bone, table1 (pos, rot) weights, table2 (pos, rot) weights).
# Weight pattern follows GMR's LAFAN1 -> G1 config, except the hands: position only, because the Arena hand rest
# orientation points down rather than along the forearm (wrist joints sat at their limits in 90 % of frames). The
# human Wrist bone is the wrist joint, so it maps to wrist_roll_link (the G1 wrist joint); wrist angles stay at 0.
MAP = {
    "pelvis": ("Hips", (0, 10), (100, 5)),
    "torso_link": ("Chest", (0, 100), (0, 10)),
    "left_hip_roll_link": ("LeftHip", (1, 0), (10, 0)),
    "left_hip_yaw_link": ("LeftHip~rot", (0, 10), (0, 5)),
    "left_knee_link": ("LeftKnee", (0, 10), (10, 5)),
    "left_ankle_roll_link": ("LeftAnkle", (50, 10), (50, 10)),
    "right_hip_roll_link": ("RightHip", (1, 0), (10, 0)),
    "right_hip_yaw_link": ("RightHip~rot", (0, 10), (0, 5)),
    "right_knee_link": ("RightKnee", (0, 10), (10, 5)),
    "right_ankle_roll_link": ("RightAnkle", (50, 10), (50, 10)),
    "left_shoulder_roll_link": ("LeftShoulder", (1, 0), (5, 0)),
    "left_shoulder_yaw_link": ("LeftShoulder~rot", (0, 100), (0, 100)),
    "left_elbow_link": ("LeftElbow", (0, 10), (10, 5)),
    "left_wrist_roll_link": ("LeftWrist", (1, 0), (10, 0)),
    "right_shoulder_roll_link": ("RightShoulder", (1, 0), (5, 0)),
    "right_shoulder_yaw_link": ("RightShoulder~rot", (0, 100), (0, 100)),
    "right_elbow_link": ("RightElbow", (0, 10), (10, 5)),
    "right_wrist_roll_link": ("RightWrist", (1, 0), (10, 0)),
}
# G1 T-pose matching the BVH rest pose: arms straight out to the sides (the G1's zero pose has the elbows bent
# 90 deg with the forearm forward; +90 deg straightens them, inside the joint range).
TPOSE = {"left_shoulder_roll_joint": np.pi / 2, "right_shoulder_roll_joint": -np.pi / 2,
         "left_elbow_joint": np.pi / 2, "right_elbow_joint": np.pi / 2}
HEIGHT_ASSUMPTION = 1.8
POS_BODIES = [n for n, (b, w1, w2) in MAP.items() if w2[0] > 0]  # bodies with a position target
MAP_BONES = [v[0] for v in MAP.values()]


def add_aliases(frame):
    for k in [b for b in MAP_BONES if b.endswith("~rot")]:
        frame[k] = frame[k[:-4]]
    return frame


def load_bvh(path):
    """Frames as {bone: (pos m, quat wxyz)} in Z-up world, plus rest offsets (Z-up, m) and the human height."""
    # The vendored parser splits frame lines on single spaces; Arena exports pad with runs of spaces.
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in Path(path).read_text().splitlines() if ln.strip()]
    # Some exports hold more frame lines than the "Frames:" header says; keep the declared number.
    head = next(i for i, ln in enumerate(lines) if ln.startswith("Frame Time"))
    n = int(next(ln for ln in lines if ln.startswith("Frames:")).split()[1])
    text = "\n".join(lines[: head + 1 + n])
    with tempfile.NamedTemporaryFile("w", suffix=".bvh", delete=False) as tmp:
        tmp.write(text + "\n")
    data = read_bvh(tmp.name)
    os.unlink(tmp.name)
    rot, pos = lafan_utils.quat_fk(data.quats, data.pos, data.parents)
    q0 = Q0.as_quat(scalar_first=True)
    m = Q0.as_matrix()
    frames = []
    for f in range(pos.shape[0]):
        frames.append({b: [pos[f, i] @ m.T / 100.0, lafan_utils.quat_mul(q0, rot[f, i])]
                       for i, b in enumerate(data.bones)})
    rest = {b: data.offsets[i] @ m.T / 100.0 for i, b in enumerate(data.bones)}
    f0 = frames[0]
    height = float(f0["Head"][0][2] - min(f0["LeftAnkle"][0][2], f0["RightAnkle"][0][2])) + 0.25  # head top + foot
    return frames, rest, height, data.bones


def robot_tpose(model):
    data = mj.MjData(model)
    data.qpos[:] = 0
    data.qpos[3] = 1.0
    for j, v in TPOSE.items():
        data.qpos[model.jnt_qposadr[model.joint(j).id]] = v
    mj.mj_forward(model, data)
    return data


def build_config(rest):
    """offset = Q0^-1 * H * R_tpose: the human rest pose (every bone at Q0) maps onto the G1 T-pose, facing +x."""
    model = mj.MjModel.from_xml_path(str(G1_XML))
    data = robot_tpose(model)
    t1, t2 = {}, {}
    for body, (bone, w1, w2) in MAP.items():
        r_t = R.from_matrix(data.xmat[model.body(body).id].reshape(3, 3))
        off = (Q0.inv() * H * r_t).as_quat(scalar_first=True).tolist()
        p_off = [0.0, 0.0, pelvis_above_hips(model)] if body == "pelvis" else [0.0, 0.0, 0.0]  # in the link frame
        t1[body] = [bone, w1[0], w1[1], p_off, off]
        t2[body] = [bone, w2[0], w2[1], p_off, off]
    return {"robot_root_name": "pelvis", "human_root_name": "Hips", "ground_height": 0.0,
            "human_height_assumption": HEIGHT_ASSUMPTION, "use_ik_match_table1": True, "use_ik_match_table2": True,
            "human_scale_table": scale_table(model, rest), "ik_match_table1": t1, "ik_match_table2": t2}


def rest_positions(rest, bones_parent):
    pos = {}
    for b, p in bones_parent.items():
        pos[b] = np.zeros(3) if p is None else pos[p] + rest[b]
    return pos


PARENT = {"Hips": None, "Chest": "Hips", "Neck": "Chest", "Head": "Neck"}
for _s in ("Left", "Right"):
    PARENT.update({f"{_s}Collar": "Chest", f"{_s}Shoulder": f"{_s}Collar", f"{_s}Elbow": f"{_s}Shoulder",
                   f"{_s}Wrist": f"{_s}Elbow", f"{_s}Hip": "Hips", f"{_s}Knee": f"{_s}Hip", f"{_s}Ankle": f"{_s}Knee"})


def hip_centre(model, data):
    return 0.5 * (data.xpos[model.body("left_hip_roll_link").id] + data.xpos[model.body("right_hip_roll_link").id])


def pelvis_above_hips(model):
    data = robot_tpose(model)
    return float(data.xpos[model.body("pelvis").id][2] - hip_centre(model, data)[2])


def scale_table(model, rest):
    """Per-bone scale = robot / human distance from the root, both in T-pose (robot_tpose).

    GMR scales each bone's position relative to the root by its factor, so this makes the scaled human T-pose land
    on the robot's T-pose body positions. Used with human_height_assumption == actual height (ratio 1).
    """
    data = robot_tpose(model)
    hp = rest_positions(rest, PARENT)
    root_r = hip_centre(model, data)  # the human root (Hips) is at hip-joint height; so is this
    table = {"Hips": 1.0}
    for body, (bone, *_w) in MAP.items():
        if bone == "Hips" or bone.endswith("~rot"):
            continue
        d_r = np.linalg.norm(data.xpos[model.body(body).id] - root_r)
        d_h = np.linalg.norm(hp[bone] - hp["Hips"])
        table[bone] = round(float(d_r / d_h), 4) if d_h > 1e-6 else 1.0
    # Root: hip-centre height over the ankles, robot / human (both standing straight); ground_shift fixes the rest.
    leg_h = -min(hp["LeftAnkle"][2], hp["RightAnkle"][2])
    leg_r = root_r[2] - data.xpos[model.body("left_ankle_roll_link").id][2]
    table["Hips"] = round(float(leg_r / leg_h), 4)
    for bone in MAP_BONES:
        if bone.endswith("~rot"):
            table[bone] = table[bone[:-4]]  # rotation-only alias: its position is not tracked
    return table


STAND_ANKLE_Z = 0.036  # G1 ankle_roll_link height with the foot flat on the ground (zero pose)


def ground_shift(model, qs):
    """Height to subtract so the lowest ankle over the clip sits at the standing ankle height (feet on the ground)."""
    data = mj.MjData(model)
    ids = [model.body("left_ankle_roll_link").id, model.body("right_ankle_roll_link").id]
    low = np.inf
    for q in qs:
        data.qpos[:] = q
        mj.mj_kinematics(model, data)
        low = min(low, float(data.xpos[ids, 2].min()))
    return low - STAND_ANKLE_Z


def checks(model, qs, retargeter_errors, frames, fps):
    data = mj.MjData(model)
    lo, hi = model.jnt_range[1:, 0], model.jnt_range[1:, 1]
    joints = qs[:, 7:]
    margin = np.minimum(joints - lo, hi - joints)
    at_limit = margin < np.deg2rad(2)
    feet = {"left": model.body("left_ankle_roll_link").id, "right": model.body("right_ankle_roll_link").id}
    fz, fxy, wrist = {k: [] for k in feet}, {k: [] for k in feet}, []
    w = model.body("right_wrist_yaw_link").id
    for q in qs:
        data.qpos[:] = q
        mj.mj_kinematics(model, data)
        for k, i in feet.items():
            fz[k].append(data.xpos[i, 2])
            fxy[k].append(data.xpos[i, :2].copy())
        wrist.append(data.xpos[w].copy())
    out = {"frames": int(len(qs)), "fps": fps, "seconds": round(len(qs) / fps, 2)}
    names = [mj.mj_id2name(model, mj.mjtObj.mjOBJ_JOINT, j) for j in range(1, model.njnt)]
    out["joint_limit_frac_frames"] = float(at_limit.any(axis=1).mean())
    out["joints_at_limit"] = {n: round(float(at_limit[:, i].mean()), 3) for i, n in enumerate(names)
                              if at_limit[:, i].mean() > 0.05}
    for k in feet:
        z, xy = np.array(fz[k]), np.array(fxy[k])
        speed = np.r_[0, np.linalg.norm(np.diff(xy, axis=0), axis=1) * fps]
        low = z < z.min() + 0.03  # in contact (ankle-body height, near its lowest)
        out[f"{k}_ankle_z_min_m"] = round(float(z.min()), 3)
        out[f"{k}_skate_median_mps"] = round(float(np.median(speed[low])) if low.any() else 0.0, 3)
    ws = np.r_[0, np.linalg.norm(np.diff(np.array(wrist), axis=0), axis=1) * fps]
    out["right_wrist_speed_p99_mps"] = round(float(np.percentile(ws, 99)), 2)
    lw = np.array([f["LeftWrist"][0] for f in frames])
    rw = np.array([f["RightWrist"][0] for f in frames])
    sp = lambda p: float(np.percentile(np.linalg.norm(np.diff(p, axis=0), axis=1), 99))
    out["human_hand"] = "right" if sp(rw) >= sp(lw) else "left"
    out["ik_error_median"] = round(float(np.median(retargeter_errors)), 4)
    return out


def warm_start(rt, frame, iters=50):
    """Start the IK at the human's pose instead of the G1 zero pose facing +x.

    From the zero pose, clips where the player faces another way got stuck in a local minimum on the first frame
    (a shoulder pinned at its limits for the whole clip, ~15-20 cm median error). Place the pelvis at its target
    (position and heading), the arms in the T-pose, then settle on the first frame.
    """
    rt.update_targets(frame)
    pos, quat = rt.scaled_human_data["Hips"]
    q = np.zeros(rt.model.nq)
    q[0:3] = pos
    q[3:7] = quat  # already offset to the pelvis link frame (wxyz)
    for j, v in TPOSE.items():
        q[rt.model.jnt_qposadr[rt.model.joint(j).id]] = v
    rt.configuration.update(q)
    for _ in range(iters):
        rt.retarget(frame)


def make_retargeter(rest, cfg_path):
    cfg_path = Path(cfg_path)
    cfg_path.write_text(json.dumps(build_config(rest), indent=1))
    gmr_params.IK_CONFIG_DICT["bvh_tennis"] = {"unitree_g1": cfg_path}
    return GMR(src_human="bvh_tennis", tgt_robot="unitree_g1", actual_human_height=None, verbose=False)  # absolute


def retarget_rest(path, cfg_path):
    """Retarget the BVH rest pose (T-pose, hips over the ankles' standing height): should give the G1 TPOSE."""
    _, rest, _, bones = load_bvh(path)
    pos = rest_positions(rest, PARENT)
    lift = np.array([0.0, 0.0, -min(pos["LeftAnkle"][2], pos["RightAnkle"][2]) + 0.08])
    frame = add_aliases({b: [pos[b] + lift, Q0.as_quat(scalar_first=True)] for b in bones})
    rt = make_retargeter(rest, cfg_path)
    for _ in range(30):
        q = rt.retarget(frame)
    return rt.model, q


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bvh", nargs="+")
    ap.add_argument("--out", default="artifacts/motion/retargeted")
    ap.add_argument("--fps", type=int, default=50, help="output rate (source is 100 Hz; mjlab tracking uses 50)")
    ap.add_argument("--max-seconds", type=float, default=None)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    failed = []
    for path in map(Path, args.bvh):
        try:
            retarget_clip(path, out, args)
        except Exception as e:  # one bad clip must not stop the batch; it is listed at the end
            failed.append(path.name)
            print(json.dumps({"source": path.name, "error": f"{type(e).__name__}: {e}"}))
    if failed:
        print("failed:", failed)


def retarget_clip(path, out, args):
        frames, rest, height, _ = load_bvh(path)
        src_fps = 100
        frames = frames[:: src_fps // args.fps]
        if args.max_seconds:
            frames = frames[: int(args.max_seconds * args.fps)]
        rt = make_retargeter(rest, out / "bvh_tennis_to_g1.json")
        qs, errs, human, pos_err = [], [], [], []
        bones = list(MAP_BONES)
        warm_start(rt, add_aliases(frames[0]))
        for f in frames:
            qs.append(rt.retarget(add_aliases(f)))
            errs.append(rt.error2())
            human.append([rt.scaled_human_data[b][0] for b in bones])
            robot = np.array([rt.configuration.data.xpos[rt.model.body(n).id] for n in POS_BODIES])
            target = np.array([rt.scaled_human_data[MAP[n][0]][0] for n in POS_BODIES])
            pos_err.append(np.linalg.norm(robot - target, axis=1))
        qs = np.array(qs)
        qs[:, 2] -= ground_shift(rt.model, qs)
        np.savez(out / f"{path.stem}_human.npz", bones=np.array(bones), pos=np.array(human), fps=args.fps)
        csv = np.concatenate([qs[:, :3], qs[:, [4, 5, 6, 3]], qs[:, 7:]], axis=1)  # wxyz -> xyzw
        np.savetxt(out / f"{path.stem}.csv", csv, delimiter=",")
        rep = {"source": path.name, "human_height_m": round(height, 3), **checks(rt.model, qs, errs, frames, args.fps)}
        pe = np.array(pos_err)  # robot body vs scaled human target, before grounding (m)
        rep["pos_err_median_m"] = round(float(np.median(pe)), 4)
        rep["pos_err_p95_m"] = round(float(np.percentile(pe, 95)), 4)
        rep["pos_err_by_body_median_m"] = {n: round(float(np.median(pe[:, i])), 3) for i, n in enumerate(POS_BODIES)}
        (out / f"{path.stem}.json").write_text(json.dumps(rep, indent=1))
        print(json.dumps(rep))


if __name__ == "__main__":
    main()

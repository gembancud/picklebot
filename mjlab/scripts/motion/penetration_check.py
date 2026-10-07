"""Self-penetration in retargeted clips (Stage 5B): how deep and how often body parts and the paddle overlap.

The retargeting IK has no collision avoidance and the paddle geoms do not collide (contype 0), so clips can pass
limbs or the paddle through the body. This replays each clip kinematically on the paddle G1 with the paddle face
made collidable, and reads MuJoCo's contacts between robot geoms (the G1's own collision capsules; parent-child
pairs are filtered by MuJoCo; the paddle vs its own hand/wrist is ignored because it is held there).

Usage (picklebot-mj venv):
    python scripts/motion/penetration_check.py artifacts/motion/retargeted-v3 [--json OUT] [--clips a,b]
Per clip: fraction of frames with any overlap deeper than DEPTH_M, worst depth, and the same per pair category
(arm-torso, arm-leg, arm-arm, leg-leg, paddle-body). Summary per stroke type at the end.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import mjlab.tasks  # noqa: F401  (import order: avoids a circular import in picklebot_mj.g1_paddle)
import mujoco
import numpy as np

from picklebot_mj.g1_paddle import get_spec

DEPTH_M = 0.01  # overlaps shallower than this are capsule-fit noise
GMR_JOINTS = [
    "left_hip_pitch_joint", "left_hip_roll_joint", "left_hip_yaw_joint", "left_knee_joint", "left_ankle_pitch_joint",
    "left_ankle_roll_joint", "right_hip_pitch_joint", "right_hip_roll_joint", "right_hip_yaw_joint",
    "right_knee_joint", "right_ankle_pitch_joint", "right_ankle_roll_joint", "waist_yaw_joint", "waist_roll_joint",
    "waist_pitch_joint", "left_shoulder_pitch_joint", "left_shoulder_roll_joint", "left_shoulder_yaw_joint",
    "left_elbow_joint", "left_wrist_roll_joint", "left_wrist_pitch_joint", "left_wrist_yaw_joint",
    "right_shoulder_pitch_joint", "right_shoulder_roll_joint", "right_shoulder_yaw_joint", "right_elbow_joint",
    "right_wrist_roll_joint", "right_wrist_pitch_joint", "right_wrist_yaw_joint",
]
STROKES = {"Servicio": "serve", "Remate": "smash", "VDerecha": "forehand_volley", "VReves": "backhand_volley",
           "Derecha": "forehand", "Reves": "backhand"}


def part(body: str) -> str:
    if body == "paddle":
        return "paddle"
    if body in ("pelvis", "torso_link") or body.startswith("waist"):
        return "torso"
    if any(k in body for k in ("hip", "knee", "ankle")):
        return "leg"
    if any(k in body for k in ("shoulder", "elbow", "wrist", "hand")):
        return "arm"
    return "other"


def category(a: str, b: str) -> str:
    pa, pb = sorted((part(a), part(b)))
    if "paddle" in (pa, pb):
        return "paddle-body"
    if pa == pb == "arm":  # same arm (tight elbow: forearm vs upper-arm capsules) or hand against hand
        return "arm-self" if a.split("_")[0] == b.split("_")[0] else "arm-arm"
    return f"{pa}-{pb}"


def build_model():
    spec = get_spec()
    m = spec.compile()
    face = m.geom("paddle_face").id
    m.geom_contype[face] = m.geom_conaffinity[face] = 1
    m.geom_margin[:] = 0.0
    return m


def stroke_of(stem: str) -> str:
    tag = stem.split("_", 1)[1] if "_" in stem else stem
    for k in STROKES:  # VDerecha before Derecha
        if tag.startswith(k):
            return STROKES[k]
    return "other"


def check_clip(m, d, adr, csv: Path):
    motion = np.loadtxt(csv, delimiter=",", ndmin=2)
    paddle_hand = {m.body(n).id for n in ("right_wrist_roll_link", "right_wrist_pitch_link", "right_wrist_yaw_link")}
    paddle = m.body("paddle").id
    any_hit = np.zeros(len(motion), bool)
    worst = 0.0
    cat_frames, cat_worst = defaultdict(int), defaultdict(float)
    for i, row in enumerate(motion):
        d.qpos[0:3] = row[0:3]
        d.qpos[3:7] = row[[6, 3, 4, 5]]
        d.qpos[adr] = row[7:36]
        mujoco.mj_kinematics(m, d)
        mujoco.mj_collision(m, d)
        hits = {}
        for c in d.contact[: d.ncon]:
            if -c.dist < DEPTH_M:
                continue
            b1, b2 = m.geom_bodyid[c.geom1], m.geom_bodyid[c.geom2]
            if b1 == 0 or b2 == 0:
                continue
            if (b1 == paddle and b2 in paddle_hand) or (b2 == paddle and b1 in paddle_hand):
                continue
            cat = category(m.body(b1).name, m.body(b2).name)
            hits[cat] = max(hits.get(cat, 0.0), -c.dist)
        if hits:
            any_hit[i] = True
            worst = max(worst, max(hits.values()))
            for k, v in hits.items():
                cat_frames[k] += 1
                cat_worst[k] = max(cat_worst[k], v)
    n = len(motion)
    return {"clip": csv.stem, "stroke": stroke_of(csv.stem), "frames": n,
            "frac_frames": round(float(any_hit.mean()), 4), "worst_m": round(worst, 3),
            "by_category": {k: {"frac_frames": round(cat_frames[k] / n, 4), "worst_m": round(cat_worst[k], 3)}
                            for k in sorted(cat_frames)}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--json", default=None)
    ap.add_argument("--clips", default=None, help="comma-separated clip stems (default: accepted.json or all)")
    args = ap.parse_args()
    root = Path(args.dir)
    if args.clips:
        stems = args.clips.split(",")
    elif (root / "accepted.json").exists():
        stems = json.loads((root / "accepted.json").read_text())
    else:
        stems = sorted(p.stem for p in root.glob("*.csv"))
    m = build_model()
    d = mujoco.MjData(m)
    adr = [m.jnt_qposadr[m.joint(n).id] for n in GMR_JOINTS]
    reps = [check_clip(m, d, adr, root / f"{s}.csv") for s in stems]
    by = defaultdict(list)
    for r in reps:
        by[r["stroke"]].append(r)
    print(f"{'stroke':16s} clips  frames-with-overlap  worst(cm)  top categories (frac of frames, worst cm)")
    summary = {}
    for s, g in sorted(by.items()):
        fr = np.mean([r["frac_frames"] for r in g])
        wo = max(r["worst_m"] for r in g)
        cats = defaultdict(list)
        for r in g:
            for k, v in r["by_category"].items():
                cats[k].append((v["frac_frames"], v["worst_m"]))
        tops = sorted(((k, sum(f for f, _ in v) / len(g), max(w for _, w in v)) for k, v in cats.items()),
                      key=lambda x: -x[1])[:3]
        summary[s] = {"clips": len(g), "frac_frames": round(float(fr), 4), "worst_m": wo,
                      "categories": {k: {"frac_frames": round(f, 4), "worst_m": w} for k, f, w in tops}}
        print(f"{s:16s} {len(g):5d}  {fr:18.1%}  {100 * wo:8.1f}   "
              + ", ".join(f"{k} {f:.1%} ({100 * w:.1f})" for k, f, w in tops))
    if args.json:
        Path(args.json).write_text(json.dumps({"depth_threshold_m": DEPTH_M, "summary": summary, "clips": reps},
                                              indent=1))


if __name__ == "__main__":
    main()

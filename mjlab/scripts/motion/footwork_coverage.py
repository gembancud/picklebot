"""How much footwork the motion set contains (Stage 5B H0): seconds of each behaviour per clip type.

Heuristics on the reference motion (pelvis heading frame, 50 Hz):
- ready stance: feet >= 0.30 m apart sideways, pelvis >= 4 cm below its clip's standing height, speed < 0.3 m/s;
- lateral shuffle: sideways pelvis speed > 0.5 m/s and forward speed < half of it;
- crossover: during lateral motion, the feet swap sides (their sideways order flips);
- split-step: both feet off the ground (ankles > 4 cm above their lowest) for >= 2 frames while the pelvis moves
  < 1.5 m/s horizontally (a hop, not a running flight phase).
Usage (picklebot-mj venv): python scripts/motion/footwork_coverage.py MOTION.npz [--json OUT]
"""

import argparse
import json
from collections import defaultdict

import numpy as np

import mjlab.tasks  # noqa: F401
from mjlab.tasks.registry import load_env_cfg

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tracking_eval import scene_body_names  # noqa: E402

TAGS = (("Servicio", "serve"), ("Remate", "smash"), ("VDerecha", "forehand_volley"), ("VReves", "backhand_volley"),
        ("Derecha", "forehand"), ("Reves", "backhand"))


def kind(name):
    tag = name.split("_", 1)[1]
    if tag.startswith("subject"):
        return "lafan_" + name.split("_")[0].rstrip("0123456789")
    return next(s for k, s in TAGS if tag.startswith(k))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("motion")
    ap.add_argument("--task", default="Picklebot-Tracking-TennisLafan2-Huge-G1")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    d = np.load(a.motion)
    names = [str(n) for n in d["clip_names"]]
    st = d["clip_starts"]
    en = np.r_[st[1:], len(d["joint_pos"])]
    fps = float(d["fps"][0])
    bn = scene_body_names(load_env_cfg(a.task))
    pel, la, ra = bn.index("pelvis"), bn.index("left_ankle_roll_link"), bn.index("right_ankle_roll_link")
    out = defaultdict(lambda: defaultdict(float))
    for i, n in enumerate(names):
        p = d["body_pos_w"][st[i]:en[i]]
        q = d["body_quat_w"][st[i]:en[i], pel]
        v = d["body_lin_vel_w"][st[i]:en[i], pel]
        yaw = np.arctan2(2 * (q[:, 0] * q[:, 3] + q[:, 1] * q[:, 2]), 1 - 2 * (q[:, 2] ** 2 + q[:, 3] ** 2))
        fwd = np.stack([np.cos(yaw), np.sin(yaw)], 1)
        lat = np.stack([-np.sin(yaw), np.cos(yaw)], 1)
        vf, vl = (v[:, :2] * fwd).sum(1), (v[:, :2] * lat).sum(1)
        feet = p[:, la, :2] - p[:, ra, :2]
        side = (feet * lat).sum(1)  # > 0: left foot on the left
        z = p[:, pel, 2]
        stand = np.percentile(z, 90)
        speed = np.hypot(vf, vl)
        ready = (np.abs(side) >= 0.30) & (z <= stand - 0.04) & (speed < 0.3)
        shuffle = (np.abs(vl) > 0.5) & (np.abs(vf) < 0.5 * np.abs(vl))
        lateral = np.abs(vl) > 0.4
        crossings = np.r_[False, np.sign(side[1:]) != np.sign(side[:-1])] & lateral
        lz, rz = p[:, la, 2], p[:, ra, 2]
        air = (lz > lz.min() + 0.04) & (rz > rz.min() + 0.04) & (speed < 1.5)
        hop = air & np.r_[False, air[:-1]]
        k = kind(n)
        o = out[k]
        o["clips"] += 1
        o["seconds"] += len(z) / fps
        o["ready_s"] += ready.sum() / fps
        o["shuffle_s"] += shuffle.sum() / fps
        o["crossovers"] += int(crossings.sum())
        o["split_step_s"] += hop.sum() / fps
    print(f"{'type':24s} clips   min  ready(s) shuffle(s) crossovers split-step(s)")
    for k in sorted(out):
        o = out[k]
        print(f"{k:24s} {int(o['clips']):5d} {o['seconds'] / 60:5.1f} {o['ready_s']:9.0f} {o['shuffle_s']:10.0f} "
              f"{int(o['crossovers']):10d} {o['split_step_s']:12.1f}")
    if a.json:
        json.dump({k: dict(v) for k, v in out.items()}, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()

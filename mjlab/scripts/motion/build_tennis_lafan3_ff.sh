#!/usr/bin/env bash
# D-185: H0 fine-tune motion set = tennis-lafan3's three originals + the footwork specialist's accepted clips.
# merge_motions.py sets clip_source by input file (0 tennis-v5, 1 LAFAN1, 2 mirrored LAFAN1, 3 footwork-fast), so it is
# fed the originals, not tennis-lafan3.npz (whose 3-way split it would collapse). Asserts the first 549,350 frames equal
# tennis-lafan3.npz exactly and the clip / source counts. Output: artifacts/motion/tracking/tennis-lafan3-ff.npz.
set -euo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate
T=artifacts/motion/tracking; OUT=$T/tennis-lafan3-ff.npz
[ -s $OUT ] && { echo "$OUT exists"; exit 0; }
python -I scripts/motion/merge_motions.py $OUT $T/tennis-v5.npz $T/lafan-g1-v2.npz $T/lafan-g1-mirror.npz \
  artifacts/motion/footwork-fast/footwork-fast-src0.npz
python -I - $OUT $T/tennis-lafan3.npz artifacts/motion/footwork-fast/footwork-fast-src0.npz <<'PY'
import sys, numpy as np
m, ref, ff = (np.load(f) for f in sys.argv[1:4])
n = len(ref["joint_pos"])
for k in ("joint_pos", "body_pos_w", "body_quat_w"):
    assert np.array_equal(m[k][:n], ref[k]), k
assert np.array_equal(m["clip_starts"][:len(ref["clip_starts"])], ref["clip_starts"])
assert np.array_equal(m["clip_source"][:len(ref["clip_source"])], ref["clip_source"])
assert len(m["joint_pos"]) == n + len(ff["joint_pos"]) and float(m["fps"][0]) == 50.0
print("frames", len(m["joint_pos"]), "clips by source", np.bincount(m["clip_source"]).tolist(), "-> identical prefix OK")
PY

#!/usr/bin/env bash
# Feed-anchor check (audit 2026-10-28, environment F1; D-159). Start-anchored feeds aim from ROBOT_START y = 0.35 while
# the robot recovers to y = 0, so they land 0.35 m to its left. One variable: the anchor's y (task default 0.35 vs 0.0,
# --anchor-y), same checkpoint, same seeds, old bookkeeping (no --audit-fixes). Reads: the pairs read (M1 protocol,
# contact hand-off, 2,048 envs, 120 s, seed 4220000) and the direction split (seed 4220001), each at both anchors.
# Usage: anchor_check.sh CHECKPOINT TAG   (from the fix worktree; PICKLEBOT_LAM_R as the checkpoint needs)
# Diagnostic only: no selection. Reported: partner / feeder legal, P(5+) (old and with open rallies), per direction.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab-fix/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore PYTHONPATH=$PWD
CK=$1; TAG=$2; R=/mnt/f/dev/picklebot-mjlab/mjlab/results/anchor-$TAG
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120 --seed 4220000"
for y in default 0.0; do
  A=""; [ $y = default ] || A="--anchor-y $y"
  python scripts/stage2_eval.py --checkpoint $CK $PA $A --json $R-y$y-pairs.json > /tmp/anchor-$TAG.log 2>&1 || { echo "READ CRASHED: pairs $y"; tail -5 /tmp/anchor-$TAG.log; }
  python scripts/diag/feeder_speed_envelope.py --checkpoint $CK --seed 4220001 $A --json $R-y$y-dir.json > /tmp/anchor-$TAG.log 2>&1 || { echo "READ CRASHED: dir $y"; tail -5 /tmp/anchor-$TAG.log; }
  echo "anchor $y done"
done
python - $R <<'PY'
import json, sys
sys.path.insert(0, "scripts")
from rally_check import boot_low, pair_stats
R = sys.argv[1]
for y in ("default", "0.0"):
    p = json.load(open(f"{R}-y{y}-pairs.json"))["pairs"]; P = pair_stats(p)
    own, _ = boot_low(p["court_counts"], 1, 0); fed, _ = boot_low(p["court_counts"], 3, 2)
    d = json.load(open(f"{R}-y{y}-dir.json"))["directions"]
    dirs = {k: (v["feeds"], v["contact"], v["legal"]) for k, v in d.items()}
    print(f"anchor y {y}: partner legal {own:.4f}, feeder legal {fed:.4f}, P(5+) {P['p5']:.4f} (with open {p.get('p_len_ge_5_with_open')}), "
          f"rallies {P['rallies']}; directions (feeds, contact, legal) {dirs}")
PY

#!/usr/bin/env bash
# The damping premise read (the user, 2026-11-09: "what is our blocker specifically?"; registered by motion in round 92,
# voted by motion and RL in round 109, never run). Reads only, no training: Q (rally-d1s3cap8hr2 model_36793, lam_r 2 on
# the d1 base) with the leg, waist and ankle damping halved (mjlab's G1 damping ratio 2.0 -> 1.0; footwork_specialist
# with_loose_legs), everything else unchanged, zero-shot.
#   1. Footwork: Measure60 bridge drill (Picklebot-Footwork-Measure60-RallyLamR2-Loose-G1), dev 4220447, paired with the
#      standard read results/agility249-Q.json (same seed): first step to 1.5 m, sustained speed, arrival, falls.
#   2. Rally: frozen set-start pairs read, dev 4220449, standard and loose (P(5+), hazards, falls).
# Reported only; motion's round-109 PASS form is printed for reference, not as a verdict.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER
while pgrep -f "artifacts/videos/agility" > /dev/null; do sleep 30; done  # the user's video renders finish first
L=artifacts/train/logs/picklebot_return_stand; R=results/damp249
export PICKLEBOT_RES_BASE=/mnt/f/dev/picklebot-mjlab/mjlab/$L/2026-10-31_18-24-20_s5c-d1-fw1bS/model_32854.pt PICKLEBOT_LAM_R=2
Q=$L/2026-11-07_19-25-03_rally-d1s3cap8hr2/model_36793.pt
[ -s $R-fw-loose.json ] || python scripts/diag/footwork_eval.py --task Picklebot-Footwork-Measure60-RallyLamR2-Loose-G1 --checkpoint $Q \
  --envs 1024 --seconds 120 --seed 4220447 --move-prob 1.0 --json $R-fw-loose.json > $R-fw-loose.log 2>&1
PA="--move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120 --pair-drill-reset --seed 4220449"
[ -s $R-pairs-loose.json ] || python scripts/diag/eval_fs.py --checkpoint $Q --task Picklebot-Latent-Court-Res-Loose-G1 $PA --json $R-pairs-loose.json > $R-pairs-loose.log 2>&1
[ -s $R-pairs-std.json ] || python scripts/stage2_eval.py --checkpoint $Q --task Picklebot-Latent-Court-Res-G1 $PA --json $R-pairs-std.json > $R-pairs-std.log 2>&1
python - <<'PY' | tee $R-summary.txt
import json, os, sys
sys.path.insert(0, ".")
from picklebot_mj import bodyspeed_rule as bsr, d1_rule as dr
def med(h, b):
    n = sum(h); c = 0
    for i, x in enumerate(h):
        c += x
        if n and c >= n / 2:
            return (i + 0.5) * b
    return float("nan")
rows = {}
for tag, p in (("standard", "results/agility249-Q.json"), ("loose", "results/damp249-fw-loose.json")):
    if not os.path.exists(p):
        print(f"{tag}: no footwork read"); continue
    d = json.load(open(p)); c = d["move_drill"]["footwork"]; s = bsr.sectors(c)
    fs, fb = c["first_step_hist"], c.get("first_step_bin_s", 0.05)
    rows[tag] = {"first": [med(fs[i], fb) for i in range(8)], "sus": [x["sustained_p50"] for x in s], "peak": [x["peak_p50"] for x in s],
                 "arr": [x["arrival"] for x in s], "names": [x["name"] for x in s],
                 "falls": 1000 * d["robot_falls"] / (d["envs"] * d["sim_seconds"])}
print("Q, Measure60 bridge drill (spots 3-5 m), dev 4220447, mean actions: first step to 1.5 m (s) / sustained p50 (m/s) / peak p50 / arrival")
if rows:
    for i, nm in enumerate(next(iter(rows.values()))["names"]):
        print(f"  {nm:13s} " + "   ".join(f"{t} {r['first'][i]:.2f}s {r['sus'][i]:.2f} {r['peak'][i]:.2f} {r['arr'][i]:.3f}" for t, r in rows.items()))
    for t, r in rows.items():
        lb = (2, 3, 4)
        print(f"{t}: falls {r['falls']:.2f} per 1,000 env-s; left/back first step {sum(r['first'][i] for i in lb) / 3:.2f} s, "
              f"all {sum(r['first']) / 8:.2f} s; sustained all {sum(r['sus']) / 8:.2f} m/s, peak all {sum(r['peak']) / 8:.2f} m/s; "
              f"arrival {sum(r['arr']) / 8:.3f}")
for t in ("std", "loose"):
    p = f"results/damp249-pairs-{t}.json"
    if os.path.exists(p):
        h = dr.pooled_hazards([p]); q = dr.pooled_pairs([p]); d = json.load(open(p))
        print(f"set-start pairs dev 4220449, {t}: P(5+) {q['p5']:.4f}, feeder {q['feeder']:.4f}, (1-h0)(1-h1) {h['open2']:.4f}, "
              f"h0-h4 {' / '.join(f'{x:.3f}' for x in h['h'])}, falls {d['robot_falls']} of {d['envs']} envs")
print("(reference, motion round 109, not a verdict) PASS = left/back first step >= 0.10 s faster; falls <= 3.14 per 1,000 env-s; "
      "(1-h0)(1-h1) no more than 0.02 below standard")
PY
echo done > artifacts/train/damp249.done

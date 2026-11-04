#!/usr/bin/env bash
# D-211 (panel round 75, (i)): CONFIRM rally-d1s3lr3 (C, model_32598) against the parent d1s3 model_31399 on fresh dev
# seeds, reads only (no training). Pairs 4220341-4220344, direction 4220345-4220348 (reserved since D-208, never read).
# CONFIRMED = d1_rule.gain2(C, parent) on the fresh seeds (diff >= +1 point, lower bound > 0) and r19_guards (C fresh
# pooled vs parent fresh pooled) with no breach and d1_rule.replicated's mechanism bars (ready >= 0.25, falls per 1,000
# hits <= 1.3). Otherwise CONFIRM-FAIL (no promotion; panel). EVAL-FAIL if any of the 16 reads is missing.
# Reported only: drift_verdict, feeder legal, the parent's fresh vs D-204 P(5+) (0.3812), motion's dip / speed reads.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER PICKLEBOT_READY_LOG \
  PICKLEBOT_RESTART_OBS PICKLEBOT_RESTART_OBS_FREEZE PICKLEBOT_REF_CKPT PICKLEBOT_REF_COEF
pgrep -f "run-name |kickstart_h4|stage2_eval|footwork_eval|feeder_speed" > /dev/null && { echo "GPU busy: not started"; exit 1; }
R=results/conf75; L=artifacts/train/logs/picklebot_return_stand
BASE=/mnt/f/dev/picklebot-mjlab/mjlab/$L/2026-10-31_18-24-20_s5c-d1-fw1bS/model_32854.pt
P=$L/2026-11-01_12-07-09_rally-d1s3/model_31399.pt
CKC=$(ls -d $L/*_rally-d1s3lr3 | tail -1)/model_32598.pt
for f in $BASE $P $CKC; do [ -f $f ] || { echo "missing $f"; exit 1; }; done
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120"
onbase() { PICKLEBOT_RES_BASE=$BASE PICKLEBOT_LAM_R=2 "$@"; }
echo "D-211: CONFIRM C = rally-d1s3lr3 model_32598 vs parent model_31399; fresh dev 4220341-4220348; $CKC" > $R-summary.txt
reads() {  # tag, checkpoint
  for s in 4220341 4220342 4220343 4220344; do [ -s $R-$1-pairs-$s.json ] || onbase python scripts/stage2_eval.py --checkpoint $2 $PA --seed $s --json $R-$1-pairs-$s.json >> $R-reads.log 2>&1; done
  for s in 4220345 4220346 4220347 4220348; do [ -s $R-$1-dir-$s.json ] || onbase python scripts/diag/feeder_speed_envelope.py --checkpoint $2 --seed $s --json $R-$1-dir-$s.json >> $R-reads.log 2>&1; done
}
reads parent $P
reads C $CKC
python - <<'PY' | tee -a $R-summary.txt
import json, os, sys
sys.path.insert(0, "scripts"); sys.path.insert(0, ".")
import rally_check as rc
from picklebot_mj import d1_rule as dr
R = "results/conf75"
S = (4220341, 4220342, 4220343, 4220344); D = (4220345, 4220346, 4220347, 4220348)
arm = {w: ([f"{R}-{w}-pairs-{s}.json" for s in S], [f"{R}-{w}-dir-{s}.json" for s in D]) for w in ("parent", "C")}
if not all(os.path.exists(f) for w in arm for f in arm[w][0] + arm[w][1]):
    print("RESULT EVAL-FAIL"); sys.exit(0)
pooled = {}
for w in arm:
    pf, pd = dr.pool_reads(*arm[w])
    json.dump(pf, open(f"{R}-{w}-pooled-pairs.json", "w"), indent=1); json.dump(pd, open(f"{R}-{w}-pooled-dir.json", "w"), indent=1)
    pooled[w] = (pf, pd, dr.pooled_pairs(arm[w][0]))
ok_g, d, lo, line = dr.gain2(arm["C"][0], arm["parent"][0]); print("GAIN2 " + line)
print("C (fresh pooled) against the parent (fresh pooled):")
g = rc.r19_guards(pooled["C"][0]["per_family"], pooled["C"][1]["directions"], ref=f"{R}-parent-pooled",
                  cross_ref=f"{R}-parent-pooled-pairs.json", name="parent (fresh)", cross_name="parent (fresh)")
m = dr.mechanism(arm["C"][0])
print(f"mechanism C: ready {m['ready']:.3f} (>= {dr.REP_READY}), falls/1000 hits {m['falls_per_1000_hits']:.2f} (<= {dr.REP_FALLS}), "
      f"WRONG_SIDE {m['wrong_side_share']:.3f}, recovery {m['recovery_median_m']:.3f} m")
mp = dr.mechanism(arm["parent"][0])
print(f"(reported) mechanism parent: ready {mp['ready']:.3f}, falls/1000 hits {mp['falls_per_1000_hits']:.2f}, WRONG_SIDE {mp['wrong_side_share']:.3f}, recovery {mp['recovery_median_m']:.3f} m")
ms = dr.mean_family_shift(pooled["C"][0]["per_family"], pooled["parent"][0]["per_family"])
pc, pp = pooled["C"][2], pooled["parent"][2]
print(f"(reported) feeder legal C {pc['feeder']:.4f} vs parent {pp['feeder']:.4f}; P(5+) C {pc['p5']:.4f} vs parent {pp['p5']:.4f} "
      f"(parent D-204 0.3812, C D-204 0.4115); mean family shift {100 * ms:+.2f}; drift_verdict {dr.drift_verdict(g, ms, pc['feeder'], pp['feeder'], pc['p5'], pp['p5'])}")
ok = dr.replicated(ok_g, m) and g
json.dump({"gain2": ok_g, "diff": d, "lower": lo, "guards": g, "mechanism": m, "confirmed": ok}, open(f"{R}-summary.json", "w"), indent=1)
print(f"RESULT {'CONFIRMED' if ok else 'CONFIRM-FAIL'}")
PY
echo "VERDICT: $(tail -1 $R-summary.txt | cut -d' ' -f2)" | tee -a $R-summary.txt
echo done > artifacts/train/conf75.done

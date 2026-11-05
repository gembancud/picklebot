#!/usr/bin/env bash
# D-224 (panel round 87: (i) 5 of 5; read plan by the tie rule, experiment design's). D-223 with the hand-off tally fixed:
# PairCourts.ho_live (set on receive; cleared for both envs at a feeder ball, on reset, and once tallied) gates the tally,
# so a reset (leak) ball carrying a stale `handed` / class is not booked; excluded feeds go to handoff_stale (reported).
# handed, court_counts and len_hist are unchanged. Lines unchanged (d1_rule.h1_recon at 1 % / 0.01; h1_route).
#   1. Instrument check (the D-216 precedent): re-read dev 4220375 unchanged with the fixed tally. VALID only if
#      H1-RECON passes; handoff_stale reported (the hypothesis predicts about 35). Otherwise INVALID, no route.
#   2. Read dev 4220377 (the standard pairs read: 2,048 envs, 120 s).
#   3. Pooled (4220375 + 4220377): H1-RECON, then h1_route (BALL / POSITION / MIXED / INVALID-SPLIT).
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER PICKLEBOT_READY_LOG
pgrep -f "run-name |kickstart_h4|stage2_eval|footwork_eval|feeder_speed|distill_latent|latent_reach_floor" > /dev/null && { echo "GPU busy: not started"; exit 1; }
R=results/h1r87; L=artifacts/train/logs/picklebot_return_stand
BASE=/mnt/f/dev/picklebot-mjlab/mjlab/$L/2026-10-31_18-24-20_s5c-d1-fw1bS/model_32854.pt
P=$L/2026-11-04_00-06-34_rally-d1s3lr3/model_32598.pt
for f in $BASE $P; do [ -f $f ] || { echo "missing $f"; exit 1; }; done
onbase() { PICKLEBOT_RES_BASE=$BASE PICKLEBOT_LAM_R=2 "$@"; }
stop() { echo "VERDICT: $1" | tee -a $R-summary.txt; echo done > artifacts/train/h1r87.done; exit 0; }
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120"
echo "D-224: h1 attribution on C (fixed tally); instrument re-read dev 4220375, read dev 4220377" | tee $R-summary.txt

for s in 4220375 4220377; do
  [ -s $R-read-$s.json ] || onbase python scripts/stage2_eval.py --checkpoint $P $PA --seed $s --json $R-read-$s.json > $R-read-$s.log 2>&1
  python - "$s" <<'PY' | tee -a $R-summary.txt
import json, sys
sys.path.insert(0, ".")
from picklebot_mj import d1_rule as dr
s = sys.argv[1]
f = [f"results/h1r87-read-{s}.json"]
ok, line = dr.h1_recon(f)
print(f"{s} " + line + f"; handoff_stale {json.load(open(f[0]))['pairs'].get('handoff_stale')}")
PY
  [ $s = 4220375 ] && { grep -q -- "^4220375 .*-> VALID" $R-summary.txt || stop "INVALID (the fixed tally does not reconcile on 4220375)"; }
done
python - <<'PY' | tee -a $R-summary.txt
import sys
sys.path.insert(0, ".")
from picklebot_mj import d1_rule as dr
f = ["results/h1r87-read-4220375.json", "results/h1r87-read-4220377.json"]
ok, line = dr.h1_recon(f)
print("pooled " + line)
v, lines = dr.h1_route(f)
for x in lines:
    print(x)
hz = dr.pooled_hazards(f)
print("(reported) hazards h0-h4 " + " / ".join(f"{x:.3f}" for x in hz["h"]) + f"; court conversion {dr.court_conv(f)}")
print(f"RESULT {v if ok else 'INVALID'}")
PY
v=$(grep "^RESULT" $R-summary.txt | tail -1 | cut -d' ' -f2)
stop "$v"

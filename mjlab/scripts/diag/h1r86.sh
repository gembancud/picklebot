#!/usr/bin/env bash
# D-223 (panel round 86: no majority; least new code / fewest moving parts: (ii), RL's form). A read-only attribution of
# h1 (the partner's first ball) on C = rally-d1s3lr3 model_32598 (frozen d1 base, lam_r 2), mean actions. The pairs
# summary now carries handoff_by_d: own-ball feeds and legal returns by hand-off class (the rally's first hand-off vs
# later) and the receiver's distance from its spot at the hand-off (LAUNCH_D_EDGES bins). Logging only.
#   Smoke (dev 4220376, 256 envs, 60 s): d1_rule.h1_recon: the tally within 1 % of court_counts' own-ball columns, and
#   first hand-off legal within 0.01 of 1 - h1 -> VALID, else INVALID (stop; the D-216 lesson).
#   Read (dev 4220375, the standard pairs read: 2,048 envs, 120 s): d1_rule.h1_route ->
#     BALL (near first hand-offs legal >= 0.05 below near later ones, Wilson separated: the first return is a hard ball;
#       next a hitter-side lever on the feeder-ball return, its own entry);
#     POSITION (|gap| <= 0.03 and >= 40 % of first hand-offs far, > 1.2 m: h1 has h0's footwork limit; no lever left on
#       this stack -> STOP recorded with the estimate; under D-169 the loop moves to the next phase);
#     MIXED otherwise (panel); INVALID-SPLIT if fewer than 200 near hand-offs in a class.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER PICKLEBOT_READY_LOG
pgrep -f "run-name |kickstart_h4|stage2_eval|footwork_eval|feeder_speed|distill_latent|latent_reach_floor" > /dev/null && { echo "GPU busy: not started"; exit 1; }
R=results/h1r86; L=artifacts/train/logs/picklebot_return_stand
BASE=/mnt/f/dev/picklebot-mjlab/mjlab/$L/2026-10-31_18-24-20_s5c-d1-fw1bS/model_32854.pt
P=$L/2026-11-04_00-06-34_rally-d1s3lr3/model_32598.pt
for f in $BASE $P; do [ -f $f ] || { echo "missing $f"; exit 1; }; done
onbase() { PICKLEBOT_RES_BASE=$BASE PICKLEBOT_LAM_R=2 "$@"; }
stop() { echo "VERDICT: $1" | tee -a $R-summary.txt; echo done > artifacts/train/h1r86.done; exit 0; }
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact"
echo "D-223: h1 attribution on C = $P (base $BASE, lam_r 2); smoke dev 4220376, read dev 4220375" | tee $R-summary.txt

[ -s $R-smoke.json ] || onbase python scripts/stage2_eval.py --checkpoint $P $PA --envs 256 --seconds 60 --seed 4220376 --json $R-smoke.json > $R-smoke.log 2>&1
python - <<'PY' | tee -a $R-summary.txt
import sys
sys.path.insert(0, ".")
from picklebot_mj import d1_rule as dr
ok, line = dr.h1_recon(["results/h1r86-smoke.json"])
print("smoke " + line)
PY
grep -q -- "-> VALID" $R-summary.txt || stop "INVALID (the hand-off tally does not reconcile)"

[ -s $R-read.json ] || onbase python scripts/stage2_eval.py --checkpoint $P $PA --envs 2048 --seconds 120 --seed 4220375 --json $R-read.json > $R-read.log 2>&1
python - <<'PY' | tee -a $R-summary.txt
import sys
sys.path.insert(0, ".")
from picklebot_mj import d1_rule as dr
f = ["results/h1r86-read.json"]
ok, line = dr.h1_recon(f)
print("read " + line)
v, lines = dr.h1_route(f)
for x in lines:
    print(x)
hz = dr.pooled_hazards(f)
print("(reported) hazards h0-h4 " + " / ".join(f"{x:.3f}" for x in hz["h"]) + f"; court conversion {dr.court_conv(f)}")
print(f"RESULT {v if ok else 'INVALID'}")
PY
v=$(grep "^RESULT" $R-summary.txt | tail -1 | cut -d' ' -f2)
stop "$v"

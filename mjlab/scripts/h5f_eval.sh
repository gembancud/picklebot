#!/usr/bin/env bash
# Stage 5F evaluation of one fixed endpoint (D-108/D-109/D-111). Development seeds S..S+29 only.
# Usage: h5f_eval.sh RUN CKFILE TAG SEED TASK_V2 TASK_COURT TASK_5B [quick]
#   1. The frozen D-101 battery, unchanged: h5e_eval.sh on seeds S..S+15 (files results/stage5e-s5f-TAG-*).
#   2. The delay grid (ball 0/20/40 ms x command 0/10/20 ms, fixed per episode, ball noise on, plus the extrapolation
#      cell 60/30), each cell on the same seed (paired across cells):
#        drill v2 with the noisy planner spot (512 envs, 40 s, seed S+20)   -> results/stage5f-TAG-v2-bB-cC.json
#        court drill, main metric and falls (2048 envs, 24 s, seed S+21)   -> results/stage5f-TAG-court-bB-cC.json
#      plus the move drill at command 0/10/20 ms (2048 envs, 24 s, seed S+22) -> results/stage5f-TAG-move-cC.json
#   "quick" runs only the cells the kill rules and gate read: drill v2 and court at 0/0 and 40/20, move at 0 and 20 ms.
#   Then scripts/h5f_summary.py TAG.
set -uo pipefail
cd "$(dirname "$0")/.."
RUN=$1; CK=$2; TAG=$3; S=$4; TV2=$5; TC=$6; T5B=$7; MODE=${8:-full}; R=results/stage5f-$TAG; FAIL=0; MARK=$(mktemp)
check() { if [ $1 -ne 0 ] || [ ! "$2" -nt "$MARK" ]; then echo "EVAL JOB FAILED: $2 (exit $1)"; FAIL=1; fi; }
bash scripts/h5e_eval.sh $RUN $CK s5f-$TAG $S $TV2 $TC $T5B || FAIL=1
if [ "$MODE" = quick ]; then CELLS="0,0 40,20"; MC="0 20"; else
  CELLS="0,0 0,10 0,20 20,0 20,10 20,20 40,0 40,10 40,20 60,30"; MC="0 10 20"; fi
V="--task $TV2 --envs 512 --seconds 40 --move-prob 0.0 --swing-prob 0.0 --target A --no-hint --rally --planner noisy"
C="--task $TC --envs 2048 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --recovery random"
M="--task $TC --envs 2048 --seconds 24 --move-prob 1.0 --swing-prob 0.0 --families every --target A --no-hint"
for c in $CELLS; do b=${c%,*}; d=${c#*,}
  bash scripts/stage2_eval.sh $RUN $CK $V --grid $b $d --seed $((S+20)) --json $R-v2-b$b-c$d.json > /tmp/h5f_$TAG.log 2>&1; check $? $R-v2-b$b-c$d.json
  bash scripts/stage2_eval.sh $RUN $CK $C --grid $b $d --seed $((S+21)) --json $R-court-b$b-c$d.json > /tmp/h5f_$TAG.log 2>&1; check $? $R-court-b$b-c$d.json
done
for d in $MC; do
  bash scripts/stage2_eval.sh $RUN $CK $M --grid 0 $d --seed $((S+22)) --json $R-move-c$d.json > /tmp/h5f_$TAG.log 2>&1; check $? $R-move-c$d.json
done
[ $FAIL -eq 0 ] || echo "WARNING: at least one evaluation job failed; the summary below may be incomplete"
~/envs/picklebot-mj/bin/python scripts/h5f_summary.py $TAG
exit $FAIL

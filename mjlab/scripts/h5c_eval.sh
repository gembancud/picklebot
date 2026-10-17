#!/usr/bin/env bash
# Stage 5C evaluation of one fixed endpoint (D-075/D-076). Seeds S..S+3 (development seeds only).
# Usage: h5c_eval.sh RUN CKFILE TAG SEED [TASK] [STAGE5B_TASK]   -> results/stage5c-TAG-{court,move,drill5b,style}.json + summary
set -uo pipefail
cd "$(dirname "$0")/.."
RUN=$1; CK=$2; TAG=$3; S=$4; MARK=$(mktemp); FAIL=0
# Each job must exit 0 and write a fresh JSON (D-086: failures were hidden behind > /dev/null).
check() { if [ $1 -ne 0 ] || [ ! "$2" -nt "$MARK" ]; then echo "EVAL JOB FAILED: $2 (exit $1)"; FAIL=1; fi; }
 T=${5:-Picklebot-Latent-Court-G1}; T5B=${6:-Picklebot-Latent-Drill3-Prior5-G1}; R=results/stage5c-$TAG; P=~/envs/picklebot-mj/bin/python
# 1. Court-wide drill: every family from court-wide positions, no hint, random court-wide recovery spots.
bash scripts/stage2_eval.sh $RUN $CK --task $T --envs 2048 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --recovery random --seed $S --json $R-court.json > /tmp/h5c_${TAG}.log 2>&1; check $? $R-court.json
# 2. Move-to-spot drill only: arrival per direction (8 sectors, spots 0.5-3 m).
bash scripts/stage2_eval.sh $RUN $CK --task $T --envs 2048 --seconds 24 --move-prob 1.0 --swing-prob 0.0 --families every --target A --no-hint --seed $((S+1)) --json $R-move.json > /tmp/h5c_${TAG}.log 2>&1; check $? $R-move.json
# 3. Regression on the Stage 5B drill (its task: baseline starts, fixed recovery), no hint.
bash scripts/stage2_eval.sh $RUN $CK --task $T5B --envs 2048 --seconds 16 --move-prob 0.0 --swing-prob 0.0 --families drill5b --target A --no-hint --seed $((S+2)) --json $R-drill5b.json > /tmp/h5c_${TAG}.log 2>&1; check $? $R-drill5b.json
# 5. Recovery (D-086): court drill with an 8 s pause before the next feed, so the time-model deadline (1.5 s + 1.25 s/m
#    after contact) comes first; also gives the stand-still baseline (gap to the spot at contact).
bash scripts/stage2_eval.sh $RUN $CK --task $T --envs 1024 --seconds 30 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --recovery random --refeed-delay 8 --seed $((S+4)) --json $R-recovery.json > /tmp/h5c_${TAG}.log 2>&1; check $? $R-recovery.json
# 6. Rally evaluation (D-086, reported next to the gate, not gated): court-anchored feeds, consecutive legal returns.
bash scripts/stage2_eval.sh $RUN $CK --task $T --envs 1024 --seconds 90 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --seed $((S+5)) --json $R-rally.json > /tmp/h5c_${TAG}.log 2>&1; check $? $R-rally.json
# 4. Style score on the court drill.
DIR="$(ls -d artifacts/train/logs/picklebot_return_stand/*_"$RUN" | tail -1)"  # exact run name (D-086)
$P scripts/motion/style_score.py --checkpoint "$DIR/$CK" --task $T --seed $((S+3)) --json $R-style.json > /tmp/h5c_${TAG}_style.log 2>&1; check $? $R-style.json
[ $FAIL -eq 0 ] || echo "WARNING: at least one evaluation job failed; the summary below may be incomplete"
$P scripts/h5c_summary.py $TAG

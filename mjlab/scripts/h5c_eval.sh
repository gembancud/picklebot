#!/usr/bin/env bash
# Stage 5C evaluation of one fixed endpoint (D-075/D-076). Seeds S..S+3 (development seeds only).
# Usage: h5c_eval.sh RUN CKFILE TAG SEED [TASK]   -> results/stage5c-TAG-{court,move,drill5b,style}.json + summary
set -uo pipefail
cd "$(dirname "$0")/.."
RUN=$1; CK=$2; TAG=$3; S=$4; T=${5:-Picklebot-Latent-Court-G1}; R=results/stage5c-$TAG; P=~/envs/picklebot-mj/bin/python
# 1. Court-wide drill: every family from court-wide positions, no hint, random court-wide recovery spots.
bash scripts/stage2_eval.sh $RUN $CK --task $T --envs 2048 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --recovery random --seed $S --json $R-court.json > /dev/null 2>&1
# 2. Move-to-spot drill only: arrival per direction (8 sectors, spots 0.5-3 m).
bash scripts/stage2_eval.sh $RUN $CK --task $T --envs 2048 --seconds 24 --move-prob 1.0 --swing-prob 0.0 --families every --target A --no-hint --seed $((S+1)) --json $R-move.json > /dev/null 2>&1
# 3. Regression on the Stage 5B drill (its task: baseline starts, fixed recovery), no hint.
bash scripts/stage2_eval.sh $RUN $CK --task Picklebot-Latent-Drill3-Prior5-G1 --envs 2048 --seconds 16 --move-prob 0.0 --swing-prob 0.0 --families drill5b --target A --no-hint --seed $((S+2)) --json $R-drill5b.json > /dev/null 2>&1
# 4. Style score on the court drill.
DIR="$(ls -d artifacts/train/logs/picklebot_return_stand/*"$RUN"* | tail -1)"
$P scripts/motion/style_score.py --checkpoint "$DIR/$CK" --task $T --seed $((S+3)) --json $R-style.json > /dev/null 2>&1
$P scripts/h5c_summary.py $TAG

#!/usr/bin/env bash
# Stage 5B H4 / gate evaluation of one fixed endpoint (the Stage 5 gate protocol of artifacts/eval/s5_gate_eval.sh
# plus the style score), for any Drill 3 task variant.
# Usage: h4_eval.sh RUN CKFILE TAG SEED [TASK]   (seeds S..S+3 are used; development seeds only)
#   writes results/stage5b-h4-TAG-{A,B,nohint-A,nohint-B,retention-A,retention-parent-A,gain,nohint-gain,style}.json
set -uo pipefail
cd "$(dirname "$0")/.."
RUN=$1; CK=$2; TAG=$3; S=$4; T=${5:-Picklebot-Latent-Drill3-G1}; R=results/stage5b-h4-$TAG; P=~/envs/picklebot-mj/bin/python
A="--task $T --envs 2048 --seconds 16 --move-prob 0.0 --swing-prob 0.0 --families drill5b"  # the 14 Stage 5B families (court families came later)
for tg in A B; do
  bash scripts/stage2_eval.sh $RUN $CK $A --seed $S --target $tg --json $R-$tg.json > /dev/null 2>&1
  bash scripts/stage2_eval.sh $RUN $CK $A --seed $((S+1)) --target $tg --no-hint --json $R-nohint-$tg.json > /dev/null 2>&1
done
# Retention: Stage 4 families from the fixed start, no hint, vs model_7600 on the same feeds.
bash scripts/stage2_eval.sh $RUN $CK --task $T --envs 2048 --seconds 16 --move-prob 0.0 --swing-prob 0.0 --families all --fixed-start --no-hint --target A --seed $((S+2)) --json $R-retention-A.json > /dev/null 2>&1
bash scripts/stage2_eval.sh 2026-10-03_08-00-47_aim-all-c01 model_7600.pt --task Picklebot-Aim-All-G1 --envs 2048 --seconds 16 --families all --target A --seed $((S+2)) --json $R-retention-parent-A.json > /dev/null 2>&1
$P scripts/aim_gain.py $R-A.json $R-B.json > $R-gain.json
$P scripts/aim_gain.py $R-nohint-A.json $R-nohint-B.json > $R-nohint-gain.json
DIR="$(ls -d artifacts/train/logs/picklebot_return_stand/*"$RUN"* | tail -1)"
$P scripts/motion/style_score.py --checkpoint "$DIR/$CK" --task $T --seed $((S+3)) --json $R-style.json > /dev/null 2>&1
$P scripts/h4_summary.py $TAG

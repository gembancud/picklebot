#!/usr/bin/env bash
# Stage 5C paired final evaluation (D-075 step 6, D-086): the named candidate and the stage baseline h4-25b on the same
# four fresh dev seeds S..S+3 for the court drill (pooled per cell), plus the candidate's other gate jobs once (h5c_eval).
# Usage: h5c_final.sh RUN CKFILE TASK TASK5B SEED   -> results/stage5c-final-*.json
set -uo pipefail
cd "$(dirname "$0")/.."
RUN=$1; CK=$2; T=$3; T5B=$4; S=$5; P=~/envs/picklebot-mj/bin/python; R=results/stage5c-final
C="--envs 2048 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --recovery random"
for i in 0 1 2 3; do
  bash scripts/stage2_eval.sh $RUN $CK --task $T $C --seed $((S+i)) --json $R-cand-court-$i.json > /tmp/fin.log 2>&1; echo "cand court $i: $?"
  bash scripts/stage2_eval.sh h4-25b-more model_27700.pt --task Picklebot-Latent-Court-G1 $C --seed $((S+i)) --json $R-base-court-$i.json > /tmp/fin.log 2>&1; echo "base court $i: $?"
done
$P scripts/h5c_pool.py $R-cand-pooled.json $R-cand-court-[0-3].json
$P scripts/h5c_pool.py $R-base-pooled.json $R-base-court-[0-3].json
bash scripts/h5c_eval.sh $RUN $CK final-cand $((S+4)) $T $T5B

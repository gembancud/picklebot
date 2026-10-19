#!/usr/bin/env bash
# Stage 5F run 4 (D-115). One change from its parent: the ready-position and split-step reward (shot item 1;
# Picklebot-Latent-Court-V2-Res-PPO-Clean-Ready-G1; picklebot_mj/ready.py), READY_WEIGHT 0.5 / step_dt per part.
# Same clean drill v2 environment, Stage 5E PPO settings with the fixed warm-up (D-114), 12,288 envs, training seed 73.
# Usage: h5f_run04.sh PARENT_RUN PARENT_DIR PARENT_CKFILE PARENT_IT
# Endpoint: PARENT_IT + 1000 or the last checkpoint before the 7000 s cap. Early kill at PARENT_IT + 300: drill v2 0/0,
# 256 envs, 30 s, seed 4211200 (> 5 points below the parent kills); move drill clean, seed 4211201 (arrival < 90 %
# kills). A crashed early evaluation never kills (D-112); after a kill the endpoint battery is skipped.
# Endpoint evaluation: h5f_clean_eval.sh on seeds 4211210-4211225.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
PRUN=$1; PDIR=$2; PCK=$3; PIT=$4; EIT=$((PIT + 300))
RUN=s5f-04-ready; L=artifacts/train/logs/picklebot_return_stand; R=results/stage5f-s5f04
EV="--task Picklebot-Latent-Court-V2-Res-G1 --envs 256 --seconds 30 --move-prob 0.0 --swing-prob 0.0 --target A --no-hint --rally --planner noisy --grid 0 0 --seed 4211200"
MV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 20 --move-prob 1.0 --swing-prob 0.0 --families every --target A --no-hint --seed 4211201"
bash scripts/stage2_eval.sh $PRUN $PCK $EV --json $R-parent-early-v2.json > /tmp/r04.log 2>&1; echo "parent early v2: $?"
( # early-kill watcher
  while [ ! -f "$(ls -d $L/*_$RUN 2>/dev/null | tail -1)/model_$EIT.pt" ]; do
    [ -f artifacts/train/$RUN.exit.json ] && { echo "training ended before the early check"; exit 0; }; sleep 60; done
  D=$(ls -d $L/*_$RUN | tail -1)
  python scripts/stage2_eval.py --checkpoint $D/model_$EIT.pt $EV --json $R-early-v2.json > /tmp/r04e.log 2>&1 \
    || { echo "EARLY EVALUATION CRASHED (no kill)"; exit 2; }
  python scripts/stage2_eval.py --checkpoint $D/model_$EIT.pt $MV --json $R-early-move.json > /tmp/r04e.log 2>&1 \
    || { echo "EARLY EVALUATION CRASHED (no kill)"; exit 2; }
  python - "$R" <<'PY' && echo "early check: pass" || { echo "early check: KILL"; touch artifacts/train/$RUN.killed; pkill -f "run-name $RUN"; }
import json, sys
R = sys.argv[1]
p0 = json.load(open(f"{R}-parent-early-v2.json"))["drill_v2"]["per_shot_p"]
p1 = json.load(open(f"{R}-early-v2.json"))["drill_v2"]["per_shot_p"]
sec = json.load(open(f"{R}-early-move.json"))["move_drill"]["sectors"]
arr = min(s["arrival_rate"] for s in sec if s["sector"] < 8 and s.get("arrival_rate") is not None)
print(f"early: drill v2 p parent {p0} -> {p1} ({100 * (p1 - p0):+.1f} points; kill below -5); move arrival min {arr} (kill below 0.90)")
sys.exit(0 if (p1 >= p0 - 0.05 and arr >= 0.90) else 1)
PY
) > artifacts/train/$RUN-early.log 2>&1 &
PICKLEBOT_ENVS=12288 bash scripts/train_run.sh $RUN Picklebot-Latent-Court-V2-Res-PPO-Clean-Ready-G1 --agent.seed 73 \
  --agent.max-iterations 1000 --agent.resume True --agent.load-run $PDIR --agent.load-checkpoint $PCK
wait
cat artifacts/train/$RUN-early.log
[ -f artifacts/train/$RUN.killed ] && { echo "killed at the early check: endpoint battery skipped"; exit 0; }
D=$(ls -d $L/*_$RUN | tail -1); CK=$(ls $D/model_*.pt | sort -V | tail -1); echo "endpoint $CK"
bash scripts/h5f_clean_eval.sh $RUN $(basename $CK) s5f04 4211210

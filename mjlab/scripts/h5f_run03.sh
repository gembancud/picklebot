#!/usr/bin/env bash
# Stage 5F run 3 (D-114). One change from run 2: the critic warm-up holds the learning rate (CriticWarmupHoldLrRunner).
# Same environment, PPO settings, start (s5d-01-rally/model_1800), 12,288 envs and training seed 73 as run 2.
# Endpoint: iteration 2800 or the last checkpoint before the 7000 s cap. Early kill at model_2100 as run 2 (drill v2 0/0,
# 256 envs, 30 s, seed 4211100: > 5 points below the parent; move drill clean, seed 4211101: arrival < 90 %); a crashed
# early evaluation never kills (D-112). Endpoint evaluation: h5f_clean_eval.sh on seeds 4211110-4211125.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
RUN=s5f-03-v2-clean-hold; L=artifacts/train/logs/picklebot_return_stand; R=results/stage5f-s5f03
EV="--task Picklebot-Latent-Court-V2-Res-G1 --envs 256 --seconds 30 --move-prob 0.0 --swing-prob 0.0 --target A --no-hint --rally --planner noisy --grid 0 0 --seed 4211100"
MV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 20 --move-prob 1.0 --swing-prob 0.0 --families every --target A --no-hint --seed 4211101"
bash scripts/stage2_eval.sh s5d-01-rally model_1800.pt $EV --json $R-parent-early-v2.json > /tmp/r03.log 2>&1; echo "parent early v2: $?"
( # early-kill watcher
  while [ ! -f "$(ls -d $L/*_$RUN 2>/dev/null | tail -1)/model_2100.pt" ]; do
    [ -f artifacts/train/$RUN.exit.json ] && { echo "training ended before the early check"; exit 0; }; sleep 60; done
  D=$(ls -d $L/*_$RUN | tail -1)
  python scripts/stage2_eval.py --checkpoint $D/model_2100.pt $EV --json $R-early-v2.json > /tmp/r03e.log 2>&1 \
    || { echo "EARLY EVALUATION CRASHED (no kill)"; exit 2; }
  python scripts/stage2_eval.py --checkpoint $D/model_2100.pt $MV --json $R-early-move.json > /tmp/r03e.log 2>&1 \
    || { echo "EARLY EVALUATION CRASHED (no kill)"; exit 2; }
  python - "$R" <<'PY' && echo "early check: pass" || { echo "early check: KILL"; pkill -f "run-name $RUN"; }
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
PICKLEBOT_ENVS=12288 bash scripts/train_run.sh $RUN Picklebot-Latent-Court-V2-Res-PPO-Clean-Hold-G1 --agent.seed 73 \
  --agent.max-iterations 1000 --agent.resume True --agent.load-run 2026-10-17_06-13-47_s5d-01-rally --agent.load-checkpoint model_1800.pt
wait
cat artifacts/train/$RUN-early.log
D=$(ls -d $L/*_$RUN | tail -1); CK=$(ls $D/model_*.pt | sort -V | tail -1); echo "endpoint $CK"
bash scripts/h5f_clean_eval.sh $RUN $(basename $CK) s5f03 4211110

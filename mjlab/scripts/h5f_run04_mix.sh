#!/usr/bin/env bash
# Stage 5F run 4 (D-116; review rounds 7 and 8). One change from run 3: 40 % of feeds are court-task feeds on drill v2
# terms (Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-G1). Parent s5d-01-rally/model_1800, training seed 73, 12,288 envs,
# Stage 5E PPO settings with the fixed warm-up (D-114). Endpoint: iteration 2600 (800 more) or the last checkpoint
# before the 7000 s cap. Early kill at model_2100 (kill only; a crashed evaluation never kills, D-112):
#   drill v2 0/0, 256 envs, 30 s, seed 4211200: > 5 points below the parent;
#   move drill clean, 256 envs, 20 s, seed 4211201: arrival < 90 % in any direction;
#   court drill clean, 256 envs, 24 s, seed 4211202: > 5 points below the parent (D-116, tightening only).
# After a kill the endpoint battery is skipped. Endpoint evaluation: h5f_clean_eval.sh on seeds 4211210-4211225.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
RUN=s5f-04-mix-court40; L=artifacts/train/logs/picklebot_return_stand; R=results/stage5f-s5f04
EV="--task Picklebot-Latent-Court-V2-Res-G1 --envs 256 --seconds 30 --move-prob 0.0 --swing-prob 0.0 --target A --no-hint --rally --planner noisy --grid 0 0 --seed 4211200"
MV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 20 --move-prob 1.0 --swing-prob 0.0 --families every --target A --no-hint --seed 4211201"
CV="--task Picklebot-Latent-Court-Res-G1 --envs 256 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --recovery random --seed 4211202"
bash scripts/stage2_eval.sh s5d-01-rally model_1800.pt $EV --json $R-parent-early-v2.json > /tmp/r04.log 2>&1; echo "parent early v2: $?"
bash scripts/stage2_eval.sh s5d-01-rally model_1800.pt $CV --json $R-parent-early-court.json > /tmp/r04.log 2>&1; echo "parent early court: $?"
( # early-kill watcher
  while [ ! -f "$(ls -d $L/*_$RUN 2>/dev/null | tail -1)/model_2100.pt" ]; do
    [ -f artifacts/train/$RUN.exit.json ] && { echo "training ended before the early check"; exit 0; }; sleep 60; done
  D=$(ls -d $L/*_$RUN | tail -1)
  for spec in "v2:$EV" "move:$MV" "court:$CV"; do
    python scripts/stage2_eval.py --checkpoint $D/model_2100.pt ${spec#*:} --json $R-early-${spec%%:*}.json > /tmp/r04e.log 2>&1 \
      || { echo "EARLY EVALUATION CRASHED (no kill): ${spec%%:*}"; exit 2; }
  done
  python - "$R" <<'PY' && echo "early check: pass" || { echo "early check: KILL"; touch artifacts/train/$RUN.killed; pkill -f "run-name $RUN"; }
import json, sys
R = sys.argv[1]
ld = lambda k: json.load(open(f"{R}-{k}.json"))
p0, p1 = ld("parent-early-v2")["drill_v2"]["per_shot_p"], ld("early-v2")["drill_v2"]["per_shot_p"]
c0, c1 = ld("parent-early-court")["legal_return_rate"], ld("early-court")["legal_return_rate"]
arr = min(s["arrival_rate"] for s in ld("early-move")["move_drill"]["sectors"] if s["sector"] < 8 and s.get("arrival_rate") is not None)
print(f"early: drill v2 p {p0} -> {p1} ({100 * (p1 - p0):+.1f}; kill below -5); court main {c0} -> {c1} ({100 * (c1 - c0):+.1f}; kill below -5); move arrival min {arr} (kill below 0.90)")
sys.exit(0 if (p1 >= p0 - 0.05 and c1 >= c0 - 0.05 and arr >= 0.90) else 1)
PY
) > artifacts/train/$RUN-early.log 2>&1 &
PICKLEBOT_ENVS=12288 bash scripts/train_run.sh $RUN Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-G1 --agent.seed 73 \
  --agent.max-iterations 800 --agent.resume True --agent.load-run 2026-10-17_06-13-47_s5d-01-rally --agent.load-checkpoint model_1800.pt
wait
cat artifacts/train/$RUN-early.log
[ -f artifacts/train/$RUN.killed ] && { echo "killed at the early check: endpoint battery skipped"; exit 0; }
D=$(ls -d $L/*_$RUN | tail -1); CK=$(ls $D/model_*.pt | sort -V | tail -1); echo "endpoint $CK"
bash scripts/h5f_clean_eval.sh $RUN $(basename $CK) s5f04 4211210

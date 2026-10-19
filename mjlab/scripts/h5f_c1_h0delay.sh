#!/usr/bin/env bash
# Stage 5F controller run C1 (D-111 trigger fired): H0 delay fine-tune. One change: per-episode command delay (30 % clean,
# else 5-25 ms) on H0's own task and settings (tracking-20-decay: fixed lr 1e-5), lag shown to the critic only.
# Endpoint: iteration 63800 (3000 more) or the last checkpoint before the 7000 s cap. Early kill (D-111): at ~30 % (iter
# >= 61700), clean tracking, 1 repeat, seed 4210500; killed if any source is > 3 points below the parent on that protocol.
# Gate (D-111): per source and per tennis stroke type at 0/10/20 ms >= old H0 at 0 ms - 2 points; seed 4210501, 2 repeats.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
L=artifacts/train/logs/picklebot_tracking; P=$L/2026-10-10_05-18-15_tracking-20-decay/model_60800.pt
INIT=$L/2026-10-19_12-00-00_s5f-c1-init; R=results/stage5f-c1
mkdir -p $INIT
AD=$(python -c "import torch;print(torch.load('$P',map_location='cpu',weights_only=False)['actor_state_dict']['mlp.0.weight'].shape[1])")
CD=$(python -c "import torch;print(torch.load('$P',map_location='cpu',weights_only=False)['critic_state_dict']['mlp.0.weight'].shape[1])")
python scripts/expand_checkpoint.py $P $INIT/model_60800.pt --actor-dim $AD --critic-dim $((CD+1)) > /dev/null; echo "expanded critic $CD -> $((CD+1))"
TE="python scripts/motion/tracking_eval.py --task Picklebot-Tracking-TennisLafan4-Huge-G1 --per-stroke"
$TE --checkpoint $P --repeats 1 --seed 4210500 --json $R-parent-early.json > /tmp/c1.log 2>&1; echo "parent early-protocol eval: $?"
( # early-kill watcher
  while [ ! -f "$(ls -d $L/*_s5f-c1-h0delay 2>/dev/null | tail -1)/model_61700.pt" ]; do
    [ -f artifacts/train/s5f-c1-h0delay.exit.json ] && { echo "training ended before the early check"; exit 0; }; sleep 60; done
  D=$(ls -d $L/*_s5f-c1-h0delay | tail -1)
  $TE --checkpoint $D/model_61700.pt --repeats 1 --seed 4210500 --json $R-early.json > /tmp/c1e.log 2>&1
  python - "$R" <<'PY' && echo "early check: pass" || { echo "early check: KILL"; pkill -f "s5f-c1-h0delay Picklebot-Tracking" ; pkill -f "run-name s5f-c1-h0delay"; }
import json, sys
R = sys.argv[1]
p, e = json.load(open(f"{R}-parent-early.json"))["by_source"], json.load(open(f"{R}-early.json"))["by_source"]
worst = min(e[k] - p[k] for k in p)
print("early: worst source change", round(100 * worst, 1), "points", {k: round(100 * (e[k] - p[k]), 1) for k in p})
sys.exit(0 if worst >= -0.03 else 1)
PY
) > artifacts/train/s5f-c1-early.log 2>&1 &
bash scripts/train_run.sh s5f-c1-h0delay Picklebot-Tracking-TennisLafan2-Huge-Delay-G1 --agent.seed 71 --agent.max-iterations 3000 --agent.algorithm.schedule fixed --agent.algorithm.learning-rate 1e-5 --agent.resume True --agent.load-run 2026-10-19_12-00-00_s5f-c1-init --agent.load-checkpoint model_60800.pt
wait
cat artifacts/train/s5f-c1-early.log
D=$(ls -d $L/*_s5f-c1-h0delay | tail -1); CK=$(ls $D/model_*.pt | sort -V | tail -1); echo "endpoint $CK"
for d in 0 10 20; do
  $TE --checkpoint $CK --repeats 2 --seed 4210501 --cmd-delay-ms $d --json $R-gate-new-cmd$d.json > /tmp/c1.log 2>&1; echo "gate new cmd$d: $?"
done
$TE --checkpoint $P --repeats 2 --seed 4210501 --json $R-gate-old-cmd0.json > /tmp/c1.log 2>&1; echo "gate old cmd0: $?"

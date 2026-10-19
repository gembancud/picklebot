#!/usr/bin/env bash
# Stage 5F run C1, continued (D-112). C1's early-kill watcher stopped the training at iteration ~61,720 because the
# early evaluation itself crashed (tracking_eval loaded the delay-trained 287-input critic into a 286-input task); the
# watcher treated the missing result as a kill. Fixed (actor-only load) and re-run on the same protocol: model_61700
# passes (worst source +0.0 points). The run continues from model_61700 to its pre-registered endpoint 63,800 with the
# same task and settings; the wall-clock cap is what C1 had left (7000 s - 2231 s used = 4769 s, rounded down to 4700 s).
# Gate (D-111) unchanged: per source and per tennis stroke type at 0/10/20 ms >= old H0 at 0 ms - 2 points; seed 4210501.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
L=artifacts/train/logs/picklebot_tracking; P=$L/2026-10-10_05-18-15_tracking-20-decay/model_60800.pt; R=results/stage5f-c1
PICKLEBOT_WALL_CAP=4700 bash scripts/train_run.sh s5f-c1b-h0delay Picklebot-Tracking-TennisLafan2-Huge-Delay-G1 --agent.seed 71 \
  --agent.max-iterations 2100 --agent.algorithm.schedule fixed --agent.algorithm.learning-rate 1e-5 --agent.resume True \
  --agent.load-run 2026-10-19_18-34-23_s5f-c1-h0delay --agent.load-checkpoint model_61700.pt
D=$(ls -d $L/*_s5f-c1b-h0delay | tail -1); CK=$(ls $D/model_*.pt | sort -V | tail -1); echo "endpoint $CK"
TE="python scripts/motion/tracking_eval.py --task Picklebot-Tracking-TennisLafan4-Huge-G1 --per-stroke"
for d in 0 10 20; do
  $TE --checkpoint $CK --repeats 2 --seed 4210501 --cmd-delay-ms $d --json $R-gate-new-cmd$d.json > /tmp/c1.log 2>&1; echo "gate new cmd$d: $?"
done
[ -f $R-gate-old-cmd0.json ] || { $TE --checkpoint $P --repeats 2 --seed 4210501 --json $R-gate-old-cmd0.json > /tmp/c1.log 2>&1; echo "gate old cmd0: $?"; }

#!/usr/bin/env bash
# Stage 5F step 0 (D-108/D-109/D-111): where does command delay hurt? No training. Dev seeds 4210000-4210019.
#   A/B: H0 (tracking-20-decay/model_60800) and latent-07 (encoder tracking) on tennis + LAFAN1 + mirror + footwork,
#        command delay 0 / 10 / 20 ms, same seed (paired)
#   C:   latent-07 on tennis + 100STYLE, command delay 0 / 20 ms
#   D:   executor-driven move drill (Stage 5D run 1 on latent-07): clean, and command 10 / 20 ms (ball 0)
#   E:   flat walking teacher (teacher-move-01/model_15900) move drill: clean, command 20 ms
#   F:   Stage 5D run 1 on drill v2 (noisy spot) at grid cells 0/0, 0/20, 40/0, 40/20 (ball / command ms):
#        the oracle ball-prediction ceiling (ball 0) and the split of ball vs command loss
set -uo pipefail
cd "$(dirname "$0")/.."
source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
R=results/stage5f-step0; L=artifacts/train/logs; H0=$L/picklebot_tracking/2026-10-10_05-18-15_tracking-20-decay/model_60800.pt
LAT=artifacts/train/latent/latent-07/latent_10651.pt
for d in 0 10 20; do
  python scripts/motion/tracking_eval.py --checkpoint $H0 --task Picklebot-Tracking-TennisLafan4-Huge-G1 --per-stroke --repeats 2 --seed 4210000 --cmd-delay-ms $d --json $R-h0-cmd$d.json > /tmp/s0.log 2>&1; echo "A h0 cmd$d: $?"
  python scripts/motion/tracking_eval.py --latent --checkpoint $LAT --task Picklebot-Tracking-TennisLafan4-Huge-G1 --per-stroke --repeats 2 --seed 4210000 --cmd-delay-ms $d --json $R-lat07-cmd$d.json > /tmp/s0.log 2>&1; echo "B lat07 cmd$d: $?"
done
for d in 0 20; do
  python scripts/motion/tracking_eval.py --latent --checkpoint $LAT --task Picklebot-Tracking-TennisStyle100-G1 --per-stroke --repeats 2 --seed 4210001 --cmd-delay-ms $d --json $R-lat07-style100-cmd$d.json > /tmp/s0.log 2>&1; echo "C lat07 100style cmd$d: $?"
done
M="--envs 2048 --seconds 24 --move-prob 1.0 --swing-prob 0.0 --families every --target A --no-hint"
bash scripts/stage2_eval.sh s5d-01-rally model_1800.pt --task Picklebot-Latent-Court-Res-G1 $M --seed 4210002 --json $R-move-s5d01-clean.json > /tmp/s0.log 2>&1; echo "D move clean: $?"
for d in 10 20; do
  bash scripts/stage2_eval.sh s5d-01-rally model_1800.pt --task Picklebot-Latent-Court-Res-G1 $M --grid 0 $d --seed 4210002 --json $R-move-s5d01-cmd$d.json > /tmp/s0.log 2>&1; echo "D move cmd$d: $?"
done
T="--envs 2048 --seconds 24 --move-prob 1.0"
bash scripts/stage2_eval.sh teacher-move-01 model_15900.pt --task Picklebot-Teacher-Move-G1 $T --seed 4210003 --json $R-walkteacher-clean.json > /tmp/s0.log 2>&1; echo "E teacher clean: $?"
bash scripts/stage2_eval.sh teacher-move-01 model_15900.pt --task Picklebot-Teacher-Move-G1 $T --grid 0 20 --seed 4210003 --json $R-walkteacher-cmd20.json > /tmp/s0.log 2>&1; echo "E teacher cmd20: $?"
V="--task Picklebot-Latent-Court-V2-Res-G1 --envs 1024 --seconds 60 --move-prob 0.0 --swing-prob 0.0 --target A --no-hint --rally --planner noisy"
for c in "0 0" "0 20" "40 0" "40 20"; do set -- $c
  bash scripts/stage2_eval.sh s5d-01-rally model_1800.pt $V --grid $1 $2 --seed 4210004 --json $R-v2-s5d01-b$1-c$2.json > /tmp/s0.log 2>&1; echo "F v2 b$1 c$2: $?"
done

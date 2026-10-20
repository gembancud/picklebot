#!/usr/bin/env bash
# Stage 5G run E2 (D-119): E1 with one paddle-reward redesign (Picklebot-Latent-TimedReach-V2-G1: reach-06 paddle_track to
# p* while the goal is open, no swing guide, linear contact velocity factor) and the two timed_reach fixes (D-119).
# As E1 otherwise (from reach-06 (Picklebot-Latent-Reach-E2-G1,
# model_34700): the timed command and its rewards (Picklebot-Latent-TimedReach-G1; goal bank bank-s5g-01.pt), reach-06
# warm-started with zero-weight inputs for the 6 new command dims. 4,096 envs (as reach-06), training seed 74.
# Endpoint: iteration 39700 (5000 more) or the last checkpoint before the 7000 s cap.
# Early kill (D-118) at about 30 % (model_36200): timed_reach_eval, 256 envs, 20 s, seed 4216101: kill if falls > 5 % per
# episode or the median paddle error at t* > 0.25 m. A crashed evaluation never kills (D-112).
# Gate (D-118): median paddle error <= 0.08 m, p90 <= 0.20 m; timing within 50 ms >= 80 %; median speed error <= 20 %;
# falls <= 2 % per episode; root within 0.25 m at t* >= 90 %. Endpoint evaluation: 1024 envs, 30 s, seed 4216110.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
RUN=s5g-e2-timed-v2; L=artifacts/train/logs/picklebot_latent; R=results/stage5g-e2
( # early-kill watcher
  while [ ! -f "$(ls -d $L/*_$RUN 2>/dev/null | tail -1)/model_36200.pt" ]; do
    [ -f artifacts/train/$RUN.exit.json ] && { echo "training ended before the early check"; exit 0; }; sleep 60; done
  D=$(ls -d $L/*_$RUN | tail -1)
  python scripts/motion/timed_reach_eval.py --task Picklebot-Latent-TimedReach-V2-G1 --checkpoint $D/model_36200.pt --envs 256 --seconds 20 --seed 4216101 \
    --json $R-early.json > /tmp/e1e.log 2>&1 || { echo "EARLY EVALUATION CRASHED (no kill)"; exit 2; }
  python - "$R" <<'PY' && echo "early check: pass" || { echo "early check: KILL"; touch artifacts/train/$RUN.killed; pkill -f "run-name $RUN"; }
import json, sys
d = json.load(open(sys.argv[1] + "-early.json"))
print(f"early: falls {d['fall_rate']:.4f} (kill above 0.05); paddle error median {d['paddle_err_median_m']} (kill above 0.25)")
sys.exit(0 if (d["fall_rate"] <= 0.05 and d["paddle_err_median_m"] <= 0.25) else 1)
PY
) > artifacts/train/$RUN-early.log 2>&1 &
bash scripts/train_run.sh $RUN Picklebot-Latent-TimedReach-V2-G1 --agent.seed 74 --agent.max-iterations 5000 \
  --agent.resume True --agent.load-run 2026-10-20_10-00-00_s5g-e1-init --agent.load-checkpoint model_34700.pt
wait
cat artifacts/train/$RUN-early.log
[ -f artifacts/train/$RUN.killed ] && { echo "killed at the early check"; exit 0; }
D=$(ls -d $L/*_$RUN | tail -1); CK=$(ls $D/model_*.pt | sort -V | tail -1); echo "endpoint $CK"
python scripts/motion/timed_reach_eval.py --task Picklebot-Latent-TimedReach-V2-G1 --checkpoint $CK --envs 1024 --seconds 30 --seed 4216110 --json $R-endpoint.json 2>&1 | grep -v -i warn | tail -14

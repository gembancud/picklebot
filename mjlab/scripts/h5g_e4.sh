#!/usr/bin/env bash
# Stage 5G run E4 (D-122): D-118's one extension. One change from E3: root_progress max_speed 1.0 -> 1.6 m/s
# (Picklebot-Latent-TimedReach-V4-G1). Parent: E3's endpoint (s5g-e3-timed-v3/model_39699). 4,096 envs, training seed 74.
# Endpoint: iteration 44699 (5000 more) or the last checkpoint before the 7000 s cap.
# Early kill (D-122) at about 30 % (model_41200): timed_reach_eval, 256 envs, 20 s, seed 4216301: kill if falls > 3 %
# per episode, paddle p90 > 0.20 m, or median speed error > 20 %. A crashed evaluation never kills (D-112).
# Gate (D-118, timing per D-122): paddle median <= 0.08 m, p90 <= 0.20 m; timing within 50 ms >= 80 %; speed error
# <= 20 %; falls <= 2 %; root within 0.25 m >= 90 %. Endpoint evaluation: 1024 envs, 30 s, seed 4216310.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
RUN=s5g-e4-root16; L=artifacts/train/logs/picklebot_latent; R=results/stage5g-e4; T=Picklebot-Latent-TimedReach-V4-G1
( # early-kill watcher
  while [ ! -f "$(ls -d $L/*_$RUN 2>/dev/null | tail -1)/model_41200.pt" ]; do
    [ -f artifacts/train/$RUN.exit.json ] && { echo "training ended before the early check"; exit 0; }; sleep 60; done
  D=$(ls -d $L/*_$RUN | tail -1)
  python scripts/motion/timed_reach_eval.py --task $T --checkpoint $D/model_41200.pt --envs 256 --seconds 20 --seed 4216301 \
    --json $R-early.json > /tmp/e4e.log 2>&1 || { echo "EARLY EVALUATION CRASHED (no kill)"; exit 2; }
  python - "$R" <<'PY' && echo "early check: pass" || { echo "early check: KILL"; touch artifacts/train/$RUN.killed; pkill -f "run-name $RUN"; }
import json, sys
d = json.load(open(sys.argv[1] + "-early.json"))
print(f"early: falls {d['fall_rate']:.4f} (kill > 0.03); paddle p90 {d['paddle_err_p90_m']} (kill > 0.20); speed err {d['speed_err_rel_median']} (kill > 0.20)")
sys.exit(0 if (d["fall_rate"] <= 0.03 and d["paddle_err_p90_m"] <= 0.20 and d["speed_err_rel_median"] <= 0.20) else 1)
PY
) > artifacts/train/$RUN-early.log 2>&1 &
bash scripts/train_run.sh $RUN $T --agent.seed 74 --agent.max-iterations 5000 \
  --agent.resume True --agent.load-run 2026-10-20_15-12-17_s5g-e3-timed-v3 --agent.load-checkpoint model_39699.pt
wait
cat artifacts/train/$RUN-early.log
[ -f artifacts/train/$RUN.killed ] && { echo "killed at the early check"; exit 0; }
D=$(ls -d $L/*_$RUN | tail -1); CK=$(ls $D/model_*.pt | sort -V | tail -1); echo "endpoint $CK"
python scripts/motion/timed_reach_eval.py --task $T --checkpoint $CK --envs 1024 --seconds 30 --seed 4216310 --json $R-endpoint.json 2>&1 | grep -v -i warn | tail -30

#!/usr/bin/env bash
# Stage 5G run E6 (D-126, panel round 15): PPO on the robot's own returns (Picklebot-Latent-TimedBall-Own-G1; entropy_coef 0.001 as the D-125 correction) from E3's
# endpoint (s5g-e3-timed-v3/model_39699). One change from E5: every feed is one of E3's own legal returns, mirrored (D-126).
# Everything else as E5.
# 4,096 envs, training seed 77. Endpoint: ITERS more iterations (set from the throughput probe) or the last checkpoint
# before the 7000 s cap.
# Early kill at about 30 % (EARLY): any of
#   ball smoke (stage2_eval, 256 envs, 30 s, seed 4216601): falls per feed > 2.5 %, or legal returns <= LEGAL (E3 zero-shot on this task);
#   ball-free bank re-read (timed_reach_eval on V3, 256 envs, 20 s, seed 4216602): paddle p90 > 0.20 m or speed error > 20 %.
# A crashed evaluation never kills (D-112).
# Endpoint: the ball battery (1,024 envs, 30 s, seed 4216610) with falls per feed reported against 2.5 %; the bank
# re-read (1,024 envs, 30 s, seed 4216611) with the E1 items reported (gate missed, D-124).
# Report only (round 13b), against E3's zero-shot table (seed 4216020): root, legal returns and falls by required speed;
# paddle p90 of reachable goals (<= 1.5 m/s); the share of goals swung at from more than 0.5 m; goals per feed.
# Pre-registered expectation: the bins above 1.5 m/s stay near zero; any gain comes from the 0.5-1.5 m/s bins.
set -uo pipefail
ITERS=${ITERS:?set from the probe}; EARLY=${EARLY:?}; LEGAL=${LEGAL:?the zero-shot legal rate on this task}
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
RUN=s5g-e6-own; L=artifacts/train/logs/picklebot_latent; R=results/stage5g-e6; T=Picklebot-Latent-TimedBall-Own-G1
V3=Picklebot-Latent-TimedReach-V3-G1
BALL="--move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally"
( # early-kill watcher
  while [ ! -f "$(ls -d $L/*_$RUN 2>/dev/null | tail -1)/model_$EARLY.pt" ]; do
    [ -f artifacts/train/$RUN.exit.json ] && { echo "training ended before the early check"; exit 0; }; sleep 60; done
  D=$(ls -d $L/*_$RUN | tail -1)
  python scripts/stage2_eval.py --checkpoint $D/model_$EARLY.pt --task $T --envs 256 --seconds 30 $BALL --seed 4216601 \
    --json $R-early-ball.json > /tmp/e5b.log 2>&1 || { echo "EARLY BALL EVALUATION CRASHED (no kill)"; exit 2; }
  python scripts/motion/timed_reach_eval.py --task $V3 --checkpoint $D/model_$EARLY.pt --envs 256 --seconds 20 --seed 4216602 \
    --json $R-early-bank.json > /tmp/e5r.log 2>&1 || { echo "EARLY BANK EVALUATION CRASHED (no kill)"; exit 2; }
  python - "$R" "$LEGAL" <<'PY' && echo "early check: pass" || { echo "early check: KILL"; touch artifacts/train/$RUN.killed; pkill -f "run-name $RUN"; }
import json, sys
b = json.load(open(sys.argv[1] + "-early-ball.json")); r = json.load(open(sys.argv[1] + "-early-bank.json"))
print(f"early ball: falls per feed {b['fall_rate']:.4f} (kill > 0.025); legal {b['legal_return_rate']:.4f} {b['legal_return_ci95']} (kill <= {sys.argv[2]})")
print(f"early bank: paddle p90 {r['paddle_err_p90_m']} (kill > 0.20); speed err {r['speed_err_rel_median']} (kill > 0.20); "
      f"falls {r['fall_rate']}; timing {r.get('timing_within_50ms')}; root {r.get('root_within_25cm')}")
g = b.get("timed_goals") or {}
for k in ("goals_set", "root_within_25cm_by_required_speed", "legal_returns_and_falls_per_goal_by_required_speed",
          "paddle_err_p90_reachable_m", "paddle_err_over_50cm", "timing_within_50ms"):
    print(f"early ball (report only, round 13b) {k}: {g.get(k)}")
ok = b["fall_rate"] <= 0.025 and b["legal_return_rate"] > float(sys.argv[2]) and r["paddle_err_p90_m"] <= 0.20 and r["speed_err_rel_median"] <= 0.20
sys.exit(0 if ok else 1)
PY
) > artifacts/train/$RUN-early.log 2>&1 &
bash scripts/train_run.sh $RUN $T --agent.seed 77 --agent.max-iterations $ITERS \
  --agent.resume True --agent.load-run 2026-10-20_15-12-17_s5g-e3-timed-v3 --agent.load-checkpoint model_39699.pt
wait
cat artifacts/train/$RUN-early.log
[ -f artifacts/train/$RUN.killed ] && { echo "killed at the early check"; exit 0; }
D=$(ls -d $L/*_$RUN | tail -1); CK=$(ls $D/model_*.pt | sort -V | tail -1); echo "endpoint $CK"
python scripts/stage2_eval.py --checkpoint $CK --task $T --envs 1024 --seconds 30 $BALL --seed 4216610 --json $R-endpoint-ball.json \
  > /tmp/e5eb.log 2>&1; echo "ball endpoint exit $?"; tail -22 /tmp/e5eb.log | grep -v -i warn
python scripts/motion/timed_reach_eval.py --task $V3 --checkpoint $CK --envs 1024 --seconds 30 --seed 4216611 \
  --json $R-endpoint-bank.json 2>&1 | grep -v -i warn | tail -20
grep -a "Mean action std\|Mean action noise std" artifacts/train/$RUN.log | sed -n '1p;$p' | sed 's/^/action std (report only): /'
# Endpoint report (round 15, report only): the court battery on E5's task (retention of the hard families; E3 15.0-15.2 %)
# and a two-robot pair-mode smoke test on E5's task (P(4+), own-ball legal per side), development seeds 4216612 / 4216613.
python scripts/stage2_eval.py --checkpoint $CK --task Picklebot-Latent-TimedBall-PPO-G1 --envs 1024 --seconds 30 $BALL \
  --seed 4216612 --json $R-endpoint-court.json > /tmp/e6c.log 2>&1; echo "court battery exit $?"
python scripts/stage2_eval.py --checkpoint $CK --task Picklebot-Latent-TimedBall-PPO-G1 --envs 2048 --seconds 120 $BALL \
  --pairs --seed 4216613 --json $R-endpoint-pairs.json > /tmp/e6p.log 2>&1; echo "pairs exit $?"
python - "$R" <<'PY'
import json, sys
c = json.load(open(sys.argv[1] + "-endpoint-court.json")); p = json.load(open(sys.argv[1] + "-endpoint-pairs.json"))["pairs"]
print(f"court battery: legal {c['legal_return_rate']:.4f} {c['legal_return_ci95']}; falls/feed {c['fall_rate']:.4f}")
print(f"pairs: rallies {p['rallies']}; P(4+) {p['p_len_ge_4']}; mean {p['mean_len']}; own-ball {p['sides_own_ball']}")
PY

#!/usr/bin/env bash
# Rally run 22's pre-launch check (D-169, coded): the run's exact task and overrides at std x1, learning rate 0, 200
# iterations at 1,024 envs from run 18b model_29000, training seed 127; pair courts, second half. PASS: per-ball legal
# >= 0.678 (S2's 0.648 + 3.0) and feeder share 0.15-0.45. Also reported: shots per rally, P(3+), P(5+), rally ends.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
export PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_LR_PEAK=0 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_LR_TOTAL=0 PICKLEBOT_STD_MIN=0.1
B=--env.actions.ball; OV="$B.court-feed-prob 1.0 $B.refeed-delay-s 0.5 $B.recovery-mode fixed $B.planner-mode off $B.target-mode A"
for f in backhand reach-backhand cross-backhand fast drop low reach-deep short high reach-forehand; do OV="$OV $B.feed-mix.weights.$f 1.0"; done
out=results/prelaunch22.jsonl; rm -f $out
PICKLEBOT_PAIR_LOG=$out PICKLEBOT_PAIR_LOG_EVERY=240 PICKLEBOT_ENVS=1024 PICKLEBOT_WALL_CAP=2400 bash scripts/train_run.sh prelaunch22 \
  Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR2-DrillCourts-Ep120-G1 --agent.seed 127 \
  --agent.max-iterations 200 --agent.resume True --agent.load-run 2026-10-28_12-03-16_rally-18b-sched --agent.load-checkpoint model_29000.pt $ALG $OV
python - $out <<'PY' | tee results/prelaunch22-summary.txt
import json, sys
rows, seen = [], set()
for l in open(sys.argv[1]):
    r = json.loads(l)
    if r["step"] not in seen:
        seen.add(r["step"]); rows.append(r)
a, b = rows[len(rows) // 2], rows[-1]
h = [y - x for x, y in zip(a["len_hist_group"][0], b["len_hist_group"][0])]
er = [y - x for x, y in zip(a["end_reasons"][0], b["end_reasons"][0])]
sp = [b["split"][0][j] - a["split"][0][j] for j in range(2)]
n = sum(h); shots = sum(i * c for i, c in enumerate(h)); per = shots / max(shots + er[0], 1); share = sp[0] / max(sum(sp), 1)
print(f"pair courts: {n} rallies, {shots / max(n, 1):.3f} shots per rally, per-ball legal {per:.4f}, P(3+) {sum(h[3:]) / max(n, 1):.3f}, "
      f"P(5+) {sum(h[5:]) / max(n, 1):.3f}, feeder share {share:.3f}; ends: not legal {er[0]}, reset {er[2]}")
ok = per >= 0.678 and 0.15 <= share <= 0.45
print(f"pre-launch check (D-169): per-ball {per:.4f} (>= 0.678), feeder share {share:.3f} (0.15-0.45): {'ok' if ok else 'STOP'}")
PY

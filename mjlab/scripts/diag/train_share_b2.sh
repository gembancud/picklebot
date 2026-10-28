#!/usr/bin/env bash
# Run 21's pre-launch check re-measured on the pair courts (D-163, panel round 44, 4/1 option 2). The drill-court task
# only (pair_drill_court_frac 0.5), 200 throwaway iterations at 1,024 envs from run 18b model_29000, training seed 106,
# PICKLEBOT_PAIR_LOG every 240 steps with the per-court-group rally histogram (len_hist_group) and rally-end reasons.
# Pre-registered (D-163): pair-court legal shots per finished rally >= 1.64 (2 x run 14's task's 0.82) and pair-court
# feeder share within 0.15-0.45, over the second half of the run; else run 21 does not start and the panel reconvenes.
# Also reported: drill-court shots per rally, pair-court P(3+) and P(5+) in training, and rally ends by reason.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
PRUN=2026-10-28_12-03-16_rally-18b-sched; PCK=model_29000.pt
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
export PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_STD_MIN=0.1 PICKLEBOT_LR_PEAK=1e-4 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_KL_GUARD=0.05 PICKLEBOT_LR_TOTAL=0
T=Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR2-DrillCourts-G1
out=results/train-share-b2-drill.jsonl; rm -f $out
PICKLEBOT_PAIR_LOG=$out PICKLEBOT_PAIR_LOG_EVERY=240 PICKLEBOT_ENVS=1024 PICKLEBOT_WALL_CAP=2400 bash scripts/train_run.sh train-share-b2-drill $T \
  --agent.seed 106 --agent.max-iterations 200 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG
python - $out <<'PY' | tee results/train-share-b2-summary.txt
import json, sys
rows, seen = [], set()
for l in open(sys.argv[1]):
    r = json.loads(l)
    if r["step"] not in seen:
        seen.add(r["step"]); rows.append(r)
a, b = rows[len(rows) // 2], rows[-1]
sp = [[b["split"][i][j] - a["split"][i][j] for j in range(2)] for i in range(2)]
names = ["pair", "drill"]
for g in (0, 1):
    h = [y - x for x, y in zip(a["len_hist_group"][g], b["len_hist_group"][g])]
    n = sum(h); shots = sum(i * c for i, c in enumerate(h))
    er = [y - x for x, y in zip(a["end_reasons"][g], b["end_reasons"][g])]
    share = sp[g][0] / max(sp[g][0] + sp[g][1], 1)
    p3, p5 = sum(h[3:]) / max(n, 1), sum(h[5:]) / max(n, 1)
    print(f"{names[g]} courts: {n} rallies, {shots} shots, {shots / max(n, 1):.3f} shots per rally; P(3+) {p3:.3f}, P(5+) {p5:.3f}; "
          f"feeder share {share:.3f} ({sp[g]}); ends: not legal {er[0]}, busy partner {er[1]}, reset {er[2]}, cap {er[3]}")
    if g == 0:
        L, S = shots / max(n, 1), share
ok = L >= 1.64 and 0.15 <= S <= 0.45
print(f"manipulation check (D-163): pair-court shots per rally {L:.3f} (>= 1.64), pair-court feeder share {S:.3f} (0.15-0.45): {'ok' if ok else 'STOP'}")
PY
echo done > artifacts/train/train-share-b2.done

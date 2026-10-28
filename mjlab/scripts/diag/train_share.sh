#!/usr/bin/env bash
# Training feeder share (D-161 manipulation check, 2026-10-28). Run 20's smoke read a feeder share of 0.686 in its
# second half (about 10 s of play after a fresh start), outside the pre-registered 0.20-0.35, which was taken from the
# pairs reads (no move or swing episodes, 120 s rallies). This measures the share in real training dynamics, with and
# without the cap: 200 throwaway iterations at 1,024 envs from run 18b model_29000 for run 14's task (cap off) and run
# 20's task (cap 5), PICKLEBOT_PAIR_LOG every 240 steps; the share over the last half of each. Training seeds 100 / 101.
# Diagnostic only: nothing is selected, the throwaway run dirs are not used.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
PRUN=2026-10-28_12-03-16_rally-18b-sched; PCK=model_29000.pt
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
export PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_STD_MIN=0.1 PICKLEBOT_LR_PEAK=1e-4 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_KL_GUARD=0.05 PICKLEBOT_LR_TOTAL=0
T=Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR2
for spec in "cap0:$T-G1:100" "cap5:$T-Cap5-G1:101"; do
  tag=${spec%%:*}; rest=${spec#*:}; task=${rest%:*}; seed=${rest##*:}; out=results/train-share-$tag.jsonl; rm -f $out
  PICKLEBOT_PAIR_LOG=$out PICKLEBOT_PAIR_LOG_EVERY=240 PICKLEBOT_ENVS=1024 PICKLEBOT_WALL_CAP=2400 bash scripts/train_run.sh train-share-$tag $task \
    --agent.seed $seed --agent.max-iterations 200 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG
  python - $out $tag <<'PY'
import json, sys
rows, seen = [], set()
for l in open(sys.argv[1]):
    r = json.loads(l)
    if r["step"] not in seen:
        seen.add(r["step"]); rows.append(r)
q = [rows[len(rows) * i // 4] for i in range(4)] + [rows[-1]]
for a, b in zip(q, q[1:]):
    f, h = b["feeder"] - a["feeder"], b["handoffs"] - a["handoffs"]
    print(f"{sys.argv[2]} steps {a['step']}-{b['step']}: feeder share {f / max(f + h, 1):.3f} ({f} feeder, {h} hand-offs)")
PY
done
echo done > artifacts/train/train-share.done

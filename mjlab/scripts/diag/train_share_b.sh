#!/usr/bin/env bash
# Pre-launch manipulation check for rally run 21 (D-162, panel round 43; the round-43 rule: a training premise is
# measured in training before launch). 200 throwaway iterations at 1,024 envs from run 18b model_29000 for run 14's
# task (baseline) and the drill-court task (pair_drill_court_frac 0.5), PICKLEBOT_PAIR_LOG every 240 steps. Reported
# over the second half of each: the feeder share of balls started (all courts; pair courts and drill courts for the
# drill-court task) and the mean training rally length (shots per finished rally). Pass (experiment design, round 43):
# pair-court feeder share within 0.15-0.45 and mean rally length >= 2 x the baseline's. Training seeds 102 / 103.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
PRUN=2026-10-28_12-03-16_rally-18b-sched; PCK=model_29000.pt
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
export PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_STD_MIN=0.1 PICKLEBOT_LR_PEAK=1e-4 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_KL_GUARD=0.05 PICKLEBOT_LR_TOTAL=0
T=Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR2
for spec in "base:$T-G1:102" "drill:$T-DrillCourts-G1:103"; do
  tag=${spec%%:*}; rest=${spec#*:}; task=${rest%:*}; seed=${rest##*:}; out=results/train-share-b-$tag.jsonl; rm -f $out
  PICKLEBOT_PAIR_LOG=$out PICKLEBOT_PAIR_LOG_EVERY=240 PICKLEBOT_ENVS=1024 PICKLEBOT_WALL_CAP=2400 bash scripts/train_run.sh train-share-b-$tag $task \
    --agent.seed $seed --agent.max-iterations 200 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG
done
python - <<'PY' | tee results/train-share-b-summary.txt
import json
def rows(p):
    out, seen = [], set()
    for l in open(p):
        r = json.loads(l)
        if r["step"] not in seen:
            seen.add(r["step"]); out.append(r)
    return out
res = {}
for tag in ("base", "drill"):
    r = rows(f"results/train-share-b-{tag}.jsonl"); a, b = r[len(r) // 2], r[-1]
    f, h = b["feeder"] - a["feeder"], b["handoffs"] - a["handoffs"]
    L = (b["shots"] - a["shots"]) / max(b["rallies"] - a["rallies"], 1)
    sp = [[b["split"][i][j] - a["split"][i][j] for j in range(2)] for i in range(2)]
    pc = sp[0][0] / max(sp[0][0] + sp[0][1], 1); dc = sp[1][0] / max(sp[1][0] + sp[1][1], 1)
    res[tag] = (pc, L)
    print(f"{tag}: feeder share {f / max(f + h, 1):.3f} ({f} feeder, {h} hand-offs); mean training rally {L:.2f} shots"
          + (f"; pair courts {pc:.3f} ({sp[0]}), drill courts {dc:.3f} ({sp[1]})" if tag == "drill" else ""))
pc, L = res["drill"]; Lb = res["base"][1]
ok = 0.15 <= pc <= 0.45 and L >= 2 * Lb
print(f"manipulation check: pair-court feeder share {pc:.3f} (0.15-0.45), rally length {L:.2f} vs 2 x {Lb:.2f}: {'ok' if ok else 'STOP'}")
PY
echo done > artifacts/train/train-share-b.done

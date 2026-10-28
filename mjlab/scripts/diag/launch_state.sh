#!/usr/bin/env bash
# Launch-state measurement (D-165; round 45's route after the screen: S1 per-ball 0.648 rejected C, S2 P(3+) 0.226
# failed M, so "A after launch-state logging"). Logging only (return_stand._launch_log): at each feeder-ball launch, the
# receiver's distance from its recovery spot and its ground speed, binned by the court's previous rally length (0-1, 2-4,
# 5+), and that feeder ball's outcome.
#   reads: run 18b model_29000 and run 19 model_30200, the standard pairs read (0.5 s refeed), seed 4220079 for both;
#   training: run 14's task, 200 iterations at learning rate 0 from model_29000, training seed 110.
# Pre-registered (D-165, coach's round-45 rule): A ("move, then serve") if, in model_30200's read, feeder legal after a
# 5+ rally is >= 5 points below feeder legal after a 0-1 rally AND the median launch displacement after a 5+ rally is
# above the 90th percentile of training's launch displacement; otherwise the panel reconvenes with the training-vs-read
# configuration table (the screen showed the training task itself is harder: mean actions return 0.648 per ball).
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
L=artifacts/train/logs/picklebot_return_stand; PRUN=2026-10-28_12-03-16_rally-18b-sched; PCK=model_29000.pt
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120 --seed 4220079"
for spec in "29000:$L/$PRUN/$PCK" "30200:$(ls -d $L/*_rally-19-cont | tail -1)/model_30200.pt"; do
  PICKLEBOT_LAM_R=2 python scripts/stage2_eval.py --checkpoint ${spec#*:} $PA --json results/launch-${spec%%:*}-pairs.json > /tmp/launch.log 2>&1 \
    || { echo "READ CRASHED: ${spec%%:*}"; tail -5 /tmp/launch.log; }
  echo "read ${spec%%:*} done"
done
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
out=results/launch-train.jsonl; rm -f $out
PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_LR_PEAK=0 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_LR_TOTAL=0 PICKLEBOT_STD_MIN=0.1 PICKLEBOT_PAIR_LOG=$out \
  PICKLEBOT_PAIR_LOG_EVERY=240 PICKLEBOT_ENVS=1024 PICKLEBOT_WALL_CAP=2400 bash scripts/train_run.sh launch-train \
  Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR2-G1 --agent.seed 110 \
  --agent.max-iterations 200 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG
python - <<'PY' | tee results/launch-summary.txt
import json
def quant(hist, edges, q):
    n = sum(hist); c = 0
    for i, k in enumerate(hist):
        c += k
        if n and c >= q * n:
            return f"<= {edges[i]}" if i < len(edges) else f"> {edges[-1]}"
    return "n/a"
rows, seen = [], set()
for l in open("results/launch-train.jsonl"):
    r = json.loads(l)
    if r["step"] not in seen:
        seen.add(r["step"]); rows.append(r)
a, b = rows[len(rows) // 2]["launch"], rows[-1]["launch"]
E = b["d_edges"]
td = [sum(y - x for x, y in zip(a["d_hist"][g], b["d_hist"][g])) for g in range(3)]
tdh = [sum(b["d_hist"][g][i] - a["d_hist"][g][i] for g in range(3)) for i in range(len(E) + 1)]
print(f"training launches by previous rally length (0-1, 2-4, 5+): {td}; training displacement 90th pct {quant(tdh, E, 0.9)} m, "
      f"median {quant(tdh, E, 0.5)} m")
for t in ("29000", "30200"):
    s = json.load(open(f"results/launch-{t}-pairs.json"))["launch_state"]
    o = s["outcome_feeds_legal"]
    leg = [round(x[1] / max(x[0], 1), 4) for x in o]
    print(f"read {t}: feeder legal by previous rally length (0-1, 2-4, 5+) {leg} (n {[x[0] for x in o]}); "
          f"median displacement by bin {[quant(h, E, 0.5) for h in s['d_hist']]}; speed median by bin "
          f"{[quant(h, s['v_edges'], 0.5) for h in s['v_hist']]}")
s = json.load(open("results/launch-30200-pairs.json"))["launch_state"]; o = s["outcome_feeds_legal"]
gap = 100 * (o[0][1] / max(o[0][0], 1) - o[2][1] / max(o[2][0], 1))
print(f"rule: model_30200 feeder legal gap (0-1 minus 5+) {gap:.1f} points (>= 5), 5+ median displacement "
      f"{quant(s['d_hist'][2], E, 0.5)} vs training 90th pct {quant(tdh, E, 0.9)} -> decide by hand from the bins")
PY
echo done > artifacts/train/launch.done

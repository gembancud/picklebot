#!/usr/bin/env bash
# Training-side erosion check (panel round 46, D-166; no majority on one option: A read-side 2, A-T training-side 1,
# E checkpoint contrast 2; tie rule least new code -> E, experiment design's form). Does run 19's feeder-ball loss
# (read: 80.9 -> 77.3 %) also happen in training? Run 14's task (the task run 19 trained on), 200 iterations at 1,024
# envs, learning rate 0, sampled actions, the D-165 launch log; second half.
#   T1 model_29000 (training seed 111), T2 model_30200 (seed 112), T3 model_29000 again (seed 113, the noise replicate).
# Pre-registered (D-166): Dtrain = feeder legal T2 - T1 (pooled; the 0-1 bin reported). If |T3 - T1| > 1.0, extend all
# three to 400 iterations before routing. Dtrain <= -2.0: forgetting under the training distribution -> run 22 (run 19's
# design from model_29000 with feeder-ball returns paid more; the smallest existing knob, else run 11's feeder bonus on
# all feeder families). Dtrain >= -1.0: the loss lives in the read -> attribution (architecture's training-side
# leave-one-out screen). Between: one replicate, then the attribution branch if still between.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
L=artifacts/train/logs/picklebot_return_stand
R18=2026-10-28_12-03-16_rally-18b-sched; R19=$(basename $(ls -d $L/*_rally-19-cont | tail -1))
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
export PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_LR_PEAK=0 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_LR_TOTAL=0 PICKLEBOT_STD_MIN=0.1
T=Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR2-G1
for spec in "T1:$R18:model_29000.pt:111" "T2:$R19:model_30200.pt:112" "T3:$R18:model_29000.pt:113"; do
  IFS=: read tag run ck seed <<< "$spec"; out=results/erosion-$tag.jsonl; rm -f $out
  PICKLEBOT_PAIR_LOG=$out PICKLEBOT_PAIR_LOG_EVERY=240 PICKLEBOT_ENVS=1024 PICKLEBOT_WALL_CAP=2400 bash scripts/train_run.sh erosion-$tag $T \
    --agent.seed $seed --agent.max-iterations 200 --agent.resume True --agent.load-run $run --agent.load-checkpoint $ck $ALG
done
python - <<'PY' | tee results/erosion-summary.txt
import json, math
def rows(p):
    out, seen = [], set()
    for l in open(p):
        r = json.loads(l)
        if r["step"] not in seen:
            seen.add(r["step"]); out.append(r)
    return out
v = {}
for t in ("T1", "T2", "T3"):
    r = rows(f"results/erosion-{t}.jsonl"); a, b = r[len(r) // 2]["launch"]["outcome_feeds_legal"], r[-1]["launch"]["outcome_feeds_legal"]
    o = [[b[g][j] - a[g][j] for j in range(2)] for g in range(3)]
    n, k = sum(x[0] for x in o), sum(x[1] for x in o)
    v[t] = (k / max(n, 1), n, o[0][1] / max(o[0][0], 1))
    print(f"{t}: feeder legal {v[t][0]:.4f} (n {n}; SE {100 * math.sqrt(v[t][0] * (1 - v[t][0]) / max(n, 1)):.2f} pts), "
          f"after 0-1 rallies {v[t][2]:.4f}, by bin {[round(x[1] / max(x[0], 1), 4) for x in o]} (n {[x[0] for x in o]})")
d = 100 * (v["T2"][0] - v["T1"][0]); rep = 100 * (v["T3"][0] - v["T1"][0])
print(f"Dtrain (T2 - T1) {d:+.2f} points; replicate |T3 - T1| {abs(rep):.2f} points")
if abs(rep) > 1.0:
    print("VERDICT: NOISY - extend all three arms to 400 iterations before routing")
elif d <= -2.0:
    print("VERDICT: FORGETTING IN TRAINING - run 22 (feeder-ball returns paid more)")
elif d >= -1.0:
    print("VERDICT: NO TRAINING LOSS - the loss lives in the read -> attribution (training-side leave-one-out)")
else:
    print("VERDICT: BETWEEN - one replicate, then the attribution branch if still between")
PY
echo done > artifacts/train/erosion.done

#!/usr/bin/env bash
# Panel round 45 screen (D-164, 5/5 E; experiment design's design with RL / architecture's x1 calibration arm). Rally
# run 21's drill-court task, from run 18b model_29000, 200 iterations at 1,024 envs with the learning rate at 0
# (rollouts only), PICKLEBOT_PAIR_LOG every 240 steps (per-court-group rally histogram, end reasons, feeder share).
#   S0 (seed 107): std x1, 30 s episodes: calibration, must reproduce run 21's check (1.19 shots per rally, ~0.61 per shot)
#   S1 (seed 108): std x 0.001 (about mean actions; PICKLEBOT_STD_MIN 1e-6): noise attribution
#   S2 (seed 109): std x1, 120 s episodes (task ...-DrillCourts-Ep120-G1): B's lever
# Pre-registered (D-164): M = pair-court P(3+) of finished rallies >= 0.30 and pair-court feeder share 0.15-0.45, second
# half. S1 per-ball legal >= 0.75: noise is the cause (C eligible); <= 0.65: not (C rejected). Route: S2 passes M -> run
# B; else S1 >= 0.75 -> a C screen (std cap) next; else -> A (needs launch-state logging). Diagnostic only.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
L=artifacts/train/logs/picklebot_return_stand; PRUN=2026-10-28_12-03-16_rally-18b-sched; PCK=model_29000.pt
SRUN=2026-10-29_00-00-00_std0001-init
[ -f $L/$SRUN/$PCK ] || CUDA_VISIBLE_DEVICES= python scripts/std_scale_init.py $L/$PRUN/$PCK $L/$SRUN/$PCK --scale 0.001
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
export PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_LR_PEAK=0 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_KL_GUARD=0.05 PICKLEBOT_LR_TOTAL=0
T=Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR2-DrillCourts
for spec in "S0:$T-G1:107:$PRUN:0.1" "S1:$T-G1:108:$SRUN:1e-6" "S2:$T-Ep120-G1:109:$PRUN:0.1"; do
  IFS=: read tag task seed run smin <<< "$spec"; out=results/screen45-$tag.jsonl; rm -f $out
  PICKLEBOT_STD_MIN=$smin PICKLEBOT_PAIR_LOG=$out PICKLEBOT_PAIR_LOG_EVERY=240 PICKLEBOT_ENVS=1024 PICKLEBOT_WALL_CAP=2400 \
    bash scripts/train_run.sh screen45-$tag $task --agent.seed $seed --agent.max-iterations 200 --agent.resume True \
    --agent.load-run $run --agent.load-checkpoint $PCK $ALG
done
python - <<'PY' | tee results/screen45-summary.txt
import json
def rows(p):
    out, seen = [], set()
    for l in open(p):
        r = json.loads(l)
        if r["step"] not in seen:
            seen.add(r["step"]); out.append(r)
    return out
res = {}
for tag in ("S0", "S1", "S2"):
    r = rows(f"results/screen45-{tag}.jsonl"); a, b = r[len(r) // 2], r[-1]
    h = [y - x for x, y in zip(a["len_hist_group"][0], b["len_hist_group"][0])]
    er = [y - x for x, y in zip(a["end_reasons"][0], b["end_reasons"][0])]
    n = sum(h); shots = sum(i * c for i, c in enumerate(h))
    sp = [b["split"][0][j] - a["split"][0][j] for j in range(2)]
    share = sp[0] / max(sum(sp), 1); per = shots / max(shots + er[0], 1)
    p3, p5 = sum(h[3:]) / max(n, 1), sum(h[5:]) / max(n, 1)
    res[tag] = dict(per=per, p3=p3, share=share)
    print(f"{tag}: pair courts {n} rallies, {shots / max(n, 1):.3f} shots per rally, per-ball legal {per:.3f}, P(3+) {p3:.3f}, "
          f"P(5+) {p5:.3f}, feeder share {share:.3f}; ends: not legal {er[0]}, reset {er[2]}")
M = lambda t: res[t]["p3"] >= 0.30 and 0.15 <= res[t]["share"] <= 0.45
s1 = res["S1"]["per"]
print(f"calibration S0: per-ball {res['S0']['per']:.3f} (run 21's check ~0.61)")
print(f"S1 noise attribution: per-ball {s1:.3f} -> " + ("noise is the cause (C eligible)" if s1 >= 0.75 else "noise is not the cause (C rejected)" if s1 <= 0.65 else "in between"))
print("route: " + ("S2 passes M -> run B (120 s pair-court episodes)" if M("S2") else
                    "S1 >= 0.75 -> a C screen (std cap) next" if s1 >= 0.75 else "neither -> A (launch-state logging first)"))
PY
echo done > artifacts/train/screen45.done

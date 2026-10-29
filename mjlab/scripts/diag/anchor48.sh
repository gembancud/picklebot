#!/usr/bin/env bash
# Feed-anchor diagnostic (D-172, panel round 48, architecture's E). Training runs court_feed_prob 1.0 with
# court_feed_anchor_prob 0.75: 25 % of feeder balls are aimed from the robot's current pelvis, so a displaced robot gets
# a ball that comes to it. The pairs read aims every feed from the fixed start spot (feed_anchor "start"). Within the
# 0-1 launch bin (feeder balls after a 0-1 shot rally) training feeder legal is 73.0 % [train-log] against 65.4 % in the
# read [read:protocol] (run 23 model_31400).
# Arms: run 23's task and overrides WITHOUT the cap (read-like restarts), learning rate 0, 200 iterations, 4,096 envs,
# second half, metric = feeder legal in the 0-1 launch bin (launch.outcome_feeds_legal[0]):
#   X0 (seed 139) run 23 model_31400 as is; X1 (seed 140) + court_feed_anchor_prob 1.0;
#   X2 (seed 141) X1 with std x 0.001 (near-mean actions, reported);
#   Y0 (seed 142) / Y1 (seed 143): X0 / X1 from run 22b model_30200 (reported).
# Pre-registered rule (coded): ANCHOR if X0 - X1 >= 3.0 points and |X1 - 65.4| <= 3.0 points: the next run is one
# change, court_feed_anchor_prob 1.0, from run 22b model_30200, with feeder premises measured per launch bin. Otherwise
# MOTOR: the remaining gap is not the anchor; next the agility drill fix (experiment design's F), then D / C.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
L=artifacts/train/logs/picklebot_return_stand
R23=2026-10-29_22-13-00_rally-23-cap3; C23=model_31400.pt
R22=2026-10-29_16-41-45_rally-22b-readcfg; C22=model_30200.pt
S23=2026-10-30_00-00-00_std0001-r23-31400-init
pgrep -f "run-name rally-" > /dev/null && { echo "a rally trainer is running: not started"; exit 1; }
[ -f $L/$R23/$C23 ] && [ -f $L/$R22/$C22 ] || { echo "missing parent"; exit 1; }
[ -f $L/$S23/$C23 ] || CUDA_VISIBLE_DEVICES= python scripts/std_scale_init.py $L/$R23/$C23 $L/$S23/$C23 --scale 0.001
T=Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR2-DrillCourts-Ep120-G1
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
B=--env.actions.ball; OV="$B.court-feed-prob 1.0 $B.refeed-delay-s 0.5 $B.recovery-mode fixed $B.planner-mode off $B.target-mode A"
for f in backhand reach-backhand cross-backhand fast drop low reach-deep short high reach-forehand; do OV="$OV $B.feed-mix.weights.$f 1.0"; done
A1="$B.court-feed-anchor-prob 1.0"
export PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_LR_PEAK=0 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_LR_TOTAL=0
arm() { # tag seed std_min run checkpoint extra-overrides...
  local tag=$1 seed=$2 smin=$3 run=$4 ck=$5; shift 5; local out=results/anchor48-$tag.jsonl; rm -f $out
  PICKLEBOT_STD_MIN=$smin PICKLEBOT_PAIR_LOG=$out PICKLEBOT_PAIR_LOG_EVERY=240 PICKLEBOT_ENVS=4096 PICKLEBOT_WALL_CAP=2400 \
    bash scripts/train_run.sh anchor48-$tag $T --agent.seed $seed --agent.max-iterations 200 --agent.resume True \
    --agent.load-run $run --agent.load-checkpoint $ck $ALG $OV "$@"
  echo "arm $tag: $(cat artifacts/train/anchor48-$tag.exit.json)"
}
arm X0 139 0.1 $R23 $C23
arm X1 140 0.1 $R23 $C23 $A1
arm X2 141 1e-6 $S23 $C23 $A1
arm Y0 142 0.1 $R22 $C22
arm Y1 143 0.1 $R22 $C22 $A1
python - <<'PY' | tee results/anchor48-summary.txt
import glob, json, re
def rows(p):
    out, seen = [], set()
    for l in open(p):
        r = json.loads(l)
        if r["step"] not in seen:
            seen.add(r["step"]); out.append(r)
    return out
def stats(tag):
    r = rows(f"results/anchor48-{tag}.jsonl"); a, b = r[len(r) // 2], r[-1]
    o = [[b["launch"]["outcome_feeds_legal"][g][j] - a["launch"]["outcome_feeds_legal"][g][j] for j in range(2)] for g in range(3)]
    bins = [x[1] / max(x[0], 1) for x in o]
    pooled = sum(x[1] for x in o) / max(sum(x[0] for x in o), 1)
    return bins, pooled, [x[0] for x in o]
s = {t: stats(t) for t in ("X0", "X1", "X2", "Y0", "Y1")}
for t, (bins, pooled, n) in s.items():
    print(f"{t}: feeder legal by launch bin 0-1 / 2-4 / 5+ {bins[0]:.4f} / {bins[1]:.4f} / {bins[2]:.4f} (feeds {n}), pooled {pooled:.4f}")
d = 100 * (s["X0"][0][0] - s["X1"][0][0]); gap = 100 * abs(s["X1"][0][0] - 0.654)
ok = d >= 3.0 and gap <= 3.0
print(f"rule: X0 - X1 (0-1 bin) {d:+.2f} points (needs >= +3.0); |X1 - 65.4| {gap:.2f} points (needs <= 3.0)")
d1 = sorted(glob.glob("artifacts/train/logs/picklebot_return_stand/*_anchor48-X1/params/env.yaml"))
anch = bool(d1) and re.search(r"^\s+court_feed_anchor_prob: 1\.0\s*$", open(d1[-1]).read(), re.M) is not None
print(f"override check X1 court_feed_anchor_prob 1.0: {'ok' if anch else 'VOID'}")
print("VERDICT: VOID" if not anch else ("VERDICT: ANCHOR" if ok else "VERDICT: MOTOR"))
PY
echo done > artifacts/train/anchor48.done

#!/usr/bin/env bash
# Pre-launch check for rally run 23 (D-171). Run 22b (D-170) was killed at model_30200: partner-ball legal 0.769 -> 0.989
# but feeder-ball legal 0.803 -> 0.656 [read:protocol]. In training [train-log] the feeder ball's share of all pair-court
# balls fell 0.290 -> 0.150 as rallies lengthened while training feeder legal fell 0.796 -> 0.731, and the first two
# balls of a rally (the feeder ball and the first robot-to-robot ball) carry nearly all rally ends (failure 0.33 / 0.32
# against <= 0.18 from the third ball on). Candidate single change: end every training rally after its 3rd shot
# (pair_rally_cap 3, D-161's mechanism), so the first balls of a rally keep their share of practice.
# Two arms from run 22b model_30200 (with its optimizer state), run 22b's task and overrides, 1e-4 constant, KL guard
# 0.05, 300 iterations at 4,096 envs: C0 no cap (training seed 135), C3 pair_rally_cap 3 (training seed 136). Measured
# over each arm's second half (pair courts):
#   feeder legal = legal feeder-ball returns / feeder balls (launch outcomes); feeder share = rallies / balls;
#   per-ball legal; failure of ball 0 and ball 1; falls per 1,000 env-seconds (scripts/diag/falls_by_length.py).
# Pre-registered rule (coded below): PASS (run 23 = run 22b's design + pair_rally_cap 3, parent run 22b model_30200)
# if C3 feeder legal - C0 feeder legal >= +0.020, C3 feeder share >= 0.29 and C3 falls <= 4.157 per 1,000 env-seconds.
# Otherwise FAIL: no run 23 on this premise.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
L=artifacts/train/logs/picklebot_return_stand
PRUN=$(basename "$(ls -d $L/*_rally-22b-readcfg | tail -1)"); PCK=model_30200.pt
[ -f $L/$PRUN/$PCK ] || { echo "missing parent $L/$PRUN/$PCK"; exit 1; }
pgrep -f "run-name rally-" > /dev/null && { echo "a rally trainer is running: not started"; exit 1; }
T=Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR2-DrillCourts-Ep120-G1
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
B=--env.actions.ball; OV="$B.court-feed-prob 1.0 $B.refeed-delay-s 0.5 $B.recovery-mode fixed $B.planner-mode off $B.target-mode A"
for f in backhand reach-backhand cross-backhand fast drop low reach-deep short high reach-forehand; do OV="$OV $B.feed-mix.weights.$f 1.0"; done
export PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_STD_MIN=0.1 PICKLEBOT_LR_PEAK=1e-4 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_KL_GUARD=0.05 PICKLEBOT_LR_TOTAL=0
arm() { # tag seed extra-overrides...
  local tag=$1 seed=$2; shift 2; local out=results/prelaunch23-$tag.jsonl; rm -f $out
  PICKLEBOT_PAIR_LOG=$out PICKLEBOT_PAIR_LOG_EVERY=240 PICKLEBOT_ENVS=4096 PICKLEBOT_WALL_CAP=3000 bash scripts/train_run.sh prelaunch23-$tag $T \
    --agent.seed $seed --agent.max-iterations 300 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG $OV "$@"
  echo "arm $tag: $(cat artifacts/train/prelaunch23-$tag.exit.json)"
}
arm C0 135
arm C3 136 $B.pair-rally-cap 3
python - <<'PY' | tee results/prelaunch23-summary.txt
import glob, json, re, sys
sys.path.insert(0, "scripts/diag")
from falls_by_length import falls_per_1000_env_s
def rows(p):
    out, seen = [], set()
    for l in open(p):
        r = json.loads(l)
        if r["step"] not in seen:
            seen.add(r["step"]); out.append(r)
    return out
def stats(tag):
    r = rows(f"results/prelaunch23-{tag}.jsonl"); a, b = r[len(r) // 2], r[-1]
    h = [y - x for x, y in zip(a["len_hist_group"][0], b["len_hist_group"][0])]
    er = [y - x for x, y in zip(a["end_reasons"][0], b["end_reasons"][0])]
    shots = sum(i * c for i, c in enumerate(h)); n = sum(h); balls = shots + er[0]
    o = [[b["launch"]["outcome_feeds_legal"][g][j] - a["launch"]["outcome_feeds_legal"][g][j] for j in range(2)] for g in range(3)]
    fed = sum(x[1] for x in o) / max(sum(x[0] for x in o), 1)
    haz = [h[k] / max(sum(h[k:]), 1) for k in range(2)]  # rallies ending at ball k / rallies reaching ball k (cap ends only at 3)
    falls = falls_per_1000_env_s(f"artifacts/train/prelaunch23-{tag}.log", envs=4096)[0]
    return dict(feeder=fed, share=n / max(balls, 1), per_ball=shots / max(balls, 1), h0=haz[0], h1=haz[1], falls=falls, rallies=n, ends=er)
s = {t: stats(t) for t in ("C0", "C3")}
for t, v in s.items():
    print(f"{t}: feeder legal {v['feeder']:.4f}, feeder share {v['share']:.3f}, per-ball {v['per_ball']:.4f}, failure ball 0 {v['h0']:.3f}, "
          f"ball 1 {v['h1']:.3f}, falls / 1,000 env-s {v['falls']:.3f}, rallies {v['rallies']}, end reasons {v['ends']}")
d = s["C3"]["feeder"] - s["C0"]["feeder"]
ok = d >= 0.020 and s["C3"]["share"] >= 0.29 and s["C3"]["falls"] <= 4.157
print(f"rule: C3 - C0 feeder legal {100 * d:+.2f} (needs >= +2.0); C3 share {s['C3']['share']:.3f} (needs >= 0.29); "
      f"C3 falls {s['C3']['falls']:.3f} (needs <= 4.157)")
d3 = sorted(glob.glob("artifacts/train/logs/picklebot_return_stand/*_prelaunch23-C3/params/env.yaml"))
cap = bool(d3) and re.search(r"^\s+pair_rally_cap: 3\s*$", open(d3[-1]).read(), re.M) is not None
print(f"override check C3 pair_rally_cap 3: {'ok' if cap else 'VOID'}")
print(f"VERDICT: {'PASS' if ok and cap else ('VOID' if not cap else 'FAIL')}: ok" if ok and cap else f"VERDICT: {'VOID' if not cap else 'FAIL'}")
PY
echo done > artifacts/train/prelaunch23.done

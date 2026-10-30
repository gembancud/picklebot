#!/usr/bin/env bash
# Idle-recovery screen (D-177). Premise (ballidx52, matched 0.75-1.5 m band, pair courts): at ball 1 (k=1) the receiver
# stands ~0.62 m from its recovery spot (k>=3: 0.32 m) and nearly still (0.16 vs 0.38 m/s), and k=1 failure rises with
# that distance (.108 / .151 / .232 by tercile). In pair mode spot_progress (the only reward toward recover_xy besides
# recovery_reward, both gated by hit_done) is off for an env with no ball in play unless its last ball's hit_done is
# still set; at rally start after a reset or a no-contact miss nothing pulls the waiting robot to its spot.
# One change: pair_idle_recovery (task Picklebot-Agility-BallIdx-IdleRec-ReadCfg-LamR2-G1): spot_progress (same
# function, weight 1.0, max_speed 1.0) is also active while the env is parked (no ball of its own in play), toward
# recover_xy (RECOVERY_FIXED in this configuration). Observations unchanged.
# Arms from run 22b model_30200 with run 22b's read-like overrides (anchor48's OV, no cap), 1e-4 (ScheduledPPO, no
# warm-up, KL guard 0.05, std min 0.1), 400 iterations, 4,096 envs, last quarter, pair courts:
#   K0a (seed 155) and K0b (seed 156): the BallIdx-ReadCfg tally task (A/A control); KI (seed 157): the IdleRec task.
# Pre-registered rule (coded): PASS if KI k=1 legal - mean(K0) >= +3.0 points AND >= 2 x |K0a - K0b| (k=1), KI k>=3
# legal >= mean(K0) - 1.0 points, KI feeder legal >= mean(K0) - 2.0 points, KI falls <= 4.157 per 1,000 env-seconds,
# and the config check finds pair_idle_recovery: true in KI's params/env.yaml. Else FAIL (VOID if the check fails).
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER
L=artifacts/train/logs/picklebot_return_stand; R=results/idlerec53
R22=2026-10-29_16-41-45_rally-22b-readcfg; C22=model_30200.pt
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
B=--env.actions.ball; OV="$B.court-feed-prob 1.0 $B.refeed-delay-s 0.5 $B.recovery-mode fixed $B.planner-mode off $B.target-mode A"
for f in backhand reach-backhand cross-backhand fast drop low reach-deep short high reach-forehand; do OV="$OV $B.feed-mix.weights.$f 1.0"; done
export PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_LR_PEAK=1e-4 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_LR_TOTAL=0 PICKLEBOT_KL_GUARD=0.05 \
  PICKLEBOT_STD_MIN=0.1 PICKLEBOT_BALLIDX_LOG_EVERY=240 PICKLEBOT_PAIR_LOG_EVERY=240
pgrep -f "run-name " > /dev/null && { echo "a trainer is running: not started"; exit 1; }
[ -f $L/$R22/$C22 ] || { echo "missing parent $L/$R22/$C22"; exit 1; }
arm() { # tag task seed
  local tag=$1 task=$2 seed=$3 out=$R-$1.jsonl pout=$R-$1-pairs.jsonl
  [ -s $out ] && { echo "$out exists: not re-run"; return 1; }
  PICKLEBOT_BALLIDX_LOG=$out PICKLEBOT_PAIR_LOG=$pout PICKLEBOT_ENVS=4096 PICKLEBOT_WALL_CAP=3600 \
    bash scripts/diag/agility_train_run.sh idlerec53-$tag $task --agent.seed $seed --agent.max-iterations 400 \
    --agent.resume True --agent.load-run $R22 --agent.load-checkpoint $C22 $ALG $OV
  echo "arm $tag: $(cat artifacts/train/idlerec53-$tag.exit.json)"
  [ -s $out ] && [ -s $pout ] || { echo "arm $tag wrote no counters"; return 1; }
}
arm K0a Picklebot-Agility-BallIdx-ReadCfg-LamR2-G1 155 || exit 1
arm K0b Picklebot-Agility-BallIdx-ReadCfg-LamR2-G1 156 || exit 1
arm KI Picklebot-Agility-BallIdx-IdleRec-ReadCfg-LamR2-G1 157 || exit 1
python - <<'PY' | tee $R-summary.txt
import glob, json, re, sys
sys.path.insert(0, "scripts/diag")
from falls_by_length import falls_per_1000_env_s
from picklebot_mj import agility_rule as ar, ballidx_rule as br
LO = 0.75  # last quarter
def pick(rows, f):
    s0, s1 = rows[0]["step"], rows[-1]["step"]
    return min(rows, key=lambda r: abs(r["step"] - (s0 + f * (s1 - s0))))
def feeder(tag):
    rows = ar.read_rows(f"results/idlerec53-{tag}-pairs.jsonl")
    a, b = pick(rows, LO), rows[-1]
    o = [[b["launch"]["outcome_feeds_legal"][g][j] - a["launch"]["outcome_feeds_legal"][g][j] for j in range(2)] for g in range(3)]
    return sum(x[1] for x in o) / max(sum(x[0] for x in o), 1), o[0][1] / max(o[0][0], 1), sum(x[0] for x in o), o[0][0]
s, out = {}, {}
print("arm   k=1 legal (n)      k=2 legal (n)      k>=3 legal (n)       feeder legal all (n) / 0-1 bin (n)   falls/1000 env-s")
for t in ("K0a", "K0b", "KI"):
    c = ar.window(ar.read_rows(f"results/idlerec53-{t}.jsonl"), "ballidx", LO, 1.0)
    ks = br.summarize(c, 0)["k"]
    fa, f01, nfa, nf01 = feeder(t)
    falls = falls_per_1000_env_s(f"artifacts/train/idlerec53-{t}.log", envs=4096)[0]
    s[t] = {"k1": ks[0]["legal"], "k2": ks[1]["legal"], "k3": ks[2]["legal"], "n": [k["balls"] for k in ks],
            "k1_contact": ks[0]["contact"], "k1_dist_p50": ks[0]["dist_p50"], "feeder": fa, "feeder_01": f01,
            "feeder_n": [nfa, nf01], "falls": falls}
    v = s[t]
    print(f"{t:4s}  {v['k1']:.4f} ({v['n'][0]:5d})   {v['k2']:.4f} ({v['n'][1]:5d})   {v['k3']:.4f} ({v['n'][2]:6d})"
          f"    {fa:.4f} ({nfa:5d}) / {f01:.4f} ({nf01:5d})         {falls:.3f}")
m = lambda key: (s["K0a"][key] + s["K0b"][key]) / 2  # noqa: E731
aa = 100 * abs(s["K0a"]["k1"] - s["K0b"]["k1"])
d1, d3, df = 100 * (s["KI"]["k1"] - m("k1")), 100 * (s["KI"]["k3"] - m("k3")), 100 * (s["KI"]["feeder"] - m("feeder"))
fk = s["KI"]["falls"]
lines = [(d1 >= 3.0, f"KI k=1 legal - mean(K0): {d1:+.2f} pt >= +3.00"),
         (d1 >= 2 * aa, f"KI k=1 legal - mean(K0): {d1:+.2f} pt >= 2 x |K0a - K0b| = 2 x {aa:.2f} = {2 * aa:.2f}"),
         (d3 >= -1.0, f"KI k>=3 legal - mean(K0): {d3:+.2f} pt >= -1.00"),
         (df >= -2.0, f"KI feeder legal - mean(K0): {df:+.2f} pt >= -2.00"),
         (fk <= 4.157, f"KI falls per 1,000 env-s: {fk:.3f} <= 4.157")]
print("\nrule (last quarter, pair courts):")
for ok, text in lines:
    print(f"  {text} -> {'PASS' if ok else 'FAIL'}")
d = sorted(glob.glob("artifacts/train/logs/picklebot_return_stand/*_idlerec53-KI/params/env.yaml"))
d0 = sorted(glob.glob("artifacts/train/logs/picklebot_return_stand/*_idlerec53-K0a/params/env.yaml"))
flag = bool(d) and re.search(r"^\s+pair_idle_recovery: true\s*$", open(d[-1]).read(), re.M) is not None
ctrl = bool(d0) and re.search(r"^\s+pair_idle_recovery: true\s*$", open(d0[-1]).read(), re.M) is None
print(f"config check KI pair_idle_recovery true: {'ok' if flag else 'VOID'}; K0a without it: {'ok' if ctrl else 'VOID'}")
verdict = "VOID" if not (flag and ctrl) else ("PASS" if all(ok for ok, _ in lines) else "FAIL")
print(f"VERDICT: {verdict}")
json.dump({"arms": s, "rule": [{"ok": ok, "line": t} for ok, t in lines], "verdict": verdict},
          open("results/idlerec53-summary.json", "w"), indent=1)
PY
echo done > artifacts/train/idlerec53.done

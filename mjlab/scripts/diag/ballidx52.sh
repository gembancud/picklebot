#!/usr/bin/env bash
# Ball-index split diagnostic (follow-up to ballidx51, verdict OTHER: ball 1 fails 3-5 x more than balls 3+ at the SAME
# predicted-interception distance). This splits receiver state from shot quality at matched distance: the ballidx51 arm
# exactly (run 22b model_30200, read-like overrides as anchor48's OV, no rally cap, learning rate 0, 200 iterations,
# 4,096 envs, second half, pair courts) with training seed 154 and task Picklebot-Agility-BallIdx-Split-ReadCfg-LamR2-G1
# (the ballidx task plus ball_index_split, logging only). Variables per handed ball (picklebot_mj/tasks/ball_index.py):
#   shot: |spin| at the hand-off, net clearance where it crosses x = 0 and its first-bounce depth (both simulated, before
#   the receiver's contact), incoming horizontal angle vs the court axis;
#   receiver state at the hand-off: pelvis speed, pelvis distance to recover_xy, |yaw| vs facing the net, idle time
#   (since its own last paddle contact or its episode / rally start, whichever is later).
# Matched band: predicted-interception distance 0.75-1.5 m. Pre-registered rule (coded, picklebot_mj/ballidx_rule.py
# route_split): SHOT if a shot variable's k=1 p50 differs from k>=3's by spin +30 %, net clearance -0.10 / +0.15 m,
# bounce depth +/-0.5 m or angle +/-10 deg AND k=1 failure in its worst tercile >= 2 x its best; STATE likewise for
# pelvis speed -0.2 m/s, recovery distance +0.4 m, yaw error +15 deg, idle +1.0 s; both: BOTH; neither: OTHER.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER
L=artifacts/train/logs/picklebot_return_stand; R=results/ballidx52
R22=2026-10-29_16-41-45_rally-22b-readcfg; C22=model_30200.pt
T=Picklebot-Agility-BallIdx-Split-ReadCfg-LamR2-G1
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
B=--env.actions.ball; OV="$B.court-feed-prob 1.0 $B.refeed-delay-s 0.5 $B.recovery-mode fixed $B.planner-mode off $B.target-mode A"
for f in backhand reach-backhand cross-backhand fast drop low reach-deep short high reach-forehand; do OV="$OV $B.feed-mix.weights.$f 1.0"; done
export PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_LR_PEAK=0 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_LR_TOTAL=0 PICKLEBOT_STD_MIN=0.1
export PICKLEBOT_BALLIDX_LOG_EVERY=240
pgrep -f "run-name " > /dev/null && { echo "a trainer is running: not started"; exit 1; }
[ -f $L/$R22/$C22 ] || { echo "missing parent $L/$R22/$C22"; exit 1; }
OUT=$R-K.jsonl
[ -s $OUT ] && { echo "$OUT exists: not re-run"; exit 1; }
PICKLEBOT_BALLIDX_LOG=$OUT PICKLEBOT_ENVS=4096 PICKLEBOT_WALL_CAP=2400 bash scripts/diag/agility_train_run.sh ballidx52-K $T \
  --agent.seed 154 --agent.max-iterations 200 --agent.resume True --agent.load-run $R22 --agent.load-checkpoint $C22 $ALG $OV
echo "arm K: $(cat artifacts/train/ballidx52-K.exit.json)"
[ -s $OUT ] || { echo "arm K wrote no counters"; exit 1; }
python - <<'PY' | tee $R-summary.txt
import glob, json, re
from picklebot_mj import agility_rule as ar, ballidx_rule as br
from picklebot_mj.tasks.ball_index import SHOT_VARS, STATE_VARS
rows = ar.read_rows("results/ballidx52-K.jsonl")
c = ar.window(rows, "ballidx", 0.5, 1.0)
f = lambda x, nd=3: "n/a" if x is None else f"{x:.{nd}f}"  # noqa: E731
print(f"window: second half of {len(rows)} rows, steps {rows[0]['step']}-{rows[-1]['step']}; pair courts")
s = br.summarize(c, 0)
print("k   balls  legal  contact  dist p50")
for k in s["k"]:
    print(f"{k['k']:3s} {k['balls']:6d}  {f(k['legal'])}  {f(k['contact'])}    {f(k['dist_p50'], 2)}")
ss = br.split_summary(c, 0)
print(f"\nmatched band {ss['band_m'][0]:.2f}-{ss['band_m'][1]:.2f} m (predicted-interception distance)")
for fam, names in (("shot", SHOT_VARS), ("receiver state", STATE_VARS)):
    print(f"\n-- {fam} --")
    for name in names:
        for kb, v in zip(br.K_NAMES, ss["vars"][name]):
            ts = "  ".join(f"T{i + 1} {t.get('range', ['-', '-'])[0]}..{t.get('range', ['-', '-'])[1]} n {t['balls']} fail {f(t['failure'])}"
                           for i, t in enumerate(v["terciles"]))
            print(f"{name:13s} k={kb:2s} n {v['balls']:6d} (missing {v['missing']:4d}) p50 {f(v['p50'])} p90 {f(v['p90'])}"
                  f" fail {f(v['failure'])} | {ts}")
r = br.route_split(ss)
print("\nrule (pair courts, matched band, second half):")
for line in r["lines"]:
    print("  " + line)
print(f"fired: SHOT {r['fired']['SHOT']} STATE {r['fired']['STATE']}")
d = sorted(glob.glob("artifacts/train/logs/picklebot_return_stand/*_ballidx52-K/params/env.yaml"))
text = open(d[-1]).read() if d else ""
want = [("ball_index_tally", "true"), ("ball_index_split", "true"), ("court_feed_prob", "1.0"), ("refeed_delay_s", "0.5"),
        ("recovery_mode", "fixed"), ("planner_mode", "'?off'?"), ("target_mode", "A"), ("pair_rally_cap", "0"),
        ("reach_deep", "1.0"), ("fast", "1.0")]
miss = [k for k, v in want if not re.search(rf"^\s*{k}: {v}\s*$", text, re.M)]
print(f"config check: missing {miss} {'ok' if d and not miss else 'VOID'}")
print("VERDICT: VOID" if (not d or miss) else f"VERDICT: {r['verdict']}")
json.dump({"k": [{kk: v for kk, v in k.items() if not kk.endswith("hist")} for k in s["k"]], "split": ss, "rule": r,
           "config_missing": miss}, open("results/ballidx52-summary.json", "w"), indent=1)
PY
echo done > artifacts/train/ballidx52.done

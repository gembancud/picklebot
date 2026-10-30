#!/usr/bin/env bash
# Ball-index tally diagnostic (ball 1). In the reads, two-robot rallies now fail almost only on the first two balls:
# ball 0 (the feeder ball) 0.31-0.37 and ball 1 (the first robot-to-robot ball: the partner receives the feeder-returner's
# shot) 0.26-0.30, against 0.01-0.04 for balls 3-5 (results/selfplay.md, runs 22b / 23). This measures in training WHY
# ball 1 fails: every handed ball by rally index k (1, 2, 3+), incoming speed at the hand-off, predicted-interception
# direction and the receiver's pelvis distance to it, and outcome (picklebot_mj/tasks/ball_index.py).
# One arm: task Picklebot-Agility-BallIdx-ReadCfg-LamR2-G1 (run 22b's training task plus the tally, logging only) with run
# 22b's read-like overrides exactly as scripts/diag/anchor48.sh's OV, no rally cap, learning rate 0 (ScheduledPPO),
# 200 iterations, 4,096 envs, training seed 153, parent run 22b model_30200. Window: the second half. Pair courts
# (group 0, no drill episodes) are the read-like courts and carry the rule; drill courts are reported.
# Pre-registered rule (coded, picklebot_mj/ballidx_rule.py; failure = 1 - legal; terciles by count of k = 1's balls):
#   PACE if k=1 speed p50 >= (k>=3 p50) + 1.0 m/s AND k=1 failure top speed tercile >= 2 x bottom -> a pace ceiling on
#     feeder-ball returns;
#   REACH if k=1 distance p50 >= (k>=3 p50) + 0.5 m AND k=1 failure top distance tercile >= 2 x bottom -> placement
#     shaping of feeder returns toward the partner;
#   DIRECTION if k=1 left + back share >= 2 x k>=3 share AND k=1 left + back failure >= 2 x k=1 forward + right failure
#     -> footwork again (body-limited);
#   otherwise OTHER (report only). Several may fire: all printed, ordered PACE, REACH, DIRECTION.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER
L=artifacts/train/logs/picklebot_return_stand; R=results/ballidx51
R22=2026-10-29_16-41-45_rally-22b-readcfg; C22=model_30200.pt
T=Picklebot-Agility-BallIdx-ReadCfg-LamR2-G1
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
B=--env.actions.ball; OV="$B.court-feed-prob 1.0 $B.refeed-delay-s 0.5 $B.recovery-mode fixed $B.planner-mode off $B.target-mode A"
for f in backhand reach-backhand cross-backhand fast drop low reach-deep short high reach-forehand; do OV="$OV $B.feed-mix.weights.$f 1.0"; done
export PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_LR_PEAK=0 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_LR_TOTAL=0 PICKLEBOT_STD_MIN=0.1
export PICKLEBOT_BALLIDX_LOG_EVERY=240
pgrep -f "run-name " > /dev/null && { echo "a trainer is running: not started"; exit 1; }
[ -f $L/$R22/$C22 ] || { echo "missing parent $L/$R22/$C22"; exit 1; }
OUT=$R-K.jsonl
[ -s $OUT ] && { echo "$OUT exists: not re-run"; exit 1; }
PICKLEBOT_BALLIDX_LOG=$OUT PICKLEBOT_ENVS=4096 PICKLEBOT_WALL_CAP=2400 bash scripts/diag/agility_train_run.sh ballidx51-K $T \
  --agent.seed 153 --agent.max-iterations 200 --agent.resume True --agent.load-run $R22 --agent.load-checkpoint $C22 $ALG $OV
echo "arm K: $(cat artifacts/train/ballidx51-K.exit.json)"
[ -s $OUT ] || { echo "arm K wrote no counters"; exit 1; }
python - <<'PY' | tee $R-summary.txt
import glob, json, re
from picklebot_mj import agility_rule as ar, ballidx_rule as br
rows = ar.read_rows("results/ballidx51-K.jsonl")
c = ar.window(rows, "ballidx", 0.5, 1.0)
print(f"window: steps {rows[len(rows) // 2]['step']}-{rows[-1]['step']} of {rows[-1]['step']} (second half, {len(rows)} rows)")
out = {"window": [rows[len(rows) // 2]["step"], rows[-1]["step"]], "groups": {}}
for g, gname in ((0, "pair courts"), (1, "drill courts")):
    s = br.summarize(c, g)
    out["groups"][gname] = s
    print(f"\n== {gname} ==")
    print("k   balls  legal  contact  legal|contact  speed p50/p90  hspeed p50  dist p50/p90  void  censored  fell  early  none")
    for k in s["k"]:
        f = lambda x, nd=3: "n/a" if x is None else f"{x:.{nd}f}"  # noqa: E731
        print(f"{k['k']:3s} {k['balls']:6d}  {f(k['legal'])}  {f(k['contact'])}    {f(k['legal_given_contact'])}"
              f"        {f(k['speed_p50'], 2)}/{f(k['speed_p90'], 2)}     {f(k['hspeed_p50'], 2)}"
              f"       {f(k['dist_p50'], 2)}/{f(k['dist_p90'], 2)}   {k['void']:5d} {k['censored']:6d} {k['fell']:6d}"
              f" {k['early']:6d} {k['directions']['none']['balls']:5d}")
    for k in s["k"]:
        d = k["directions"]
        print(f"  k={k['k']:2s} shares / legal:  " + "  ".join(
            f"{n} {f(d[n]['share'])} / {f(d[n]['legal'])}" for n in ("forward", "left", "back", "right"))
              + f"   left+back share {f(k['lb_share'])}, failure LB {f(k['lb_failure'])} FR {f(k['fr_failure'])}")
    for kk in ("1", "3+"):
        print(f"  failure by incoming speed (0.5 m/s bins), k={kk}: " + ", ".join(
            f"{x['lo']:.1f}:{x['failure']:.2f}({x['balls']})" for x in s["fail_by_speed"][kk] if x["balls"] >= 20))
        print(f"  failure by distance (0.25 m bins), k={kk}: " + ", ".join(
            f"{x['lo']:.2f}:{x['failure']:.2f}({x['balls']})" for x in s["fail_by_dist"][kk] if x["balls"] >= 20))
    for kk, k in (("1", s["k"][0]), ("3+", s["k"][2])):
        for name in ("speed_terciles", "dist_terciles"):
            t = k[name]
            if t["bottom"] is None:
                continue
            w = br.SPEED_BIN if name == "speed_terciles" else br.DIST_BIN
            print(f"  k={kk} {name}: bottom bins {t['bottom']['bins'][0] * w:.2f}-{(t['bottom']['bins'][1] + 1) * w:.2f} "
                  f"n {t['bottom']['balls']} failure {f(t['bottom']['failure'])}; top bins {t['top']['bins'][0] * w:.2f}-"
                  f"{(t['top']['bins'][1] + 1) * w:.2f} n {t['top']['balls']} failure {f(t['top']['failure'])}"
                  f"{' (overlap)' if t['overlap'] else ''}")
s0 = out["groups"]["pair courts"]
r = br.route(s0)
out["rule"] = r
print("\nrule (pair courts, second half):")
for line in r["lines"]:
    print("  " + line)
d = sorted(glob.glob("artifacts/train/logs/picklebot_return_stand/*_ballidx51-K/params/env.yaml"))
text = open(d[-1]).read() if d else ""
want = [("ball_index_tally", "true"), ("court_feed_prob", "1.0"), ("refeed_delay_s", "0.5"), ("recovery_mode", "fixed"),
        ("planner_mode", "'?off'?"), ("target_mode", "A"), ("pair_rally_cap", "0"), ("reach_deep", "1.0"), ("fast", "1.0")]
miss = [k for k, v in want if not re.search(rf"^\s*{k}: {v}\s*$", text, re.M)]
out["config_missing"] = miss
print(f"config check: missing {miss} {'ok' if d and not miss else 'VOID'}")
print("VERDICT: VOID" if (not d or miss) else f"VERDICT: {r['verdict']}")
json.dump(out, open("results/ballidx51-summary.json", "w"), indent=1)
PY
echo done > artifacts/train/ballidx51.done

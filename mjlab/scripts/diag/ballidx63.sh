#!/usr/bin/env bash
# D-198 feeder-ball split (panel round 63: coach, experiment design, architecture: a read first). The rally target's first
# good shot is the feeder ball's return, so P(5+) <= feeder legal (~0.65 for every player); 76 % of feeder failures are
# missed contacts. ballidx52.sh with the feeder-ball tally added (Picklebot-Agility-BallIdx-Feeder-ReadCfg-LamR2-G1:
# the split task + ball_index_feeder; logging only) and three arms, each LR 0, 200 iterations, 4,096 envs, ballidx52's
# overrides, second half, pair courts:
#   C  = the d1s3 child (rally-d1s3 model_31399) on the d1 base (PICKLEBOT_RES_BASE), dev seed 4220303;
#   P  = 22b model_30200 on its own base, dev seed 4220303 (paired with C; reported);
#   C2 = the d1s3 child, dev seed 4220304 (the noise arm).
# Rule: picklebot_mj/feeder_rule.py -> FEED-STATE / FEED-SHOT / FEED-OTHER / INVALID. Reported: P and C - P; the C child's
# pairs read at refeed 0.5 s and 3 s (dev 4220305; D-171's readiness manipulation); k >= 1 summary as ballidx52.
# At LR 0 the reward does not act (the C child's own task differs from 22b's only in move_track_lin_vel).
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER
L=artifacts/train/logs/picklebot_return_stand; R=results/ballidx63
BASE=/mnt/f/dev/picklebot-mjlab/mjlab/$L/2026-10-31_18-24-20_s5c-d1-fw1bS/model_32854.pt
R22=2026-10-29_16-41-45_rally-22b-readcfg; C22=model_30200.pt
RC=2026-11-01_12-07-09_rally-d1s3; CC=model_31399.pt
T=Picklebot-Agility-BallIdx-Feeder-ReadCfg-LamR2-G1
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
B=--env.actions.ball; OV="$B.court-feed-prob 1.0 $B.refeed-delay-s 0.5 $B.recovery-mode fixed $B.planner-mode off $B.target-mode A"
for f in backhand reach-backhand cross-backhand fast drop low reach-deep short high reach-forehand; do OV="$OV $B.feed-mix.weights.$f 1.0"; done
export PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_LR_PEAK=0 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_LR_TOTAL=0 PICKLEBOT_STD_MIN=0.1
export PICKLEBOT_BALLIDX_LOG_EVERY=240
pgrep -f "run-name |kickstart_h4|stage2_eval|footwork_eval" > /dev/null && { echo "GPU busy: not started"; exit 1; }
for f in $BASE $L/$R22/$C22 $L/$RC/$CC; do [ -f $f ] || { echo "missing $f"; exit 1; }; done
arm() {  # name, seed, run, checkpoint, base (or "")
  [ -s $R-$1.jsonl ] && return 0
  if [ -n "$5" ]; then export PICKLEBOT_RES_BASE=$5; else unset PICKLEBOT_RES_BASE; fi
  PICKLEBOT_BALLIDX_LOG=$R-$1.jsonl PICKLEBOT_ENVS=4096 PICKLEBOT_WALL_CAP=2400 bash scripts/diag/agility_train_run.sh ballidx63-$1 $T \
    --agent.seed $2 --agent.max-iterations 200 --agent.resume True --agent.load-run $3 --agent.load-checkpoint $4 $ALG $OV
  unset PICKLEBOT_RES_BASE
  echo "arm $1: $(cat artifacts/train/ballidx63-$1.exit.json)"
}
arm C 4220303 $RC $CC $BASE
arm P 4220303 $R22 $C22 ""
arm C2 4220304 $RC $CC $BASE
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120"
[ -s $R-refeed05.json ] || PICKLEBOT_RES_BASE=$BASE PICKLEBOT_LAM_R=2 python scripts/stage2_eval.py --checkpoint $L/$RC/$CC $PA --seed 4220305 --json $R-refeed05.json > $R-refeed.log 2>&1
[ -s $R-refeed3.json ] || PICKLEBOT_RES_BASE=$BASE PICKLEBOT_LAM_R=2 python scripts/stage2_eval.py --checkpoint $L/$RC/$CC $PA --refeed-delay 3.0 --seed 4220305 --json $R-refeed3.json >> $R-refeed.log 2>&1
python - "$BASE" <<'PY' | tee $R-summary.txt
import glob, json, re, sys
from picklebot_mj import agility_rule as ar, ballidx_rule as br, feeder_rule as fr
base = sys.argv[1]
f = lambda x, nd=3: "n/a" if x is None else f"{x:.{nd}f}"  # noqa: E731
want = [("ball_index_tally", "true"), ("ball_index_split", "true"), ("ball_index_feeder", "true"), ("court_feed_prob", "1.0"),
        ("refeed_delay_s", "0.5"), ("recovery_mode", "fixed"), ("planner_mode", "'?off'?"), ("target_mode", "A"),
        ("pair_rally_cap", "0"), ("reach_deep", "1.0"), ("fast", "1.0")]
c, ok = {}, True
for arm in ("C", "P", "C2"):
    rows = ar.read_rows(f"results/ballidx63-{arm}.jsonl")
    c[arm] = ar.window(rows, "ballidx", 0.5, 1.0)
    d = sorted(glob.glob(f"artifacts/train/logs/picklebot_return_stand/*_ballidx63-{arm}/params/env.yaml"))
    text = open(d[-1]).read() if d else ""
    miss = [k for k, v in want if not re.search(rf"^\s*{k}: {v}\s*$", text, re.M)]
    bc = re.search(r"^\s*base_checkpoint: (\S+)\s*$", text, re.M)
    base_ok = bc is not None and ((bc.group(1) == base) == (arm != "P")) and (arm != "P" or bc.group(1).endswith("s5c-18-merge17/model_32874.pt"))
    ok &= bool(d) and not miss and base_ok
    print(f"arm {arm}: {len(rows)} rows; config missing {miss}; base {bc.group(1) if bc else None} ({'ok' if base_ok else 'WRONG'})")
for arm in ("C", "P", "C2"):
    s = fr.feeder_stats(c[arm])
    k = fr.k3_band_contact(c[arm])
    ks = br.summarize(c[arm], 0)["k"]
    print(f"{arm}: feeder balls {s['balls']} legal {f(s['legal'])} contact {f(s['contact'])}; matched band n {s['band_balls']} "
          f"contact {f(s['band_contact'])} legal {f(s['band_legal'])}; k>=3 band contact {f(k['band_contact'])} (n {k['band_balls']}); "
          + "; ".join(f"k={x['k']} legal {f(x['legal'])} contact {f(x['contact'])}" for x in ks))
    for name, v in s["vars"].items():
        ts = "  ".join(f"T{i + 1} {t.get('range', ['-', '-'])[0]}..{t.get('range', ['-', '-'])[1]} n {t['balls']} fail {f(t['failure'])}"
                       for i, t in enumerate(v["terciles"]))
        print(f"   k=0 {name:13s} p50 {f(v['p50'])} fail {f(v['failure'])} | {ts}")
r = fr.route(c["C"], c["C2"], valid=ok)
print("rule (C, matched band, noise arm C2):")
for line in r["lines"]:
    print("  " + line)
sp, sc = fr.feeder_stats(c["P"]), fr.feeder_stats(c["C"])
if sp["legal"] is not None and sc["legal"] is not None:
    print(f"reported C - P: feeder legal {sc['legal'] - sp['legal']:+.4f}, contact {sc['contact'] - sp['contact']:+.4f}")
import sys as _s
_s.path.insert(0, "scripts")
import rally_check as rc
for tag in ("refeed05", "refeed3"):
    try:
        p = json.load(open(f"results/ballidx63-{tag}.json"))["pairs"]
        print(f"reported C pairs {tag}: P(5+) open {rc.p5_open(p)[0]:.4f}; feeder legal {rc.boot_low(p['court_counts'], 3, 2)[0]:.4f}; "
              f"partner {rc.boot_low(p['court_counts'], 1, 0)[0]:.4f}")
    except FileNotFoundError:
        print(f"reported C pairs {tag}: missing")
json.dump({"rule": {k: v for k, v in r.items() if k != "lines"}, "lines": r["lines"], "config_ok": ok},
          open("results/ballidx63-summary.json", "w"), indent=1, default=str)
print(f"VERDICT: {r['verdict']}")
PY
echo done > artifacts/train/ballidx63.done

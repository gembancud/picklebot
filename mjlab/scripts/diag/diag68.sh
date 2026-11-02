#!/usr/bin/env bash
# D-204 (panel round 68): (i) the first-handed-ball diagnostic, then (iii) the drift control. No new lever until both are in.
# (i) diag68: the parent d1s3 child (model_31399, d1 base), two LR-0 reads with the ball-index split tally (the TF task,
#   4,096 envs, 200 iterations, second half, pair courts, matched band): refeed 0.5 s on dev 4220332, 3.0 s on dev
#   4220333. Rule picklebot_mj/d1_rule.diag68_route on the 0.5-s read: INVALID / STATE / BALL / BOTH / NEITHER.
#   RESTART (reported): k = 1 / 2 / 3+ failure at 3.0 s vs 0.5 s.
# (iii) rally-d1s3ctl: the parent continued 1,200 iterations on its own task with no change (D-203 settings, training
#   seed 197, no smoke: no code change), kill at +360 on D-194's lines only. Guard reads pooled over 4 seeds: parent
#   pairs 4220306 (reused) + 4220328, 4220329, 4220331, direction 4220307 (reused) + 4220334, 4220335, 4220336; the
#   control on the same seeds. Lines: GUARD-N (the parent's single read breaches against its pooled read), DRIFT (the
#   control breaches r19_guards against the pooled parent, or its mean family contact shift <= -2.0 points), NO-DRIFT.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER PICKLEBOT_READY_LOG \
  PICKLEBOT_RESTART_OBS PICKLEBOT_RESTART_OBS_FREEZE
pgrep -f "run-name |kickstart_h4|stage2_eval|footwork_eval|feeder_speed" > /dev/null && { echo "GPU busy: not started"; exit 1; }
R=results/diag68; RC=results/d1s3ctl; CTRL=rally-d1s3ctlb;  # D-204 addendum: b = the relaunch after the task-entry fault (no training ran in rally-d1s3ctl)
 L=artifacts/train/logs/picklebot_return_stand
BASE=/mnt/f/dev/picklebot-mjlab/mjlab/$L/2026-10-31_18-24-20_s5c-d1-fw1bS/model_32854.pt
PRUN=2026-11-01_12-07-09_rally-d1s3; PCK=model_31399.pt; P=$L/$PRUN/$PCK
T=Picklebot-Rally22b-FastMove-G1; TF=Picklebot-Agility-BallIdx-Feeder-ReadCfg-LamR2-G1
for f in $BASE $P; do [ -f $f ] || { echo "missing $f"; exit 1; }; done
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
B=--env.actions.ball
ov() { local o="$B.court-feed-prob 1.0 $B.refeed-delay-s $1 $B.recovery-mode fixed $B.planner-mode off $B.target-mode A"
  for f in backhand reach-backhand cross-backhand fast drop low reach-deep short high reach-forehand; do o="$o $B.feed-mix.weights.$f 1.0"; done; echo "$o"; }
export PICKLEBOT_TRAIN_ENTRY=scripts/diag/footwork_train.py  # registers Picklebot-Rally22b-FastMove-G1 (missing in the first launch)
TRAINENV="PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_STD_MIN=0.1 PICKLEBOT_LR_PEAK=1e-4 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_KL_GUARD=0.05 PICKLEBOT_LR_TOTAL=0"
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120"
onbase() { PICKLEBOT_RES_BASE=$BASE PICKLEBOT_LAM_R=2 "$@"; }
[ -s $R-summary.txt ] || echo "parent $P on the d1 base $BASE" > $R-summary.txt
# (i) the diagnostic reads
diag() {  # name, refeed delay, seed
  [ -s $R-$1.jsonl ] && return 0
  rm -f $R-$1.jsonl
  env PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_LR_PEAK=0 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_LR_TOTAL=0 PICKLEBOT_STD_MIN=0.1 PICKLEBOT_BALLIDX_LOG_EVERY=240 \
    PICKLEBOT_RES_BASE=$BASE PICKLEBOT_BALLIDX_LOG=$R-$1.jsonl PICKLEBOT_ENVS=4096 PICKLEBOT_WALL_CAP=2700 PICKLEBOT_TRAIN_ENTRY=scripts/diag/agility_train.py \
    bash scripts/diag/agility_train_run.sh diag68-$1 $TF --agent.seed $3 --agent.max-iterations 200 --agent.resume True \
    --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG $(ov $2) >> $R-reads.log 2>&1
}
diag r05 0.5 4220332
diag r30 3.0 4220333
diag r05b 0.5 4220337  # D-204 addendum: the 0.5-s read had 939 < 1,000 k = 1 balls in the band; one more seed, counters summed, same rule
python - <<'PY' | tee -a $R-summary.txt
import json, os
from picklebot_mj import agility_rule as ar, ballidx_rule as br, d1_rule as dr
c = {}
for arm in ("r05", "r30", "r05b"):
    p = f"results/diag68-{arm}.jsonl"
    c[arm] = ar.window(ar.read_rows(p), "ballidx", 0.5, 1.0) if os.path.exists(p) and os.path.getsize(p) else None
if c["r05"] is not None and c["r05b"] is not None:  # D-204 addendum: the two 0.5-s seeds summed (4220332 + 4220337)
    c["r05"] = dr.sum_counters(c["r05"], c["r05b"])
    print("0.5-s read: seeds 4220332 + 4220337 summed (D-204 addendum)")
if c["r05"] is None:
    print("VERDICT (i): EVAL-FAIL (no 0.5-s read)")
else:
    v, lines = dr.diag68_route(c["r05"])
    for line in lines:
        print(line)
    for arm in ("r05", "r30"):
        if c[arm] is not None:
            ks = br.summarize(c[arm], 0)["k"]
            print(f"RESTART (reported) {arm}: failure k=1 / 2 / 3+ = " + " / ".join(
                f"{1 - x['legal']:.3f} (n {x['balls']})" if x.get("legal") is not None else "n/a" for x in ks))
    json.dump({"verdict": v, "lines": lines}, open("results/diag68-summary.json", "w"), indent=1)
    print(f"VERDICT (i): {v}")
PY
# (iii) the drift control
if [ ! -f artifacts/train/$CTRL.exit.json ]; then
  ( python - <<'PY' > $RC-kill.txt 2>&1
import os, sys, time
sys.path.insert(0, ".")
from picklebot_mj import d1_rule as dr
LOG, EXIT = "artifacts/train/rally-d1s3ctlb.log", "artifacts/train/rally-d1s3ctlb.exit.json"
k = None
while k is None:
    if os.path.exists(EXIT):
        print("training ended before the +360 check"); sys.exit(0)
    time.sleep(60)
    try:
        k = dr.s2_train_kill(LOG, 31399, "artifacts/train/rally-22b-readcfg.log", 12288)
    except FileNotFoundError:
        pass
print(k[1], flush=True)
if k[0].startswith("KILL"):
    os.system("pkill -f 'run-name rally-d1s3ctlb '")
PY
  ) &
  env $TRAINENV PICKLEBOT_RES_BASE=$BASE PICKLEBOT_PAIR_LOG=$RC-train-share.jsonl PICKLEBOT_SCHED_LOG=$RC-train.jsonl \
    PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=14400 bash scripts/diag/agility_train_run.sh $CTRL $T --agent.seed 197 \
    --agent.max-iterations 1200 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG $(ov 0.5) --agent.save-interval 40
  wait
fi
echo "control training: $(cat artifacts/train/$CTRL.exit.json)" | tee -a $R-summary.txt; cat $RC-kill.txt | tee -a $R-summary.txt
grep -q "KILL-" $RC-kill.txt && { echo "VERDICT (iii): KILL" | tee -a $R-summary.txt; echo done > artifacts/train/diag68.done; exit 0; }
CD=$(ls -d $L/*_$CTRL | tail -1); CC=$(ls $CD/model_*.pt | sort -V | tail -1); echo "control endpoint $CC" | tee -a $R-summary.txt
[ "$(basename $CC)" = model_32598.pt ] || { echo "VERDICT (iii): ENDPOINT-MISMATCH" | tee -a $R-summary.txt; echo done > artifacts/train/diag68.done; exit 0; }
[ -s $RC-parent-pairs-4220306.json ] || cp results/d1s7-parent-pairs.json $RC-parent-pairs-4220306.json
[ -s $RC-parent-dir-4220307.json ] || cp results/d1s7-parent-dir.json $RC-parent-dir-4220307.json
for s in 4220328 4220329 4220331; do
  [ -s $RC-parent-pairs-$s.json ] || onbase python scripts/stage2_eval.py --checkpoint $P $PA --seed $s --json $RC-parent-pairs-$s.json >> $RC-reads.log 2>&1
done
for s in 4220306 4220328 4220329 4220331; do
  [ -s $RC-control-pairs-$s.json ] || onbase python scripts/stage2_eval.py --checkpoint $CC $PA --seed $s --json $RC-control-pairs-$s.json >> $RC-reads.log 2>&1
done
for s in 4220334 4220335 4220336; do
  [ -s $RC-parent-dir-$s.json ] || onbase python scripts/diag/feeder_speed_envelope.py --checkpoint $P --seed $s --json $RC-parent-dir-$s.json >> $RC-reads.log 2>&1
done
for s in 4220307 4220334 4220335 4220336; do
  [ -s $RC-control-dir-$s.json ] || onbase python scripts/diag/feeder_speed_envelope.py --checkpoint $CC --seed $s --json $RC-control-dir-$s.json >> $RC-reads.log 2>&1
done
python - <<'PY' | tee -a $R-summary.txt
import glob, json, sys
sys.path.insert(0, "scripts")
import rally_check as rc
from picklebot_mj import d1_rule as dr
R = "results/d1s3ctl"
need = [f"{R}-{w}-pairs-{s}.json" for w in ("parent", "control") for s in (4220306, 4220328, 4220329, 4220331)]
need += [f"{R}-{w}-dir-{s}.json" for w in ("parent", "control") for s in (4220307, 4220334, 4220335, 4220336)]
miss = [f for f in need if not glob.glob(f)]
if miss:
    print(f"VERDICT (iii): EVAL-FAIL {miss}"); sys.exit(0)
for w in ("parent", "control"):
    pf, pd = dr.pool_reads(sorted(glob.glob(f"{R}-{w}-pairs-*.json")), sorted(glob.glob(f"{R}-{w}-dir-*.json")))
    json.dump(pf, open(f"{R}-{w}-pooled-pairs.json", "w"), indent=1)
    json.dump(pd, open(f"{R}-{w}-pooled-dir.json", "w"), indent=1)
pp = json.load(open(f"{R}-parent-pooled-pairs.json"))
cp = json.load(open(f"{R}-control-pooled-pairs.json"))
print("GUARD-N: the parent's single read (4220306) against its own pooled read:")
gn_ok = rc.r19_guards(json.load(open(f"{R}-parent-pairs-4220306.json"))["per_family"],
                      json.load(open(f"{R}-parent-dir-4220307.json"))["directions"], ref=f"{R}-parent-pooled",
                      cross_ref=f"{R}-parent-pooled-pairs.json", name="parent pooled", cross_name="parent pooled")
print(f"GUARD-N: {'not needed (single read within the guards)' if gn_ok else 'GUARD-N (later guard reads use >= 4 seeds)'}")
print("DRIFT: the control (pooled) against the parent (pooled):")
g = rc.r19_guards(cp["per_family"], json.load(open(f"{R}-control-pooled-dir.json"))["directions"], ref=f"{R}-parent-pooled",
                  cross_ref=f"{R}-parent-pooled-pairs.json", name="parent pooled", cross_name="parent pooled")
ms = dr.mean_family_shift(cp["per_family"], pp["per_family"])
drift = (not g) or ms <= dr.DRIFT_MEAN
print(f"mean family contact shift, control - parent (pooled): {100 * ms:+.2f} points (DRIFT at <= {100 * dr.DRIFT_MEAN:+.1f})")
for w in ("parent", "control"):
    p = json.load(open(f"{R}-{w}-pairs-4220306.json"))["pairs"]
    print(f"{w} on 4220306 (reported): P(5+) open {rc.p5_open(p)[0]:.4f}; feeder {rc.boot_low(p['court_counts'], 3, 2)[0]:.4f}; "
          f"partner {rc.boot_low(p['court_counts'], 1, 0)[0]:.4f}; failure by shot position " + ", ".join(f"{x:.3f}" for x in dr.open_hazards(p)))
v = "DRIFT" if drift else "NO-DRIFT"
json.dump({"guard_n": not gn_ok, "guards_ok": g, "mean_shift": ms, "verdict": v}, open(f"{R}-summary.json", "w"), indent=1)
print(f"VERDICT (iii): {v}")
PY
echo done > artifacts/train/diag68.done

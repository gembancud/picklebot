#!/usr/bin/env bash
# D-206 (panel round 70, 5 of 5 for (iii)): fix the drift before any lever.
# Stage A (reads only, paired reuse): the drift control rally-d1s3ctlb's model_31800 (+400) and model_32200 (+800) on
# D-204's pooled guard seeds (pairs 4220306/328/329/331, direction 4220307/334/335/336). EARLY-DRIFT if +400 breaches
# r19_guards against the pooled parent or its mean family shift <= -2.0 -> stop, panel (the anchored recipe is new code).
# Otherwise LATE -> stage B: rally-d1s3lr = model_31399 on d1s3's task, one change PICKLEBOT_LR_PEAK 1e-4 -> 3e-5, 1,200
# iterations, training seed 201, no smoke (a knob only, as the control), kill at +360 on D-194's lines; read on the same
# pooled seeds. d1_rule.drift_verdict: FIXED / PARTIAL / STILL-DRIFT (against the pooled parent; the control reported).
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER PICKLEBOT_READY_LOG \
  PICKLEBOT_RESTART_OBS PICKLEBOT_RESTART_OBS_FREEZE
pgrep -f "run-name |kickstart_h4|stage2_eval|footwork_eval|feeder_speed" > /dev/null && { echo "GPU busy: not started"; exit 1; }
R=results/drift70; RC=results/d1s3ctl; RUN=rally-d1s3lr; L=artifacts/train/logs/picklebot_return_stand
BASE=/mnt/f/dev/picklebot-mjlab/mjlab/$L/2026-10-31_18-24-20_s5c-d1-fw1bS/model_32854.pt
PRUN=2026-11-01_12-07-09_rally-d1s3; PCK=model_31399.pt; P=$L/$PRUN/$PCK
CD=$L/2026-11-02_17-23-37_rally-d1s3ctlb; T=Picklebot-Rally22b-FastMove-G1
for f in $BASE $P $CD/model_31800.pt $CD/model_32200.pt; do [ -f $f ] || { echo "missing $f"; exit 1; }; done
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
B=--env.actions.ball; OV="$B.court-feed-prob 1.0 $B.refeed-delay-s 0.5 $B.recovery-mode fixed $B.planner-mode off $B.target-mode A"
for f in backhand reach-backhand cross-backhand fast drop low reach-deep short high reach-forehand; do OV="$OV $B.feed-mix.weights.$f 1.0"; done
TRAINENV="PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_STD_MIN=0.1 PICKLEBOT_LR_PEAK=3e-5 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_KL_GUARD=0.05 PICKLEBOT_LR_TOTAL=0"
export PICKLEBOT_TRAIN_ENTRY=scripts/diag/footwork_train.py
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120"
onbase() { PICKLEBOT_RES_BASE=$BASE PICKLEBOT_LAM_R=2 "$@"; }
stop() { echo "VERDICT: $1" | tee -a $R-summary.txt; echo done > artifacts/train/drift70.done; exit 0; }
[ -s $R-summary.txt ] || echo "D-206: drift onset on rally-d1s3ctlb, then (if LATE) rally-d1s3lr (LR 3e-5)" > $R-summary.txt
guardreads() {  # tag, checkpoint
  for s in 4220306 4220328 4220329 4220331; do
    [ -s $R-$1-pairs-$s.json ] || onbase python scripts/stage2_eval.py --checkpoint $2 $PA --seed $s --json $R-$1-pairs-$s.json >> $R-reads.log 2>&1
  done
  for s in 4220307 4220334 4220335 4220336; do
    [ -s $R-$1-dir-$s.json ] || onbase python scripts/diag/feeder_speed_envelope.py --checkpoint $2 --seed $s --json $R-$1-dir-$s.json >> $R-reads.log 2>&1
  done
}
judge() {  # tag -> prints lines, last line "RESULT <verdict> <guards_ok> <mean_shift>"
  python - "$1" <<'PY'
import glob, json, sys
sys.path.insert(0, "scripts")
import rally_check as rc
from picklebot_mj import d1_rule as dr
tag, R, RC = sys.argv[1], "results/drift70", "results/d1s3ctl"
pp = sorted(glob.glob(f"{R}-{tag}-pairs-*.json")); dd = sorted(glob.glob(f"{R}-{tag}-dir-*.json"))
if len(pp) != 4 or len(dd) != 4:
    print(f"RESULT EVAL-FAIL False 0"); sys.exit(0)
pf, pd = dr.pool_reads(pp, dd)
par = json.load(open(f"{RC}-parent-pooled-pairs.json"))
print(f"{tag} (pooled) against the parent (pooled):")
g = rc.r19_guards(pf["per_family"], pd["directions"], ref=f"{RC}-parent-pooled", cross_ref=f"{RC}-parent-pooled-pairs.json",
                  name="parent pooled", cross_name="parent pooled")
ms = dr.mean_family_shift(pf["per_family"], par["per_family"])
q = dr.pooled_pairs(pp)
qp = dr.pooled_pairs(sorted(glob.glob(f"{RC}-parent-pairs-42203*.json")))
qc = dr.pooled_pairs(sorted(glob.glob(f"{RC}-control-pairs-42203*.json")))
print(f"{tag}: mean family shift {100 * ms:+.2f} points; pooled feeder {q['feeder']:.4f} (parent {qp['feeder']:.4f}, control "
      f"{qc['feeder']:.4f}); pooled P(5+) {q['p5']:.4f} (parent {qp['p5']:.4f}, control {qc['p5']:.4f})")
v = dr.drift_verdict(g, ms, q["feeder"], qp["feeder"], q["p5"], qp["p5"])
print(f"RESULT {v} {g} {ms:.5f}")
PY
}
# stage A
guardreads ctl400 $CD/model_31800.pt
guardreads ctl800 $CD/model_32200.pt
judge ctl400 | tee -a $R-summary.txt; A=$(tail -1 $R-summary.txt)
judge ctl800 | tee -a $R-summary.txt
set -- $A
[ "$2" = EVAL-FAIL ] && stop "EVAL-FAIL (stage A)"
python -c "import sys; sys.exit(0 if ('$3' == 'True' and float('$4') > -0.02) else 1)" && ONSET=LATE || ONSET=EARLY
echo "stage A onset at +400: $ONSET (EARLY-DRIFT: a breach or mean shift <= -2.0 at +400)" | tee -a $R-summary.txt
[ "$ONSET" = EARLY ] && stop "EARLY-DRIFT (stage B not run; the anchored recipe goes to the panel)"
# stage B
if [ ! -f artifacts/train/$RUN.exit.json ]; then
  ( python - <<'PY' > $R-kill.txt 2>&1
import os, sys, time
sys.path.insert(0, ".")
from picklebot_mj import d1_rule as dr
LOG, EXIT = "artifacts/train/rally-d1s3lr.log", "artifacts/train/rally-d1s3lr.exit.json"
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
    os.system("pkill -f 'run-name rally-d1s3lr '")
PY
  ) &
  env $TRAINENV PICKLEBOT_RES_BASE=$BASE PICKLEBOT_PAIR_LOG=$R-train-share.jsonl PICKLEBOT_SCHED_LOG=$R-train.jsonl \
    PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=14400 bash scripts/diag/agility_train_run.sh $RUN $T --agent.seed 201 \
    --agent.max-iterations 1200 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG $OV --agent.save-interval 40
  wait
fi
echo "training: $(cat artifacts/train/$RUN.exit.json)" | tee -a $R-summary.txt; cat $R-kill.txt | tee -a $R-summary.txt
grep -q "KILL-" $R-kill.txt && stop "KILL ($(grep -o 'KILL-[A-Z-]*' $R-kill.txt | head -1))"
grep -q '"exit_code": 0' artifacts/train/$RUN.exit.json || stop TRAIN-FAIL
D=$(ls -d $L/*_$RUN | tail -1); CK=$D/model_32598.pt; [ -f $CK ] || stop ENDPOINT-MISMATCH
guardreads lr $CK
judge lr | tee -a $R-summary.txt; set -- $(tail -1 $R-summary.txt)
stop "$2 (rally-d1s3lr, LR 3e-5)"

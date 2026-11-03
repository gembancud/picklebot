#!/usr/bin/env bash
# D-210 (panel round 74, 5 of 5 for (ii): LR 3e-5 as the recipe base, no promotion). Training seed 206, two runs:
#   C = rally-d1s3lr3: rally-d1s3lr's recipe (model_31399, d1s3's task, LR 3e-5, ScheduledPPO, no anchor, 1,200 iterations).
#   L = rally-d1s3bh:  C + one change, feeder weights backhand / reach-backhand / cross-backhand 1.0 -> 2.0 (coach).
# No smoke (knobs only). Kill at +360: D-194's lines (each run). Reads on D-204's pooled seeds; the parent's reads reused.
# RECIPE (C vs parent): d1_rule.gain2 + ready >= 0.25 + falls/1000 hits <= 1.3 (confirmatory on seed-206 data only).
# LEVER (L vs C): d1_rule.gain2; r19_guards (pooled) against the parent. LEVER pass + guards -> CONFIRM (pooled, fresh dev
# 4220341-4220344 pairs / 4220345-4220348 direction; parent, C and L re-read; CONFIRM-FAIL on an L breach vs the parent
# or L P(5+) < C); else panel. Reported: the 3-training-seed estimate (d1s3lr, d1s3lr2, C), never a verdict.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER PICKLEBOT_READY_LOG \
  PICKLEBOT_RESTART_OBS PICKLEBOT_RESTART_OBS_FREEZE PICKLEBOT_REF_CKPT PICKLEBOT_REF_COEF
pgrep -f "run-name |kickstart_h4|stage2_eval|footwork_eval|feeder_speed" > /dev/null && { echo "GPU busy: not started"; exit 1; }
R=results/lev74; RC=results/d1s3ctl; L=artifacts/train/logs/picklebot_return_stand
BASE=/mnt/f/dev/picklebot-mjlab/mjlab/$L/2026-10-31_18-24-20_s5c-d1-fw1bS/model_32854.pt
PRUN=2026-11-01_12-07-09_rally-d1s3; PCK=model_31399.pt; P=$L/$PRUN/$PCK; T=Picklebot-Rally22b-FastMove-G1
for f in $BASE $P; do [ -f $f ] || { echo "missing $f"; exit 1; }; done
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
B=--env.actions.ball; BASEOV="$B.court-feed-prob 1.0 $B.refeed-delay-s 0.5 $B.recovery-mode fixed $B.planner-mode off $B.target-mode A"
ov() { local o="$BASEOV" bh=$1
  for f in backhand reach-backhand cross-backhand; do o="$o $B.feed-mix.weights.$f $bh"; done
  for f in fast drop low reach-deep short high reach-forehand; do o="$o $B.feed-mix.weights.$f 1.0"; done; echo "$o"; }
TRAINENV="PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_STD_MIN=0.1 PICKLEBOT_LR_PEAK=3e-5 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_KL_GUARD=0.05 PICKLEBOT_LR_TOTAL=0"
export PICKLEBOT_TRAIN_ENTRY=scripts/diag/footwork_train.py
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120"
onbase() { PICKLEBOT_RES_BASE=$BASE PICKLEBOT_LAM_R=2 "$@"; }
stop() { echo "VERDICT: $1" | tee -a $R-summary.txt; echo done > artifacts/train/lev74.done; exit 0; }
[ -s $R-summary.txt ] || echo "D-210: C = rally-d1s3lr3, L = rally-d1s3bh (backhand-family weights 2.0); training seed 206" > $R-summary.txt
train() {  # run name, backhand weight
  if [ ! -f artifacts/train/$1.exit.json ]; then
    ( python - "$1" <<'PY' > $R-$1-kill.txt 2>&1
import os, sys, time
sys.path.insert(0, ".")
from picklebot_mj import d1_rule as dr
run = sys.argv[1]
LOG, EXIT = f"artifacts/train/{run}.log", f"artifacts/train/{run}.exit.json"
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
    os.system(f"pkill -f 'run-name {run} '")
PY
    ) &
    env $TRAINENV PICKLEBOT_RES_BASE=$BASE PICKLEBOT_SCHED_LOG=$R-$1-train.jsonl PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=14400 \
      bash scripts/diag/agility_train_run.sh $1 $T --agent.seed 206 --agent.max-iterations 1200 --agent.resume True \
      --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG $(ov $2) --agent.save-interval 40
    wait
  fi
  echo "$1 training: $(cat artifacts/train/$1.exit.json)" | tee -a $R-summary.txt; cat $R-$1-kill.txt | tee -a $R-summary.txt
  grep -q "KILL-" $R-$1-kill.txt && stop "KILL $1 ($(grep -o 'KILL-[A-Z-]*' $R-$1-kill.txt | head -1))"
  grep -q '"exit_code": 0' artifacts/train/$1.exit.json || stop "TRAIN-FAIL $1"
}
reads() {  # tag, checkpoint, pairs seeds, direction seeds
  local tag=$1 ck=$2
  for s in $3; do [ -s $R-$tag-pairs-$s.json ] || onbase python scripts/stage2_eval.py --checkpoint $ck $PA --seed $s --json $R-$tag-pairs-$s.json >> $R-reads.log 2>&1; done
  for s in $4; do [ -s $R-$tag-dir-$s.json ] || onbase python scripts/diag/feeder_speed_envelope.py --checkpoint $ck --seed $s --json $R-$tag-dir-$s.json >> $R-reads.log 2>&1; done
}
train rally-d1s3lr3 1.0
train rally-d1s3bh 2.0
CKC=$(ls -d $L/*_rally-d1s3lr3 | tail -1)/model_32598.pt; CKL=$(ls -d $L/*_rally-d1s3bh | tail -1)/model_32598.pt
for f in $CKC $CKL; do [ -f $f ] || stop "ENDPOINT-MISMATCH $f"; done
reads C $CKC "4220306 4220328 4220329 4220331" "4220307 4220334 4220335 4220336"
reads L $CKL "4220306 4220328 4220329 4220331" "4220307 4220334 4220335 4220336"
python - <<'PY' | tee -a $R-summary.txt
import glob, json, os, sys
sys.path.insert(0, "scripts")
import rally_check as rc
from picklebot_mj import d1_rule as dr
R, RC = "results/lev74", "results/d1s3ctl"
S = (4220306, 4220328, 4220329, 4220331); D = (4220307, 4220334, 4220335, 4220336)
par = [f"{RC}-parent-pairs-{s}.json" for s in S]
arm = {w: ([f"{R}-{w}-pairs-{s}.json" for s in S], [f"{R}-{w}-dir-{s}.json" for s in D]) for w in ("C", "L")}
if not all(os.path.exists(f) for w in arm for f in arm[w][0] + arm[w][1]):
    print("RESULT EVAL-FAIL"); sys.exit(0)
ok_c, dc, _, line = dr.gain2(arm["C"][0], par); print("RECIPE " + line)
mc = dr.mechanism(arm["C"][0])
recipe = ok_c and mc["ready"] >= dr.REP_READY and mc["falls_per_1000_hits"] <= dr.REP_FALLS
print(f"RECIPE (C vs parent): GAIN2 {ok_c}, ready {mc['ready']:.3f} (>= {dr.REP_READY}), falls/1000 hits {mc['falls_per_1000_hits']:.2f} (<= {dr.REP_FALLS}) -> {recipe}")
ok_l, dl, _, line = dr.gain2(arm["L"][0], arm["C"][0]); print("LEVER " + line)
pf, pd = dr.pool_reads(*arm["L"])
print("L (pooled) against the parent (pooled):")
g = rc.r19_guards(pf["per_family"], pd["directions"], ref=f"{RC}-parent-pooled", cross_ref=f"{RC}-parent-pooled-pairs.json",
                  name="parent pooled", cross_name="parent pooled")
cf, _ = dr.pool_reads(*arm["C"])
for k in ("backhand", "reach_backhand", "cross_backhand"):
    print(f"(reported) {k} contact: L {pf['per_family'][k]['contact']:.4f}, C {cf['per_family'][k]['contact']:.4f}")
ml = dr.mechanism(arm["L"][0])
for n, m in (("C", mc), ("L", ml)):
    print(f"mechanism (reported) {n}: ready {m['ready']:.3f}, falls/1000 hits {m['falls_per_1000_hits']:.2f}, WRONG_SIDE {m['wrong_side_share']:.3f}, recovery {m['recovery_median_m']:.3f} m")
prev = [dr.pooled_pairs([f"results/drift70-lr-pairs-{s}.json" for s in S])["p5"], dr.pooled_pairs([f"results/rep73-anc-pairs-{s}.json" for s in S])["p5"],
        dr.pooled_pairs(arm["C"][0])["p5"]]
p0 = dr.pooled_pairs(par)["p5"]
print(dr.seed_estimate([x - p0 for x in prev]) + " (d1s3lr, d1s3lr2, C)")
lever = ok_l and g
json.dump({"recipe": recipe, "gain_c": ok_c, "gain_l": ok_l, "guards_l": g, "lever": lever}, open(f"{R}-summary.json", "w"), indent=1)
print(f"RESULT {'CONFIRM' if lever else 'LEVER-FAIL'}")
PY
set -- $(tail -1 $R-summary.txt)
[ "$2" = CONFIRM ] || stop "$2 (RECIPE: $(python -c "import json; print(json.load(open('$R-summary.json'))['recipe'])"))"
for w in parent C L; do
  ck=$P; [ $w = C ] && ck=$CKC; [ $w = L ] && ck=$CKL
  reads confirm-$w $ck "4220341 4220342 4220343 4220344" "4220345 4220346 4220347 4220348"
done
python - <<'PY' | tee -a $R-summary.txt
import glob, json, sys
sys.path.insert(0, "scripts")
import rally_check as rc
from picklebot_mj import d1_rule as dr
R = "results/lev74"
pooled = {}
for w in ("parent", "C", "L"):
    pp = sorted(glob.glob(f"{R}-confirm-{w}-pairs-*.json")); dd = sorted(glob.glob(f"{R}-confirm-{w}-dir-*.json"))
    if len(pp) != 4 or len(dd) != 4:
        print("RESULT CONFIRM-EVAL-FAIL"); sys.exit(0)
    pf, pd = dr.pool_reads(pp, dd)
    json.dump(pf, open(f"{R}-confirm-{w}-pooled-pairs.json", "w"), indent=1); json.dump(pd, open(f"{R}-confirm-{w}-pooled-dir.json", "w"), indent=1)
    pooled[w] = (pf, pd, dr.pooled_pairs(pp))
print("confirmation: L (fresh pooled) against the parent (fresh pooled):")
g = rc.r19_guards(pooled["L"][0]["per_family"], pooled["L"][1]["directions"], ref=f"{R}-confirm-parent-pooled",
                  cross_ref=f"{R}-confirm-parent-pooled-pairs.json", name="parent (fresh)", cross_name="parent (fresh)")
p5l, p5c, p5p = pooled["L"][2]["p5"], pooled["C"][2]["p5"], pooled["parent"][2]["p5"]
ok = g and p5l >= p5c
print(f"confirmation pooled P(5+): L {p5l:.4f}, C {p5c:.4f}, parent {p5p:.4f}; guards {g} -> {'CONFIRMED' if ok else 'CONFIRM-FAIL'}")
print(f"RESULT {'CONFIRMED' if ok else 'CONFIRM-FAIL'}")
PY
set -- $(tail -1 $R-summary.txt)
stop "$2"

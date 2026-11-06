#!/usr/bin/env bash
# D-239 (panel round 99, (i) 4 of 5: RL, motion, experiment design, architecture; coach voted (ii), a rerun from M).
# rally-d1s3drl5 (D-238) was killed by KILL-NO-HIT on a restart-censored line; the paired line (D-236's form) is frozen
# now and read on the existing log: N's +181-300 14.054 >= 0.9 x M's +181-300 14.289 (12.86) -> pass.
# Continue: rally-d1s3drl6, resumed from rally-d1s3drl5 model_35320 to the fixed endpoint model_35595 (276 iterations),
# same task (Launch-LeftBack3) and recipe; training seed 241; a fresh share log. No mid-run kill (the remaining run is
# shorter than one post-restart window). Gate and CONFIRM exactly as D-237 / D-238.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER PICKLEBOT_READY_LOG \
  PICKLEBOT_RESTART_OBS PICKLEBOT_RESTART_OBS_FREEZE PICKLEBOT_REF_CKPT PICKLEBOT_REF_COEF PICKLEBOT_PAIR_LOG
pgrep -f "run-name |kickstart_h4|stage2_eval|footwork_eval|feeder_speed|distill_latent|latent_reach_floor" > /dev/null && { echo "GPU busy: not started"; exit 1; }
R=results/lc101; RC=results/d1s3ctl; L=artifacts/train/logs/picklebot_return_stand; RUN=rally-d1s3drl6
BASE=/mnt/f/dev/picklebot-mjlab/mjlab/$L/2026-10-31_18-24-20_s5c-d1-fw1bS/model_32854.pt
PRUN=2026-11-06_15-24-56_rally-d1s3drl3; PCK=model_34996.pt; P=$L/2026-11-04_00-06-34_rally-d1s3lr3/model_32598.pt; PR=$L/$PRUN/$PCK; T=Picklebot-Rally22b-FastMove-DrillReset-Launch-LeftBack3-G1; END=model_35595.pt
C2SHARE=results/lev76-rally-d1s3lr4-share.jsonl
for f in $BASE $P $PR $C2SHARE; do [ -f $f ] || { echo "missing $f"; exit 1; }; done
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
B=--env.actions.ball; OV="$B.court-feed-prob 1.0 $B.refeed-delay-s 0.5 $B.recovery-mode fixed $B.planner-mode off $B.target-mode A"
for f in backhand reach-backhand cross-backhand fast drop low reach-deep short high reach-forehand; do OV="$OV $B.feed-mix.weights.$f 1.0"; done
EP=""
TRAINENV="PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_STD_MIN=0.1 PICKLEBOT_LR_PEAK=3e-5 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_KL_GUARD=0.05 PICKLEBOT_LR_TOTAL=0"
export PICKLEBOT_TRAIN_ENTRY=scripts/diag/footwork_train.py
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120"
onbase() { PICKLEBOT_RES_BASE=$BASE PICKLEBOT_LAM_R=2 "$@"; }
stop() { echo "VERDICT: $1" | tee -a $R-summary.txt; echo done > artifacts/train/lc101.done; exit 0; }
[ -s $R-summary.txt ] || echo "D-239: C = $P (reference); M = $PR (unpromoted, the gate reference); N = $RUN on $T, resumed from rally-d1s3drl5 model_35320; training seed 241" > $R-summary.txt


NRUN=2026-11-06_21-24-15_rally-d1s3drl5; NCK=model_35320.pt
[ -f $L/$NRUN/$NCK ] || { echo "missing $L/$NRUN/$NCK"; exit 1; }
# --- training to the fixed endpoint (no mid-run kill) ------------------------------------------------------------------
if [ ! -f artifacts/train/$RUN.exit.json ]; then
  env $TRAINENV PICKLEBOT_RES_BASE=$BASE PICKLEBOT_PAIR_LOG=$R-train-share.jsonl PICKLEBOT_PAIR_LOG_EVERY=480 PICKLEBOT_SCHED_LOG=$R-train.jsonl \
    PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=14400 bash scripts/diag/agility_train_run.sh $RUN $T \
    --agent.seed 241 --agent.max-iterations 276 --agent.resume True --agent.load-run $NRUN --agent.load-checkpoint $NCK $ALG $OV $EP --agent.save-interval 40
fi
touch $R-kill.txt
echo "training: $(cat artifacts/train/$RUN.exit.json)" | tee -a $R-summary.txt; cat $R-kill.txt | tee -a $R-summary.txt
grep -q -E -- "-> (KILL-|NO-DATA)" $R-kill.txt && stop "KILL ($(grep -o -- '-> KILL-[A-Z-]*' $R-kill.txt | head -1))"
grep -q '"exit_code": 0' artifacts/train/$RUN.exit.json || stop TRAIN-FAIL
CKR=$(ls -d $L/*_$RUN | tail -1)/$END; [ -f $CKR ] || stop ENDPOINT-MISMATCH

# --- reads on D-204's pooled seeds -------------------------------------------------------------------------------------
reads() {  # tag, checkpoint, pairs seeds, direction seeds
  local tag=$1 ck=$2
  for s in $3; do [ -s $R-$tag-pairs-$s.json ] || onbase python scripts/stage2_eval.py --checkpoint $ck $PA --seed $s --json $R-$tag-pairs-$s.json >> $R-reads.log 2>&1; done
  for s in $4; do [ -s $R-$tag-dir-$s.json ] || onbase python scripts/diag/feeder_speed_envelope.py --checkpoint $ck --seed $s --json $R-$tag-dir-$s.json >> $R-reads.log 2>&1; done
}
PAO="$PA"; PA="$PA --pair-drill-reset"
reads R $CKR "4220385 4220386 4220387 4220388" "4220307 4220334 4220335 4220336"
for s in 4220385 4220386 4220387 4220388; do [ -s $R-R-old-$s.json ] || onbase python scripts/stage2_eval.py --checkpoint $CKR $PAO --seed $s --json $R-R-old-$s.json >> $R-reads.log 2>&1; done
CT="--task Picklebot-Latent-Court-Res-G1 --envs 2048 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --recovery random --seed 4220403"
[ -s $R-court-N.json ] || onbase python scripts/stage2_eval.py --checkpoint $CKR $CT --json $R-court-N.json >> $R-reads.log 2>&1
[ -s $R-court-M-4220403.json ] || onbase python scripts/stage2_eval.py --checkpoint $PR $CT --json $R-court-M-4220403.json >> $R-reads.log 2>&1
python - <<'PY' | tee -a $R-summary.txt
import json, os, sys
sys.path.insert(0, "scripts"); sys.path.insert(0, ".")
import rally_check as rc
from picklebot_mj import d1_rule as dr
R, RC = "results/lc101", "results/d1s3ctl"
S = (4220385, 4220386, 4220387, 4220388); D = (4220307, 4220334, 4220335, 4220336)
LBL = {"R": "N", "Ro": "N (old read)", "W": "M", "C": "C", "Co": "C (old read)"}
arm = {"W": ([f"results/lc98-R-pairs-{s}.json" for s in S], [f"results/lc98-R-dir-{s}.json" for s in D]),
       "R": ([f"{R}-R-pairs-{s}.json" for s in S], [f"{R}-R-dir-{s}.json" for s in D]),
       "C": ([f"results/sr91-set-{s}.json" for s in S], [f"results/lev74-C-dir-{s}.json" for s in D]),
       "Ro": ([f"{R}-R-old-{s}.json" for s in S], [f"{R}-R-dir-{s}.json" for s in D]),
       "Co": ([f"results/sr91-old-{s}.json" for s in S], [f"results/lev74-C-dir-{s}.json" for s in D])}
if not all(os.path.exists(f) for w in arm for f in arm[w][0] + arm[w][1]):
    print("RESULT EVAL-FAIL"); sys.exit(0)
ok_g, d, lo, line = dr.gain2(arm["R"][0], arm["C"][0]); print("N vs C " + line)
print("(reported) old read: N vs C " + dr.gain2(arm["Ro"][0], arm["Co"][0])[3])
for w in ("R", "C"):
    print(f"(reported) court conversion {LBL[w]}: " + str({k: round(v, 4) if isinstance(v, float) else v for k, v in dr.court_conv(arm[w][0]).items()}))
pf, pd = dr.pool_reads(*arm["R"])
print("N (pooled) against the original parent (pooled, same seeds):")
g = rc.r19_guards(pf["per_family"], pd["directions"], ref=f"{RC}-parent-pooled", cross_ref=f"{RC}-parent-pooled-pairs.json",
                  name="parent pooled", cross_name="parent pooled")
m = dr.mechanism(arm["R"][0])
print(f"mechanism N: ready {m['ready']:.3f} (>= {dr.REP_READY}), falls/1000 hits {m['falls_per_1000_hits']:.2f} (<= {dr.REP_FALLS}), "
      f"WRONG_SIDE {m['wrong_side_share']:.3f}, recovery {m['recovery_median_m']:.3f} m")
ok_l, lines = dr.cfs79_lines(arm["R"][0], arm["C"][0])
for x in lines:
    print(x)
for w in ("R", "W", "C", "Ro", "Co"):
    q = dr.pooled_pairs(arm[w][0])
    fl = sum(json.load(open(p))["robot_falls"] for p in arm[w][0]); n = sum(json.load(open(p))["envs"] for p in arm[w][0])
    print(f"(reported) {LBL[w]}: P(5+) {q['p5']:.4f}, feeder {q['feeder']:.4f}; R3 pairs falls / (falls + envs) {fl / (fl + n):.4f}")
r3 = json.load(open(f"{R}-court-N.json"))["robot_fall_rate_per_episode"] if os.path.exists(f"{R}-court-N.json") else 1.0
ok_r3 = r3 <= 0.04
print(f"R3: court read N (24 s, dev 4220403) robot falls per episode {r3:.4f} (<= 0.04) -> {ok_r3}")
for w in ("R", "W", "C"):
    _, pdw = dr.pool_reads(*arm[w])
    print(f"(reported) {LBL[w]} direction contact: " + ", ".join(f"{k} {v['contact']:.3f}" for k, v in pdw["directions"].items()))
ob = [[0, 0] for _ in range(8)]
for p in arm["R"][0]:
    L = json.load(open(p)).get("launch_state", {}).get("outcome_by_d")
    if L:
        ob = [[x[0] + y[0], x[1] + y[1]] for x, y in zip(ob, L)]
print("(reported) N " + dr.dist_route(ob)[1][0])
ok_k, line = dr.r_kept(arm["R"][0], arm["W"][0]); print(line.replace("R-KEPT", "M-KEPT").replace(" vs R ", " vs M "))
def _lb(paths):
    n = c = 0
    for p in paths:
        dd = json.load(open(p))["directions"]
        for k in ("left", "back"):
            n += dd[k]["feeds"]; c += dd[k]["feeds"] * dd[k]["contact"]
    return c / max(n, 1), n
(a, na), (bm, nb) = _lb(arm["R"][1]), _lb(arm["W"][1])
se = (a * (1 - a) / max(na, 1) + bm * (1 - bm) / max(nb, 1)) ** 0.5
print(f"(reported) left + back feeder contact N {a:.4f} (n {na}) vs M {bm:.4f} (n {nb}): {100 * (a - bm):+.1f} points, SE {100 * se:.1f}")
w3 = json.load(open(f"{R}-court-M-4220403.json"))["robot_fall_rate_per_episode"] if os.path.exists(f"{R}-court-M-4220403.json") else None
print(f"(reported) R3 court read of the warm start M on dev 4220403: {w3}")
ok = dr.replicated(ok_g, m) and g and ok_l and ok_r3 and ok_k
json.dump({"gain2": ok_g, "guards": g, "mechanism": m, "rec_lines": ok_l, "candidate": ok}, open(f"{R}-summary.json", "w"), indent=1)
print(f"RESULT {'CANDIDATE' if ok else 'NO-CANDIDATE'}")
PY
set -- $(tail -1 $R-summary.txt)
[ "$1" = RESULT ] || stop "SUMMARY-CRASH"
[ "$2" = CANDIDATE ] || stop "$2 (panel)"

# --- CONFIRM on fresh dev seeds ------------------------------------------------------------------------------------------
reads confirm-C $P "4220349 4220350 4220351 4220352" "4220353 4220354 4220355 4220356"  # PA has --pair-drill-reset
reads confirm-R $CKR "4220349 4220350 4220351 4220352" "4220353 4220354 4220355 4220356"
[ -s $R-confirm-court-4220399.json ] || onbase python scripts/stage2_eval.py --checkpoint $CKR ${CT%4220403}4220399 --json $R-confirm-court-4220399.json >> $R-reads.log 2>&1
python - <<'PY' | tee -a $R-summary.txt
import json, os, sys
sys.path.insert(0, "scripts"); sys.path.insert(0, ".")
import rally_check as rc
from picklebot_mj import d1_rule as dr
R = "results/lc101"
S = (4220349, 4220350, 4220351, 4220352); D = (4220353, 4220354, 4220355, 4220356)
arm = {w: ([f"{R}-confirm-{w}-pairs-{s}.json" for s in S], [f"{R}-confirm-{w}-dir-{s}.json" for s in D]) for w in ("C", "R")}
if not all(os.path.exists(f) for w in arm for f in arm[w][0] + arm[w][1]):
    print("RESULT CONFIRM-EVAL-FAIL"); sys.exit(0)
for w in arm:
    pf, pd = dr.pool_reads(*arm[w])
    json.dump(pf, open(f"{R}-confirm-{w}-pooled-pairs.json", "w"), indent=1); json.dump(pd, open(f"{R}-confirm-{w}-pooled-dir.json", "w"), indent=1)
ok_g, d, lo, line = dr.gain2(arm["R"][0], arm["C"][0]); print("confirmation N vs C " + line)
pf, pd = dr.pool_reads(*arm["R"])
print("confirmation: N (fresh pooled) against C (fresh pooled):")
g = rc.r19_guards(pf["per_family"], pd["directions"], ref=f"{R}-confirm-C-pooled", cross_ref=f"{R}-confirm-C-pooled-pairs.json",
                  name="C (fresh)", cross_name="C (fresh)")
m = dr.mechanism(arm["R"][0])
print(f"mechanism N: ready {m['ready']:.3f}, falls/1000 hits {m['falls_per_1000_hits']:.2f}, WRONG_SIDE {m['wrong_side_share']:.3f}, recovery {m['recovery_median_m']:.3f} m")
for x in dr.cfs79_lines(arm["R"][0], arm["C"][0])[1]:
    print("(reported) " + x)
r3c = json.load(open(f"{R}-confirm-court-4220399.json"))["robot_fall_rate_per_episode"]
print(f"confirmation R3: court read N (dev 4220399) {r3c:.4f} (<= 0.04) -> {r3c <= 0.04}")
ok = dr.replicated(ok_g, m) and g and r3c <= 0.04
print(f"RESULT {'CONFIRMED' if ok else 'CONFIRM-FAIL'}")
PY
set -- $(tail -1 $R-summary.txt)
stop "$2"

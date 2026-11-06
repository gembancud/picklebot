#!/usr/bin/env bash
# D-236 (panel round 96, (ii) 3 of 5: coach, motion, architecture; RL and experiment design voted (i), a rerun).
# rally-d1s3drl2 (D-235) was killed at +360 by D-194's KILL-NO-HIT, a line that measures the launcher courts' episode mix.
# Continue it: M = rally-d1s3drl3, resumed from rally-d1s3drl2 model_34160 to the same endpoint model_34996 (837 iterations),
# same task, recipe and lines except D-194's two log lines, replaced by exact counts (d1_rule.launch_kill): KILL-NO-HIT
# (pair-court mean rally length >= 0.9 x R's at the same offsets) and KILL-UNSTABLE (exact falls off the launcher courts
# <= 3.14 per 1,000 env-s). Training seed 237. No new smoke (same task and env; config checked at the kill).
# Kill at +600 (global offset from R's model_33797; window +481-600; every line read before any stop):
#   KILL-NO-HIT, KILL-UNSTABLE; KILL-LOST-OPEN (training (1-h0)(1-h1) over +481-600 >= rally-d1s3drl2's own +20-140
#   value 0.6188 - 0.02); KILL-NO-FALLS (model_34400's court falls / episode on dev 4220397 <= R's 0.0653 - 0.01);
#   config (pair_launch_court_frac 0.25, launch_time_out, no fall term).
# Gate and CONFIRM unchanged from D-235: every D-231 line on dev 4220385-4220388 against C, R-KEPT, R3 <= 0.04 on dev
#   4220398; CONFIRM dev 4220349-4220356 plus R3 on dev 4220399.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER PICKLEBOT_READY_LOG \
  PICKLEBOT_RESTART_OBS PICKLEBOT_RESTART_OBS_FREEZE PICKLEBOT_REF_CKPT PICKLEBOT_REF_COEF PICKLEBOT_PAIR_LOG
pgrep -f "run-name |kickstart_h4|stage2_eval|footwork_eval|feeder_speed|distill_latent|latent_reach_floor" > /dev/null && { echo "GPU busy: not started"; exit 1; }
R=results/lc98; RC=results/d1s3ctl; L=artifacts/train/logs/picklebot_return_stand; RUN=rally-d1s3drl3
BASE=/mnt/f/dev/picklebot-mjlab/mjlab/$L/2026-10-31_18-24-20_s5c-d1-fw1bS/model_32854.pt
PRUN=2026-11-06_05-15-42_rally-d1s3dr; PCK=model_33797.pt; P=$L/2026-11-04_00-06-34_rally-d1s3lr3/model_32598.pt; PR=$L/$PRUN/$PCK; T=Picklebot-Rally22b-FastMove-DrillReset-Launch-G1; END=model_34996.pt
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
stop() { echo "VERDICT: $1" | tee -a $R-summary.txt; echo done > artifacts/train/lc98.done; exit 0; }
[ -s $R-summary.txt ] || echo "D-236: C = $P (reference); R = $PR (unpromoted); M = $RUN on $T (launcher courts), resumed from rally-d1s3drl2 model_34160; training seed 237" > $R-summary.txt

KRUN=2026-11-06_14-21-55_rally-d1s3drl2; KCK=model_34160.pt
[ -f $L/$KRUN/$KCK ] || { echo "missing $L/$KRUN/$KCK"; exit 1; }
export KILL_BASE=$BASE

# --- training with the +600 kill -----------------------------------------------------------------------------------------
if [ ! -f artifacts/train/$RUN.exit.json ]; then
  ( python - <<'PY' > $R-kill.txt 2>&1
import glob, json, os, re, subprocess, sys, time
sys.path.insert(0, ".")
from picklebot_mj import d1_rule as dr
run, START, RSTART = "rally-d1s3drl3", 33797, 32598
EXIT, SHARE = f"artifacts/train/{run}.exit.json", "results/lc98-train-share.jsonl"
rd = lambda p: [json.loads(x) for x in open(p)] if os.path.exists(p) else []  # noqa: E731
CKN = (START + 600 + 39) // 40 * 40
ck = None
while ck is None:
    if os.path.exists(EXIT):
        print("training ended before the +600 check"); sys.exit(0)
    time.sleep(60)
    rows = rd(SHARE)
    c = glob.glob(f"artifacts/train/logs/picklebot_return_stand/*_{run}/model_{CKN}.pt")
    if c and rows and rows[-1]["step"] >= (START + 600) * dr.STEPS_PER_IT:
        ck = c[0]
rows = rd(SHARE)
v = []
for x, line in dr.launch_kill(rows, rd("results/dr92-train-share.jsonl"), START, RSTART, 12288 - 3072):
    v.append(x); print(line, flush=True)
e = dr.train_open(rd("results/lc97-train-share.jsonl"), 20, 140, START)
l = dr.train_open(rows, 481, 600, START)
if e is None or l is None or min(e["n"], l["n"]) < dr.OPEN_MIN_RALLIES:
    v.append("NO-DATA"); print("KILL-LOST-OPEN: not readable -> NO-DATA", flush=True)
else:
    ok = l["open2"] >= e["open2"] - dr.OPEN_KEEP - 1e-9
    v.append("CONTINUE" if ok else "KILL-LOST-OPEN")
    print(f"KILL-LOST-OPEN: training (1-h0)(1-h1) {e['open2']:.4f} (rally-d1s3drl2 +20-140) -> {l['open2']:.4f} (+481-600) "
          f"(>= -{dr.OPEN_KEEP}; n {e['n']} / {l['n']}) -> " + ("CONTINUE" if ok else "KILL-LOST-OPEN"), flush=True)
envy = open(os.path.join(os.path.dirname(ck), "params", "env.yaml")).read()
cfg_ok = (re.search(r"^\s*pair_launch_court_frac: 0.25\s*$", envy, re.M) is not None and "launch_time_out" in envy
          and "is_terminated" not in envy and re.search(r"^\s*pair_drill_reset: true\s*$", envy, re.M) is not None)
v.append("CONTINUE" if cfg_ok else "KILL-CONFIG"); print(f"config: launcher courts, launch_time_out, drill reset, no fall term -> {cfg_ok}", flush=True)
env = dict(os.environ, PICKLEBOT_RES_BASE=os.environ["KILL_BASE"], PICKLEBOT_LAM_R="2")
CT = ("--task Picklebot-Latent-Court-Res-G1 --envs 2048 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every "
      "--target A --no-hint --recovery random --seed 4220397").split()
subprocess.run(["python", "scripts/stage2_eval.py", "--checkpoint", ck] + CT + ["--json", "results/lc98-kill-court.json"], env=env,
               stdout=open("results/lc98-kill-court.log", "w"), stderr=subprocess.STDOUT)
try:
    rc_ = json.load(open("results/lc98-kill-court.json"))["robot_fall_rate_per_episode"]
    rr = json.load(open("results/lc96-court-R-4220397.json"))["robot_fall_rate_per_episode"]
    fk = dr.fall_kill(rc_, rr)
except Exception as ex:  # noqa: BLE001
    fk = ("NO-DATA", f"KILL-NO-FALLS: not read ({ex}) -> NO-DATA")
v.append(fk[0]); print(fk[1].replace("+360", "+600"), flush=True)
if any(x.startswith("KILL") or x == "NO-DATA" for x in v):
    os.system(f"pkill -f 'run-name {run} '")
PY
  ) &
  env $TRAINENV PICKLEBOT_RES_BASE=$BASE PICKLEBOT_PAIR_LOG=$R-train-share.jsonl PICKLEBOT_PAIR_LOG_EVERY=480 PICKLEBOT_SCHED_LOG=$R-train.jsonl \
    PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=14400 bash scripts/diag/agility_train_run.sh $RUN $T \
    --agent.seed 237 --agent.max-iterations 837 --agent.resume True --agent.load-run $KRUN --agent.load-checkpoint $KCK $ALG $OV $EP --agent.save-interval 40
  wait
fi
echo "training: $(cat artifacts/train/$RUN.exit.json)" | tee -a $R-summary.txt; cat $R-kill.txt | tee -a $R-summary.txt
grep -q -E -- "-> (KILL-|NO-DATA)" $R-kill.txt && stop "KILL ($(grep -o -- '-> \(KILL-[A-Z-]*\|NO-DATA\)' $R-kill.txt | head -1))"
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
CT="--task Picklebot-Latent-Court-Res-G1 --envs 2048 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --recovery random --seed 4220398"
[ -s $R-court-L.json ] || onbase python scripts/stage2_eval.py --checkpoint $CKR $CT --json $R-court-L.json >> $R-reads.log 2>&1
[ -s $R-court-W-4220398.json ] || onbase python scripts/stage2_eval.py --checkpoint $PR $CT --json $R-court-W-4220398.json >> $R-reads.log 2>&1
python - <<'PY' | tee -a $R-summary.txt
import json, os, sys
sys.path.insert(0, "scripts"); sys.path.insert(0, ".")
import rally_check as rc
from picklebot_mj import d1_rule as dr
R, RC = "results/lc98", "results/d1s3ctl"
S = (4220385, 4220386, 4220387, 4220388); D = (4220307, 4220334, 4220335, 4220336)
arm = {"W": ([f"results/dr92-R-pairs-{s}.json" for s in S], [f"results/dr92-R-dir-{s}.json" for s in D]),
       "R": ([f"{R}-R-pairs-{s}.json" for s in S], [f"{R}-R-dir-{s}.json" for s in D]),
       "C": ([f"results/sr91-set-{s}.json" for s in S], [f"results/lev74-C-dir-{s}.json" for s in D]),
       "Ro": ([f"{R}-R-old-{s}.json" for s in S], [f"{R}-R-dir-{s}.json" for s in D]),
       "Co": ([f"results/sr91-old-{s}.json" for s in S], [f"results/lev74-C-dir-{s}.json" for s in D])}
if not all(os.path.exists(f) for w in arm for f in arm[w][0] + arm[w][1]):
    print("RESULT EVAL-FAIL"); sys.exit(0)
ok_g, d, lo, line = dr.gain2(arm["R"][0], arm["C"][0]); print("R vs C " + line)
print("(reported) old read: R vs C " + dr.gain2(arm["Ro"][0], arm["Co"][0])[3])
for w in ("R", "C"):
    print(f"(reported) court conversion {w}: " + str({k: round(v, 4) if isinstance(v, float) else v for k, v in dr.court_conv(arm[w][0]).items()}))
pf, pd = dr.pool_reads(*arm["R"])
print("R (pooled) against the original parent (pooled, same seeds):")
g = rc.r19_guards(pf["per_family"], pd["directions"], ref=f"{RC}-parent-pooled", cross_ref=f"{RC}-parent-pooled-pairs.json",
                  name="parent pooled", cross_name="parent pooled")
m = dr.mechanism(arm["R"][0])
print(f"mechanism R: ready {m['ready']:.3f} (>= {dr.REP_READY}), falls/1000 hits {m['falls_per_1000_hits']:.2f} (<= {dr.REP_FALLS}), "
      f"WRONG_SIDE {m['wrong_side_share']:.3f}, recovery {m['recovery_median_m']:.3f} m")
ok_l, lines = dr.cfs79_lines(arm["R"][0], arm["C"][0])
for x in lines:
    print(x)
for w in ("R", "C", "Ro", "Co"):
    q = dr.pooled_pairs(arm[w][0])
    fl = sum(json.load(open(p))["robot_falls"] for p in arm[w][0]); n = sum(json.load(open(p))["envs"] for p in arm[w][0])
    print(f"(reported) {w}: P(5+) {q['p5']:.4f}, feeder {q['feeder']:.4f}; R3 pairs falls / (falls + envs) {fl / (fl + n):.4f}")
r3 = json.load(open(f"{R}-court-L.json"))["robot_fall_rate_per_episode"] if os.path.exists(f"{R}-court-L.json") else 1.0
ok_r3 = r3 <= 0.04
print(f"R3: court read L (24 s, dev 4220398) robot falls per episode {r3:.4f} (<= 0.04; R 0.0622 pooled on dev 4220394-4220395) -> {ok_r3}")
for w in ("R", "C"):
    _, pdw = dr.pool_reads(*arm[w])
    print(f"(reported) {w} direction contact: " + ", ".join(f"{k} {v['contact']:.3f}" for k, v in pdw["directions"].items()))
ob = [[0, 0] for _ in range(8)]
for p in arm["R"][0]:
    L = json.load(open(p)).get("launch_state", {}).get("outcome_by_d")
    if L:
        ob = [[x[0] + y[0], x[1] + y[1]] for x, y in zip(ob, L)]
print("(reported) R " + dr.dist_route(ob)[1][0])
ok_k, line = dr.r_kept(arm["R"][0], arm["W"][0]); print(line)
w3 = json.load(open(f"{R}-court-W-4220398.json"))["robot_fall_rate_per_episode"] if os.path.exists(f"{R}-court-W-4220398.json") else None
print(f"(reported) R3 court read of the warm start R on dev 4220398: {w3}")
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
[ -s $R-confirm-court-4220399.json ] || onbase python scripts/stage2_eval.py --checkpoint $CKR ${CT%4220398}4220399 --json $R-confirm-court-4220399.json >> $R-reads.log 2>&1
python - <<'PY' | tee -a $R-summary.txt
import json, os, sys
sys.path.insert(0, "scripts"); sys.path.insert(0, ".")
import rally_check as rc
from picklebot_mj import d1_rule as dr
R = "results/lc98"
S = (4220349, 4220350, 4220351, 4220352); D = (4220353, 4220354, 4220355, 4220356)
arm = {w: ([f"{R}-confirm-{w}-pairs-{s}.json" for s in S], [f"{R}-confirm-{w}-dir-{s}.json" for s in D]) for w in ("C", "R")}
if not all(os.path.exists(f) for w in arm for f in arm[w][0] + arm[w][1]):
    print("RESULT CONFIRM-EVAL-FAIL"); sys.exit(0)
for w in arm:
    pf, pd = dr.pool_reads(*arm[w])
    json.dump(pf, open(f"{R}-confirm-{w}-pooled-pairs.json", "w"), indent=1); json.dump(pd, open(f"{R}-confirm-{w}-pooled-dir.json", "w"), indent=1)
ok_g, d, lo, line = dr.gain2(arm["R"][0], arm["C"][0]); print("confirmation R vs C " + line)
pf, pd = dr.pool_reads(*arm["R"])
print("confirmation: R (fresh pooled) against C (fresh pooled):")
g = rc.r19_guards(pf["per_family"], pd["directions"], ref=f"{R}-confirm-C-pooled", cross_ref=f"{R}-confirm-C-pooled-pairs.json",
                  name="C (fresh)", cross_name="C (fresh)")
m = dr.mechanism(arm["R"][0])
print(f"mechanism R: ready {m['ready']:.3f}, falls/1000 hits {m['falls_per_1000_hits']:.2f}, WRONG_SIDE {m['wrong_side_share']:.3f}, recovery {m['recovery_median_m']:.3f} m")
for x in dr.cfs79_lines(arm["R"][0], arm["C"][0])[1]:
    print("(reported) " + x)
r3c = json.load(open(f"{R}-confirm-court-4220399.json"))["robot_fall_rate_per_episode"]
print(f"confirmation R3: court read L (dev 4220399) {r3c:.4f} (<= 0.04) -> {r3c <= 0.04}")
ok = dr.replicated(ok_g, m) and g and r3c <= 0.04
print(f"RESULT {'CONFIRMED' if ok else 'CONFIRM-FAIL'}")
PY
set -- $(tail -1 $R-summary.txt)
stop "$2"

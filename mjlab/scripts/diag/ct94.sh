#!/usr/bin/env bash
# D-233 (panel round 94: (i) 3 of 5; the (i) forms differed, least new code: RL's zero-code form). K = rally-d1s3drc:
# R (rally-d1s3dr model_33797; UNPROMOTED, NO-CANDIDATE on R3) continued on the R3 read's own task,
# Picklebot-Latent-Court-Res-G1 (8-s episodes, solo launcher feeds, random recovery spots, task defaults; RES_BASE = the d1
# base, LAM_R 2), ScheduledPPO, LR 3e-5, 400 iterations, endpoint model_34196; training seed 232, smoke 233.
# Smoke (60 iterations, 1,024 envs): exit 0, no traceback, falls <= 4.157, std, config (d1 base, lam_r 2.0, 8-s episodes,
#   random recovery, no pairs), training falls readable over 20-60.
# Kill at +120 (30 %): training falls per 1,000 env-s over 100-120 <= 0.8 x the run's own 20-40 window; and the first
#   checkpoint at or after +100 (model_33920) read on the R3 court read, dev 4220391: <= 0.0486 (D-232's line).
# Gate (forgetting is the main risk; KEPT is binding): on the frozen set-start read, dev 4220385-4220388, against C's
#   reference: gain2, r19_guards, the bars, cfs79_lines; R-KEPT (P(5+) >= R's 0.7236 - 0.02); R3 <= 0.04 on dev 4220392
#   (R and C read on 4220392 too, reported). All pass -> CONFIRM on 4220349-4220356 (C re-read) + K's R3 on dev 4220393.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER PICKLEBOT_READY_LOG \
  PICKLEBOT_RESTART_OBS PICKLEBOT_RESTART_OBS_FREEZE PICKLEBOT_REF_CKPT PICKLEBOT_REF_COEF PICKLEBOT_PAIR_LOG
R=results/ct94; RC=results/d1s3ctl; L=artifacts/train/logs/picklebot_return_stand; RUN=rally-d1s3drc
BASE=/mnt/f/dev/picklebot-mjlab/mjlab/$L/2026-10-31_18-24-20_s5c-d1-fw1bS/model_32854.pt
PRUN=2026-11-06_05-15-42_rally-d1s3dr; PCK=model_33797.pt; PR=$L/$PRUN/$PCK; P=$L/2026-11-04_00-06-34_rally-d1s3lr3/model_32598.pt
T=Picklebot-Latent-Court-Res-G1; END=model_34196.pt
for f in $BASE $P $PR; do [ -f $f ] || { echo "missing $f"; exit 1; }; done
if [ ! -f artifacts/train/$RUN.exit.json ]; then
  pgrep -f "run-name |kickstart_h4|stage2_eval|footwork_eval|feeder_speed|distill_latent|latent_reach_floor" > /dev/null && { echo "GPU busy: not started"; exit 1; }
fi
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
TRAINENV="PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_STD_MIN=0.1 PICKLEBOT_LR_PEAK=3e-5 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_KL_GUARD=0.05 PICKLEBOT_LR_TOTAL=0"
export PICKLEBOT_TRAIN_ENTRY=scripts/diag/footwork_train.py
onbase() { PICKLEBOT_RES_BASE=$BASE PICKLEBOT_LAM_R=2 "$@"; }
stop() { echo "VERDICT: $1" | tee -a $R-summary.txt; echo done > artifacts/train/ct94.done; exit 0; }
CTB="--task Picklebot-Latent-Court-Res-G1 --envs 2048 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --recovery random"
[ -s $R-summary.txt ] || echo "D-233: C = $P (reference); warm start R = $PR (unpromoted); K = $RUN on $T; training seed 232, smoke 233" > $R-summary.txt

# --- smoke ---------------------------------------------------------------------------------------------------------------
if [ ! -f artifacts/train/$RUN-smoke.exit.json ]; then
  env $TRAINENV PICKLEBOT_RES_BASE=$BASE PICKLEBOT_LAM_R=2 PICKLEBOT_SCHED_LOG=$R-smoke.jsonl PICKLEBOT_ENVS=1024 PICKLEBOT_WALL_CAP=1800 \
    bash scripts/diag/agility_train_run.sh $RUN-smoke $T --agent.seed 233 --agent.max-iterations 60 --agent.resume True \
    --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG --agent.save-interval 20
fi
SD=$(ls -d $L/*_$RUN-smoke | tail -1)
{ grep -q '"exit_code": 0' artifacts/train/$RUN-smoke.exit.json && echo "smoke exit 0 ok" || echo "smoke exit STOP"; } > /tmp/ct94-smoke.txt
{ grep -a -q -E "Traceback|Error" artifacts/train/$RUN-smoke.log && echo "smoke traceback STOP" || echo "smoke no traceback ok"; } >> /tmp/ct94-smoke.txt
python scripts/diag/falls_by_length.py artifacts/train/$RUN-smoke.log | awk '{r=$NF; print "smoke falls per 1,000 env-seconds", r, (r <= 4.157 ? "ok" : "STOP")}' >> /tmp/ct94-smoke.txt
CUDA_VISIBLE_DEVICES= python - "$(ls $SD/model_*.pt | sort -V | tail -1)" <<'PY' >> /tmp/ct94-smoke.txt
import sys, torch
sd = torch.load(sys.argv[1], map_location="cpu", weights_only=False)
s = sd["actor_state_dict"]["distribution.std_param"]
dead = sorted({i for v in sd["optimizer_state_dict"]["state"].values() if v["exp_avg_sq"].shape == s.shape
               for i in (v["exp_avg_sq"] == 0).nonzero().flatten().tolist()})
print("smoke std min", round(float(s.min()), 4), "outputs with no gradient", dead, "ok" if not dead and float(s.min()) >= 0.0999 else "STOP")
PY
python - "$SD" "$BASE" <<'PY' >> /tmp/ct94-smoke.txt
import re, sys
d, base = sys.argv[1], sys.argv[2]
env = open(f"{d}/params/env.yaml").read()
want = [("episode_length_s", "8.0"), ("recovery_mode", "random"), ("lam_r", "2.0"), ("pair_mode", "false")]
miss = [k for k, v in want if not re.search(rf"^\s*{k}: {v}\s*$", env, re.M)]
based = re.search(rf"^\s*base_checkpoint: {re.escape(base)}\s*$", env, re.M) is not None
print(f"smoke config check: missing {miss}; d1 base {based} -> {'ok' if not miss and based else 'STOP'}")
PY
python - artifacts/train/$RUN-smoke.log <<'PY' >> /tmp/ct94-smoke.txt
import os, sys, tempfile
sys.path.insert(0, "scripts/diag")
from falls_by_length import falls_per_1000_env_s
b = open(sys.argv[1], errors="ignore").read().split("Learning iteration")
if len(b) - 1 < 60:
    print("smoke falls window 20-60 not readable STOP"); sys.exit(0)
with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as f:
    f.write("Learning iteration".join(b[21:61]))
r = falls_per_1000_env_s(f.name, envs=1024)[0]
os.unlink(f.name)
print(f"smoke training falls per 1,000 env-s over 20-60: {r:.3f} readable ok")
PY
cat /tmp/ct94-smoke.txt | tee -a $R-summary.txt
[ "$(grep -c " ok$" /tmp/ct94-smoke.txt)" = 6 ] || stop SMOKE-FAIL

# --- training with the +120 kill ------------------------------------------------------------------------------------------
if [ ! -f artifacts/train/$RUN.exit.json ]; then
  ( python - "$BASE" <<'PY' > $R-kill.txt 2>&1
import glob, json, os, subprocess, sys, tempfile, time
sys.path.insert(0, "scripts/diag")
from falls_by_length import falls_per_1000_env_s
base = sys.argv[1]
run, START = "rally-d1s3drc", 33797
LOG, EXIT = f"artifacts/train/{run}.log", f"artifacts/train/{run}.exit.json"
def seg(b, lo, hi):
    with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as f:
        f.write("Learning iteration".join(b[lo + 1:hi + 1]))
    r = falls_per_1000_env_s(f.name, envs=12288)[0]
    os.unlink(f.name)
    return r
while True:
    if os.path.exists(EXIT):
        print("training ended before the +120 check"); sys.exit(0)
    time.sleep(60)
    try:
        b = open(LOG, errors="ignore").read().split("Learning iteration")
    except FileNotFoundError:
        continue
    if len(b) - 1 >= 125:
        break
e, l = seg(b, 20, 40), seg(b, 100, 120)
ok_f = l <= 0.8 * e + 1e-9
print(f"KILL-NO-SAFER: training falls per 1,000 env-s {e:.3f} over 20-40 -> {l:.3f} over 100-120 (<= 0.8 x) -> "
      + ("CONTINUE" if ok_f else "KILL-NO-SAFER"), flush=True)
ck = None
for _ in range(120):
    c = glob.glob(f"artifacts/train/logs/picklebot_return_stand/*_{run}/model_{(START + 100 + 39) // 40 * 40}.pt")
    if c:
        ck = c[0]; break
    time.sleep(30)
r3 = None
if ck:
    env = dict(os.environ, PICKLEBOT_RES_BASE=base, PICKLEBOT_LAM_R="2")
    subprocess.run(["python", "scripts/stage2_eval.py", "--checkpoint", ck] + os.environ["CTB"].split() + ["--seed", "4220391", "--json", "results/ct94-kill-court.json"],
                   env=env, stdout=open("results/ct94-kill-court.log", "w"), stderr=subprocess.STDOUT)
    r3 = json.load(open("results/ct94-kill-court.json"))["robot_fall_rate_per_episode"]
ok_r = r3 is not None and r3 <= 0.0486 + 1e-9
print(f"KILL-NO-FALLS: {os.path.basename(ck) if ck else None} court falls per episode {r3} on dev 4220391 (<= 0.0486) -> "
      + ("CONTINUE" if ok_r else "KILL-NO-FALLS"), flush=True)
if not (ok_f and ok_r):
    os.system(f"pkill -f 'run-name {run} '")
PY
  ) &
  export CTB
  env $TRAINENV PICKLEBOT_RES_BASE=$BASE PICKLEBOT_LAM_R=2 PICKLEBOT_SCHED_LOG=$R-train.jsonl PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=14400 \
    bash scripts/diag/agility_train_run.sh $RUN $T --agent.seed 232 --agent.max-iterations 400 --agent.resume True \
    --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG --agent.save-interval 40
  wait
fi
echo "training: $(cat artifacts/train/$RUN.exit.json)" | tee -a $R-summary.txt; cat $R-kill.txt | tee -a $R-summary.txt
grep -q -- "-> KILL-" $R-kill.txt && stop "KILL ($(grep -o -- '-> KILL-[A-Z-]*' $R-kill.txt | head -1))"
grep -q '"exit_code": 0' artifacts/train/$RUN.exit.json || stop TRAIN-FAIL
CKR=$(ls -d $L/*_$RUN | tail -1)/$END; [ -f $CKR ] || stop ENDPOINT-MISMATCH

# --- gate reads -----------------------------------------------------------------------------------------------------------
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120 --pair-drill-reset"
reads() {  # tag, checkpoint, pairs seeds, direction seeds
  local tag=$1 ck=$2
  for s in $3; do [ -s $R-$tag-pairs-$s.json ] || onbase python scripts/stage2_eval.py --checkpoint $ck $PA --seed $s --json $R-$tag-pairs-$s.json >> $R-reads.log 2>&1; done
  for s in $4; do [ -s $R-$tag-dir-$s.json ] || onbase python scripts/diag/feeder_speed_envelope.py --checkpoint $ck --seed $s --json $R-$tag-dir-$s.json >> $R-reads.log 2>&1; done
}
reads K $CKR "4220385 4220386 4220387 4220388" "4220307 4220334 4220335 4220336"
for w in K:$CKR R:$PR C:$P; do
  t=${w%%:*}; c=${w#*:}
  [ -s $R-court-$t-4220392.json ] || onbase python scripts/stage2_eval.py --checkpoint $c $CTB --seed 4220392 --json $R-court-$t-4220392.json >> $R-reads.log 2>&1
done
python - <<'PY' | tee -a $R-summary.txt
import json, os, sys
sys.path.insert(0, "scripts"); sys.path.insert(0, ".")
import rally_check as rc
from picklebot_mj import d1_rule as dr
R, RC = "results/ct94", "results/d1s3ctl"
S = (4220385, 4220386, 4220387, 4220388); D = (4220307, 4220334, 4220335, 4220336)
arm = {"K": ([f"{R}-K-pairs-{s}.json" for s in S], [f"{R}-K-dir-{s}.json" for s in D]),
       "C": ([f"results/sr91-set-{s}.json" for s in S], [f"results/lev74-C-dir-{s}.json" for s in D]),
       "W": ([f"results/dr92-R-pairs-{s}.json" for s in S], [f"results/dr92-R-dir-{s}.json" for s in D])}
if not all(os.path.exists(f) for w in arm for f in arm[w][0] + arm[w][1]):
    print("RESULT EVAL-FAIL"); sys.exit(0)
ok_g, d, lo, line = dr.gain2(arm["K"][0], arm["C"][0]); print("K vs C " + line)
pf, pd = dr.pool_reads(*arm["K"])
print("K (pooled) against the original parent (pooled, same seeds):")
g = rc.r19_guards(pf["per_family"], pd["directions"], ref=f"{RC}-parent-pooled", cross_ref=f"{RC}-parent-pooled-pairs.json",
                  name="parent pooled", cross_name="parent pooled")
m = dr.mechanism(arm["K"][0])
print(f"mechanism K: ready {m['ready']:.3f} (>= {dr.REP_READY}), falls/1000 hits {m['falls_per_1000_hits']:.2f} (<= {dr.REP_FALLS})")
ok_l, lines = dr.cfs79_lines(arm["K"][0], arm["C"][0])
for x in lines:
    print(x)
ok_k, line = dr.r_kept(arm["K"][0], arm["W"][0]); print(line)
r3 = {t: json.load(open(f"{R}-court-{t}-4220392.json"))["robot_fall_rate_per_episode"] for t in ("K", "R", "C")}
ok_r3 = r3["K"] <= dr.R3_MAX + 1e-9
print(f"R3: court read K (dev 4220392) {r3['K']:.4f} (<= {dr.R3_MAX}) -> {ok_r3}; (reported, same seed) R {r3['R']:.4f}, C {r3['C']:.4f}")
for w in ("K", "W", "C"):
    q = dr.pooled_pairs(arm[w][0]); print(f"(reported) {w}: P(5+) {q['p5']:.4f}, feeder {q['feeder']:.4f}, hazards " + " / ".join(f"{x:.3f}" for x in dr.pooled_hazards(arm[w][0])["h"]))
ok = dr.replicated(ok_g, m) and g and ok_l and ok_k and ok_r3
json.dump({"gain2": ok_g, "guards": g, "mechanism": m, "rec_lines": ok_l, "r_kept": ok_k, "r3": r3, "candidate": ok}, open(f"{R}-summary.json", "w"), indent=1)
print(f"RESULT {'CANDIDATE' if ok else 'NO-CANDIDATE'}")
PY
set -- $(tail -1 $R-summary.txt)
[ "$1" = RESULT ] || stop "SUMMARY-CRASH"
[ "$2" = CANDIDATE ] || stop "$2 (panel)"

# --- CONFIRM on fresh dev seeds -------------------------------------------------------------------------------------------
reads confirm-C $P "4220349 4220350 4220351 4220352" "4220353 4220354 4220355 4220356"
reads confirm-K $CKR "4220349 4220350 4220351 4220352" "4220353 4220354 4220355 4220356"
[ -s $R-confirm-court-4220393.json ] || onbase python scripts/stage2_eval.py --checkpoint $CKR $CTB --seed 4220393 --json $R-confirm-court-4220393.json >> $R-reads.log 2>&1
python - <<'PY' | tee -a $R-summary.txt
import json, os, sys
sys.path.insert(0, "scripts"); sys.path.insert(0, ".")
import rally_check as rc
from picklebot_mj import d1_rule as dr
R = "results/ct94"
S = (4220349, 4220350, 4220351, 4220352); D = (4220353, 4220354, 4220355, 4220356)
arm = {w: ([f"{R}-confirm-{w}-pairs-{s}.json" for s in S], [f"{R}-confirm-{w}-dir-{s}.json" for s in D]) for w in ("C", "K")}
if not all(os.path.exists(f) for w in arm for f in arm[w][0] + arm[w][1]):
    print("RESULT CONFIRM-EVAL-FAIL"); sys.exit(0)
for w in arm:
    pf, pd = dr.pool_reads(*arm[w])
    json.dump(pf, open(f"{R}-confirm-{w}-pooled-pairs.json", "w"), indent=1); json.dump(pd, open(f"{R}-confirm-{w}-pooled-dir.json", "w"), indent=1)
ok_g, d, lo, line = dr.gain2(arm["K"][0], arm["C"][0]); print("confirmation K vs C " + line)
pf, pd = dr.pool_reads(*arm["K"])
g = rc.r19_guards(pf["per_family"], pd["directions"], ref=f"{R}-confirm-C-pooled", cross_ref=f"{R}-confirm-C-pooled-pairs.json",
                  name="C (fresh)", cross_name="C (fresh)")
m = dr.mechanism(arm["K"][0])
r3c = json.load(open(f"{R}-confirm-court-4220393.json"))["robot_fall_rate_per_episode"]
print(f"confirmation R3: court read K (dev 4220393) {r3c:.4f} (<= 0.04) -> {r3c <= 0.04}")
q = dr.pooled_pairs(arm["K"][0]); k = round(q["p5"] * q["rallies"]); lo_w, hi_w = dr.wilson(k, q["rallies"])
print(f"(reported) confirmation K P(5+) {q['p5']:.4f} (Wilson {lo_w:.4f}-{hi_w:.4f}, rallies {q['rallies']}); C {dr.pooled_pairs(arm['C'][0])['p5']:.4f}")
ok = dr.replicated(ok_g, m) and g and r3c <= 0.04
print(f"RESULT {'CONFIRMED' if ok else 'CONFIRM-FAIL'}")
PY
set -- $(tail -1 $R-summary.txt)
stop "$2"

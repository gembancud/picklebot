#!/usr/bin/env bash
# D-212 (panel round 76; (ii) 3 of 5: motion, coach, RL; (i) 2: experiment design, architecture). Parent C = rally-d1s3lr3
# model_32598 (D-211). Stage 0 (reads only, reported, 3 of 5): the Fast4 floor test, fw-fast4-01 model_18099 on its own
# task, dev 4220248, scripts/latent_reach_floor.py as fw_floor.sh (legs explained at lam 3 >= 0.85 -> FLOOR-PASS; the
# settle and mean-action arrival lines are set by the panel only if it passes). Then two runs on training seed 207
# (LR 3e-5, ScheduledPPO, no anchor, 1,200 iterations, endpoint model_33797):
#   C2 = rally-d1s3lr4: C on d1s3's task (the recipe continued).
#   K  = rally-d1s3cap: C2 + the training-only pair_rally_cap 5 (D-161 knob; the least-new-code lever, coach). Smoke
#        seed 208 (40 iterations, 1,024 envs, D-201's checks; falls line 4.157 unchanged, half-split reported). A
#        SMOKE-FAIL skips K only.
# Kill at +360 (each run): D-194's lines via s2_train_kill from start 32598 (round 76: no longer hard-coded 31399). K also
#   KILL-NO-SHARE (s5_share_kill) against C2's pair-court share log at the same iterations (both runs log the share).
# Reads on D-204's pooled seeds. COMPOUND (C2 vs C = lev74-C): gain2, r19_guards against the original parent's pooled
#   reads on the same seeds (results/d1s3ctl-parent-pooled), ready >= 0.25, falls/1000 hits <= 1.3. LEVER (K vs C2): the
#   same lines + d1_rule.lever_lines (OPEN, K3-KEPT, FEEDER). Candidate = K if LEVER, else C2 if COMPOUND, else panel.
# CONFIRM (candidate only): fresh dev pairs 4220349-4220352 / direction 4220353-4220356, C and the candidate re-read.
#   CONFIRMED = gain2(candidate, C) + r19_guards (candidate fresh pooled vs C fresh pooled) + the mechanism bars.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER PICKLEBOT_READY_LOG \
  PICKLEBOT_RESTART_OBS PICKLEBOT_RESTART_OBS_FREEZE PICKLEBOT_REF_CKPT PICKLEBOT_REF_COEF PICKLEBOT_PAIR_LOG
pgrep -f "run-name |kickstart_h4|stage2_eval|footwork_eval|feeder_speed|distill_latent|latent_reach_floor" > /dev/null && { echo "GPU busy: not started"; exit 1; }
R=results/lev76; RC=results/d1s3ctl; L=artifacts/train/logs/picklebot_return_stand
BASE=/mnt/f/dev/picklebot-mjlab/mjlab/$L/2026-10-31_18-24-20_s5c-d1-fw1bS/model_32854.pt
PRUN=2026-11-04_00-06-34_rally-d1s3lr3; PCK=model_32598.pt; P=$L/$PRUN/$PCK; T=Picklebot-Rally22b-FastMove-G1; START=32598; END=model_33797.pt
F4=$L/2026-10-31_15-22-10_fw-fast4-01/model_18099.pt
for f in $BASE $P $F4; do [ -f $f ] || { echo "missing $f"; exit 1; }; done
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
B=--env.actions.ball; OV="$B.court-feed-prob 1.0 $B.refeed-delay-s 0.5 $B.recovery-mode fixed $B.planner-mode off $B.target-mode A"
for f in backhand reach-backhand cross-backhand fast drop low reach-deep short high reach-forehand; do OV="$OV $B.feed-mix.weights.$f 1.0"; done
CAP="$B.pair-rally-cap 5"
TRAINENV="PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_STD_MIN=0.1 PICKLEBOT_LR_PEAK=3e-5 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_KL_GUARD=0.05 PICKLEBOT_LR_TOTAL=0"
export PICKLEBOT_TRAIN_ENTRY=scripts/diag/footwork_train.py
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120"
onbase() { PICKLEBOT_RES_BASE=$BASE PICKLEBOT_LAM_R=2 "$@"; }
stop() { echo "VERDICT: $1" | tee -a $R-summary.txt; echo done > artifacts/train/lev76.done; exit 0; }
[ -s $R-summary.txt ] || echo "D-212: parent C = $P; C2 = rally-d1s3lr4, K = rally-d1s3cap (pair_rally_cap 5); training seed 207, smoke 208" > $R-summary.txt

# --- stage 0: the Fast4 floor test (reads only, reported) -------------------------------------------------------------
if [ ! -s $R-fast4-floor.json ]; then
  python - <<PY 2>&1 | grep -v "^\[INFO\]\|^|\|^+" | tail -8 > $R-fast4-floor.log
import runpy, sys
import mjlab.tasks  # noqa: F401
import picklebot_mj.tasks.footwork_specialist  # noqa: F401
sys.argv = ["latent_reach_floor.py", "--checkpoint", "$F4", "--task", "Picklebot-Footwork-Specialist-Fast4-G1", "--move-prob", "1.0",
            "--lams", "3,5", "--envs", "256", "--seconds", "8", "--seed", "4220248", "--json", "$R-fast4-floor.json"]
runpy.run_path("scripts/latent_reach_floor.py", run_name="__main__")
PY
fi
python -I - <<'PY' | tee -a $R-summary.txt
import json, os
p = "results/lev76-fast4-floor.json"
if not os.path.exists(p):
    print("Fast4 floor (reported): EVAL-FAIL (no output; see results/lev76-fast4-floor.log)")
else:
    d = json.load(open(p)); var = d["action_var"]; k = next(x for x in var if "leg" in x)
    for lam, fit in d["fits"].items():
        print(f"Fast4 floor (reported) {lam}: legs explained {1 - fit[k] / var[k]:.3f}")
    e3 = 1 - d["fits"]["lambda_3"][k] / var[k]
    print("Fast4 floor (reported):", "FLOOR-PASS (>= 0.85; settle / arrival lines go to the panel)" if e3 >= 0.85 else "FLOOR-FAIL (< 0.85)")
PY

# --- training ----------------------------------------------------------------------------------------------------------
train() {  # run name, seed, share-reference log ("" = none), extra overrides
  local run=$1 seed=$2 ref=$3; shift 3
  if [ ! -f artifacts/train/$run.exit.json ]; then
    ( python - "$run" "$ref" <<'PY' > $R-$run-kill.txt 2>&1
import json, os, sys, time
sys.path.insert(0, ".")
from picklebot_mj import d1_rule as dr
run, ref = sys.argv[1], sys.argv[2]
LOG, EXIT, START = f"artifacts/train/{run}.log", f"artifacts/train/{run}.exit.json", 32598
rd = lambda p: [json.loads(x) for x in open(p)] if os.path.exists(p) else []  # noqa: E731
k = None
while k is None:
    if os.path.exists(EXIT):
        print("training ended before the +360 check"); sys.exit(0)
    time.sleep(60)
    try:
        k = dr.s2_train_kill(LOG, START, "artifacts/train/rally-22b-readcfg.log", 12288)
    except FileNotFoundError:
        pass
print(k[1], flush=True)
vs = [k[0]]
if ref:
    v, line = dr.s5_share_kill(rd(f"results/lev76-{run}-share.jsonl"), rd(ref), START, START)
    print(line, flush=True); vs.append(v)
if any(v.startswith("KILL") for v in vs):
    os.system(f"pkill -f 'run-name {run} '")
PY
    ) &
    env $TRAINENV PICKLEBOT_RES_BASE=$BASE PICKLEBOT_PAIR_LOG=$R-$run-share.jsonl PICKLEBOT_SCHED_LOG=$R-$run-train.jsonl \
      PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=14400 bash scripts/diag/agility_train_run.sh $run $T --agent.seed $seed \
      --agent.max-iterations 1200 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG $OV "$@" --agent.save-interval 40
    wait
  fi
  echo "$run training: $(cat artifacts/train/$run.exit.json)" | tee -a $R-summary.txt; cat $R-$run-kill.txt | tee -a $R-summary.txt
}
endpoint() { local d=$(ls -d $L/*_$1 2>/dev/null | tail -1); echo "$d/$END"; }
train rally-d1s3lr4 207 ""
grep -q "KILL-" $R-rally-d1s3lr4-kill.txt && stop "KILL C2 ($(grep -o 'KILL-[A-Z-]*' $R-rally-d1s3lr4-kill.txt | head -1))"
grep -q '"exit_code": 0' artifacts/train/rally-d1s3lr4.exit.json || stop "TRAIN-FAIL C2"
CK2=$(endpoint rally-d1s3lr4); [ -f $CK2 ] || stop "ENDPOINT-MISMATCH C2"

# K smoke (D-201's checks on C, pair_rally_cap 5 in params)
KOK=1; RUN=rally-d1s3cap
if [ ! -f artifacts/train/$RUN-smoke.exit.json ]; then
  env $TRAINENV PICKLEBOT_RES_BASE=$BASE PICKLEBOT_SCHED_LOG=$R-smoke.jsonl PICKLEBOT_ENVS=1024 PICKLEBOT_WALL_CAP=900 \
    bash scripts/diag/agility_train_run.sh $RUN-smoke $T --agent.seed 208 --agent.max-iterations 40 --agent.resume True --agent.load-run $PRUN \
    --agent.load-checkpoint $PCK $ALG $OV $CAP --agent.save-interval 40
fi
SD=$(ls -d $L/*_$RUN-smoke | tail -1)
{ grep -q '"exit_code": 0' artifacts/train/$RUN-smoke.exit.json && echo "smoke exit 0 ok" || echo "smoke exit STOP"; } > /tmp/lev76-smoke.txt
{ grep -a -q -E "Traceback|Error" artifacts/train/$RUN-smoke.log && echo "smoke traceback STOP" || echo "smoke no traceback ok"; } >> /tmp/lev76-smoke.txt
python scripts/diag/falls_by_length.py artifacts/train/$RUN-smoke.log | awk '{r=$NF; print "smoke falls per 1,000 env-seconds", r, (r <= 4.157 ? "ok" : "STOP")}' >> /tmp/lev76-smoke.txt
CUDA_VISIBLE_DEVICES= python - "$(ls $SD/model_*.pt | sort -V | tail -1)" <<'PY' >> /tmp/lev76-smoke.txt
import sys, torch
sd = torch.load(sys.argv[1], map_location="cpu", weights_only=False)
s = sd["actor_state_dict"]["distribution.std_param"]
dead = sorted({i for v in sd["optimizer_state_dict"]["state"].values() if v["exp_avg_sq"].shape == s.shape
               for i in (v["exp_avg_sq"] == 0).nonzero().flatten().tolist()})
print("smoke std min", round(float(s.min()), 4), "outputs with no gradient", dead, "ok" if not dead and float(s.min()) >= 0.0999 else "STOP")
PY
python - "$SD" "$BASE" <<'PY' >> /tmp/lev76-smoke.txt
import re, sys
d, base = sys.argv[1], sys.argv[2]
env = open(f"{d}/params/env.yaml").read()
want = [("court_feed_prob", "1.0"), ("refeed_delay_s", "0.5"), ("recovery_mode", "fixed"), ("planner_mode", "'?off'?"),
        ("target_mode", "A"), ("obs_ball_pos_noise", "0.03"), ("obs_ball_vel_noise", "0.15"), ("pair_drill_court_frac", "0.5"),
        ("episode_length_s", "120.0"), ("backhand", "1.0"), ("reach_backhand", "1.0"), ("fast", "1.0"), ("lam_r", "2.0"),
        ("pair_rally_cap", "5")]
miss = [k for k, v in want if not re.search(rf"^\s*{k}: {v}\s*$", env, re.M)]
based = re.search(rf"^\s*base_checkpoint: {re.escape(base)}\s*$", env, re.M) is not None
fast = "rally_fast_track_lin_vel" in env and "ready_at_event" not in env
ok = not miss and based and fast
print(f"smoke config check: missing {miss}; d1 base {based}; fast move term, no ready term {fast} -> {'ok' if ok else 'STOP'}")
PY
python - artifacts/train/$RUN-smoke.log <<'PY' >> /tmp/lev76-smoke.txt
import os, re, sys, tempfile
sys.path.insert(0, "scripts/diag")
from falls_by_length import falls_per_1000_env_s
t = open(sys.argv[1], errors="ignore").read()
cut = [m.start() for m in re.finditer(r"Learning iteration", t)]
if len(cut) >= 4:
    mid = cut[len(cut) // 2]
    out = []
    for part in (t[:mid], t[mid:]):
        with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as f:
            f.write(part)
        out.append(falls_per_1000_env_s(f.name)[0])
        os.unlink(f.name)
    print(f"smoke falls half-split (reported): first half {out[0]:.3f}, second half {out[1]:.3f}")
PY
cat /tmp/lev76-smoke.txt | tee -a $R-summary.txt
if [ "$(grep -c " ok$" /tmp/lev76-smoke.txt)" != 5 ]; then KOK=0; echo "K: SMOKE-FAIL (K not trained; C2 goes on)" | tee -a $R-summary.txt; fi
CKK=""
if [ $KOK = 1 ]; then
  train $RUN 207 $R-rally-d1s3lr4-share.jsonl $CAP
  if grep -q "KILL-" $R-$RUN-kill.txt; then echo "K: KILL ($(grep -o 'KILL-[A-Z-]*' $R-$RUN-kill.txt | head -1))" | tee -a $R-summary.txt
  elif ! grep -q '"exit_code": 0' artifacts/train/$RUN.exit.json; then echo "K: TRAIN-FAIL" | tee -a $R-summary.txt
  else CKK=$(endpoint $RUN); [ -f $CKK ] || { echo "K: ENDPOINT-MISMATCH" | tee -a $R-summary.txt; CKK=""; }; fi
fi

# --- reads on D-204's pooled seeds -------------------------------------------------------------------------------------
reads() {  # tag, checkpoint, pairs seeds, direction seeds
  local tag=$1 ck=$2
  for s in $3; do [ -s $R-$tag-pairs-$s.json ] || onbase python scripts/stage2_eval.py --checkpoint $ck $PA --seed $s --json $R-$tag-pairs-$s.json >> $R-reads.log 2>&1; done
  for s in $4; do [ -s $R-$tag-dir-$s.json ] || onbase python scripts/diag/feeder_speed_envelope.py --checkpoint $ck --seed $s --json $R-$tag-dir-$s.json >> $R-reads.log 2>&1; done
}
reads C2 $CK2 "4220306 4220328 4220329 4220331" "4220307 4220334 4220335 4220336"
[ -n "$CKK" ] && reads K $CKK "4220306 4220328 4220329 4220331" "4220307 4220334 4220335 4220336"
python - <<'PY' | tee -a $R-summary.txt
import json, os, sys
sys.path.insert(0, "scripts"); sys.path.insert(0, ".")
import rally_check as rc
from picklebot_mj import d1_rule as dr
R, RC = "results/lev76", "results/d1s3ctl"
S = (4220306, 4220328, 4220329, 4220331); D = (4220307, 4220334, 4220335, 4220336)
arm = {w: ([f"{R}-{w}-pairs-{s}.json" for s in S], [f"{R}-{w}-dir-{s}.json" for s in D]) for w in ("C2", "K")}
arm["C"] = ([f"results/lev74-C-pairs-{s}.json" for s in S], [f"results/lev74-C-dir-{s}.json" for s in D])
have = {w: all(os.path.exists(f) for f in arm[w][0] + arm[w][1]) for w in arm}
if not have["C2"] or not have["C"]:
    print("RESULT EVAL-FAIL"); sys.exit(0)
ref = json.load(open(f"{RC}-parent-pooled-pairs.json"))["per_family"]
def judge(w, against):
    ok_g, d, lo, line = dr.gain2(arm[w][0], arm[against][0]); print(f"{w} vs {against} " + line)
    pf, pd = dr.pool_reads(*arm[w])
    print(f"{w} (pooled) against the original parent (pooled, same seeds):")
    g = rc.r19_guards(pf["per_family"], pd["directions"], ref=f"{RC}-parent-pooled", cross_ref=f"{RC}-parent-pooled-pairs.json",
                      name="parent pooled", cross_name="parent pooled")
    m = dr.mechanism(arm[w][0])
    print(f"mechanism {w}: ready {m['ready']:.3f} (>= {dr.REP_READY}), falls/1000 hits {m['falls_per_1000_hits']:.2f} (<= {dr.REP_FALLS}), "
          f"WRONG_SIDE {m['wrong_side_share']:.3f}, recovery {m['recovery_median_m']:.3f} m")
    q = dr.pooled_pairs(arm[w][0])
    print(f"(reported) {w}: P(5+) {q['p5']:.4f}, feeder legal {q['feeder']:.4f}, mean family shift vs the original parent "
          f"{100 * dr.mean_family_shift(pf['per_family'], ref):+.2f}")
    return dr.replicated(ok_g, m) and g
compound = judge("C2", "C")
print(f"COMPOUND -> {compound}")
lever = False
if have["K"]:
    base_ok = judge("K", "C2")
    ok_l, lines = dr.lever_lines(arm["K"][0], arm["C2"][0])
    for x in lines:
        print("LEVER " + x)
    lever = base_ok and ok_l
    print(f"LEVER -> {lever}")
else:
    print("LEVER -> False (K not trained or not read)")
for w in ("C", "C2", "K"):
    if have[w]:
        print(f"(reported) hazards {w}: " + " / ".join(f"{x:.3f}" for x in dr.pooled_hazards(arm[w][0])["h"]))
cand = dr.lev76_candidate(compound, lever)
json.dump({"compound": compound, "lever": lever, "candidate": cand}, open(f"{R}-summary.json", "w"), indent=1)
print(f"RESULT {cand}")
PY
set -- $(tail -1 $R-summary.txt)
[ "$1" = RESULT ] || stop "SUMMARY-CRASH"
[ "$2" = EVAL-FAIL ] && stop EVAL-FAIL
[ "$2" = none ] && stop "NO-CANDIDATE (panel)"
CAND=$2; CKC=$CK2; [ $CAND = K ] && CKC=$CKK

# --- CONFIRM on fresh dev seeds ------------------------------------------------------------------------------------------
reads confirm-C $P "4220349 4220350 4220351 4220352" "4220353 4220354 4220355 4220356"
reads confirm-$CAND $CKC "4220349 4220350 4220351 4220352" "4220353 4220354 4220355 4220356"
python - $CAND <<'PY' | tee -a $R-summary.txt
import json, os, sys
sys.path.insert(0, "scripts"); sys.path.insert(0, ".")
import rally_check as rc
from picklebot_mj import d1_rule as dr
R, cand = "results/lev76", sys.argv[1]
S = (4220349, 4220350, 4220351, 4220352); D = (4220353, 4220354, 4220355, 4220356)
arm = {w: ([f"{R}-confirm-{w}-pairs-{s}.json" for s in S], [f"{R}-confirm-{w}-dir-{s}.json" for s in D]) for w in ("C", cand)}
if not all(os.path.exists(f) for w in arm for f in arm[w][0] + arm[w][1]):
    print("RESULT CONFIRM-EVAL-FAIL"); sys.exit(0)
for w in arm:
    pf, pd = dr.pool_reads(*arm[w])
    json.dump(pf, open(f"{R}-confirm-{w}-pooled-pairs.json", "w"), indent=1); json.dump(pd, open(f"{R}-confirm-{w}-pooled-dir.json", "w"), indent=1)
ok_g, d, lo, line = dr.gain2(arm[cand][0], arm["C"][0]); print(f"confirmation {cand} vs C " + line)
pf, pd = dr.pool_reads(*arm[cand])
print(f"confirmation: {cand} (fresh pooled) against C (fresh pooled):")
g = rc.r19_guards(pf["per_family"], pd["directions"], ref=f"{R}-confirm-C-pooled", cross_ref=f"{R}-confirm-C-pooled-pairs.json",
                  name="C (fresh)", cross_name="C (fresh)")
m = dr.mechanism(arm[cand][0])
print(f"mechanism {cand}: ready {m['ready']:.3f}, falls/1000 hits {m['falls_per_1000_hits']:.2f}, WRONG_SIDE {m['wrong_side_share']:.3f}, recovery {m['recovery_median_m']:.3f} m")
for w in arm:
    q = dr.pooled_pairs(arm[w][0])
    print(f"(reported) {w} fresh: P(5+) {q['p5']:.4f}, feeder {q['feeder']:.4f}; hazards " + " / ".join(f"{x:.3f}" for x in dr.pooled_hazards(arm[w][0])["h"]))
print(f"(reported) C fresh P(5+) vs its earlier reads (lev74 0.4115, conf75 0.4117)")
ok = dr.replicated(ok_g, m) and g
print(f"RESULT {'CONFIRMED-' + cand if ok else 'CONFIRM-FAIL-' + cand}")
PY
set -- $(tail -1 $R-summary.txt)
stop "$2"

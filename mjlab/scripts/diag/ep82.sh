#!/usr/bin/env bash
# D-219 (panel round 82; (ii) 3 of 5: coach, motion, architecture). Parent C = rally-d1s3lr3 model_32598. One run,
# X = rally-d1s3ep24: C on d1s3's task (Picklebot-Rally22b-FastMove-G1) with the training episode length 120 -> 24 s
# (--env.episode-length-s 24; reads set their own length). LR 3e-5, ScheduledPPO, no anchor, 1,200 iterations, endpoint
# model_33797; training seed 217, smoke 218. Premise (court_counts, no code): the read's first feeder ball per court
# converts q0 0.25-0.26 vs later balls q1 0.51-0.53; training sees about 5x fewer episode starts than the read weights.
# Smoke: 160 iterations (about 3 episodes of 24 s), D-201's checks (falls line 4.157, half-split reported; config incl.
#   episode_length_s 24.0), plus the dose premise (d1_rule.ep24_dose_kill over 0-160: reset-feed share >= 0.15), with
#   the pair log every 480 steps (20 iterations) so every kill line is readable at smoke.
# Kill at +360 (from start 32598): D-194's lines (s2_train_kill); KILL-NO-DOSE (ep24_dose_kill over 300-360).
#   KILL-FARM is reported only (shorter episodes shorten rallies by design; round 81's lesson).
# Reads on D-204's pooled seeds. Lines (d1_rule): gain2(X, lev74-C); r19_guards against the original parent's pooled reads
#   on the same seeds; ready >= 0.25, falls/1000 hits <= 1.3; cfs79_lines (H0 <= C - 0.03, FEEDER >= C - 0.01,
#   K3-KEPT <= C + 0.005). All pass -> CONFIRM on fresh dev 4220349-4220356 (C re-read; D-212's CONFIRMED lines).
# Reported: q0 / q1 (court_conv) for X and C; gain2(X, C2); late splits; direction contact; R3 pairs rate; X's court
#   read on dev 4220365 (C's: results/cfs79-court-C.json); launch-distance legal for X.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER PICKLEBOT_READY_LOG \
  PICKLEBOT_RESTART_OBS PICKLEBOT_RESTART_OBS_FREEZE PICKLEBOT_REF_CKPT PICKLEBOT_REF_COEF PICKLEBOT_PAIR_LOG
pgrep -f "run-name |kickstart_h4|stage2_eval|footwork_eval|feeder_speed|distill_latent|latent_reach_floor" > /dev/null && { echo "GPU busy: not started"; exit 1; }
R=results/ep82; RC=results/d1s3ctl; L=artifacts/train/logs/picklebot_return_stand; RUN=rally-d1s3ep24
BASE=/mnt/f/dev/picklebot-mjlab/mjlab/$L/2026-10-31_18-24-20_s5c-d1-fw1bS/model_32854.pt
PRUN=2026-11-04_00-06-34_rally-d1s3lr3; PCK=model_32598.pt; P=$L/$PRUN/$PCK; T=Picklebot-Rally22b-FastMove-G1; END=model_33797.pt
C2SHARE=results/lev76-rally-d1s3lr4-share.jsonl
for f in $BASE $P $C2SHARE; do [ -f $f ] || { echo "missing $f"; exit 1; }; done
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
B=--env.actions.ball; OV="$B.court-feed-prob 1.0 $B.refeed-delay-s 0.5 $B.recovery-mode fixed $B.planner-mode off $B.target-mode A"
for f in backhand reach-backhand cross-backhand fast drop low reach-deep short high reach-forehand; do OV="$OV $B.feed-mix.weights.$f 1.0"; done
EP="--env.episode-length-s 24"
TRAINENV="PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_STD_MIN=0.1 PICKLEBOT_LR_PEAK=3e-5 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_KL_GUARD=0.05 PICKLEBOT_LR_TOTAL=0"
export PICKLEBOT_TRAIN_ENTRY=scripts/diag/footwork_train.py
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120"
onbase() { PICKLEBOT_RES_BASE=$BASE PICKLEBOT_LAM_R=2 "$@"; }
stop() { echo "VERDICT: $1" | tee -a $R-summary.txt; echo done > artifacts/train/ep82.done; exit 0; }
[ -s $R-summary.txt ] || echo "D-219: parent C = $P; X = $RUN on $T + episode length 24 s; training seed 217, smoke 218" > $R-summary.txt

# --- smoke (D-205's checks, LR 3e-5) ------------------------------------------------------------------------------------
if [ ! -f artifacts/train/$RUN-smoke.exit.json ]; then
  env $TRAINENV PICKLEBOT_RES_BASE=$BASE PICKLEBOT_SCHED_LOG=$R-smoke.jsonl PICKLEBOT_PAIR_LOG=$R-smoke-share.jsonl PICKLEBOT_PAIR_LOG_EVERY=480 PICKLEBOT_ENVS=1024 \
    PICKLEBOT_WALL_CAP=2400 bash scripts/diag/agility_train_run.sh $RUN-smoke $T --agent.seed 218 --agent.max-iterations 160 --agent.resume True \
    --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG $OV $EP --agent.save-interval 40
fi
SD=$(ls -d $L/*_$RUN-smoke | tail -1)
{ grep -q '"exit_code": 0' artifacts/train/$RUN-smoke.exit.json && echo "smoke exit 0 ok" || echo "smoke exit STOP"; } > /tmp/ep82-smoke.txt
{ grep -a -q -E "Traceback|Error" artifacts/train/$RUN-smoke.log && echo "smoke traceback STOP" || echo "smoke no traceback ok"; } >> /tmp/ep82-smoke.txt
python scripts/diag/falls_by_length.py artifacts/train/$RUN-smoke.log | awk '{r=$NF; print "smoke falls per 1,000 env-seconds", r, (r <= 4.157 ? "ok" : "STOP")}' >> /tmp/ep82-smoke.txt
CUDA_VISIBLE_DEVICES= python - "$(ls $SD/model_*.pt | sort -V | tail -1)" <<'PY' >> /tmp/ep82-smoke.txt
import sys, torch
sd = torch.load(sys.argv[1], map_location="cpu", weights_only=False)
s = sd["actor_state_dict"]["distribution.std_param"]
dead = sorted({i for v in sd["optimizer_state_dict"]["state"].values() if v["exp_avg_sq"].shape == s.shape
               for i in (v["exp_avg_sq"] == 0).nonzero().flatten().tolist()})
print("smoke std min", round(float(s.min()), 4), "outputs with no gradient", dead, "ok" if not dead and float(s.min()) >= 0.0999 else "STOP")
PY
python - "$SD" "$BASE" <<'PY' >> /tmp/ep82-smoke.txt
import re, sys
d, base = sys.argv[1], sys.argv[2]
env = open(f"{d}/params/env.yaml").read()
want = [("court_feed_prob", "1.0"), ("refeed_delay_s", "0.5"), ("recovery_mode", "fixed"), ("planner_mode", "'?off'?"),
        ("target_mode", "A"), ("obs_ball_pos_noise", "0.03"), ("obs_ball_vel_noise", "0.15"), ("pair_drill_court_frac", "0.5"),
        ("episode_length_s", "24.0"), ("backhand", "1.0"), ("reach_backhand", "1.0"), ("fast", "1.0"), ("lam_r", "2.0"),
        ("pair_rally_cap", "0"), ("pair_cut_prob", "0.0")]
miss = [k for k, v in want if not re.search(rf"^\s*{k}: {v}\s*$", env, re.M)]
based = re.search(rf"^\s*base_checkpoint: {re.escape(base)}\s*$", env, re.M) is not None
terms = ("rally_fast_track_lin_vel" in env and "footwork_specialist.rally_recovery_reward" not in env and "return_stand.recovery_reward" in env
         and "return_stand.stance_progress" in env and "parked_ready" not in env and "ready_at_event" not in env and "restart_obs" not in env)
ok = not miss and based and terms
print(f"smoke config check: missing {miss}; d1 base {based}; fast move + stance_progress, no other new terms {terms} -> {'ok' if ok else 'STOP'}")
PY
python - artifacts/train/$RUN-smoke.log <<'PY' >> /tmp/ep82-smoke.txt
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
python - <<'PY' >> /tmp/ep82-smoke.txt
import json, os, sys
sys.path.insert(0, ".")
from picklebot_mj import d1_rule as dr
p = "results/ep82-smoke-share.jsonl"
rows = [json.loads(x) for x in open(p)] if os.path.exists(p) else []
v, line = dr.ep24_dose_kill(rows, 0, 160, 32598)
print("smoke dose " + line + (" ok" if v == "CONTINUE" else " STOP"))
PY
cat /tmp/ep82-smoke.txt | tee -a $R-summary.txt
[ "$(grep -c " ok$" /tmp/ep82-smoke.txt)" = 6 ] || stop SMOKE-FAIL

# --- training with the +360 kill -----------------------------------------------------------------------------------------
if [ ! -f artifacts/train/$RUN.exit.json ]; then
  ( python - <<'PY' > $R-kill.txt 2>&1
import json, os, sys, time
sys.path.insert(0, ".")
from picklebot_mj import d1_rule as dr
run, START = "rally-d1s3ep24", 32598
LOG, EXIT = f"artifacts/train/{run}.log", f"artifacts/train/{run}.exit.json"
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
v_farm, line = dr.s6_farm_kill(rd("results/ep82-train-share.jsonl"), rd("results/lev76-rally-d1s3lr4-share.jsonl"), START, START)
print("(reported, not a kill) " + line.split(" -> ")[0], flush=True)
v, line = dr.ep24_dose_kill(rd("results/ep82-train-share.jsonl"), 300, 360, START)
print(line, flush=True)
if any(x.startswith("KILL") for x in (k[0], v)):
    os.system(f"pkill -f 'run-name {run} '")
PY
  ) &
  env $TRAINENV PICKLEBOT_RES_BASE=$BASE PICKLEBOT_PAIR_LOG=$R-train-share.jsonl PICKLEBOT_PAIR_LOG_EVERY=480 PICKLEBOT_SCHED_LOG=$R-train.jsonl \
    PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=14400 bash scripts/diag/agility_train_run.sh $RUN $T \
    --agent.seed 217 --agent.max-iterations 1200 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG $OV $EP --agent.save-interval 40
  wait
fi
echo "training: $(cat artifacts/train/$RUN.exit.json)" | tee -a $R-summary.txt; cat $R-kill.txt | tee -a $R-summary.txt
grep -q "KILL-" $R-kill.txt && stop "KILL ($(grep -o 'KILL-[A-Z-]*' $R-kill.txt | head -1))"
grep -q '"exit_code": 0' artifacts/train/$RUN.exit.json || stop TRAIN-FAIL
CKR=$(ls -d $L/*_$RUN | tail -1)/$END; [ -f $CKR ] || stop ENDPOINT-MISMATCH

# --- reads on D-204's pooled seeds -------------------------------------------------------------------------------------
reads() {  # tag, checkpoint, pairs seeds, direction seeds
  local tag=$1 ck=$2
  for s in $3; do [ -s $R-$tag-pairs-$s.json ] || onbase python scripts/stage2_eval.py --checkpoint $ck $PA --seed $s --json $R-$tag-pairs-$s.json >> $R-reads.log 2>&1; done
  for s in $4; do [ -s $R-$tag-dir-$s.json ] || onbase python scripts/diag/feeder_speed_envelope.py --checkpoint $ck --seed $s --json $R-$tag-dir-$s.json >> $R-reads.log 2>&1; done
}
reads R $CKR "4220306 4220328 4220329 4220331" "4220307 4220334 4220335 4220336"
CT="--task Picklebot-Latent-Court-Res-G1 --envs 2048 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --recovery random --seed 4220365"
[ -s $R-court-F.json ] || onbase python scripts/stage2_eval.py --checkpoint $CKR $CT --json $R-court-F.json >> $R-reads.log 2>&1
python - <<'PY' | tee -a $R-summary.txt
import json, os, sys
sys.path.insert(0, "scripts"); sys.path.insert(0, ".")
import rally_check as rc
from picklebot_mj import d1_rule as dr
R, RC = "results/ep82", "results/d1s3ctl"
S = (4220306, 4220328, 4220329, 4220331); D = (4220307, 4220334, 4220335, 4220336)
arm = {"R": ([f"{R}-R-pairs-{s}.json" for s in S], [f"{R}-R-dir-{s}.json" for s in D]),
       "C": ([f"results/lev74-C-pairs-{s}.json" for s in S], [f"results/lev74-C-dir-{s}.json" for s in D]),
       "C2": ([f"results/lev76-C2-pairs-{s}.json" for s in S], [f"results/lev76-C2-dir-{s}.json" for s in D])}
if not all(os.path.exists(f) for w in arm for f in arm[w][0] + arm[w][1]):
    print("RESULT EVAL-FAIL"); sys.exit(0)
ok_g, d, lo, line = dr.gain2(arm["R"][0], arm["C"][0]); print("R vs C " + line)
print("(reported) X vs C2 " + dr.gain2(arm["R"][0], arm["C2"][0])[3])
for w in ("R", "C", "C2"):
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
for w in ("R", "C", "C2"):
    q = dr.pooled_pairs(arm[w][0])
    fl = sum(json.load(open(p))["robot_falls"] for p in arm[w][0]); n = sum(json.load(open(p))["envs"] for p in arm[w][0])
    print(f"(reported) {w}: P(5+) {q['p5']:.4f}, feeder {q['feeder']:.4f}; R3 pairs falls / (falls + envs) {fl / (fl + n):.4f}")
for w, f in (("C", "results/cfs79-court-C.json"), ("X", f"{R}-court-F.json")):
    if os.path.exists(f):
        print(f"(reported) R3 court read {w} (24 s, dev 4220365): robot falls per episode {json.load(open(f))['robot_fall_rate_per_episode']:.4f}")
for w in ("R", "C"):
    _, pdw = dr.pool_reads(*arm[w])
    print(f"(reported) {w} direction contact: " + ", ".join(f"{k} {v['contact']:.3f}" for k, v in pdw["directions"].items()))
ob = [[0, 0] for _ in range(8)]
for p in arm["R"][0]:
    L = json.load(open(p)).get("launch_state", {}).get("outcome_by_d")
    if L:
        ob = [[x[0] + y[0], x[1] + y[1]] for x, y in zip(ob, L)]
print("(reported) X " + dr.dist_route(ob)[1][0] + " (C, dist80b: legal(d <= 0.3) 0.901, legal(d > 1.2) 0.422)")
ok = dr.replicated(ok_g, m) and g and ok_l
json.dump({"gain2": ok_g, "guards": g, "mechanism": m, "rec_lines": ok_l, "candidate": ok}, open(f"{R}-summary.json", "w"), indent=1)
print(f"RESULT {'CANDIDATE' if ok else 'NO-CANDIDATE'}")
PY
set -- $(tail -1 $R-summary.txt)
[ "$1" = RESULT ] || stop "SUMMARY-CRASH"
[ "$2" = CANDIDATE ] || stop "$2 (panel)"

# --- CONFIRM on fresh dev seeds ------------------------------------------------------------------------------------------
reads confirm-C $P "4220349 4220350 4220351 4220352" "4220353 4220354 4220355 4220356"
reads confirm-R $CKR "4220349 4220350 4220351 4220352" "4220353 4220354 4220355 4220356"
python - <<'PY' | tee -a $R-summary.txt
import json, os, sys
sys.path.insert(0, "scripts"); sys.path.insert(0, ".")
import rally_check as rc
from picklebot_mj import d1_rule as dr
R = "results/ep82"
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
ok = dr.replicated(ok_g, m) and g
print(f"RESULT {'CONFIRMED' if ok else 'CONFIRM-FAIL'}")
PY
set -- $(tail -1 $R-summary.txt)
stop "$2"

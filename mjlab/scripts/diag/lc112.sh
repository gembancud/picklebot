#!/usr/bin/env bash
# D-253 (panel round 111, 5 of 5 on the core): the first footwork lever. Child rally-d1s3call1 = Q (rally-d1s3cap8hr2
# model_36793) on Q's recipe (HalfReset task, pair_rally_cap 8 on the set-start half, every feed weight 1.0) with the move
# episodes on the drill courts replaced by the call-and-set drill and one event reward paid at T,
# (SET + READY + REACH + pass) / 4 at move_arrival's weight (task ...-HalfReset-CallSet-G1). The only change.
# 600 iterations to model_37392; training seed 263, smoke 264.
# Stage 0: Q's reads on the same seeds as the child's: call-and-set on 4220453 (kill) and 4220455 (gate); set-start
#   pairs on 4220454 (kill) and 4220456 (gate).
# Smoke (160 iterations): D-249's smoke lines with Q's basis-smoke predictions (feeder share 0.1498, three-family share
#   0.183, +/- 25 %; seed 259, the same parent and recipe), the config check with move_call_set and the event term, and
#   a call-drill line: >= 200 judged calls with SET + READY + REACH > 0.
# Kill at the first checkpoint past +180: config (training-log falls reported only, round 107's rule); then the call-and-set read
#   (dev 4220453): falls per 1,000 env-s <= Q's on the same seed, and the 1.5 m/s ladder on normal calls >= 0.02; then the
#   set-start pairs read (dev 4220454): feeder-ball legal >= Q's - 0.05.
# Gate (dev 4220455 call-and-set, 4220456 pairs, child and Q): the deciding line is the headline pass gain over Q when
#   either arm reads >= 0.05, else the 1.5 m/s ladder gain on normal calls: KEEP if its 95 % lower bound > 0, FLAT if
#   its upper bound < +0.02; guards: falls <= Q's, feeder-ball legal >= Q's - 0.05. No target read (the target block
#   4220500-4220509 is read only for a candidate that passes 0.80 on a fresh development seed).
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER PICKLEBOT_READY_LOG \
  PICKLEBOT_RESTART_OBS PICKLEBOT_RESTART_OBS_FREEZE PICKLEBOT_REF_CKPT PICKLEBOT_REF_COEF PICKLEBOT_PAIR_LOG
# stage2_eval is left out of the guard on 2026-11-09 only: the README video render (scripts/rally_videos_q.sh, CPU-bound, the user's
# request) may finish beside this run
pgrep -f "run-name |kickstart_h4|footwork_eval|callset_eval|feeder_speed|distill_latent|latent_reach_floor" > /dev/null && { echo "GPU busy: not started"; exit 1; }
R=results/lc112; L=artifacts/train/logs/picklebot_return_stand; RUN=rally-d1s3call1
BASE=/mnt/f/dev/picklebot-mjlab/mjlab/$L/2026-10-31_18-24-20_s5c-d1-fw1bS/model_32854.pt
PRUN=2026-11-07_19-25-03_rally-d1s3cap8hr2; PCK=model_36793.pt; PR=$L/$PRUN/$PCK; T=Picklebot-Rally22b-FastMove-DrillReset-Launch-HalfReset-CallSet-G1; END=model_37392.pt
for f in $BASE $PR; do [ -f $f ] || { echo "missing $f"; exit 1; }; done
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
B=--env.actions.ball; OV="$B.court-feed-prob 1.0 $B.refeed-delay-s 0.5 $B.recovery-mode fixed $B.planner-mode off $B.target-mode A"
for f in backhand fast drop low short high reach-forehand reach-deep cross-backhand reach-backhand; do OV="$OV $B.feed-mix.weights.$f 1.0"; done
CAP="$B.pair-rally-cap 8 $B.pair-rally-cap-reset-only True"
TRAINENV="PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_STD_MIN=0.1 PICKLEBOT_LR_PEAK=3e-5 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_KL_GUARD=0.05 PICKLEBOT_LR_TOTAL=0"
export PICKLEBOT_TRAIN_ENTRY=scripts/diag/footwork_train.py
CS="--task Picklebot-Footwork-CallSet-RallyLamR2-G1 --envs 1024 --seconds 120 --move-prob 1.0"
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120 --pair-drill-reset"
onbase() { PICKLEBOT_RES_BASE=$BASE PICKLEBOT_LAM_R=2 "$@"; }
stop() { echo "VERDICT: $1" | tee -a $R-summary.txt; echo done > artifacts/train/lc112.done; exit 0; }
[ -s $R-summary.txt ] || echo "D-253: warm start Q = $PR; child = $RUN on $T (the call drill on the drill courts + its event at T); Q's recipe (cap 8 on the set-start half, feed weights 1.0); training seed 263, smoke 264" > $R-summary.txt

# --- stage 0: Q's reads on the kill and gate seeds ----------------------------------------------------------------------
for s in 4220453 4220455; do [ -s $R-csQ-$s.json ] || onbase python scripts/diag/callset_eval.py --checkpoint $PR $CS --seed $s --json $R-csQ-$s.json > $R-csQ-$s.log 2>&1; done
for s in 4220454 4220456; do [ -s $R-pairsQ-$s.json ] || onbase python scripts/stage2_eval.py --checkpoint $PR $PA --seed $s --json $R-pairsQ-$s.json > $R-pairsQ-$s.log 2>&1; done
export KILL_BASE=$BASE

# --- smoke (160 iterations) ---------------------------------------------------------------------------------------------
if [ ! -f artifacts/train/$RUN-smoke.exit.json ]; then
  env $TRAINENV PICKLEBOT_RES_BASE=$BASE PICKLEBOT_SCHED_LOG=$R-smoke.jsonl PICKLEBOT_PAIR_LOG=$R-smoke-share.jsonl PICKLEBOT_PAIR_LOG_EVERY=480 PICKLEBOT_ENVS=1024 \
    PICKLEBOT_WALL_CAP=2400 bash scripts/diag/agility_train_run.sh $RUN-smoke $T --agent.seed 264 --agent.max-iterations 160 --agent.resume True \
    --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG $OV $CAP --agent.save-interval 40
fi
SD=$(ls -d $L/*_$RUN-smoke | tail -1)
{ grep -q '"exit_code": 0' artifacts/train/$RUN-smoke.exit.json && echo "smoke exit 0 ok" || echo "smoke exit STOP"; } > /tmp/lc112-smoke.txt
{ grep -a -q -E "Traceback|Error" artifacts/train/$RUN-smoke.log && echo "smoke traceback STOP" || echo "smoke no traceback ok"; } >> /tmp/lc112-smoke.txt
python - <<'PY' >> /tmp/lc112-smoke.txt
import json, os
p = 'results/lc112-smoke-share.jsonl'
rows = [json.loads(x) for x in open(p)] if os.path.exists(p) else []
rows = [r for r in rows if 'other_falls' in r['launch'].get('launch_courts', {})]
if len(rows) < 2:
    print('smoke falls per 1,000 env-seconds off the launcher courts: NO-DATA STOP')
else:
    a, b = rows[0], rows[-1]
    la, lb = a['launch']['launch_courts'], b['launch']['launch_courts']
    n = 1024 - lb['envs']
    r = 1000 * (lb['other_falls'] - la['other_falls']) / ((b['step'] - a['step']) * 0.02 * n)
    print(f'smoke falls per 1,000 env-seconds off the launcher courts (exact count, steps {a["step"]}-{b["step"]}) {r:.3f} (reported; call episodes fall more by design)')
PY
CUDA_VISIBLE_DEVICES= python - "$(ls $SD/model_*.pt | sort -V | tail -1)" <<'PY' >> /tmp/lc112-smoke.txt
import sys, torch
sd = torch.load(sys.argv[1], map_location="cpu", weights_only=False)
s = sd["actor_state_dict"]["distribution.std_param"]
dead = sorted({i for v in sd["optimizer_state_dict"]["state"].values() if v["exp_avg_sq"].shape == s.shape
               for i in (v["exp_avg_sq"] == 0).nonzero().flatten().tolist()})
print("smoke std min", round(float(s.min()), 4), "outputs with no gradient", dead, "ok" if not dead and float(s.min()) >= 0.0999 else "STOP")
PY
python - "$SD" "$BASE" <<'PY' >> /tmp/lc112-smoke.txt
import re, sys
d, base = sys.argv[1], sys.argv[2]
env = open(f"{d}/params/env.yaml").read()
want = [("court_feed_prob", "1.0"), ("refeed_delay_s", "0.5"), ("recovery_mode", "fixed"), ("planner_mode", "'?off'?"),
        ("target_mode", "A"), ("pair_drill_court_frac", "0.5"), ("episode_length_s", "120.0"), ("pair_drill_reset", "true"),
        ("pair_reset_parks", "true"), ("reach_backhand", "1.0"), ("reach_deep", "1.0"), ("cross_backhand", "1.0"), ("lam_r", "2.0"),
        ("pair_rally_cap", "8"), ("pair_drill_reset_frac", "0.5"), ("pair_rally_cap_reset_only", "true"), ("pair_launch_court_frac", "0.25"),
        ("move_call_set", "true"), ("move_pro_moves", "false")]
miss = [k for k, v in want if not re.search(rf"^\s*{k}: {v}\s*$", env, re.M)]
based = re.search(rf"^\s*base_checkpoint: {re.escape(base)}\s*$", env, re.M) is not None
terms = ("rally_fast_track_lin_vel" in env and "callset_event" in env and "launch_time_out" in env and "is_terminated" not in env)
ok = not miss and based and terms
print(f"smoke config check: missing {miss}; d1 base {based}; fast move + call event + launch_time_out, no fall term {terms} -> {'ok' if ok else 'STOP'}")
PY
python - <<'PY' >> /tmp/lc112-smoke.txt
import json, os, sys
sys.path.insert(0, ".")
from picklebot_mj import d1_rule as dr
p = "results/lc112-smoke-share.jsonl"
rows = [json.loads(x) for x in open(p)] if os.path.exists(p) else []
ok_d, line = dr.half_dose(rows, 36793)
print("smoke dose " + line + (" ok" if ok_d else " STOP"))
c = dr.cap_split(rows)
pred, pf3 = 0.1498, 0.183  # D-249's basis smoke of Q's recipe (seed 259)
if not c or c["balls"] < 2000:
    print(f"smoke cap split: {c} -> NO-DATA STOP")
else:
    f3, nf3 = dr.fam3_share(rows)
    ok = abs(c["share"] - pred) <= dr.CAPR_BAND * pred and c["reset_max"] <= 8 and nf3 >= 500 and abs(f3 - pf3) <= dr.CAPR_BAND * pf3
    print(f"smoke cap split: pair-court feeder share {c['share']:.4f} (basis smoke {pred} +/- 25 %), reset-half longest rally "
          f"{c['reset_max']} (<= 8); three-family feeder share {f3:.3f} of {nf3} (basis smoke {pf3} +/- 25 %) " + ("ok" if ok else "STOP"))
mc = [r["launch"].get("move_call") for r in rows if r["launch"].get("move_call")]
if not mc:
    print("smoke call drill: no move_call counters -> NO-DATA STOP")
else:
    c = mc[-1]
    n = sum(c["judged"]); parts = sum(c["set"]) + sum(c["ready"]) + sum(c["reach"])
    ok = n >= 200 and parts > 0
    print(f"smoke call drill: {sum(c['issued'])} calls issued, {n} judged (>= 200), SET / READY / REACH / passed "
          f"{sum(c['set'])} / {sum(c['ready'])} / {sum(c['reach'])} / {sum(c['passed'])} (parts > 0) " + ("ok" if ok else "STOP"))
lc = rows[-1]["launch"].get("launch_courts", {}) if rows else {}
ok = lc.get("envs") == 256 and lc.get("episodes_falls", [0])[0] > 0
print(f"smoke launcher courts: {lc} (256 envs, episodes booked)" + (" ok" if ok else " STOP"))
PY
cat /tmp/lc112-smoke.txt | tee -a $R-summary.txt
[ "$(grep -c " ok$" /tmp/lc112-smoke.txt)" = 8 ] || stop SMOKE-FAIL

# --- training with the +180 kill ------------------------------------------------------------------------------------------
if [ ! -f artifacts/train/$RUN.exit.json ]; then
  ( python - <<'PY' > $R-kill.txt 2>&1
import glob, json, os, re, subprocess, sys, time
sys.path.insert(0, ".")
from picklebot_mj import callset_rule as cr, d1_rule as dr
run, START, KW = "rally-d1s3call1", 36793, (121, 180)
EXIT, SHARE, LOG = f"artifacts/train/{run}.exit.json", "results/lc112-train-share.jsonl", f"artifacts/train/{run}.log"
rd = lambda p: [json.loads(x) for x in open(p)] if os.path.exists(p) else []  # noqa: E731
def stop_now(why):
    os.system(f"pkill -f 'run-name {run} '")
    time.sleep(20)
    its = re.findall(r"Learning iteration (\d+)", open(LOG, errors="ignore").read()) if os.path.exists(LOG) else []
    print(f"STOPPED on {why}: training stopped at iteration {its[-1] if its else '?'} (+{int(its[-1]) - START if its else '?'})", flush=True)
CKN = (START + KW[1] + 39) // 40 * 40
ck = None
while ck is None:
    if os.path.exists(EXIT):
        print("training ended before the +180 check"); sys.exit(0)
    time.sleep(60)
    rows = rd(SHARE)
    c = glob.glob(f"artifacts/train/logs/picklebot_return_stand/*_{run}/model_{CKN}.pt")
    if c and rows and rows[-1]["step"] >= (START + KW[1]) * dr.STEPS_PER_IT:
        ck = c[0]
v = []
f = dr.exact_falls(rd(SHARE), *KW, START) / (12288 - 3072)
# Reported only (round 107's standing rule: a lever that changes the training input gets its line on the read mix against
# Q on the same seed): call episodes fall about 6x the move episodes by design, so the paired KILL-FALLS read decides.
print(f"(reported) training-log exact falls off the launcher courts {f:.3f} per 1,000 env-s over +{KW[0]}-{KW[1]} "
      f"(D-236's line {dr.EXACT_FALLS_MAX} was set for move episodes)", flush=True)
envy = open(os.path.join(os.path.dirname(ck), "params", "env.yaml")).read()
cfg_ok = (re.search(r"^\s*move_call_set: true\s*$", envy, re.M) is not None and "callset_event" in envy
          and re.search(r"^\s*pair_rally_cap: 8\s*$", envy, re.M) is not None and re.search(r"^\s*pair_drill_reset_frac: 0.5\s*$", envy, re.M) is not None)
v.append("CONTINUE" if cfg_ok else "KILL-CONFIG"); print(f"config: move_call_set, call event, cap 8, reset frac 0.5 -> {cfg_ok}", flush=True)
if any(y.startswith("KILL") or y == "NO-DATA" for y in v):
    stop_now("a training-log line"); sys.exit(0)
env = dict(os.environ, PICKLEBOT_RES_BASE=os.environ["KILL_BASE"], PICKLEBOT_LAM_R="2")
CS = "--task Picklebot-Footwork-CallSet-RallyLamR2-G1 --envs 1024 --seconds 120 --move-prob 1.0 --seed 4220453".split()
subprocess.run(["python", "scripts/diag/callset_eval.py", "--checkpoint", ck] + CS + ["--json", "results/lc112-kill-cs.json"], env=env,
               stdout=open("results/lc112-kill-cs.log", "w"), stderr=subprocess.STDOUT)
try:
    a, q = json.load(open("results/lc112-kill-cs.json")), json.load(open("results/lc112-csQ-4220453.json"))
    fa, fq = (1000 * d["robot_falls"] / (d["envs"] * d["sim_seconds"]) for d in (a, q))
    ka, na = cr.ladder_normal(a["move_drill"]["call_set"]); kq, nq = cr.ladder_normal(q["move_drill"]["call_set"])
    xf = "CONTINUE" if fa <= fq + 1e-9 else "KILL-FALLS"
    xl = "CONTINUE" if ka / max(na, 1) >= 0.02 else "KILL-NO-LADDER"
    print(f"KILL-FALLS: {os.path.basename(ck)} call-and-set falls {fa:.2f} vs Q {fq:.2f} per 1,000 env-s on dev 4220453 (<=) -> {xf}", flush=True)
    print(f"KILL-NO-LADDER: 1.5 m/s ladder, normal calls {ka / max(na, 1):.4f} (n {na}; Q {kq / max(nq, 1):.4f}) (>= 0.02) -> {xl}", flush=True)
    print("(reported) " + " | ".join(cr.target_lines(cr.read(a["move_drill"]["call_set"]))[1][:3]), flush=True)
    x = xf if xf != "CONTINUE" else xl
except Exception as ex:  # noqa: BLE001
    x = "NO-DATA"; print(f"KILL-FALLS / KILL-NO-LADDER: not read ({ex}) -> NO-DATA", flush=True)
if x != "CONTINUE":
    stop_now(x); sys.exit(0)
PA = ("--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally "
      "--pairs --pair-handoff contact --envs 2048 --seconds 120 --pair-drill-reset --seed 4220454").split()
subprocess.run(["python", "scripts/stage2_eval.py", "--checkpoint", ck] + PA + ["--json", "results/lc112-kill-pairs.json"], env=env,
               stdout=open("results/lc112-kill-pairs.log", "w"), stderr=subprocess.STDOUT)
try:
    pa, pq = dr.pooled_pairs(["results/lc112-kill-pairs.json"]), dr.pooled_pairs(["results/lc112-pairsQ-4220454.json"])
    x = "CONTINUE" if pa["feeder"] >= pq["feeder"] - 0.05 - 1e-9 else "KILL-FEEDER"
    print(f"KILL-FEEDER: feeder-ball legal {pa['feeder']:.4f} vs Q {pq['feeder']:.4f} on dev 4220454 (>= -0.05); (reported) "
          f"P(5+) {pa['p5']:.4f} vs {pq['p5']:.4f} -> {x}", flush=True)
except Exception as ex:  # noqa: BLE001
    x = "NO-DATA"; print(f"KILL-FEEDER: not read ({ex}) -> NO-DATA", flush=True)
if x != "CONTINUE":
    stop_now(x)
PY
  ) &
  env $TRAINENV PICKLEBOT_RES_BASE=$BASE PICKLEBOT_PAIR_LOG=$R-train-share.jsonl PICKLEBOT_PAIR_LOG_EVERY=480 PICKLEBOT_SCHED_LOG=$R-train.jsonl \
    PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=14400 bash scripts/diag/agility_train_run.sh $RUN $T \
    --agent.seed 263 --agent.max-iterations 600 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG $OV $CAP --agent.save-interval 40
  wait
fi
echo "training: $(cat artifacts/train/$RUN.exit.json)" | tee -a $R-summary.txt; cat $R-kill.txt | tee -a $R-summary.txt
grep -q -E -- "-> (KILL-|NO-DATA)" $R-kill.txt && stop "KILL ($(grep -o -- '-> KILL-[A-Z-]*' $R-kill.txt | head -1))"
grep -q '"exit_code": 0' artifacts/train/$RUN.exit.json || stop TRAIN-FAIL
CKR=$(ls -d $L/*_$RUN | tail -1)/$END; [ -f $CKR ] || stop ENDPOINT-MISMATCH

# --- gate: paired with Q on dev 4220455 (call-and-set) and 4220456 (pairs) -----------------------------------------------
[ -s $R-cs-4220455.json ] || onbase python scripts/diag/callset_eval.py --checkpoint $CKR $CS --seed 4220455 --json $R-cs-4220455.json > $R-cs-4220455.log 2>&1
[ -s $R-pairs-4220456.json ] || onbase python scripts/stage2_eval.py --checkpoint $CKR $PA --seed 4220456 --json $R-pairs-4220456.json > $R-pairs-4220456.log 2>&1
python - <<'PY' | tee -a $R-summary.txt
import json, os, sys
sys.path.insert(0, ".")
from picklebot_mj import callset_rule as cr, d1_rule as dr
R = "results/lc112"
need = [f"{R}-cs-4220455.json", f"{R}-csQ-4220455.json", f"{R}-pairs-4220456.json", f"{R}-pairsQ-4220456.json"]
if not all(os.path.exists(p) for p in need):
    print("RESULT EVAL-FAIL"); sys.exit(0)
a, q = (json.load(open(p)) for p in need[:2])
ca, cq = a["move_drill"]["call_set"], q["move_drill"]["call_set"]
ra, rq = cr.read(ca), cr.read(cq)
for w, r in (("child", ra), ("Q", rq)):
    for line in cr.target_lines(r)[1][:-1]:
        print(f"({w}) {line}")
if max(ra["pass"], rq["pass"]) >= 0.05:
    g, lo, hi = cr.paired_gain(ra["passed"], ra["judged"], rq["passed"], rq["judged"]); what = "headline pass"
else:
    (ka, na), (kq, nq) = cr.ladder_normal(ca), cr.ladder_normal(cq)
    g, lo, hi = cr.paired_gain(ka, na, kq, nq); what = "1.5 m/s ladder, normal calls"
keep, flat = lo > 0, hi < 0.02
fa, fq = (1000 * d["robot_falls"] / (d["envs"] * d["sim_seconds"]) for d in (a, q))
pa, pq = dr.pooled_pairs([need[2]]), dr.pooled_pairs([need[3]])
gf, gl = fa <= fq + 1e-9, pa["feeder"] >= pq["feeder"] - 0.05 - 1e-9
print(f"DECIDING ({what}): child - Q {g:+.4f} (95 % {lo:+.4f} to {hi:+.4f}) -> {'KEEP' if keep else 'FLAT' if flat else 'NOT-SHOWN'}")
print(f"GUARD falls: {fa:.2f} vs Q {fq:.2f} per 1,000 env-s (<=) -> {gf}")
print(f"GUARD feeder: {pa['feeder']:.4f} vs Q {pq['feeder']:.4f} (>= -0.05) -> {gl}; (reported) P(5+) {pa['p5']:.4f} vs {pq['p5']:.4f}")
v = "KEEP" if (keep and gf and gl) else ("FLAT" if flat else "NOT-KEPT")
json.dump({"deciding": what, "gain": [g, lo, hi], "guards": [gf, gl], "verdict": v}, open(f"{R}-summary.json", "w"), indent=1)
print(f"RESULT {v}")
PY
set -- $(tail -1 $R-summary.txt)
[ "$1" = RESULT ] || stop "SUMMARY-CRASH"
stop "$2 (panel)"

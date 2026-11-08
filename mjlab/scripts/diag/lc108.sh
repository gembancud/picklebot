#!/usr/bin/env bash
# D-246 (panel round 106, (a): D-245 re-run unchanged on a fresh smoke seed; the cap-split share re-predicted from a
# smoke read of Q's recipe + the dose (D-245's smoke, 0.1642), band +/- 25 % unchanged; training seed 254, smoke 255).
# D-245 (panel round 105; the weak-family feed dose 5 of 5, x2 by 4 of 5, Q's cap-8 recipe by 4 of 5): child =
# rally-d1s3q8w2 = Q (rally-d1s3cap8hr2 model_36793, CONFIRMED in D-243) on Q's recipe (HalfReset task, pair_rally_cap 8
# on the set-start half only) with training feed-mix weights 2.0 on reach_deep, cross_backhand and reach_backhand (the
# families that held 424 of Q's 616 feeder misses). The only change. 600 iterations to model_37392; training seed 252,
# smoke 253.
# Stage 0: Q's direction read on dev 4220435 (KILL-DIR's paired reference).
# Smoke (160 iterations): D-244's lines with the cap back at 8: pair-court feeder share within +/- 25 % of 0.1306 (Q's
#   formula), set-start half never past 8, free-half rallies ending 9-15 > 0; and the three families' share of
#   pair-court feeder balls within +/- 25 % of 6/23 = 0.261 (recorded before the smoke); config checks the weights.
# Kill at +240: training-log lines first (KILL-LOST-OPEN reset half >= Q's 0.7356 - 0.02; KILL-UNSTABLE <= 3.14; config),
#   then KILL-NO-FALLS (dev 4220434), KILL-DIR (left contact on dev 4220435 >= Q's - 0.01), KILL-LATE (dev 4220436:
#   late failure share <= 0.0319).
# Gate: every D-244 line unchanged (K3-KEPT, OPEN against Q + 0.02, M/N/P/Q-KEPT, guards), plus D244-KEPT (P(5+) >=
#   0.7880 - 0.02); R3 on dev 4220437 (Q read there too). All pass -> CONFIRM on pairs 4220425-4220428, directions
#   4220429-4220432 (C re-read), R3 4220433; every line gating; the CONFIRM block is the registered target read (D-244's
#   registration carried to D-245, one look).
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER PICKLEBOT_READY_LOG \
  PICKLEBOT_RESTART_OBS PICKLEBOT_RESTART_OBS_FREEZE PICKLEBOT_REF_CKPT PICKLEBOT_REF_COEF PICKLEBOT_PAIR_LOG
pgrep -f "run-name |kickstart_h4|stage2_eval|footwork_eval|feeder_speed|distill_latent|latent_reach_floor" > /dev/null && { echo "GPU busy: not started"; exit 1; }
R=results/lc108; RC=results/d1s3ctl; L=artifacts/train/logs/picklebot_return_stand; RUN=rally-d1s3q8w2b
BASE=/mnt/f/dev/picklebot-mjlab/mjlab/$L/2026-10-31_18-24-20_s5c-d1-fw1bS/model_32854.pt
PRUN=2026-11-07_19-25-03_rally-d1s3cap8hr2; PCK=model_36793.pt; P=$L/2026-11-04_00-06-34_rally-d1s3lr3/model_32598.pt; PR=$L/$PRUN/$PCK; T=Picklebot-Rally22b-FastMove-DrillReset-Launch-HalfReset-G1; END=model_37392.pt
C2SHARE=results/lev76-rally-d1s3lr4-share.jsonl
for f in $BASE $P $PR $C2SHARE; do [ -f $f ] || { echo "missing $f"; exit 1; }; done
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
B=--env.actions.ball; OV="$B.court-feed-prob 1.0 $B.refeed-delay-s 0.5 $B.recovery-mode fixed $B.planner-mode off $B.target-mode A"
for f in backhand fast drop low short high reach-forehand; do OV="$OV $B.feed-mix.weights.$f 1.0"; done
for f in reach-deep cross-backhand reach-backhand; do OV="$OV $B.feed-mix.weights.$f 2.0"; done  # D-245
EP=""
CAP="$B.pair-rally-cap 8 $B.pair-rally-cap-reset-only True"
TRAINENV="PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_STD_MIN=0.1 PICKLEBOT_LR_PEAK=3e-5 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_KL_GUARD=0.05 PICKLEBOT_LR_TOTAL=0"
export PICKLEBOT_TRAIN_ENTRY=scripts/diag/footwork_train.py
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120"
onbase() { PICKLEBOT_RES_BASE=$BASE PICKLEBOT_LAM_R=2 "$@"; }
stop() { echo "VERDICT: $1" | tee -a $R-summary.txt; echo done > artifacts/train/lc108.done; exit 0; }
[ -s $R-summary.txt ] || echo "D-245: C = $P (reference); warm start Q = $PR (CONFIRMED in D-243); child = $RUN on $T + pair_rally_cap 8 on the set-start half + feed-mix x2 on reach_deep, cross_backhand, reach_backhand; training seed 254, smoke 255 (D-246)" > $R-summary.txt

# --- stage 0: Q's direction read on dev 4220435 (KILL-DIR's paired reference) -----------------------------------------
[ -s results/lc107-dirQ-4220435.json ] || onbase python scripts/diag/feeder_speed_envelope.py --checkpoint $PR --seed 4220435 --json results/lc107-dirQ-4220435.json > results/lc107-dirQ-4220435.log 2>&1
export KILL_BASE=$BASE

# --- smoke (D-205's checks, LR 3e-5) ------------------------------------------------------------------------------------
if [ ! -f artifacts/train/$RUN-smoke.exit.json ]; then
  env $TRAINENV PICKLEBOT_RES_BASE=$BASE PICKLEBOT_SCHED_LOG=$R-smoke.jsonl PICKLEBOT_PAIR_LOG=$R-smoke-share.jsonl PICKLEBOT_PAIR_LOG_EVERY=480 PICKLEBOT_ENVS=1024 \
    PICKLEBOT_WALL_CAP=2400 bash scripts/diag/agility_train_run.sh $RUN-smoke $T --agent.seed 255 --agent.max-iterations 160 --agent.resume True \
    --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG $OV $CAP $EP --agent.save-interval 40
fi
SD=$(ls -d $L/*_$RUN-smoke | tail -1)
{ grep -q '"exit_code": 0' artifacts/train/$RUN-smoke.exit.json && echo "smoke exit 0 ok" || echo "smoke exit STOP"; } > /tmp/lc108-smoke.txt
{ grep -a -q -E "Traceback|Error" artifacts/train/$RUN-smoke.log && echo "smoke traceback STOP" || echo "smoke no traceback ok"; } >> /tmp/lc108-smoke.txt
python scripts/diag/falls_by_length.py artifacts/train/$RUN-smoke.log | awk '{print "(reported) smoke falls per 1,000 env-seconds, log estimator (biased by the launcher courts synchronised time-outs)", $NF}' >> /tmp/lc108-smoke.txt
python - <<'PY' >> /tmp/lc108-smoke.txt
import json, os
p = 'results/lc108-smoke-share.jsonl'
rows = [json.loads(x) for x in open(p)] if os.path.exists(p) else []
rows = [r for r in rows if 'other_falls' in r['launch'].get('launch_courts', {})]
if len(rows) < 2:
    print('smoke falls per 1,000 env-seconds off the launcher courts: NO-DATA STOP')
else:
    a, b = rows[0], rows[-1]
    la, lb = a['launch']['launch_courts'], b['launch']['launch_courts']
    n = 1024 - lb['envs']
    r = 1000 * (lb['other_falls'] - la['other_falls']) / ((b['step'] - a['step']) * 0.02 * n)
    le = (lb['episodes_falls'][1] - la['episodes_falls'][1]) / max(1, lb['episodes_falls'][0] - la['episodes_falls'][0])
    print(f'(reported) launcher-court falls per episode {le:.4f} (R on the court read 0.0622)')
    print(f'smoke falls per 1,000 env-seconds off the launcher courts (exact count, steps {a["step"]}-{b["step"]}) {r:.3f}', 'ok' if r <= 4.157 else 'STOP')
PY
CUDA_VISIBLE_DEVICES= python - "$(ls $SD/model_*.pt | sort -V | tail -1)" <<'PY' >> /tmp/lc108-smoke.txt
import sys, torch
sd = torch.load(sys.argv[1], map_location="cpu", weights_only=False)
s = sd["actor_state_dict"]["distribution.std_param"]
dead = sorted({i for v in sd["optimizer_state_dict"]["state"].values() if v["exp_avg_sq"].shape == s.shape
               for i in (v["exp_avg_sq"] == 0).nonzero().flatten().tolist()})
print("smoke std min", round(float(s.min()), 4), "outputs with no gradient", dead, "ok" if not dead and float(s.min()) >= 0.0999 else "STOP")
PY
python - "$SD" "$BASE" <<'PY' >> /tmp/lc108-smoke.txt
import re, sys
d, base = sys.argv[1], sys.argv[2]
env = open(f"{d}/params/env.yaml").read()
want = [("court_feed_prob", "1.0"), ("refeed_delay_s", "0.5"), ("recovery_mode", "fixed"), ("planner_mode", "'?off'?"),
        ("target_mode", "A"), ("obs_ball_pos_noise", "0.03"), ("obs_ball_vel_noise", "0.15"), ("pair_drill_court_frac", "0.5"),
        ("episode_length_s", "120.0"), ("pair_drill_reset", "true"), ("pair_reset_parks", "true"), ("backhand", "1.0"), ("reach_backhand", "2.0"), ("reach_deep", "2.0"), ("cross_backhand", "2.0"), ("fast", "1.0"), ("lam_r", "2.0"),
        ("pair_rally_cap", "8"), ("pair_cut_prob", "0.0"), ("pair_drill_reset_frac", "0.5"), ("pair_rally_cap_reset_only", "true"), ("pair_launch_court_frac", "0.25")]
miss = [k for k, v in want if not re.search(rf"^\s*{k}: {v}\s*$", env, re.M)]
based = re.search(rf"^\s*base_checkpoint: {re.escape(base)}\s*$", env, re.M) is not None
terms = ("rally_fast_track_lin_vel" in env and "footwork_specialist.rally_recovery_reward" not in env and "return_stand.recovery_reward" in env
         and "return_stand.stance_progress" in env and "is_terminated" not in env and "launch_time_out" in env and "parked_ready" not in env and "ready_at_event" not in env and "restart_obs" not in env)
ok = not miss and based and terms
print(f"smoke config check: missing {miss}; d1 base {based}; fast move + stance_progress + launch_time_out, no fall term, no other new terms {terms} -> {'ok' if ok else 'STOP'}")
PY
python - artifacts/train/$RUN-smoke.log <<'PY' >> /tmp/lc108-smoke.txt
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
python - <<'PY' >> /tmp/lc108-smoke.txt
import json, os, sys
sys.path.insert(0, ".")
from picklebot_mj import d1_rule as dr
p = "results/lc108-smoke-share.jsonl"
rows = [json.loads(x) for x in open(p)] if os.path.exists(p) else []
ok_d, line = dr.half_dose(rows, 36793)
print("smoke dose " + line + (" ok" if ok_d else " STOP"))
PY
cat /tmp/lc108-smoke.txt | tee -a $R-summary.txt
python - <<'PY' >> /tmp/lc108-smoke.txt
import json, os
p = "results/lc108-smoke-share.jsonl"
rows = [json.loads(x) for x in open(p)] if os.path.exists(p) else []
lc = rows[-1]["launch"].get("launch_courts", {}) if rows else {}
ok = lc.get("envs") == 256 and lc.get("episodes_falls", [0])[0] > 0
print(f"smoke launcher courts: {lc} (256 envs, episodes booked)" + (" ok" if ok else " STOP"))
PY
cat /tmp/lc108-smoke.txt | tail -1 | tee -a $R-summary.txt
python - <<'PY' >> /tmp/lc108-smoke.txt
import json, os, sys
sys.path.insert(0, ".")
from picklebot_mj import d1_rule as dr
p = "results/lc108-smoke-share.jsonl"
rows = [json.loads(x) for x in open(p)] if os.path.exists(p) else []
c = dr.cap_split(rows)
pred = dr.D246_SHARE_PRED
if not c or c["balls"] < 2000:
    print(f"smoke cap split: {c} -> NO-DATA STOP")
else:
    f3, nf3 = dr.fam3_share(rows)
    ok = abs(c["share"] - pred) <= dr.CAPR_BAND * pred and c["reset_max"] <= 8 and c["free_9_15"] > 0 \
        and nf3 >= 500 and abs(f3 - dr.FAM3_SHARE_PRED) <= dr.CAPR_BAND * dr.FAM3_SHARE_PRED
    print(f"smoke cap split: pair-court feeder share {c['share']:.4f} (prediction {pred} +/- 25 %), reset-half longest rally "
          f"{c['reset_max']} (<= 8; n {c['reset_n']}), free-half rallies ending 9-15 {c['free_9_15']} (> 0; past 8 "
          f"{c['free_over8']:.3f} of {c['free_n']}); three-family feeder share {f3:.3f} of {nf3} (prediction "
          f"{dr.FAM3_SHARE_PRED:.3f} +/- 25 %) " + ("ok" if ok else "STOP"))
PY
cat /tmp/lc108-smoke.txt | tail -1 | tee -a $R-summary.txt
[ "$(grep -c " ok$" /tmp/lc108-smoke.txt)" = 8 ] || stop SMOKE-FAIL

# --- training with the +240 kill -----------------------------------------------------------------------------------------
if [ ! -f artifacts/train/$RUN.exit.json ]; then
  ( python - <<'PY' > $R-kill.txt 2>&1
import glob, json, os, re, subprocess, sys, time
sys.path.insert(0, ".")
from picklebot_mj import d1_rule as dr
run, START = "rally-d1s3q8w2b", 36793
EXIT, SHARE, LOG = f"artifacts/train/{run}.exit.json", "results/lc108-train-share.jsonl", f"artifacts/train/{run}.log"
rd = lambda p: [json.loads(x) for x in open(p)] if os.path.exists(p) else []  # noqa: E731
def stop_now(why):
    os.system(f"pkill -f 'run-name {run} '")
    time.sleep(20)
    its = re.findall(r"Learning iteration (\d+)", open(LOG, errors="ignore").read()) if os.path.exists(LOG) else []
    print(f"STOPPED on {why}: training stopped at iteration {its[-1] if its else '?'} (+{int(its[-1]) - START if its else '?'})", flush=True)
CKN = (START + dr.HALF_KILL_WIN[1] + 39) // 40 * 40
ck = None
while ck is None:
    if os.path.exists(EXIT):
        print("training ended before the +240 check"); sys.exit(0)
    time.sleep(60)
    rows = rd(SHARE)
    c = glob.glob(f"artifacts/train/logs/picklebot_return_stand/*_{run}/model_{CKN}.pt")
    if c and rows and rows[-1]["step"] >= (START + dr.HALF_KILL_WIN[1]) * dr.STEPS_PER_IT:
        ck = c[0]
v = []
for x, line in dr.half_kill(rd(SHARE), START, 12288 - 3072, ref_open=dr.Q_OPEN_181_240, ref_name="Q"):
    v.append(x); print(line, flush=True)
envy = open(os.path.join(os.path.dirname(ck), "params", "env.yaml")).read()
cfg_ok = (re.search(r"^\s*pair_launch_court_frac: 0.25\s*$", envy, re.M) is not None and "launch_time_out" in envy
          and "is_terminated" not in envy and re.search(r"^\s*pair_rally_cap: 8\s*$", envy, re.M) is not None
          and all(re.search(rf"^\s*{f}: 2.0\s*$", envy, re.M) is not None for f in ("reach_deep", "cross_backhand", "reach_backhand"))
          and re.search(r"^\s*pair_drill_reset_frac: 0.5\s*$", envy, re.M) is not None
          and re.search(r"^\s*pair_rally_cap_reset_only: true\s*$", envy, re.M) is not None)
v.append("CONTINUE" if cfg_ok else "KILL-CONFIG"); print(f"config: launcher courts, launch_time_out, no fall term, pair_rally_cap 8 on the reset half only, pair_drill_reset_frac 0.5, reach_deep 2.0 -> {cfg_ok}", flush=True)
if any(y.startswith("KILL") or y == "NO-DATA" for y in v):
    stop_now("a training-log line"); sys.exit(0)
env = dict(os.environ, PICKLEBOT_RES_BASE=os.environ["KILL_BASE"], PICKLEBOT_LAM_R="2")
CT = ("--task Picklebot-Latent-Court-Res-G1 --envs 2048 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every "
      "--target A --no-hint --recovery random --seed 4220434").split()
subprocess.run(["python", "scripts/stage2_eval.py", "--checkpoint", ck] + CT + ["--json", "results/lc108-kill-court.json"], env=env,
               stdout=open("results/lc108-kill-court.log", "w"), stderr=subprocess.STDOUT)
try:
    r3 = json.load(open("results/lc108-kill-court.json"))["robot_fall_rate_per_episode"]
    x = "CONTINUE" if r3 <= dr.R3_MAX else "KILL-NO-FALLS"
    print(f"KILL-NO-FALLS: {os.path.basename(ck)} court falls per episode {r3:.4f} on dev 4220434 (<= {dr.R3_MAX}) -> {x}", flush=True)
except Exception as ex:  # noqa: BLE001
    x = "NO-DATA"; print(f"KILL-NO-FALLS: not read ({ex}) -> NO-DATA", flush=True)
if x != "CONTINUE":
    stop_now("KILL-NO-FALLS"); sys.exit(0)
subprocess.run(["python", "scripts/diag/feeder_speed_envelope.py", "--checkpoint", ck, "--seed", "4220435", "--json",
                "results/lc108-kill-dir.json"], env=env, stdout=open("results/lc108-kill-dir.log", "w"), stderr=subprocess.STDOUT)
try:
    (a, na), (bn, nb) = dr.left_contact("results/lc108-kill-dir.json"), dr.left_contact("results/lc107-dirQ-4220435.json")
    x = "CONTINUE" if a >= bn - 0.01 - 1e-9 else "KILL-DIR"
    print(f"KILL-DIR: left feeder contact {os.path.basename(ck)} {a:.4f} (n {na}) vs Q {bn:.4f} (n {nb}) on dev 4220435 (>= -0.01) -> {x}", flush=True)
except Exception as ex:  # noqa: BLE001
    x = "NO-DATA"; print(f"KILL-DIR: not read ({ex}) -> NO-DATA", flush=True)
if x != "CONTINUE":
    stop_now("KILL-DIR"); sys.exit(0)
PA = ("--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally "
      "--pairs --pair-handoff contact --envs 2048 --seconds 120 --pair-drill-reset --seed 4220436").split()
subprocess.run(["python", "scripts/stage2_eval.py", "--checkpoint", ck] + PA + ["--json", "results/lc108-kill-pairs.json"], env=env,
               stdout=open("results/lc108-kill-pairs.log", "w"), stderr=subprocess.STDOUT)
try:
    late = dr.pooled_hazards(["results/lc108-kill-pairs.json"])["late"]
    x = "CONTINUE" if late <= dr.K3_LINE + 1e-9 else "KILL-LATE"
    print(f"KILL-LATE: {os.path.basename(ck)} late failure share {late:.4f} on dev 4220436 (<= {dr.K3_LINE:.4f}) -> {x}", flush=True)
except Exception as ex:  # noqa: BLE001
    x = "NO-DATA"; print(f"KILL-LATE: not read ({ex}) -> NO-DATA", flush=True)
if x != "CONTINUE":
    stop_now("KILL-LATE")
PY
  ) &
  env $TRAINENV PICKLEBOT_RES_BASE=$BASE PICKLEBOT_PAIR_LOG=$R-train-share.jsonl PICKLEBOT_PAIR_LOG_EVERY=480 PICKLEBOT_SCHED_LOG=$R-train.jsonl \
    PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=14400 bash scripts/diag/agility_train_run.sh $RUN $T \
    --agent.seed 254 --agent.max-iterations 600 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG $OV $CAP $EP --agent.save-interval 40
  wait
fi
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
CT="--task Picklebot-Latent-Court-Res-G1 --envs 2048 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --recovery random --seed 4220437"
[ -s $R-court-N.json ] || onbase python scripts/stage2_eval.py --checkpoint $CKR $CT --json $R-court-N.json >> $R-reads.log 2>&1
[ -s $R-court-Q-4220437.json ] || onbase python scripts/stage2_eval.py --checkpoint $PR $CT --json $R-court-Q-4220437.json >> $R-reads.log 2>&1
python - <<'PY' | tee -a $R-summary.txt
import json, os, sys
sys.path.insert(0, "scripts"); sys.path.insert(0, ".")
import rally_check as rc
from picklebot_mj import d1_rule as dr
R, RC = "results/lc108", "results/d1s3ctl"
S = (4220385, 4220386, 4220387, 4220388); D = (4220307, 4220334, 4220335, 4220336)
LBL = {"R": "child", "Ro": "child (old read)", "W": "M", "C": "C", "Co": "C (old read)"}
arm = {"W": ([f"results/lc98-R-pairs-{s}.json" for s in S], [f"results/lc98-R-dir-{s}.json" for s in D]),
       "R": ([f"{R}-R-pairs-{s}.json" for s in S], [f"{R}-R-dir-{s}.json" for s in D]),
       "C": ([f"results/sr91-set-{s}.json" for s in S], [f"results/lev74-C-dir-{s}.json" for s in D]),
       "Ro": ([f"{R}-R-old-{s}.json" for s in S], [f"{R}-R-dir-{s}.json" for s in D]),
       "Co": ([f"results/sr91-old-{s}.json" for s in S], [f"results/lev74-C-dir-{s}.json" for s in D])}
if not all(os.path.exists(f) for w in arm for f in arm[w][0] + arm[w][1]):
    print("RESULT EVAL-FAIL"); sys.exit(0)
ok_g, d, lo, line = dr.gain2(arm["R"][0], arm["C"][0]); print("child vs C " + line)
print("(reported) old read: child vs C " + dr.gain2(arm["Ro"][0], arm["Co"][0])[3])
for w in ("R", "C"):
    print(f"(reported) court conversion {LBL[w]}: " + str({k: round(v, 4) if isinstance(v, float) else v for k, v in dr.court_conv(arm[w][0]).items()}))
pf, pd = dr.pool_reads(*arm["R"])
print("child (pooled) against the original parent (pooled, same seeds):")
g = rc.r19_guards(pf["per_family"], pd["directions"], ref=f"{RC}-parent-pooled", cross_ref=f"{RC}-parent-pooled-pairs.json",
                  name="parent pooled", cross_name="parent pooled")
m = dr.mechanism(arm["R"][0])
print(f"mechanism child: ready {m['ready']:.3f} (>= {dr.REP_READY}), falls/1000 hits {m['falls_per_1000_hits']:.2f} (<= {dr.REP_FALLS}), "
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
print(f"R3: court read child (24 s, dev 4220437) robot falls per episode {r3:.4f} (<= 0.04) -> {ok_r3}")
for w in ("R", "W", "C"):
    _, pdw = dr.pool_reads(*arm[w])
    print(f"(reported) {LBL[w]} direction contact: " + ", ".join(f"{k} {v['contact']:.3f}" for k, v in pdw["directions"].items()))
ob = [[0, 0] for _ in range(8)]
for p in arm["R"][0]:
    L = json.load(open(p)).get("launch_state", {}).get("outcome_by_d")
    if L:
        ob = [[x[0] + y[0], x[1] + y[1]] for x, y in zip(ob, L)]
print("(reported) child " + dr.dist_route(ob)[1][0])
ok_k, line = dr.r_kept(arm["R"][0], arm["W"][0]); print(line.replace("R-KEPT", "M-KEPT").replace(" vs R ", " vs M "))
QP = [f"results/lc105-R-pairs-{s}.json" for s in S]
ok_o, line = dr.open_gate(arm["R"][0], QP); print(line.replace(" vs M ", " vs Q "))
ok_n, line = dr.r_kept(arm["R"][0], [f"results/lc102-R-pairs-{s}.json" for s in S]); print(line.replace("R-KEPT", "N-KEPT").replace(" vs R ", " vs N "))
ok_p, line = dr.r_kept(arm["R"][0], [f"results/lc103-R-pairs-{s}.json" for s in S]); print(line.replace("R-KEPT", "P-KEPT").replace(" vs R ", " vs P "))
ok_q, line = dr.r_kept(arm["R"][0], QP); print(line.replace("R-KEPT", "Q-KEPT").replace(" vs R ", " vs Q "))
ok_d, line = dr.r_kept(arm["R"][0], [f"results/lc106-R-pairs-{s}.json" for s in S]); print(line.replace("R-KEPT", "D244-KEPT").replace(" vs R ", " vs D-244 "))
for w, ps in (("child", arm["R"][0]), ("Q", QP), ("C", arm["C"][0])):
    print(f"(reported) {w} rally endings by length: " + str(dr.late_split(ps)))
def _lb(paths):
    n = c = 0
    for p in paths:
        dd = json.load(open(p))["directions"]
        for k in ("left", "back"):
            n += dd[k]["feeds"]; c += dd[k]["feeds"] * dd[k]["contact"]
    return c / max(n, 1), n
(a, na), (bm, nb) = _lb(arm["R"][1]), _lb(arm["W"][1])
se = (a * (1 - a) / max(na, 1) + bm * (1 - bm) / max(nb, 1)) ** 0.5
print(f"(reported) left + back feeder contact child {a:.4f} (n {na}) vs M {bm:.4f} (n {nb}): {100 * (a - bm):+.1f} points, SE {100 * se:.1f}")
w3 = json.load(open(f"{R}-court-Q-4220437.json"))["robot_fall_rate_per_episode"] if os.path.exists(f"{R}-court-Q-4220437.json") else None
print(f"(reported) R3 court read of the warm start Q on dev 4220437: {w3}")
ok = dr.replicated(ok_g, m) and g and ok_l and ok_r3 and ok_k and ok_o and ok_n and ok_p and ok_q and ok_d
json.dump({"gain2": ok_g, "guards": g, "mechanism": m, "rec_lines": ok_l, "open": ok_o, "n_kept": ok_n, "p_kept": ok_p, "q_kept": ok_q, "d244_kept": ok_d, "candidate": ok}, open(f"{R}-summary.json", "w"), indent=1)
print(f"RESULT {'CANDIDATE' if ok else 'NO-CANDIDATE'}")
PY
set -- $(tail -1 $R-summary.txt)
[ "$1" = RESULT ] || stop "SUMMARY-CRASH"
[ "$2" = CANDIDATE ] || stop "$2 (panel)"

# --- CONFIRM on fresh dev seeds ------------------------------------------------------------------------------------------
reads confirm-C $P "4220425 4220426 4220427 4220428" "4220429 4220430 4220431 4220432"  # PA has --pair-drill-reset
reads confirm-R $CKR "4220425 4220426 4220427 4220428" "4220429 4220430 4220431 4220432"
[ -s $R-confirm-court-4220433.json ] || onbase python scripts/stage2_eval.py --checkpoint $CKR ${CT%4220437}4220433 --json $R-confirm-court-4220433.json >> $R-reads.log 2>&1
python - <<'PY' | tee -a $R-summary.txt
import json, os, sys
sys.path.insert(0, "scripts"); sys.path.insert(0, ".")
import rally_check as rc
from picklebot_mj import d1_rule as dr
R = "results/lc108"
S = (4220425, 4220426, 4220427, 4220428); D = (4220429, 4220430, 4220431, 4220432)
arm = {w: ([f"{R}-confirm-{w}-pairs-{s}.json" for s in S], [f"{R}-confirm-{w}-dir-{s}.json" for s in D]) for w in ("C", "R")}
if not all(os.path.exists(f) for w in arm for f in arm[w][0] + arm[w][1]):
    print("RESULT CONFIRM-EVAL-FAIL"); sys.exit(0)
for w in arm:
    pf, pd = dr.pool_reads(*arm[w])
    json.dump(pf, open(f"{R}-confirm-{w}-pooled-pairs.json", "w"), indent=1); json.dump(pd, open(f"{R}-confirm-{w}-pooled-dir.json", "w"), indent=1)
ok_g, d, lo, line = dr.gain2(arm["R"][0], arm["C"][0]); print("confirmation child vs C " + line)
pf, pd = dr.pool_reads(*arm["R"])
print("confirmation: child (fresh pooled) against C (fresh pooled):")
g = rc.r19_guards(pf["per_family"], pd["directions"], ref=f"{R}-confirm-C-pooled", cross_ref=f"{R}-confirm-C-pooled-pairs.json",
                  name="C (fresh)", cross_name="C (fresh)")
m = dr.mechanism(arm["R"][0])
print(f"mechanism child: ready {m['ready']:.3f}, falls/1000 hits {m['falls_per_1000_hits']:.2f}, WRONG_SIDE {m['wrong_side_share']:.3f}, recovery {m['recovery_median_m']:.3f} m")
ok_lc, lines = dr.cfs79_lines(arm["R"][0], arm["C"][0])
for x in lines:
    print(x)
r3c = json.load(open(f"{R}-confirm-court-4220433.json"))["robot_fall_rate_per_episode"]
print(f"confirmation R3: court read child (dev 4220433) {r3c:.4f} (<= 0.04) -> {r3c <= 0.04}")
ok = dr.replicated(ok_g, m) and g and ok_lc and r3c <= 0.04
tok, tl = dr.target_read(arm["R"][0], r3c)
for x in tl:
    print(x)
print(f"TARGET {'MET' if (ok and tok) else 'NOT MET'} (the registered target read, D-244 / D-245)")
print(f"RESULT {'CONFIRMED' if ok else 'CONFIRM-FAIL'}")
PY
set -- $(tail -1 $R-summary.txt)
stop "$2"

#!/usr/bin/env bash
# D-238 (panel round 98, (a) 5 of 5): D-237 with the sector weights x3 (D-237's smoke failed the sector share, 0.436 < 0.45).
# D-237 (panel round 97, (ii) 5 of 5). N = rally-d1s3drl4 = M (rally-d1s3drl3 model_34996; UNPROMOTED: NO-CANDIDATE on the
# left + back guard alone, -5.1 vs -5) on Picklebot-Rally22b-FastMove-DrillReset-Launch-LeftBack-G1 (D-235's launcher-court
# task with the move drill's spots weighted x2 toward sectors 2 left, 3 back-left, 4 back). The only change.
# C's recipe: LR 3e-5, ScheduledPPO, 600 iterations from model_34996, endpoint model_35595; training seed 238, smoke 240.
# Stage 0: M's direction read on dev 4220402 (KILL-DIR's paired reference).
# Smoke (160 iterations): D-235's seven lines (exact falls off the launcher courts <= 4.157; config also checks the sector
#   weights) plus the sector share: sectors 2-4 >= 0.45 of the issued move spots (uniform 0.375; x2 gives 0.545 before
#   baseline flips).
# Kill at +180 (window +61-180; every line read before any stop): KILL-NO-HIT (pair-court mean rally length >= 0.9 x M's
#   last 120 iterations, +1080-1199 of rally-d1s3drl2/3); KILL-UNSTABLE (exact falls off the launcher courts <= 3.14);
#   KILL-LOST-OPEN (training (1-h0)(1-h1) >= M's last window - 0.02); KILL-NO-FALLS (model_35200 court falls / episode on
#   dev 4220402 <= 0.04); KILL-DIR (model_35200 left + back feeder contact on dev 4220402 >= M's on the same seed - 0.01);
#   config.
# Gate on the frozen set-start read, dev 4220385-4220388, against C: every D-236 line (gain2, r19_guards with the left +
#   back guard unchanged, cfs79_lines), M-KEPT (pooled P(5+) >= M's - 0.02, M = results/lc98-R-pairs-*), R3 (court falls /
#   episode <= 0.04 on dev 4220403; M read there too, reported). All pass -> CONFIRM on 4220349-4220356 (C re-read; the
#   guards re-read against C on those seeds) plus N's R3 re-read on dev 4220399 (<= 0.04).
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER PICKLEBOT_READY_LOG \
  PICKLEBOT_RESTART_OBS PICKLEBOT_RESTART_OBS_FREEZE PICKLEBOT_REF_CKPT PICKLEBOT_REF_COEF PICKLEBOT_PAIR_LOG
pgrep -f "run-name |kickstart_h4|stage2_eval|footwork_eval|feeder_speed|distill_latent|latent_reach_floor" > /dev/null && { echo "GPU busy: not started"; exit 1; }
R=results/lc100; RC=results/d1s3ctl; L=artifacts/train/logs/picklebot_return_stand; RUN=rally-d1s3drl5
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
stop() { echo "VERDICT: $1" | tee -a $R-summary.txt; echo done > artifacts/train/lc100.done; exit 0; }
[ -s $R-summary.txt ] || echo "D-238: C = $P (reference); warm start M = $PR (unpromoted); N = $RUN on $T (launcher courts + left/back move drill x3); training seed 238, smoke 240" > $R-summary.txt

# --- stage 0: M's direction read on dev 4220402 (KILL-DIR's paired reference) -----------------------------------------
[ -s results/lc99-dirM-4220402.json ] || onbase python scripts/diag/feeder_speed_envelope.py --checkpoint $PR --seed 4220402 --json results/lc99-dirM-4220402.json > results/lc99-dirM-4220402.log 2>&1
export KILL_BASE=$BASE

# --- smoke (D-205's checks, LR 3e-5) ------------------------------------------------------------------------------------
if [ ! -f artifacts/train/$RUN-smoke.exit.json ]; then
  env $TRAINENV PICKLEBOT_RES_BASE=$BASE PICKLEBOT_SCHED_LOG=$R-smoke.jsonl PICKLEBOT_PAIR_LOG=$R-smoke-share.jsonl PICKLEBOT_PAIR_LOG_EVERY=480 PICKLEBOT_ENVS=1024 \
    PICKLEBOT_WALL_CAP=2400 bash scripts/diag/agility_train_run.sh $RUN-smoke $T --agent.seed 240 --agent.max-iterations 160 --agent.resume True \
    --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG $OV $EP --agent.save-interval 40
fi
SD=$(ls -d $L/*_$RUN-smoke | tail -1)
{ grep -q '"exit_code": 0' artifacts/train/$RUN-smoke.exit.json && echo "smoke exit 0 ok" || echo "smoke exit STOP"; } > /tmp/lc100-smoke.txt
{ grep -a -q -E "Traceback|Error" artifacts/train/$RUN-smoke.log && echo "smoke traceback STOP" || echo "smoke no traceback ok"; } >> /tmp/lc100-smoke.txt
python scripts/diag/falls_by_length.py artifacts/train/$RUN-smoke.log | awk '{print "(reported) smoke falls per 1,000 env-seconds, log estimator (biased by the launcher courts synchronised time-outs)", $NF}' >> /tmp/lc100-smoke.txt
python - <<'PY' >> /tmp/lc100-smoke.txt
import json, os
p = 'results/lc100-smoke-share.jsonl'
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
CUDA_VISIBLE_DEVICES= python - "$(ls $SD/model_*.pt | sort -V | tail -1)" <<'PY' >> /tmp/lc100-smoke.txt
import sys, torch
sd = torch.load(sys.argv[1], map_location="cpu", weights_only=False)
s = sd["actor_state_dict"]["distribution.std_param"]
dead = sorted({i for v in sd["optimizer_state_dict"]["state"].values() if v["exp_avg_sq"].shape == s.shape
               for i in (v["exp_avg_sq"] == 0).nonzero().flatten().tolist()})
print("smoke std min", round(float(s.min()), 4), "outputs with no gradient", dead, "ok" if not dead and float(s.min()) >= 0.0999 else "STOP")
PY
python - "$SD" "$BASE" <<'PY' >> /tmp/lc100-smoke.txt
import re, sys
d, base = sys.argv[1], sys.argv[2]
env = open(f"{d}/params/env.yaml").read()
want = [("court_feed_prob", "1.0"), ("refeed_delay_s", "0.5"), ("recovery_mode", "fixed"), ("planner_mode", "'?off'?"),
        ("target_mode", "A"), ("obs_ball_pos_noise", "0.03"), ("obs_ball_vel_noise", "0.15"), ("pair_drill_court_frac", "0.5"),
        ("episode_length_s", "120.0"), ("pair_drill_reset", "true"), ("pair_reset_parks", "true"), ("backhand", "1.0"), ("reach_backhand", "1.0"), ("fast", "1.0"), ("lam_r", "2.0"),
        ("pair_rally_cap", "0"), ("pair_cut_prob", "0.0"), ("pair_launch_court_frac", "0.25")]
miss = [k for k, v in want if not re.search(rf"^\s*{k}: {v}\s*$", env, re.M)]
based = re.search(rf"^\s*base_checkpoint: {re.escape(base)}\s*$", env, re.M) is not None
terms = ("rally_fast_track_lin_vel" in env and "footwork_specialist.rally_recovery_reward" not in env and "return_stand.recovery_reward" in env
         and "return_stand.stance_progress" in env and "is_terminated" not in env and "launch_time_out" in env and "parked_ready" not in env and "ready_at_event" not in env and "restart_obs" not in env)
ok = not miss and based and terms
print(f"smoke config check: missing {miss}; d1 base {based}; fast move + stance_progress + launch_time_out, no fall term, no other new terms {terms} -> {'ok' if ok else 'STOP'}")
PY
python - artifacts/train/$RUN-smoke.log <<'PY' >> /tmp/lc100-smoke.txt
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
python - <<'PY' >> /tmp/lc100-smoke.txt
import json, os, sys
sys.path.insert(0, ".")
from picklebot_mj import d1_rule as dr
p = "results/lc100-smoke-share.jsonl"
rows = [json.loads(x) for x in open(p)] if os.path.exists(p) else []
ok_d, line = dr.dr_dose(rows, 34996)
print("smoke dose " + line + (" ok" if ok_d else " STOP"))
PY
cat /tmp/lc100-smoke.txt | tee -a $R-summary.txt
python - <<'PY' >> /tmp/lc100-smoke.txt
import json, os
p = "results/lc100-smoke-share.jsonl"
rows = [json.loads(x) for x in open(p)] if os.path.exists(p) else []
lc = rows[-1]["launch"].get("launch_courts", {}) if rows else {}
ok = lc.get("envs") == 256 and lc.get("episodes_falls", [0])[0] > 0
print(f"smoke launcher courts: {lc} (256 envs, episodes booked)" + (" ok" if ok else " STOP"))
PY
cat /tmp/lc100-smoke.txt | tail -1 | tee -a $R-summary.txt
python - "$SD" <<'PY' >> /tmp/lc100-smoke.txt
import json, os, re, sys
env = open(os.path.join(sys.argv[1], 'params', 'env.yaml')).read()
i = env.find('move_sector_weights:')
w = [float(x) for x in re.findall(r'^\s*- ([0-9.]+)\s*$', env[i:i + 400], re.M)[:8]] if i >= 0 else []
p = 'results/lc100-smoke-share.jsonl'
rows = [json.loads(x) for x in open(p)] if os.path.exists(p) else []
rows = [r for r in rows if r['launch'].get('move_issued')]
if len(rows) < 2 or w != [1.0, 1.0, 3.0, 3.0, 3.0, 1.0, 1.0, 1.0]:
    print(f'smoke sector check: weights {w}, rows {len(rows)} -> NO-DATA STOP')
else:
    d = [y - x for x, y in zip(rows[0]['launch']['move_issued'], rows[-1]['launch']['move_issued'])]
    s = sum(d[2:5]) / max(sum(d), 1)
    print(f'smoke sector share 2-4 (left, back-left, back) {s:.3f} of {sum(d)} spots (>= 0.45; per sector {d}) ' + ('ok' if s >= 0.45 else 'STOP'))
PY
cat /tmp/lc100-smoke.txt | tail -1 | tee -a $R-summary.txt
[ "$(grep -c " ok$" /tmp/lc100-smoke.txt)" = 8 ] || stop SMOKE-FAIL

# --- training with the +180 kill -----------------------------------------------------------------------------------------
if [ ! -f artifacts/train/$RUN.exit.json ]; then
  ( python - <<'PY' > $R-kill.txt 2>&1
import glob, json, os, re, subprocess, sys, time
sys.path.insert(0, ".")
from picklebot_mj import d1_rule as dr
run, START, MSTART = "rally-d1s3drl5", 34996, 33797
EXIT, SHARE = f"artifacts/train/{run}.exit.json", "results/lc100-train-share.jsonl"
rd = lambda p: [json.loads(x) for x in open(p)] if os.path.exists(p) else []  # noqa: E731
CKN = (START + 180 + 39) // 40 * 40
ck = None
while ck is None:
    if os.path.exists(EXIT):
        print("training ended before the +180 check"); sys.exit(0)
    time.sleep(60)
    rows = rd(SHARE)
    c = glob.glob(f"artifacts/train/logs/picklebot_return_stand/*_{run}/model_{CKN}.pt")
    if c and rows and rows[-1]["step"] >= (START + 180) * dr.STEPS_PER_IT:
        ck = c[0]
rows, mrows = rd(SHARE), rd("results/lc98-train-share.jsonl")
v = []
c, nc = dr.pair_rally(rows, 61, 180, START)
p, npar = dr.pair_rally(mrows, 1080, 1199, MSTART)
if c != c or p != p or min(nc, npar) < dr.MIN_WINDOW_EVENTS:
    v.append("NO-DATA"); print(f"KILL-NO-HIT: {c} (n {nc}) vs M {p} (n {npar}) -> NO-DATA", flush=True)
else:
    x = "CONTINUE" if c >= dr.HIT_RATIO * p - 1e-9 else "KILL-NO-HIT"
    v.append(x); print(f"KILL-NO-HIT: pair-court mean rally length +61-180 {c:.3f} vs M's last 120 iterations {p:.3f} (>= {dr.HIT_RATIO} x; n {nc} / {npar}) -> {x}", flush=True)
f = dr.exact_falls(rows, 61, 180, START) / (12288 - 3072)
x = "NO-DATA" if f != f else ("CONTINUE" if f <= dr.EXACT_FALLS_MAX else "KILL-UNSTABLE")
v.append(x); print(f"KILL-UNSTABLE: exact falls off the launcher courts {f:.3f} per 1,000 env-s (<= {dr.EXACT_FALLS_MAX}) -> {x}", flush=True)
e, l = dr.train_open(mrows, 1080, 1199, MSTART), dr.train_open(rows, 61, 180, START)
if e is None or l is None or min(e["n"], l["n"]) < dr.OPEN_MIN_RALLIES:
    v.append("NO-DATA"); print("KILL-LOST-OPEN: not readable -> NO-DATA", flush=True)
else:
    x = "CONTINUE" if l["open2"] >= e["open2"] - dr.OPEN_KEEP - 1e-9 else "KILL-LOST-OPEN"
    v.append(x); print(f"KILL-LOST-OPEN: training (1-h0)(1-h1) M's last window {e['open2']:.4f} -> {l['open2']:.4f} (+61-180) (>= -{dr.OPEN_KEEP}; n {e['n']} / {l['n']}) -> {x}", flush=True)
envy = open(os.path.join(os.path.dirname(ck), "params", "env.yaml")).read()
i = envy.find("move_sector_weights:")
w = [float(y) for y in re.findall(r"^\s*- ([0-9.]+)\s*$", envy[i:i + 400], re.M)[:8]] if i >= 0 else []
cfg_ok = (re.search(r"^\s*pair_launch_court_frac: 0.25\s*$", envy, re.M) is not None and "launch_time_out" in envy
          and "is_terminated" not in envy and w == [1.0, 1.0, 3.0, 3.0, 3.0, 1.0, 1.0, 1.0])
v.append("CONTINUE" if cfg_ok else "KILL-CONFIG"); print(f"config: launcher courts, launch_time_out, no fall term, sector weights {w} -> {cfg_ok}", flush=True)
env = dict(os.environ, PICKLEBOT_RES_BASE=os.environ["KILL_BASE"], PICKLEBOT_LAM_R="2")
CT = ("--task Picklebot-Latent-Court-Res-G1 --envs 2048 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every "
      "--target A --no-hint --recovery random --seed 4220402").split()
subprocess.run(["python", "scripts/stage2_eval.py", "--checkpoint", ck] + CT + ["--json", "results/lc100-kill-court.json"], env=env,
               stdout=open("results/lc100-kill-court.log", "w"), stderr=subprocess.STDOUT)
try:
    r3 = json.load(open("results/lc100-kill-court.json"))["robot_fall_rate_per_episode"]
    x = "CONTINUE" if r3 <= dr.R3_MAX else "KILL-NO-FALLS"
    v.append(x); print(f"KILL-NO-FALLS: +180 court falls per episode {r3:.4f} on dev 4220402 (<= {dr.R3_MAX}) -> {x}", flush=True)
except Exception as ex:  # noqa: BLE001
    v.append("NO-DATA"); print(f"KILL-NO-FALLS: not read ({ex}) -> NO-DATA", flush=True)
subprocess.run(["python", "scripts/diag/feeder_speed_envelope.py", "--checkpoint", ck, "--seed", "4220402", "--json",
                "results/lc100-kill-dir.json"], env=env, stdout=open("results/lc100-kill-dir.log", "w"), stderr=subprocess.STDOUT)
def lb(p):
    dd = json.load(open(p))["directions"]
    n = dd["left"]["feeds"] + dd["back"]["feeds"]
    return (dd["left"]["feeds"] * dd["left"]["contact"] + dd["back"]["feeds"] * dd["back"]["contact"]) / max(n, 1), n
try:
    (a, na), (bm, nb) = lb("results/lc100-kill-dir.json"), lb("results/lc99-dirM-4220402.json")
    x = "CONTINUE" if a >= bm - 0.01 - 1e-9 else "KILL-DIR"
    dn, dm = json.load(open("results/lc100-kill-dir.json"))["directions"]["right"], json.load(open("results/lc99-dirM-4220402.json"))["directions"]["right"]
    print(f"(reported) right feeder contact +180 {dn['contact']:.4f} (n {dn['feeds']}) vs M {dm['contact']:.4f} (n {dm['feeds']})", flush=True)
    v.append(x); print(f"KILL-DIR: left + back feeder contact +180 {a:.4f} (n {na}) vs M {bm:.4f} (n {nb}) on dev 4220402 (>= -0.01) -> {x}", flush=True)
except Exception as ex:  # noqa: BLE001
    v.append("NO-DATA"); print(f"KILL-DIR: not read ({ex}) -> NO-DATA", flush=True)
if any(y.startswith("KILL") or y == "NO-DATA" for y in v):
    os.system(f"pkill -f 'run-name {run} '")
PY
  ) &
  env $TRAINENV PICKLEBOT_RES_BASE=$BASE PICKLEBOT_PAIR_LOG=$R-train-share.jsonl PICKLEBOT_PAIR_LOG_EVERY=480 PICKLEBOT_SCHED_LOG=$R-train.jsonl \
    PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=14400 bash scripts/diag/agility_train_run.sh $RUN $T \
    --agent.seed 238 --agent.max-iterations 600 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG $OV $EP --agent.save-interval 40
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
CT="--task Picklebot-Latent-Court-Res-G1 --envs 2048 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --recovery random --seed 4220403"
[ -s $R-court-N.json ] || onbase python scripts/stage2_eval.py --checkpoint $CKR $CT --json $R-court-N.json >> $R-reads.log 2>&1
[ -s $R-court-M-4220403.json ] || onbase python scripts/stage2_eval.py --checkpoint $PR $CT --json $R-court-M-4220403.json >> $R-reads.log 2>&1
python - <<'PY' | tee -a $R-summary.txt
import json, os, sys
sys.path.insert(0, "scripts"); sys.path.insert(0, ".")
import rally_check as rc
from picklebot_mj import d1_rule as dr
R, RC = "results/lc100", "results/d1s3ctl"
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
R = "results/lc100"
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

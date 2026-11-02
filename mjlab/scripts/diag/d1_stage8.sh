#!/usr/bin/env bash
# D-205 d1s8 (panel round 69, 5 of 5 for (a); diag68 routed STATE): the parent d1s3 child (rally-d1s3 model_31399, d1
# base) trained 1,200 iterations on Picklebot-Rally22b-FastMove-IdleRec-G1 = d1s3's task with one change, recovery_reward
# also paying while parked on a pair court and not busy (distance only, std 1.5, weight 1.0). D-203 settings; training
# seed 199, smoke 200. Control: rally-d1s3ctlb (D-204 (iii), seed 197, same parent and settings, no change); it must
# have finished unkilled, else CONTROL-UNAVAILABLE -> panel. Waits for D-204's driver (artifacts/train/diag68.done).
# Kill at +360: D-194's lines; KILL-FARM; KILL-NO-CLIMB (d1_rule.s8_climb_kill); KILL-SLOWED / KILL-NO-ARRIVE.
# Endpoint (d1_rule.s8_lines / s8_verdict): LR-0 split reads at 0.5 s on dev 4220332 + 4220337 summed for the child and
# the control (the parent's are diag68's); guards pooled over pairs 4220306/328/329/331 and direction
# 4220307/334/335/336 (the parent's and the control's are D-204's); P5-KEPT on 4220306.
# Verdicts: KILL -> INVALID -> NO-DOSE -> NO-HAZARD -> GUARD-BREACH -> P5-LOSS -> REC-PASS.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER PICKLEBOT_READY_LOG \
  PICKLEBOT_RESTART_OBS PICKLEBOT_RESTART_OBS_FREEZE
while [ ! -f artifacts/train/diag68.done ]; do sleep 60; done
sleep 30
pgrep -f "run-name |kickstart_h4|stage2_eval|footwork_eval|feeder_speed" > /dev/null && { echo "GPU busy: not started"; exit 1; }
RUN=rally-d1s8; L=artifacts/train/logs/picklebot_return_stand; R=results/d1s8; RC=results/d1s3ctl; TAG=d1s8
BASE=/mnt/f/dev/picklebot-mjlab/mjlab/$L/2026-10-31_18-24-20_s5c-d1-fw1bS/model_32854.pt
PRUN=2026-11-01_12-07-09_rally-d1s3; PCK=model_31399.pt; P=$L/$PRUN/$PCK
T=Picklebot-Rally22b-FastMove-IdleRec-G1; TF=Picklebot-Agility-BallIdx-Feeder-ReadCfg-LamR2-G1
for f in $BASE $P; do [ -f $f ] || { echo "missing $f"; exit 1; }; done
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
B=--env.actions.ball; OV="$B.court-feed-prob 1.0 $B.refeed-delay-s 0.5 $B.recovery-mode fixed $B.planner-mode off $B.target-mode A"
for f in backhand reach-backhand cross-backhand fast drop low reach-deep short high reach-forehand; do OV="$OV $B.feed-mix.weights.$f 1.0"; done
TRAINENV="PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_STD_MIN=0.1 PICKLEBOT_LR_PEAK=1e-4 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_KL_GUARD=0.05 PICKLEBOT_LR_TOTAL=0"
export PICKLEBOT_TRAIN_ENTRY=scripts/diag/footwork_train.py
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120"
onbase() { PICKLEBOT_RES_BASE=$BASE PICKLEBOT_LAM_R=2 "$@"; }
stop() { echo "VERDICT: $1" | tee -a $R-summary.txt; echo done > artifacts/train/d1s8.done; exit 0; }
[ -s $R-summary.txt ] || echo "parent $P on the d1 base $BASE; task $T (recovery also paid while parked, std 1.5, weight 1)" > $R-summary.txt
# the control must be in
CTL=$(python -c "import json; print(json.load(open('$RC-summary.json'))['verdict'])" 2>/dev/null || echo none)
grep -q '"exit_code": 0' artifacts/train/rally-d1s3ctlb.exit.json 2>/dev/null && ! grep -q "KILL-" $RC-kill.txt || stop CONTROL-UNAVAILABLE
echo "control rally-d1s3ctlb: D-204 (iii) verdict $CTL" | tee -a $R-summary.txt
CD=$(ls -d $L/*_rally-d1s3ctlb | tail -1); CC=$CD/model_32598.pt; [ -f $CC ] || stop CONTROL-UNAVAILABLE
split() {  # name, run dir, checkpoint, seed: the LR-0 split tally at 0.5 s
  [ -s $R-split-$1.jsonl ] && return 0
  rm -f $R-split-$1.jsonl
  env PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_LR_PEAK=0 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_LR_TOTAL=0 PICKLEBOT_STD_MIN=0.1 PICKLEBOT_BALLIDX_LOG_EVERY=240 \
    PICKLEBOT_RES_BASE=$BASE PICKLEBOT_BALLIDX_LOG=$R-split-$1.jsonl PICKLEBOT_ENVS=4096 PICKLEBOT_WALL_CAP=2700 PICKLEBOT_TRAIN_ENTRY=scripts/diag/agility_train.py \
    bash scripts/diag/agility_train_run.sh d1s8-split-$1 $TF --agent.seed $4 --agent.max-iterations 200 --agent.resume True \
    --agent.load-run $2 --agent.load-checkpoint $3 $ALG $OV >> $R-reads.log 2>&1
}
# smoke
if [ ! -f artifacts/train/$RUN-smoke.exit.json ]; then
  env $TRAINENV PICKLEBOT_RES_BASE=$BASE PICKLEBOT_SCHED_LOG=$R-smoke.jsonl PICKLEBOT_READY_LOG=$R-smoke-idlerec.jsonl PICKLEBOT_ENVS=1024 \
    PICKLEBOT_WALL_CAP=900 bash scripts/diag/agility_train_run.sh $RUN-smoke $T --agent.seed 200 --agent.max-iterations 40 --agent.resume True \
    --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG $OV --agent.save-interval 40
fi
SD=$(ls -d $L/*_$RUN-smoke | tail -1)
{ grep -q '"exit_code": 0' artifacts/train/$RUN-smoke.exit.json && echo "smoke exit 0 ok" || echo "smoke exit STOP"; } | tee /tmp/d1s8-smoke.txt
{ grep -a -q -E "Traceback|Error" artifacts/train/$RUN-smoke.log && echo "smoke traceback STOP" || echo "smoke no traceback ok"; } | tee -a /tmp/d1s8-smoke.txt
python scripts/diag/falls_by_length.py artifacts/train/$RUN-smoke.log | awk '{r=$NF; print "smoke falls per 1,000 env-seconds", r, (r <= 4.157 ? "ok" : "STOP")}' | tee -a /tmp/d1s8-smoke.txt
CUDA_VISIBLE_DEVICES= python - "$(ls $SD/model_*.pt | sort -V | tail -1)" <<'PY' | tee -a /tmp/d1s8-smoke.txt
import sys, torch
sd = torch.load(sys.argv[1], map_location="cpu", weights_only=False)
s = sd["actor_state_dict"]["distribution.std_param"]
dead = sorted({i for v in sd["optimizer_state_dict"]["state"].values() if v["exp_avg_sq"].shape == s.shape
               for i in (v["exp_avg_sq"] == 0).nonzero().flatten().tolist()})
print("smoke std min", round(float(s.min()), 4), "outputs with no gradient", dead, "ok" if not dead and float(s.min()) >= 0.0999 else "STOP")
PY
python - "$SD" "$BASE" <<'PY' | tee -a /tmp/d1s8-smoke.txt
import re, sys
d, base = sys.argv[1], sys.argv[2]
env = open(f"{d}/params/env.yaml").read()
want = [("court_feed_prob", "1.0"), ("refeed_delay_s", "0.5"), ("recovery_mode", "fixed"), ("planner_mode", "'?off'?"),
        ("target_mode", "A"), ("obs_ball_pos_noise", "0.03"), ("obs_ball_vel_noise", "0.15"), ("pair_drill_court_frac", "0.5"),
        ("episode_length_s", "120.0"), ("backhand", "1.0"), ("reach_backhand", "1.0"), ("fast", "1.0"), ("lam_r", "2.0"),
        ("pair_rally_cap", "0")]
miss = [k for k, v in want if not re.search(rf"^\s*{k}: {v}\s*$", env, re.M)]
based = re.search(rf"^\s*base_checkpoint: {re.escape(base)}\s*$", env, re.M) is not None
terms = ("rally_fast_track_lin_vel" in env and "footwork_specialist.rally_recovery_reward" in env and "return_stand.recovery_reward" not in env
         and "parked_ready" not in env and "ready_at_event" not in env and "restart_obs" not in env)
ok = not miss and based and terms
print(f"smoke config check: missing {miss}; d1 base {based}; fast move + idle recovery, no other new terms {terms} -> {'ok' if ok else 'STOP'}")
PY
python - artifacts/train/$RUN-smoke.log <<'PY' | tee -a /tmp/d1s8-smoke.txt
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
cat /tmp/d1s8-smoke.txt >> $R-summary.txt
[ "$(grep -c " ok$" /tmp/d1s8-smoke.txt)" = 5 ] || stop SMOKE-FAIL
# training with the +360 kill
if [ ! -f artifacts/train/$RUN.exit.json ]; then
  ( python scripts/diag/d1s8_watch.py "$BASE" > $R-kill.txt 2>&1 ) &
  env $TRAINENV PICKLEBOT_RES_BASE=$BASE PICKLEBOT_PAIR_LOG=$R-train-share.jsonl PICKLEBOT_SCHED_LOG=$R-train.jsonl \
    PICKLEBOT_READY_LOG=$R-train-idlerec.jsonl PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=14400 bash scripts/diag/agility_train_run.sh $RUN $T \
    --agent.seed 199 --agent.max-iterations 1200 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG $OV --agent.save-interval 40
  wait
fi
echo "training: $(cat artifacts/train/$RUN.exit.json)" | tee -a $R-summary.txt; cat $R-kill.txt | tee -a $R-summary.txt
grep -q "KILL-" $R-kill.txt && stop "KILL ($(grep -o 'KILL-[A-Z-]*' $R-kill.txt | head -1))"
grep -q '"exit_code": 0' artifacts/train/$RUN.exit.json || stop TRAIN-FAIL
D=$(ls -d $L/*_$RUN | tail -1); CK=$(ls $D/model_*.pt | sort -V | tail -1); echo "endpoint $CK" | tee -a $R-summary.txt
[ "$(basename $CK)" = model_32598.pt ] || stop "ENDPOINT-MISMATCH-$(basename $CK)"
split child-a $(basename $D) $(basename $CK) 4220332
split child-b $(basename $D) $(basename $CK) 4220337
split control-a $(basename $CD) model_32598.pt 4220332
split control-b $(basename $CD) model_32598.pt 4220337
for s in 4220306 4220328 4220329 4220331; do
  [ -s $R-child-pairs-$s.json ] || onbase python scripts/stage2_eval.py --checkpoint $CK $PA --seed $s --json $R-child-pairs-$s.json >> $R-reads.log 2>&1
done
for s in 4220307 4220334 4220335 4220336; do
  [ -s $R-child-dir-$s.json ] || onbase python scripts/diag/feeder_speed_envelope.py --checkpoint $CK --seed $s --json $R-child-dir-$s.json >> $R-reads.log 2>&1
done
python - <<'PY' | tee -a $R-summary.txt
import glob, json, os, sys
sys.path.insert(0, "scripts")
import rally_check as rc
from picklebot_mj import agility_rule as ar, d1_rule as dr
R, RC = "results/d1s8", "results/d1s3ctl"
need = [f"{R}-split-{a}.jsonl" for a in ("child-a", "child-b", "control-a", "control-b")]
need += [f"{R}-child-pairs-{s}.json" for s in (4220306, 4220328, 4220329, 4220331)]
need += [f"{R}-child-dir-{s}.json" for s in (4220307, 4220334, 4220335, 4220336)]
miss = [f for f in need if not os.path.exists(f) or not os.path.getsize(f)]
if miss:
    print(f"VERDICT: EVAL-FAIL {miss}"); sys.exit(0)
win = lambda p: ar.window(ar.read_rows(p), "ballidx", 0.5, 1.0)  # noqa: E731
st = {"parent": dr.k1_state(dr.sum_counters(win("results/diag68-r05.jsonl"), win("results/diag68-r05b.jsonl"))),
      "control": dr.k1_state(dr.sum_counters(win(f"{R}-split-control-a.jsonl"), win(f"{R}-split-control-b.jsonl"))),
      "child": dr.k1_state(dr.sum_counters(win(f"{R}-split-child-a.jsonl"), win(f"{R}-split-child-b.jsonl")))}
for k, v in st.items():
    print(f"k=1 state {k}: recover_dist p50 {v['recover_dist']}, pelvis speed p50 {v['pelvis_speed']}, k=1 n {v['k1_n']}, "
          f"k=1 failure {v['k1_fail']}, k>=3 failure {v['k3_fail']}")
L = dr.s8_lines(st["child"], st["parent"], st["control"])
print(f"INVALID {L['invalid']}; DOSE (recover_dist <= parent and control - {dr.S8_DOSE_D}) {L['dose']}; "
      f"HAZARD (k=1 failure <= parent and control - {dr.S8_HAZ}, k>=3 <= parent + {dr.S8_K3}) {L['hazard']}")
pf, pd = dr.pool_reads(sorted(glob.glob(f"{R}-child-pairs-*.json")), sorted(glob.glob(f"{R}-child-dir-*.json")))
print("GUARDS: the child (pooled) against the parent (pooled):")
guards = rc.r19_guards(pf["per_family"], pd["directions"], ref=f"{RC}-parent-pooled", cross_ref=f"{RC}-parent-pooled-pairs.json",
                       name="parent pooled", cross_name="parent pooled")
print("reported, attribution: the child (pooled) against the control (pooled):")
rc.r19_guards(pf["per_family"], pd["directions"], ref=f"{RC}-control-pooled", cross_ref=f"{RC}-control-pooled-pairs.json",
              name="control pooled", cross_name="control pooled")
pp = json.load(open("results/d1s7-parent-pairs.json"))["pairs"]
cp = json.load(open(f"{R}-child-pairs-4220306.json"))["pairs"]
p5c, p5p = rc.p5_open(cp)[0], rc.p5_open(pp)[0]
p5k = p5c >= p5p - 0.01
print(f"P5-KEPT: {p5c:.4f} vs parent {p5p:.4f} -> {p5k}")
print("F-UP vs parent (reported): " + dr.f_up(cp, pp)[1])
for name, p in (("parent", pp), ("control", json.load(open(f"{RC}-control-pairs-4220306.json"))["pairs"]), ("child", cp)):
    print(f"{name} on 4220306: P(5+) open {rc.p5_open(p)[0]:.4f}; feeder {rc.boot_low(p['court_counts'], 3, 2)[0]:.4f}; "
          f"failure by shot position " + ", ".join(f"{x:.3f}" for x in dr.open_hazards(p)))
v = dr.s8_verdict(L["invalid"], L["dose"], L["hazard"], guards, p5k)
json.dump({"verdict": v, **L, "guards": guards, "p5_kept": p5k, "state": st}, open(f"{R}-summary.json", "w"), indent=1)
print(f"VERDICT: {v}")
PY
echo done > artifacts/train/d1s8.done

#!/usr/bin/env bash
# D-199 d1s4 (D-198 FEED-STATE; panel round 64): the parent d1s3 child (rally-d1s3 model_31399, on the d1 base) trained
# 1,200 iterations on Picklebot-Rally22b-FastMove-Ready-G1 = d1s3's task + ready_at_event (the one change). Everything
# else as d1s3: ScheduledPPO 1e-4 constant, KL 0.05, std floor 0.1, warm-up 0, 12,288 envs; training seed 191, smoke 192.
# Reads (parent re-read on every seed; picklebot_mj/d1_rule.py stage-4 functions):
#   pairs 4220306 (P, child; 22b reported), direction 4220307, Measure60 4220308, +360 Measure60 4220309 (P reference),
#   h5f battery 4220310-4220325 (P, child), dose read 4220326 (LR-0 feeder tally, P and child), refeed 3 s pairs 4220327
#   (P, child; reported).
# Kill at +360: D-194 training-log lines; KILL-SLOWED / KILL-NO-ARRIVE against P's Measure60 on 4220309 (D-196 lines);
#   KILL-NO-DOSE (per-event ready mean); KILL-EVENTS (feeder fires vs d1s3's own run, iterations 100-300).
# Endpoint: F-UP (feeder legal >= P + 0.05, bootstrap low above P); ABS-F (>= 0.80, required for READY-PASS); rally =
#   d1s2-gate against P; AGILE-KEPT against P; K3-KEPT; DOSE (k = 0 pelvis-speed p50 at the fire <= P - 0.05).
#   If F-UP: the control (d1s3 continued 1,200 iterations on Rally22b-FastMove, no term, training seed 191) on the same
#   pairs and dose seeds; F-UP against it too, else READY-TIME.
# Verdict precedence: KILL -> INVALID -> NO-DOSE -> READY-TIME -> READY-PASS -> READY-F -> READY-FAIL.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER
pgrep -f "run-name |kickstart_h4|stage2_eval|footwork_eval|feeder_speed" > /dev/null && { echo "GPU busy: not started"; exit 1; }
RUN=rally-d1s4; CTRL=rally-d1s4ctl; L=artifacts/train/logs/picklebot_return_stand; R=results/d1s4; TAG=d1s4
BASE=/mnt/f/dev/picklebot-mjlab/mjlab/$L/2026-10-31_18-24-20_s5c-d1-fw1bS/model_32854.pt
PRUN=2026-11-01_12-07-09_rally-d1s3; PCK=model_31399.pt; P=$L/$PRUN/$PCK; START=31399
P22=$L/2026-10-29_16-41-45_rally-22b-readcfg/model_30200.pt
T=Picklebot-Rally22b-FastMove-Ready-G1; TC=Picklebot-Rally22b-FastMove-G1; TF=Picklebot-Agility-BallIdx-Feeder-ReadCfg-LamR2-G1
for f in $BASE $P $P22; do [ -f $f ] || { echo "missing $f"; exit 1; }; done
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
B=--env.actions.ball; OV="$B.court-feed-prob 1.0 $B.refeed-delay-s 0.5 $B.recovery-mode fixed $B.planner-mode off $B.target-mode A"
for f in backhand reach-backhand cross-backhand fast drop low reach-deep short high reach-forehand; do OV="$OV $B.feed-mix.weights.$f 1.0"; done
TRAINENV="PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_STD_MIN=0.1 PICKLEBOT_LR_PEAK=1e-4 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_KL_GUARD=0.05 PICKLEBOT_LR_TOTAL=0"
export PICKLEBOT_TRAIN_ENTRY=scripts/diag/footwork_train.py
stop() { echo "VERDICT: $1" | tee -a $R-summary.txt; echo done > artifacts/train/d1s4.done; exit 0; }
[ -s $R-summary.txt ] || echo "parent $P on the d1 base $BASE" > $R-summary.txt
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120"
FW="--task Picklebot-Footwork-Measure60-RallyLamR2-G1 --envs 1024 --seconds 120 --move-prob 1.0"
onbase() { PICKLEBOT_RES_BASE=$BASE PICKLEBOT_LAM_R=2 "$@"; }
reads() {  # checkpoint, prefix (on the d1 base): pairs / dir / fw / refeed-3 s pairs
  [ -s $2-pairs.json ] || onbase python scripts/stage2_eval.py --checkpoint $1 $PA --seed 4220306 --json $2-pairs.json >> $R-reads.log 2>&1
  [ -s $2-dir.json ] || onbase python scripts/diag/feeder_speed_envelope.py --checkpoint $1 --seed 4220307 --json $2-dir.json >> $R-reads.log 2>&1
  [ -s $2-fw.json ] || PICKLEBOT_RES_BASE=$BASE python scripts/diag/footwork_eval.py --checkpoint $1 $FW --seed 4220308 --json $2-fw.json >> $R-reads.log 2>&1
  [ -s $2-refeed3.json ] || onbase python scripts/stage2_eval.py --checkpoint $1 $PA --refeed-delay 3.0 --seed 4220327 --json $2-refeed3.json >> $R-reads.log 2>&1
}
dose() {  # name, run dir, checkpoint: LR-0 feeder-tally read on dev 4220326 (the d1 base)
  [ -s $R-dose-$1.jsonl ] && return 0
  env PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_LR_PEAK=0 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_LR_TOTAL=0 PICKLEBOT_STD_MIN=0.1 PICKLEBOT_BALLIDX_LOG_EVERY=240 \
    PICKLEBOT_RES_BASE=$BASE PICKLEBOT_BALLIDX_LOG=$R-dose-$1.jsonl PICKLEBOT_ENVS=4096 PICKLEBOT_WALL_CAP=2700 PICKLEBOT_TRAIN_ENTRY=scripts/diag/agility_train.py \
    bash scripts/diag/agility_train_run.sh d1s4-dose-$1 $TF --agent.seed 4220326 --agent.max-iterations 200 --agent.resume True \
    --agent.load-run $2 --agent.load-checkpoint $3 $ALG $OV >> $R-reads.log 2>&1
}
# pre-training: the parent on every seed; 22b pairs (reported)
reads $P $R-parent
[ -s $R-killref-parent-fw.json ] || PICKLEBOT_RES_BASE=$BASE python scripts/diag/footwork_eval.py --checkpoint $P $FW --seed 4220309 --json $R-killref-parent-fw.json >> $R-reads.log 2>&1
[ -s $R-p22b-pairs.json ] || PICKLEBOT_LAM_R=2 python scripts/stage2_eval.py --checkpoint $P22 $PA --seed 4220306 --json $R-p22b-pairs.json >> $R-reads.log 2>&1
[ -s results/stage5f-$TAG-p-summary.json ] || onbase bash scripts/h5f_clean_eval.sh rally-d1s3 $PCK $TAG-p 4220310 > $R-h5f-p.log 2>&1
dose parent $PRUN $PCK
for f in parent-pairs parent-dir parent-fw parent-refeed3 killref-parent-fw p22b-pairs; do [ -s $R-$f.json ] || stop EVAL-FAIL-$f; done
[ -s results/stage5f-$TAG-p-summary.json ] || stop EVAL-FAIL-h5f-p
[ -s $R-dose-parent.jsonl ] || stop EVAL-FAIL-dose-parent
cp -n $R-parent-pairs.json $R-parent-early-pairs.json; cp -n $R-parent-dir.json $R-parent-early-dir.json
# smoke (d1s3's checks + the ready term present + ready log written)
if [ ! -f artifacts/train/$RUN-smoke.exit.json ]; then
  env $TRAINENV PICKLEBOT_RES_BASE=$BASE PICKLEBOT_READY_LOG=/tmp/d1s4-smoke-ready.jsonl PICKLEBOT_SCHED_LOG=$R-smoke.jsonl PICKLEBOT_ENVS=1024 PICKLEBOT_WALL_CAP=900 \
    bash scripts/diag/agility_train_run.sh $RUN-smoke $T --agent.seed 192 --agent.max-iterations 40 --agent.resume True --agent.load-run $PRUN \
    --agent.load-checkpoint $PCK $ALG $OV --agent.save-interval 40
fi
SD=$(ls -d $L/*_$RUN-smoke | tail -1)
{ grep -q '"exit_code": 0' artifacts/train/$RUN-smoke.exit.json && echo "smoke exit 0 ok" || echo "smoke exit STOP"; } | tee /tmp/d1s4-smoke.txt
{ grep -a -q -E "Traceback|Error" artifacts/train/$RUN-smoke.log && echo "smoke traceback STOP" || echo "smoke no traceback ok"; } | tee -a /tmp/d1s4-smoke.txt
python scripts/diag/falls_by_length.py artifacts/train/$RUN-smoke.log | awk '{r=$NF; print "smoke falls per 1,000 env-seconds", r, (r <= 4.157 ? "ok" : "STOP")}' | tee -a /tmp/d1s4-smoke.txt
CUDA_VISIBLE_DEVICES= python - "$(ls $SD/model_*.pt | sort -V | tail -1)" <<'PY' | tee -a /tmp/d1s4-smoke.txt
import sys, torch
sd = torch.load(sys.argv[1], map_location="cpu", weights_only=False)
s = sd["actor_state_dict"]["distribution.std_param"]
dead = sorted({i for v in sd["optimizer_state_dict"]["state"].values() if v["exp_avg_sq"].shape == s.shape
               for i in (v["exp_avg_sq"] == 0).nonzero().flatten().tolist()})
print("smoke std min", round(float(s.min()), 4), "outputs with no gradient", dead, "ok" if not dead and float(s.min()) >= 0.0999 else "STOP")
PY
python - "$SD" "$BASE" <<'PY' | tee -a /tmp/d1s4-smoke.txt
import json, re, sys
d, base = sys.argv[1], sys.argv[2]
env, agent = open(f"{d}/params/env.yaml").read(), open(f"{d}/params/agent.yaml").read()
want = [("court_feed_prob", "1.0"), ("refeed_delay_s", "0.5"), ("recovery_mode", "fixed"), ("planner_mode", "'?off'?"),
        ("target_mode", "A"), ("obs_ball_pos_noise", "0.03"), ("obs_ball_vel_noise", "0.15"), ("pair_drill_court_frac", "0.5"),
        ("episode_length_s", "120.0"), ("backhand", "1.0"), ("reach_backhand", "1.0"), ("fast", "1.0"), ("lam_r", "2.0")]
miss = [k for k, v in want if not re.search(rf"^\s*{k}: {v}\s*$", env, re.M)]
based = re.search(rf"^\s*base_checkpoint: {re.escape(base)}\s*$", env, re.M) is not None
terms = "rally_fast_track_lin_vel" in env and "ready_at_event" in env
rows = [json.loads(l) for l in open("/tmp/d1s4-smoke-ready.jsonl")] if __import__("os").path.exists("/tmp/d1s4-smoke-ready.jsonl") else []
paid = rows[-1]["ready"][1] if rows else 0
ok = not miss and based and terms and paid > 0
print(f"smoke config check: missing {miss}; d1 base {based}; fast move + ready terms {terms}; ready events paid {paid} -> {'ok' if ok else 'STOP'}")
PY
cat /tmp/d1s4-smoke.txt >> $R-summary.txt
[ "$(grep -c " ok$" /tmp/d1s4-smoke.txt)" = 5 ] || stop SMOKE-FAIL
# training with the +360 kill
if [ ! -f artifacts/train/$RUN.exit.json ]; then
  ( python - "$BASE" <<'PY' > $R-kill.txt 2>&1
import glob, json, os, subprocess, sys, time
from picklebot_mj import d1_rule as dr
base = sys.argv[1]
LOG, EXIT, L = "artifacts/train/rally-d1s4.log", "artifacts/train/rally-d1s4.exit.json", "artifacts/train/logs/picklebot_return_stand"
rd = lambda p: [json.loads(l) for l in open(p)] if os.path.exists(p) else []  # noqa: E731
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
kills = [k[0]]
v, line = dr.s4_dose_kill(rd("results/d1s4-ready.jsonl")); print(line, flush=True); kills.append(v)
v, line = dr.s4_events_kill(rd("results/d1s4-train-share.jsonl"), rd("results/d1s3-train-share.jsonl")); print(line, flush=True); kills.append(v)
if any(x != "CONTINUE" for x in kills):
    os.system("pkill -f 'run-name rally-d1s4 '"); sys.exit(0)
ck = None
while ck is None:
    c = glob.glob(f"{L}/*_rally-d1s4/model_31760.pt")
    ck = c[0] if c else None
    if ck is None and os.path.exists(EXIT):
        print("no +360 checkpoint"); sys.exit(0)
    time.sleep(30)
time.sleep(30)
r = subprocess.run(["python", "scripts/diag/footwork_eval.py", "--checkpoint", ck, "--task", "Picklebot-Footwork-Measure60-RallyLamR2-G1",
                    "--envs", "1024", "--seconds", "120", "--move-prob", "1.0", "--seed", "4220309", "--json", "results/d1s4-kill-fw.json"],
                   env=dict(os.environ, PICKLEBOT_RES_BASE=base), capture_output=True, text=True)
if r.returncode != 0:
    print("KILL READ CRASHED (no kill)"); sys.exit(0)
v, line = dr.s3_speed_kill(json.load(open("results/d1s4-kill-fw.json")), json.load(open("results/d1s4-killref-parent-fw.json")))
print("+360 " + line.replace(" vs Z ", " vs parent ").replace("x Z", "x parent").replace("Z -", "parent -"))
if v != "CONTINUE":
    os.system("pkill -f 'run-name rally-d1s4 '")
PY
  ) &
  env $TRAINENV PICKLEBOT_RES_BASE=$BASE PICKLEBOT_READY_LOG=$R-ready.jsonl PICKLEBOT_PAIR_LOG=$R-train-share.jsonl PICKLEBOT_SCHED_LOG=$R-train.jsonl \
    PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=14400 bash scripts/diag/agility_train_run.sh $RUN $T --agent.seed 191 --agent.max-iterations 1200 \
    --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG $OV --agent.save-interval 40
  wait
fi
echo "training: $(cat artifacts/train/$RUN.exit.json)" | tee -a $R-summary.txt; cat $R-kill.txt | tee -a $R-summary.txt
grep -q "KILL-" $R-kill.txt && stop "KILL ($(grep -o 'KILL-[A-Z-]*' $R-kill.txt | head -1))"
grep -q '"exit_code": 0' artifacts/train/$RUN.exit.json || stop TRAIN-FAIL
D=$(ls -d $L/*_$RUN | tail -1); CK=$(ls $D/model_*.pt | sort -V | tail -1); echo "endpoint $CK" | tee -a $R-summary.txt
[ "$(basename $CK)" = model_32598.pt ] || stop "ENDPOINT-MISMATCH-$(basename $CK)"
reads $CK $R-child
[ -s results/stage5f-$TAG-summary.json ] || onbase bash scripts/h5f_clean_eval.sh $RUN $(basename $CK) $TAG 4220310 > $R-h5f.log 2>&1
dose child $(basename $D) $(basename $CK)
for f in child-pairs child-dir child-fw; do [ -s $R-$f.json ] || stop EVAL-FAIL-$f; done
[ -s results/stage5f-$TAG-summary.json ] || stop EVAL-FAIL-h5f
[ -s $R-dose-child.jsonl ] || stop EVAL-FAIL-dose-child
cp -n $R-child-pairs.json $R-target.json; cp -n $R-child-dir.json $R-endpoint-dir.json
python scripts/rally_check.py d1s2-gate $R $TAG | tee -a $R-summary.txt; RALLY=${PIPESTATUS[0]}
[ "$RALLY" = 0 ] || [ "$RALLY" = 1 ] || stop "GATE-CRASH-$RALLY"
# control arm, only if the child is F-UP against the parent
FUP=$(python -c "import json; from picklebot_mj import d1_rule as dr; print(int(dr.f_up(json.load(open('$R-child-pairs.json'))['pairs'], json.load(open('$R-parent-pairs.json'))['pairs'])[0]))")
if [ "$FUP" = 1 ]; then
  if [ ! -f artifacts/train/$CTRL.exit.json ]; then
    env $TRAINENV PICKLEBOT_RES_BASE=$BASE PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=14400 bash scripts/diag/agility_train_run.sh $CTRL $TC --agent.seed 191 \
      --agent.max-iterations 1200 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG $OV --agent.save-interval 40
  fi
  CD=$(ls -d $L/*_$CTRL | tail -1); CC=$(ls $CD/model_*.pt | sort -V | tail -1)
  [ -s $R-control-pairs.json ] || onbase python scripts/stage2_eval.py --checkpoint $CC $PA --seed 4220306 --json $R-control-pairs.json >> $R-reads.log 2>&1
  dose control $(basename $CD) $(basename $CC)
fi
python - $RALLY $FUP <<'PY' | tee -a $R-summary.txt
import json, os, sys
sys.path.insert(0, "scripts")
import rally_check as rc
from picklebot_mj import agility_rule as ar, ballidx_rule as br, d1_rule as dr, feeder_rule as fr
ld = lambda f: json.load(open(f"results/d1s4-{f}.json"))  # noqa: E731
spec = json.load(open("results/fw1d-C.json"))["footwork_route"]["sectors"]
rally, fup = sys.argv[1] == "0", sys.argv[2] == "1"
ok_p, line = dr.f_up(ld("child-pairs")["pairs"], ld("parent-pairs")["pairs"]); print("F-UP vs parent: " + line)
fc = rc.boot_low(ld("child-pairs")["pairs"]["court_counts"], 3, 2)[0]
abs_f = fc >= 0.80
print(f"ABS-F: feeder legal {fc:.4f} >= 0.80 -> {abs_f}")
ak, lines = dr.s3_agility_kept(ld("child-fw"), ld("parent-fw"), spec)
print(f"AGILE-KEPT vs parent: {ak}; " + "; ".join(lines))
def dose_read(name):
    c = ar.window(ar.read_rows(f"results/d1s4-dose-{name}.jsonl"), "ballidx", 0.5, 1.0)
    s = fr.feeder_stats(c)
    k3 = [x for x in br.summarize(c, 0)["k"] if x["k"] == "3+"][0]["legal"]
    return s, k3
sc, k3c = dose_read("child")
sp, k3p = dose_read("parent")
vc, vp = sc["vars"]["pelvis_speed"]["p50"], sp["vars"]["pelvis_speed"]["p50"]
dose = vc is not None and vp is not None and vc <= vp - 0.05
k3 = k3c is not None and k3p is not None and k3c >= k3p - 0.01
print(f"DOSE: k=0 pelvis speed p50 at the fire {vc} vs parent {vp} (need <= parent - 0.05) -> {dose}; reported: recover dist p50 "
      f"{sc['vars']['recover_dist']['p50']} vs {sp['vars']['recover_dist']['p50']}, k=0 contact {sc['contact']} vs {sp['contact']}, "
      f"band contact {sc['band_contact']} vs {sp['band_contact']}")
print(f"K3-KEPT: k>=3 legal {k3c} vs parent {k3p} (need >= parent - 0.01) -> {k3}")
fup_ctl = None
if fup and os.path.exists("results/d1s4-control-pairs.json"):
    fup_ctl, line = dr.f_up(ld("child-pairs")["pairs"], ld("control-pairs")["pairs"]); print("F-UP vs control: " + line)
    if os.path.exists("results/d1s4-dose-control.jsonl"):
        scc, _ = dose_read("control")
        print(f"reported control dose: k=0 pelvis speed p50 {scc['vars']['pelvis_speed']['p50']}")
for name, f in (("parent", "parent-pairs"), ("child", "child-pairs"), ("22b (reported)", "p22b-pairs"), ("parent refeed 3 s", "parent-refeed3"),
                ("child refeed 3 s", "child-refeed3"), ("control (reported)", "control-pairs")):
    if not os.path.exists(f"results/d1s4-{f}.json"):
        continue
    p = ld(f)["pairs"]
    print(f"{name}: P(5+) open {rc.p5_open(p)[0]:.4f} {rc.p5_open(p)[1]}; feeder {rc.boot_low(p['court_counts'], 3, 2)[0]:.4f}; "
          f"partner {rc.boot_low(p['court_counts'], 1, 0)[0]:.4f}; feeder balls started {p.get('started', {}).get('feeder')}")
for name, f in (("parent", "results/stage5f-d1s4-p-summary.json"), ("child", "results/stage5f-d1s4-summary.json")):
    print(f"h5f court falls {name}: {json.load(open(f))['falls_court']}")
v = dr.s4_verdict(False, True, dose, ok_p, fup_ctl, abs_f, rally, ak == "AGILE-KEPT", k3)
json.dump({"verdict": v, "f_up": ok_p, "f_up_control": fup_ctl, "abs_f": abs_f, "rally": rally, "agile": ak, "dose": dose, "k3": k3},
          open("results/d1s4-summary.json", "w"), indent=1)
print(f"VERDICT: {v}")
PY
echo done > artifacts/train/d1s4.done

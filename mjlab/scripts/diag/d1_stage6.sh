#!/usr/bin/env bash
# D-202 d1s6 (panel round 66, 4 of 5 for (i) -> option (b) parked readiness; architecture's fixes 1-4 folded in): the
# parent d1s3 child (rally-d1s3 model_31399, on the d1 base) trained 1,200 iterations with one change, the task
# Picklebot-Rally22b-FastMove-Parked-G1 = d1s3's task + parked_ready (ready_value while parked on a dead court with both
# robots idle, not busy, not young; weight 2; nothing at contacts). No rally cap. ScheduledPPO 1e-4 constant, KL 0.05, std floor 0.1, warm-up 0,
# 12,288 envs; training seed 195, smoke 196.
# Paired references reused from D-199 / D-201 on the same dev seeds (reported as such): pairs 4220306, direction 4220307,
# Measure60 4220308, +360 Measure60 4220309, h5f 4220310-4220325, refeed 3 s 4220327, the parent's dose read with the
# launch-bin pair log on 4220326 (d1s5's, same checkpoint and base); the child's reads use the same seeds.
# Smoke: d1s3's checks, falls line 4.157 unchanged (half-split reported), config: parked_ready present, no ready_at_event,
#   pair_rally_cap 0. The parked dose log (PICKLEBOT_READY_LOG, report only) runs in the smoke and in training.
# Kill at +360 (picklebot_mj/d1_rule.py; windows from rows that exist, NO-DATA never kills): D-194 training-log lines;
#   KILL-FARM: mean rally length over iterations 100-300 < 0.9 x the parent d1s3 run's; KILL-SLOWED / KILL-NO-ARRIVE on
#   model_31760 against the parent.
# Endpoint: DOSE (pelvis speed p50 at the feeder fire <= parent - 0.05 m/s or recovery distance p50 <= parent - 0.10 m,
#   paired dose runs); GUARDS (r19_guards against the parent); F-UP + F-BIN; F-BAND (+0.03); REFEED3 (-0.01); P5-KEPT
#   (-0.01); K3-KEPT; AGILE-KEPT; rally = d1s2-gate against the parent (labelled); ABS-F (>= 0.80). Control (d1s3
#   continued on its own task, training seed 195) only if F-UP.
# Verdicts: KILL -> INVALID -> NO-DOSE -> GUARD-BREACH -> MIX -> MORE-TIME -> PARK-PASS -> PARK-F -> PARK-FAIL.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER PICKLEBOT_READY_LOG
pgrep -f "run-name |kickstart_h4|stage2_eval|footwork_eval|feeder_speed" > /dev/null && { echo "GPU busy: not started"; exit 1; }
RUN=rally-d1s6; CTRL=rally-d1s6ctl; L=artifacts/train/logs/picklebot_return_stand; R=results/d1s6; TAG=d1s6
BASE=/mnt/f/dev/picklebot-mjlab/mjlab/$L/2026-10-31_18-24-20_s5c-d1-fw1bS/model_32854.pt
PRUN=2026-11-01_12-07-09_rally-d1s3; PCK=model_31399.pt; P=$L/$PRUN/$PCK
T=Picklebot-Rally22b-FastMove-Parked-G1; TC=Picklebot-Rally22b-FastMove-G1; TF=Picklebot-Agility-BallIdx-Feeder-ReadCfg-LamR2-G1
for f in $BASE $P; do [ -f $f ] || { echo "missing $f"; exit 1; }; done
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
B=--env.actions.ball; OV="$B.court-feed-prob 1.0 $B.refeed-delay-s 0.5 $B.recovery-mode fixed $B.planner-mode off $B.target-mode A"
for f in backhand reach-backhand cross-backhand fast drop low reach-deep short high reach-forehand; do OV="$OV $B.feed-mix.weights.$f 1.0"; done
TRAINENV="PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_STD_MIN=0.1 PICKLEBOT_LR_PEAK=1e-4 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_KL_GUARD=0.05 PICKLEBOT_LR_TOTAL=0"
export PICKLEBOT_TRAIN_ENTRY=scripts/diag/footwork_train.py
stop() { echo "VERDICT: $1" | tee -a $R-summary.txt; echo done > artifacts/train/d1s6.done; exit 0; }
[ -s $R-summary.txt ] || echo "parent $P on the d1 base $BASE; task $T (parked readiness, weight 2)" > $R-summary.txt
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120"
FW="--task Picklebot-Footwork-Measure60-RallyLamR2-G1 --envs 1024 --seconds 120 --move-prob 1.0"
onbase() { PICKLEBOT_RES_BASE=$BASE PICKLEBOT_LAM_R=2 "$@"; }
reads() {  # checkpoint, prefix: as D-199
  [ -s $2-pairs.json ] || onbase python scripts/stage2_eval.py --checkpoint $1 $PA --seed 4220306 --json $2-pairs.json >> $R-reads.log 2>&1
  [ -s $2-dir.json ] || onbase python scripts/diag/feeder_speed_envelope.py --checkpoint $1 --seed 4220307 --json $2-dir.json >> $R-reads.log 2>&1
  [ -s $2-fw.json ] || PICKLEBOT_RES_BASE=$BASE python scripts/diag/footwork_eval.py --checkpoint $1 $FW --seed 4220308 --json $2-fw.json >> $R-reads.log 2>&1
  [ -s $2-refeed3.json ] || onbase python scripts/stage2_eval.py --checkpoint $1 $PA --refeed-delay 3.0 --seed 4220327 --json $2-refeed3.json >> $R-reads.log 2>&1
}
dose() {  # name, run dir, checkpoint: LR-0 feeder tally + launch-bin pair log on dev 4220326 (the d1 base)
  [ -s $R-dose-$1.jsonl ] && [ -s $R-dose-$1-pairs.jsonl ] && return 0
  rm -f $R-dose-$1.jsonl $R-dose-$1-pairs.jsonl
  env PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_LR_PEAK=0 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_LR_TOTAL=0 PICKLEBOT_STD_MIN=0.1 PICKLEBOT_BALLIDX_LOG_EVERY=240 \
    PICKLEBOT_PAIR_LOG=$R-dose-$1-pairs.jsonl PICKLEBOT_PAIR_LOG_EVERY=240 \
    PICKLEBOT_RES_BASE=$BASE PICKLEBOT_BALLIDX_LOG=$R-dose-$1.jsonl PICKLEBOT_ENVS=4096 PICKLEBOT_WALL_CAP=2700 PICKLEBOT_TRAIN_ENTRY=scripts/diag/agility_train.py \
    bash scripts/diag/agility_train_run.sh d1s6-dose-$1 $TF --agent.seed 4220326 --agent.max-iterations 200 --agent.resume True \
    --agent.load-run $2 --agent.load-checkpoint $3 $ALG $OV >> $R-reads.log 2>&1
}
# paired parent references reused from D-199 (reads) and D-201 (the dose read on 4220326): same seeds, checkpoint, base
for f in parent-pairs parent-dir parent-fw parent-refeed3 killref-parent-fw p22b-pairs; do [ -s $R-$f.json ] || cp results/d1s4-$f.json $R-$f.json; done
for f in dose-parent dose-parent-pairs; do [ -s $R-$f.jsonl ] || cp results/d1s5-$f.jsonl $R-$f.jsonl; done
[ -s results/stage5f-$TAG-p-summary.json ] || cp results/stage5f-d1s4-p-summary.json results/stage5f-$TAG-p-summary.json
for f in parent-pairs parent-dir parent-fw parent-refeed3 killref-parent-fw p22b-pairs; do [ -s $R-$f.json ] || stop EVAL-FAIL-$f; done
for f in dose-parent dose-parent-pairs; do [ -s $R-$f.jsonl ] || stop EVAL-FAIL-$f; done
cp -n $R-parent-pairs.json $R-parent-early-pairs.json; cp -n $R-parent-dir.json $R-parent-early-dir.json
# smoke (d1s3's checks; parked_ready present, no ready term, no cap)
if [ ! -f artifacts/train/$RUN-smoke.exit.json ]; then
  env $TRAINENV PICKLEBOT_RES_BASE=$BASE PICKLEBOT_SCHED_LOG=$R-smoke.jsonl PICKLEBOT_READY_LOG=$R-smoke-parked.jsonl PICKLEBOT_ENVS=1024 \
    PICKLEBOT_WALL_CAP=900 bash scripts/diag/agility_train_run.sh $RUN-smoke $T --agent.seed 196 --agent.max-iterations 40 --agent.resume True \
    --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG $OV --agent.save-interval 40
fi
SD=$(ls -d $L/*_$RUN-smoke | tail -1)
{ grep -q '"exit_code": 0' artifacts/train/$RUN-smoke.exit.json && echo "smoke exit 0 ok" || echo "smoke exit STOP"; } | tee /tmp/d1s6-smoke.txt
{ grep -a -q -E "Traceback|Error" artifacts/train/$RUN-smoke.log && echo "smoke traceback STOP" || echo "smoke no traceback ok"; } | tee -a /tmp/d1s6-smoke.txt
python scripts/diag/falls_by_length.py artifacts/train/$RUN-smoke.log | awk '{r=$NF; print "smoke falls per 1,000 env-seconds", r, (r <= 4.157 ? "ok" : "STOP")}' | tee -a /tmp/d1s6-smoke.txt
CUDA_VISIBLE_DEVICES= python - "$(ls $SD/model_*.pt | sort -V | tail -1)" <<'PY' | tee -a /tmp/d1s6-smoke.txt
import sys, torch
sd = torch.load(sys.argv[1], map_location="cpu", weights_only=False)
s = sd["actor_state_dict"]["distribution.std_param"]
dead = sorted({i for v in sd["optimizer_state_dict"]["state"].values() if v["exp_avg_sq"].shape == s.shape
               for i in (v["exp_avg_sq"] == 0).nonzero().flatten().tolist()})
print("smoke std min", round(float(s.min()), 4), "outputs with no gradient", dead, "ok" if not dead and float(s.min()) >= 0.0999 else "STOP")
PY
python - "$SD" "$BASE" <<'PY' | tee -a /tmp/d1s6-smoke.txt
import re, sys
d, base = sys.argv[1], sys.argv[2]
env, agent = open(f"{d}/params/env.yaml").read(), open(f"{d}/params/agent.yaml").read()
want = [("court_feed_prob", "1.0"), ("refeed_delay_s", "0.5"), ("recovery_mode", "fixed"), ("planner_mode", "'?off'?"),
        ("target_mode", "A"), ("obs_ball_pos_noise", "0.03"), ("obs_ball_vel_noise", "0.15"), ("pair_drill_court_frac", "0.5"),
        ("episode_length_s", "120.0"), ("backhand", "1.0"), ("reach_backhand", "1.0"), ("fast", "1.0"), ("lam_r", "2.0"),
        ("pair_rally_cap", "0")]
miss = [k for k, v in want if not re.search(rf"^\s*{k}: {v}\s*$", env, re.M)]
based = re.search(rf"^\s*base_checkpoint: {re.escape(base)}\s*$", env, re.M) is not None
terms = "rally_fast_track_lin_vel" in env and "parked_ready" in env and "ready_at_event" not in env
ok = not miss and based and terms
print(f"smoke config check: missing {miss}; d1 base {based}; fast move + parked terms, no ready term {terms} -> {'ok' if ok else 'STOP'}")
PY
python - artifacts/train/$RUN-smoke.log <<'PY' | tee -a /tmp/d1s6-smoke.txt
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
python -c "from picklebot_mj import d1_rule as dr; print('smoke ' + dr.parked_paid('$R-smoke-parked.jsonl'))" | tee -a /tmp/d1s6-smoke.txt
cat /tmp/d1s6-smoke.txt >> $R-summary.txt
[ "$(grep -c " ok$" /tmp/d1s6-smoke.txt)" = 5 ] || stop SMOKE-FAIL
# training with the +360 kill
if [ ! -f artifacts/train/$RUN.exit.json ]; then
  ( python scripts/diag/d1s6_watch.py "$BASE" > $R-kill.txt 2>&1 ) &
  env $TRAINENV PICKLEBOT_RES_BASE=$BASE PICKLEBOT_PAIR_LOG=$R-train-share.jsonl PICKLEBOT_SCHED_LOG=$R-train.jsonl \
    PICKLEBOT_READY_LOG=$R-train-parked.jsonl PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=14400 bash scripts/diag/agility_train_run.sh $RUN $T \
    --agent.seed 195 --agent.max-iterations 1200 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG $OV --agent.save-interval 40
  wait
fi
echo "training: $(cat artifacts/train/$RUN.exit.json)" | tee -a $R-summary.txt; cat $R-kill.txt | tee -a $R-summary.txt
python -c "from picklebot_mj import d1_rule as dr; print(dr.parked_paid('$R-train-parked.jsonl'))" | tee -a $R-summary.txt
grep -q "KILL-" $R-kill.txt && stop "KILL ($(grep -o 'KILL-[A-Z-]*' $R-kill.txt | head -1))"
grep -q '"exit_code": 0' artifacts/train/$RUN.exit.json || stop TRAIN-FAIL
D=$(ls -d $L/*_$RUN | tail -1); CK=$(ls $D/model_*.pt | sort -V | tail -1); echo "endpoint $CK" | tee -a $R-summary.txt
[ "$(basename $CK)" = model_32598.pt ] || stop "ENDPOINT-MISMATCH-$(basename $CK)"
reads $CK $R-child
[ -s results/stage5f-$TAG-summary.json ] || onbase bash scripts/h5f_clean_eval.sh $RUN $(basename $CK) $TAG 4220310 > $R-h5f.log 2>&1
dose child $(basename $D) $(basename $CK)
for f in child-pairs child-dir child-fw child-refeed3; do [ -s $R-$f.json ] || stop EVAL-FAIL-$f; done
[ -s results/stage5f-$TAG-summary.json ] || stop EVAL-FAIL-h5f
[ -s $R-dose-child.jsonl ] || stop EVAL-FAIL-dose-child
cp -n $R-child-pairs.json $R-target.json; cp -n $R-child-dir.json $R-endpoint-dir.json
python scripts/rally_check.py d1s2-gate $R $TAG "d1s3 child (parent)" | tee -a $R-summary.txt; RALLY=${PIPESTATUS[0]}
[ "$RALLY" = 0 ] || [ "$RALLY" = 1 ] || stop "GATE-CRASH-$RALLY"
FUP=$(python -c "import json; from picklebot_mj import d1_rule as dr; print(int(dr.f_up(json.load(open('$R-child-pairs.json'))['pairs'], json.load(open('$R-parent-pairs.json'))['pairs'])[0] and dr.f_bin('$R-dose-child-pairs.jsonl', '$R-dose-parent-pairs.jsonl')[0]))")
if [ "$FUP" = 1 ]; then
  if [ ! -f artifacts/train/$CTRL.exit.json ]; then
    env $TRAINENV PICKLEBOT_RES_BASE=$BASE PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=14400 bash scripts/diag/agility_train_run.sh $CTRL $TC --agent.seed 195 \
      --agent.max-iterations 1200 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG $OV --agent.save-interval 40
  fi
  CD=$(ls -d $L/*_$CTRL | tail -1); CC=$(ls $CD/model_*.pt | sort -V | tail -1)
  [ -s $R-control-pairs.json ] || onbase python scripts/stage2_eval.py --checkpoint $CC $PA --seed 4220306 --json $R-control-pairs.json >> $R-reads.log 2>&1
  dose control $(basename $CD) $(basename $CC)
fi
python - $RALLY <<'PY' | tee -a $R-summary.txt
import json, os, sys
sys.path.insert(0, "scripts")
import rally_check as rc
from picklebot_mj import agility_rule as ar, ballidx_rule as br, d1_rule as dr, feeder_rule as fr
ld = lambda f: json.load(open(f"results/d1s6-{f}.json"))  # noqa: E731
spec = json.load(open("results/fw1d-C.json"))["footwork_route"]["sectors"]
rally = sys.argv[1] == "0"
def dose_read(name):
    c = ar.window(ar.read_rows(f"results/d1s6-dose-{name}.jsonl"), "ballidx", 0.5, 1.0)
    return fr.feeder_stats(c), [x for x in br.summarize(c, 0)["k"] if x["k"] == "3+"][0]["legal"]
sc, k3c = dose_read("child")
sp, k3p = dose_read("parent")
dose, line = dr.s6_dose(sc["vars"], sp["vars"]); print(line)
guards = rc.r19_guards(ld("child-pairs")["per_family"], ld("child-dir")["directions"], ref="results/d1s6-parent-early",
                       cross_ref="results/d1s6-parent-early-pairs.json", name="parent", cross_name="parent")
print(f"GUARDS vs parent: {guards}")
fup, line = dr.f_up(ld("child-pairs")["pairs"], ld("parent-pairs")["pairs"]); print("F-UP vs parent (pairs): " + line)
fbin, line = dr.f_bin("results/d1s6-dose-child-pairs.jsonl", "results/d1s6-dose-parent-pairs.jsonl"); print("F-BIN vs parent (0-1 launch bin): " + line)
fc = rc.boot_low(ld("child-pairs")["pairs"]["court_counts"], 3, 2)[0]
abs_f = fc >= 0.80
print(f"ABS-F: feeder legal {fc:.4f} >= 0.80 -> {abs_f}")
fband = sc["band_contact"] is not None and sp["band_contact"] is not None and sc["band_contact"] >= sp["band_contact"] + 0.03
print(f"F-BAND: k=0 matched-band contact {sc['band_contact']} vs parent {sp['band_contact']} (need >= +0.03) -> {fband}")
k3 = k3c is not None and k3p is not None and k3c >= k3p - 0.01
print(f"K3-KEPT: k>=3 legal {k3c} vs parent {k3p} -> {k3}")
ak, lines = dr.s3_agility_kept(ld("child-fw"), ld("parent-fw"), spec)
print(f"AGILE-KEPT vs parent: {ak}; " + "; ".join(l.replace(" Z ", " parent ") for l in lines))
p5c, p5p = rc.p5_open(ld("child-pairs")["pairs"])[0], rc.p5_open(ld("parent-pairs")["pairs"])[0]
p5k = p5c >= p5p - 0.01
r3c, r3p = (rc.boot_low(ld(f)["pairs"]["court_counts"], 3, 2)[0] for f in ("child-refeed3", "parent-refeed3"))
r3k = r3c >= r3p - 0.01
print(f"P5-KEPT: {p5c:.4f} vs {p5p:.4f} -> {p5k}; REFEED3: feeder legal at 3 s {r3c:.4f} vs {r3p:.4f} -> {r3k}")
fup_ctl = None
if os.path.exists("results/d1s6-control-pairs.json"):
    fup_ctl, line = dr.f_up(ld("child-pairs")["pairs"], ld("control-pairs")["pairs"]); print("F-UP vs control: " + line)
for name, f in (("parent", "parent-pairs"), ("child", "child-pairs"), ("22b (reported)", "p22b-pairs"), ("control (reported)", "control-pairs")):
    if os.path.exists(f"results/d1s6-{f}.json"):
        p = ld(f)["pairs"]
        print(f"{name}: P(5+) open {rc.p5_open(p)[0]:.4f}; feeder {rc.boot_low(p['court_counts'], 3, 2)[0]:.4f}; partner {rc.boot_low(p['court_counts'], 1, 0)[0]:.4f}")
for name, f in (("parent", "results/stage5f-d1s6-p-summary.json"), ("child", "results/stage5f-d1s6-summary.json")):
    print(f"h5f court falls {name}: {json.load(open(f))['falls_court']}")
v = dr.s6_verdict(dose, guards, fup and fbin, fband, fup_ctl, abs_f, rally, ak == "AGILE-KEPT", k3, p5k, r3k)
json.dump({"verdict": v, "dose": dose, "guards": guards, "f_up": fup, "f_bin": fbin, "f_band": fband, "f_up_control": fup_ctl,
           "abs_f": abs_f, "rally": rally, "agile": ak, "k3": k3, "p5_kept": p5k, "refeed3": r3k}, open("results/d1s6-summary.json", "w"), indent=1)
print(f"VERDICT: {v}")
PY
echo done > artifacts/train/d1s6.done

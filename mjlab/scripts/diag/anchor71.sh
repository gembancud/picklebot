#!/usr/bin/env bash
# D-207 (panel round 71, 5 of 5 for (i)): the anchor on the LR 3e-5 recipe. rally-d1s3anc = model_31399 on d1s3's task,
# LR_PEAK 3e-5 (rally-d1s3lr's recipe) with one change, picklebot_mj.rl.sched_ppo:AnchoredScheduledPPO: a fixed
# pull-back to the parent model_31399's frozen actor (mean-only Gaussian KL with the reference std, coef 1.0, no decay,
# no warm-up). 1,200 iterations, training seed 202, smoke 203 (new code: the D-170 line).
# Smoke: D-170 falls line; exit / traceback / std; config (the anchored class); the pull-back wired: the first logged
#   update's pull-back <= 0.01 and a nonzero pull-back by update 10.
# Kill at +360: D-194's lines. Endpoint: pooled guard reads on D-204's seeds; d1_rule.drift_verdict against the pooled
#   parent (FIXED / PARTIAL / STILL-DRIFT, lines unchanged); reported per-seed against rally-d1s3lr (the one-change
#   effect) and rally-d1s3ctlb; the pull-back at +360 and at the end. If FIXED: a confirmation read of parent and child on
#   fresh dev seeds (pairs 4220338, direction 4220339): a breach there, or the child's P(5+) below the parent's -> panel,
#   no promotion (CONFIRM-FAIL); else CONFIRMED.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER PICKLEBOT_READY_LOG \
  PICKLEBOT_RESTART_OBS PICKLEBOT_RESTART_OBS_FREEZE PICKLEBOT_REF_CKPT PICKLEBOT_REF_COEF
pgrep -f "run-name |kickstart_h4|stage2_eval|footwork_eval|feeder_speed" > /dev/null && { echo "GPU busy: not started"; exit 1; }
R=results/anchor71; RD=results/drift70; RC=results/d1s3ctl; RUN=rally-d1s3anc; L=artifacts/train/logs/picklebot_return_stand
BASE=/mnt/f/dev/picklebot-mjlab/mjlab/$L/2026-10-31_18-24-20_s5c-d1-fw1bS/model_32854.pt
PRUN=2026-11-01_12-07-09_rally-d1s3; PCK=model_31399.pt; P=$L/$PRUN/$PCK; T=Picklebot-Rally22b-FastMove-G1
for f in $BASE $P; do [ -f $f ] || { echo "missing $f"; exit 1; }; done
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:AnchoredScheduledPPO"
B=--env.actions.ball; OV="$B.court-feed-prob 1.0 $B.refeed-delay-s 0.5 $B.recovery-mode fixed $B.planner-mode off $B.target-mode A"
for f in backhand reach-backhand cross-backhand fast drop low reach-deep short high reach-forehand; do OV="$OV $B.feed-mix.weights.$f 1.0"; done
TRAINENV="PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_STD_MIN=0.1 PICKLEBOT_LR_PEAK=3e-5 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_KL_GUARD=0.05 PICKLEBOT_LR_TOTAL=0 PICKLEBOT_REF_CKPT=/mnt/f/dev/picklebot-mjlab/mjlab/$P PICKLEBOT_REF_COEF=1.0"
export PICKLEBOT_TRAIN_ENTRY=scripts/diag/footwork_train.py
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120"
onbase() { PICKLEBOT_RES_BASE=$BASE PICKLEBOT_LAM_R=2 "$@"; }
stop() { echo "VERDICT: $1" | tee -a $R-summary.txt; echo done > artifacts/train/anchor71.done; exit 0; }
[ -s $R-summary.txt ] || echo "D-207: $RUN = LR 3e-5 + anchor to $P (coef 1.0, constant)" > $R-summary.txt
# smoke
if [ ! -f artifacts/train/$RUN-smoke.exit.json ]; then
  env $TRAINENV PICKLEBOT_RES_BASE=$BASE PICKLEBOT_SCHED_LOG=$R-smoke.jsonl PICKLEBOT_ENVS=1024 PICKLEBOT_WALL_CAP=900 \
    bash scripts/diag/agility_train_run.sh $RUN-smoke $T --agent.seed 203 --agent.max-iterations 40 --agent.resume True \
    --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG $OV --agent.save-interval 40
fi
SD=$(ls -d $L/*_$RUN-smoke | tail -1)
{ grep -q '"exit_code": 0' artifacts/train/$RUN-smoke.exit.json && echo "smoke exit 0 ok" || echo "smoke exit STOP"; } | tee /tmp/anc-smoke.txt
{ grep -a -q -E "Traceback|Error" artifacts/train/$RUN-smoke.log && echo "smoke traceback STOP" || echo "smoke no traceback ok"; } | tee -a /tmp/anc-smoke.txt
python scripts/diag/falls_by_length.py artifacts/train/$RUN-smoke.log | awk '{r=$NF; print "smoke falls per 1,000 env-seconds", r, (r <= 4.157 ? "ok" : "STOP")}' | tee -a /tmp/anc-smoke.txt
CUDA_VISIBLE_DEVICES= python - "$(ls $SD/model_*.pt | sort -V | tail -1)" "$SD" "$R-smoke.jsonl" <<'PY' | tee -a /tmp/anc-smoke.txt
import json, sys, torch
sd = torch.load(sys.argv[1], map_location="cpu", weights_only=False)
s = sd["actor_state_dict"]["distribution.std_param"]
dead = sorted({i for v in sd["optimizer_state_dict"]["state"].values() if v["exp_avg_sq"].shape == s.shape
               for i in (v["exp_avg_sq"] == 0).nonzero().flatten().tolist()})
print("smoke std min", round(float(s.min()), 4), "outputs with no gradient", dead, "ok" if not dead and float(s.min()) >= 0.0999 else "STOP")
agent = open(f"{sys.argv[2]}/params/agent.yaml").read()
cls = "sched_ppo:AnchoredScheduledPPO" in agent
print(f"smoke config check: algorithm AnchoredScheduledPPO {cls} -> {'ok' if cls else 'STOP'}")
rows = [json.loads(l) for l in open(sys.argv[3])] if __import__("os").path.exists(sys.argv[3]) else []
pb = [r.get("pullback") for r in rows[:10]]
ok = len(pb) >= 10 and None not in pb and pb[0] <= 0.01 and max(pb) > 0 and all(r.get("pullback_coef") == 1.0 for r in rows[:10])
print(f"smoke pull-back wired: first {pb[0] if pb else None}, max of updates 1-10 {max(pb) if pb and None not in pb else None}, coef 1.0 -> {'ok' if ok else 'STOP'}")
PY
cat /tmp/anc-smoke.txt >> $R-summary.txt
[ "$(grep -c " ok$" /tmp/anc-smoke.txt)" = 6 ] || stop SMOKE-FAIL
# training with the +360 kill
if [ ! -f artifacts/train/$RUN.exit.json ]; then
  ( python - <<'PY' > $R-kill.txt 2>&1
import os, sys, time
sys.path.insert(0, ".")
from picklebot_mj import d1_rule as dr
LOG, EXIT = "artifacts/train/rally-d1s3anc.log", "artifacts/train/rally-d1s3anc.exit.json"
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
if k[0].startswith("KILL"):
    os.system("pkill -f 'run-name rally-d1s3anc '")
PY
  ) &
  env $TRAINENV PICKLEBOT_RES_BASE=$BASE PICKLEBOT_PAIR_LOG=$R-train-share.jsonl PICKLEBOT_SCHED_LOG=$R-train.jsonl \
    PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=14400 bash scripts/diag/agility_train_run.sh $RUN $T --agent.seed 202 \
    --agent.max-iterations 1200 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG $OV --agent.save-interval 40
  wait
fi
echo "training: $(cat artifacts/train/$RUN.exit.json)" | tee -a $R-summary.txt; cat $R-kill.txt | tee -a $R-summary.txt
python -c "
import json
rows = [json.loads(l) for l in open('$R-train.jsonl')]
for u in (360, len(rows)):
    r = rows[min(u, len(rows)) - 1]
    print(f'pull-back (reported) at update {r[\"update\"]}: {r.get(\"pullback\")}, KL mean {r[\"kl_mean\"]:.4f}')" | tee -a $R-summary.txt
grep -q "KILL-" $R-kill.txt && stop "KILL ($(grep -o 'KILL-[A-Z-]*' $R-kill.txt | head -1))"
grep -q '"exit_code": 0' artifacts/train/$RUN.exit.json || stop TRAIN-FAIL
D=$(ls -d $L/*_$RUN | tail -1); CK=$D/model_32598.pt; [ -f $CK ] || stop ENDPOINT-MISMATCH
for s in 4220306 4220328 4220329 4220331; do
  [ -s $R-anc-pairs-$s.json ] || onbase python scripts/stage2_eval.py --checkpoint $CK $PA --seed $s --json $R-anc-pairs-$s.json >> $R-reads.log 2>&1
done
for s in 4220307 4220334 4220335 4220336; do
  [ -s $R-anc-dir-$s.json ] || onbase python scripts/diag/feeder_speed_envelope.py --checkpoint $CK --seed $s --json $R-anc-dir-$s.json >> $R-reads.log 2>&1
done
python - <<'PY' | tee -a $R-summary.txt
import glob, json, sys
sys.path.insert(0, "scripts")
import rally_check as rc
from picklebot_mj import d1_rule as dr
R, RD, RC = "results/anchor71", "results/drift70", "results/d1s3ctl"
pp = sorted(glob.glob(f"{R}-anc-pairs-*.json")); dd = sorted(glob.glob(f"{R}-anc-dir-*.json"))
if len(pp) != 4 or len(dd) != 4:
    print("RESULT EVAL-FAIL"); sys.exit(0)
pf, pd = dr.pool_reads(pp, dd)
par = json.load(open(f"{RC}-parent-pooled-pairs.json"))
print("rally-d1s3anc (pooled) against the parent (pooled):")
g = rc.r19_guards(pf["per_family"], pd["directions"], ref=f"{RC}-parent-pooled", cross_ref=f"{RC}-parent-pooled-pairs.json",
                  name="parent pooled", cross_name="parent pooled")
ms = dr.mean_family_shift(pf["per_family"], par["per_family"])
q = dr.pooled_pairs(pp)
qp = dr.pooled_pairs(sorted(glob.glob(f"{RC}-parent-pairs-42203*.json")))
ql = dr.pooled_pairs(sorted(glob.glob(f"{RD}-lr-pairs-*.json")))
qc = dr.pooled_pairs(sorted(glob.glob(f"{RC}-control-pairs-42203*.json")))
lf, _ = dr.pool_reads(sorted(glob.glob(f"{RD}-lr-pairs-*.json")), sorted(glob.glob(f"{RD}-lr-dir-*.json")))
print(f"mean family shift {100 * ms:+.2f} points (rally-d1s3lr {100 * dr.mean_family_shift(lf['per_family'], par['per_family']):+.2f}); "
      f"backhand {pf['per_family']['backhand']['contact']:.4f} (parent {par['per_family']['backhand']['contact']:.4f}, "
      f"rally-d1s3lr {lf['per_family']['backhand']['contact']:.4f})")
print(f"pooled feeder {q['feeder']:.4f} (parent {qp['feeder']:.4f}, d1s3lr {ql['feeder']:.4f}, control {qc['feeder']:.4f}); "
      f"pooled P(5+) {q['p5']:.4f} (parent {qp['p5']:.4f}, d1s3lr {ql['p5']:.4f}, control {qc['p5']:.4f})")
for s in (4220306, 4220328, 4220329, 4220331):
    a = json.load(open(f"{R}-anc-pairs-{s}.json"))["pairs"]; b = json.load(open(f"{RD}-lr-pairs-{s}.json"))["pairs"]
    print(f"seed {s} (reported): P(5+) anchor {rc.p5_open(a)[0]:.4f} vs d1s3lr {rc.p5_open(b)[0]:.4f}")
v = dr.drift_verdict(g, ms, q["feeder"], qp["feeder"], q["p5"], qp["p5"])
json.dump({"verdict": v, "guards_ok": g, "mean_shift": ms, "feeder": q["feeder"], "p5": q["p5"]}, open(f"{R}-summary.json", "w"), indent=1)
print(f"RESULT {v}")
PY
set -- $(tail -1 $R-summary.txt)
[ "$2" = FIXED ] || stop "$2"
# confirmation on fresh seeds (FIXED only)
for w in parent anc; do
  ck=$P; [ $w = anc ] && ck=$CK
  [ -s $R-confirm-$w-pairs.json ] || onbase python scripts/stage2_eval.py --checkpoint $ck $PA --seed 4220338 --json $R-confirm-$w-pairs.json >> $R-reads.log 2>&1
  [ -s $R-confirm-$w-dir.json ] || onbase python scripts/diag/feeder_speed_envelope.py --checkpoint $ck --seed 4220339 --json $R-confirm-$w-dir.json >> $R-reads.log 2>&1
done
python - <<'PY' | tee -a $R-summary.txt
import json, sys
sys.path.insert(0, "scripts")
import rally_check as rc
R = "results/anchor71"
cp = json.load(open(f"{R}-confirm-anc-pairs.json")); pp = json.load(open(f"{R}-confirm-parent-pairs.json"))
print("confirmation (dev 4220338 / 4220339): the child against the parent re-read on the same seeds:")
g = rc.r19_guards(cp["per_family"], json.load(open(f"{R}-confirm-anc-dir.json"))["directions"], ref=f"{R}-confirm-parent",
                  cross_ref=f"{R}-confirm-parent-pairs.json", name="parent (confirm)", cross_name="parent (confirm)")
p5c, p5p = rc.p5_open(cp["pairs"])[0], rc.p5_open(pp["pairs"])[0]
ok = g and p5c >= p5p
print(f"confirmation P(5+) {p5c:.4f} vs parent {p5p:.4f}; guards {g} -> {'CONFIRMED' if ok else 'CONFIRM-FAIL'}")
print(f"RESULT {'FIXED-CONFIRMED' if ok else 'CONFIRM-FAIL'}")
PY
set -- $(tail -1 $R-summary.txt)
stop "$2"

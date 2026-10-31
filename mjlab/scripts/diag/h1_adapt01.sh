#!/usr/bin/env bash
# D-188 probe P1 (panel round 57, (b) 3 of 5): can the rally composite adapt to H1' (h1-fwdec-01 latent_1400)?
# Evaluation-grade only: promotes nothing; H1' stays CONFOUNDED (strokes) and h0-fw-02 stays H0F-FAIL.
#   Training: rally run 22b's task and overrides (scripts/rally_run22b.sh: T, OV, ScheduledPPO 1e-4, no warm-up, KL guard
#   0.05, std floor 0.1, critic warm-up 0) from 22b model_30200 with ONE change: the latent controller H1', set by the
#   recorded cfg override --env.actions.latent.checkpoint (not PICKLEBOT_CONTROLLER, which is evaluation-only). RES_BASE
#   frozen as always. 12,288 envs as 22b. Constant rate (no cooldown), 400 iterations, fixed endpoint (last checkpoint). Training seed 178,
#   smoke seed 179 (10 iterations, 1,024 envs; the override must appear in params/env.yaml).
#   Kill (coded, training log): at +120, falls per 1,000 env-s over iterations 101-120 > 0.5 x those over iterations 1-20
#   -> KILL-NO-ADAPT.
#   Endpoint read, paired on dev 4220242 (Measure60-RallyLamR2, mean actions, 1,024 envs, 120 s): P1 with H1'
#   (PICKLEBOT_CONTROLLER at evaluation) vs 22b model_30200 with latent-07.
#   Validity (D-188 rule for any swapped / adapted controller): falls <= 2 x paired baseline AND untimed arrival >= 0.80 in
#   the worst sector AND (fallen + censored) / spots <= 0.15; else ADAPT-FAIL (NO-ADAPT if falls > 50 / 1,000 env-s).
#   If valid: dR = R(P1) - R(base): ADAPTS-FAST if >= +0.10; ADAPTS-SLOW if <= +0.03; else MIXED.
#   Reported only (CONFOUNDED by strokes): pairs rally read (contact hand-off, 2,048 envs, 120 s) on dev 4220244, both arms.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER
pgrep -f "run-name |distill_latent" > /dev/null && { echo "a trainer is running: not started"; exit 1; }
RUN=h1adapt-01; L=artifacts/train/logs/picklebot_return_stand; R=results/h1adapt01
T=Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR2-DrillCourts-Ep120-G1
PRUN=2026-10-29_16-41-45_rally-22b-readcfg; PCK=model_30200.pt
H1P=$PWD/artifacts/train/latent/h1-fwdec-01/latent_1400.pt
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
B=--env.actions.ball; OV="$B.court-feed-prob 1.0 $B.refeed-delay-s 0.5 $B.recovery-mode fixed $B.planner-mode off $B.target-mode A"
for f in backhand reach-backhand cross-backhand fast drop low reach-deep short high reach-forehand; do OV="$OV $B.feed-mix.weights.$f 1.0"; done
CTRL="--env.actions.latent.checkpoint $H1P"
export PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_STD_MIN=0.1 PICKLEBOT_LR_PEAK=1e-4 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_KL_GUARD=0.05 \
  PICKLEBOT_LR_TOTAL=0
[ -f $L/$PRUN/$PCK ] && [ -f $H1P ] || { echo "missing parent or H1'"; exit 1; }
if [ ! -f artifacts/train/$RUN-smoke.exit.json ]; then
  PICKLEBOT_ENVS=1024 PICKLEBOT_WALL_CAP=900 bash scripts/train_run.sh $RUN-smoke $T --agent.seed 179 --agent.max-iterations 10 \
    --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG $OV $CTRL
fi
cat artifacts/train/$RUN-smoke.exit.json
grep -q "checkpoint: $H1P" $(ls -d $L/*_$RUN-smoke | tail -1)/params/env.yaml || { echo "smoke: H1' override missing from params"; exit 1; }
echo "smoke: H1' override recorded"
export PICKLEBOT_ENVS=12288  # as rally run 22b (the kill watcher reads it too)
if [ ! -f artifacts/train/$RUN.exit.json ]; then
  ( # kill watcher at +120 (training log)
    while [ "$(grep -c 'Learning iteration' artifacts/train/$RUN.log 2>/dev/null || echo 0)" -lt 121 ]; do
      [ -f artifacts/train/$RUN.exit.json ] && exit 0; sleep 60; done
    python - <<'PY' > $R-kill.txt 2>&1
import os, sys, tempfile
sys.path.insert(0, "scripts/diag")
from falls_by_length import falls_per_1000_env_s
blocks = open("artifacts/train/h1adapt-01.log", errors="ignore").read().split("Learning iteration")
def rate(a, b):
    with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as f:
        f.write("Learning iteration".join(blocks[a:b]))
    try:
        return falls_per_1000_env_s(f.name, envs=int(os.environ.get("PICKLEBOT_ENVS", "4096")))[0]
    finally:
        os.unlink(f.name)
r0, r1 = rate(1, 21), rate(101, 121)
v = "KILL-NO-ADAPT" if r1 > 0.5 * r0 else "CONTINUE"
print(f"falls per 1,000 env-s: iterations 1-20 {r0:.2f}, 101-120 {r1:.2f} -> {v}")
PY
    cat $R-kill.txt
    grep -q "KILL-NO-ADAPT" $R-kill.txt && pkill -f "run-name $RUN "
  ) &
  PICKLEBOT_WALL_CAP=7000 bash scripts/train_run.sh $RUN $T --agent.seed 178 --agent.max-iterations 400 \
    --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG $OV $CTRL
  wait
fi
echo "P1: $(cat artifacts/train/$RUN.exit.json)"; cat $R-kill.txt 2>/dev/null
if grep -q "KILL-NO-ADAPT" $R-kill.txt 2>/dev/null; then echo "VERDICT: NO-ADAPT (killed at +120)" | tee $R-summary.txt; echo done > artifacts/train/h1adapt01.done; exit 0; fi
CK=$(ls $(ls -d $L/*_$RUN | tail -1)/model_*.pt | sort -V | tail -1); echo "P1 endpoint $CK"
BASE=$L/$PRUN/$PCK
for arm in base p1; do
  [ -s $R-bridge-$arm.json ] && continue
  if [ $arm = p1 ]; then export PICKLEBOT_CONTROLLER=$H1P; c=$CK; else unset PICKLEBOT_CONTROLLER; c=$BASE; fi
  python scripts/diag/footwork_eval.py --task Picklebot-Footwork-Measure60-RallyLamR2-G1 --checkpoint $c --envs 1024 \
    --seconds 120 --seed 4220242 --move-prob 1.0 --json $R-bridge-$arm.json > $R-bridge-$arm.log 2>&1
done
for arm in base p1; do
  [ -s $R-rally-$arm.json ] && continue
  if [ $arm = p1 ]; then export PICKLEBOT_CONTROLLER=$H1P; c=$CK; else unset PICKLEBOT_CONTROLLER; c=$BASE; fi
  PICKLEBOT_LAM_R=2 python scripts/stage2_eval.py --checkpoint $c --task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 \
    --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120 \
    --seed 4220244 --json $R-rally-$arm.json > $R-rally-$arm.log 2>&1
done
unset PICKLEBOT_CONTROLLER
python - <<'PY' | tee $R-summary.txt
import json
from picklebot_mj import bodyspeed_rule as bsr
spec = json.load(open("results/fw1d-C.json"))["footwork_route"]["sectors"]
out = {}
for arm in ("base", "p1"):
    d = json.load(open(f"results/h1adapt01-bridge-{arm}.json"))
    c = d["move_drill"]["footwork"]
    s = bsr.sectors(c)
    falls = 1000 * d["robot_falls"] / (d["envs"] * d["sim_seconds"])
    spots = sum(x["spots"] for x in s)
    bad = (sum(c["fell"]) + sum(c["censored"])) / max(1, spots)
    R = sum(s[i]["sustained_p50"] / spec[i]["sustained_p50"] for i in (2, 4)) / 2
    out[arm] = {"falls": falls, "worst_arrival": min(x["arrival"] for x in s), "fallen_censored_share": bad, "R": R,
                "sustained": [round(x["sustained_p50"], 2) for x in s]}
    print(arm, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in out[arm].items()})
b, p = out["base"], out["p1"]
valid = p["falls"] <= 2 * b["falls"] and p["worst_arrival"] >= 0.80 and p["fallen_censored_share"] <= 0.15
if not valid:
    v = "NO-ADAPT" if p["falls"] > 50 else "ADAPT-FAIL"
else:
    dR = p["R"] - b["R"]
    v = "ADAPTS-FAST" if dR >= 0.10 else "ADAPTS-SLOW" if dR <= 0.03 else "MIXED"
print(f"validity: falls {p['falls']:.2f} <= {2 * b['falls']:.2f}, worst arrival {p['worst_arrival']:.3f} >= 0.80, "
      f"fallen+censored {p['fallen_censored_share']:.3f} <= 0.15 -> {'valid' if valid else 'INVALID'}")
print(f"dR = {p['R'] - b['R']:+.3f}; VERDICT: {v}")
for arm in ("base", "p1"):
    try:
        d = json.load(open(f"results/h1adapt01-rally-{arm}.json"))
        pr = d.get("pairs", {})
        print(f"rally {arm} (reported, CONFOUNDED):", {k: pr[k] for k in list(pr)[:8]})
    except Exception as e:  # noqa: BLE001
        print(f"rally {arm}: unavailable ({e})")
json.dump({**out, "verdict": v, "valid": valid}, open("results/h1adapt01-summary.json", "w"), indent=1)
PY
echo done > artifacts/train/h1adapt01.done

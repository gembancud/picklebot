#!/usr/bin/env bash
# D-190 P2 (RL's capacity screen; the user 2026-10-31: "We did some shuffling and back pedal motion right? Why not just
# train for longer?"). Can the CURRENT rally composite (latent-07, RES_BASE, lam_r 2 residual) express the specialist's
# footwork when it is finally rewarded for speed? The floor test (D-189: legs explained 0.954 at lam 3) says the actions
# are reachable through latent-07.
#   Task Picklebot-Footwork-Train-RallyLamR2-G1 (run 14's task; move-only FootworkDrill, spots 1-5 m, pay "settled",
#   fw_track_lin_vel; other rewards untouched). From rally 22b model_30200, ScheduledPPO 1e-4 constant (22b's settings),
#   4,096 envs, 600 iterations, fixed endpoint. Training seed 181, smoke 182.
#   Kill at +150 (training): falls per 1,000 env-s over iterations 131-150 > 2 x those over 1-20 -> KILL-UNSTABLE; training
#   untimed arrival over iterations 131-150 < 0.80 -> KILL-NO-ARRIVE. (No ball episodes, so no legal_return line;
#   hitting is not trained here, and nothing from P2 is a rally candidate.)
#   Endpoint, paired on dev 4220246: Measure60-RallyLamR2 (mean actions, 1,024 envs, 120 s), P2 vs 22b model_30200, both
#   on latent-07. Validity (D-188): falls <= 2 x base, worst untimed arrival >= 0.80, (fallen + censored) / spots <= 0.15;
#   else INVALID (re-ask the panel). If valid, R_LB = mean over left / back of sustained p50 / the specialist's (fw1d-C):
#   EXPRESSES if R_LB >= 0.85 (latent-07 is not the cap: a rally run with this drill in move episodes, route E fixed);
#   CAP-IN-07 if R_LB <= 0.70 (route C d1: the s5c-18 recipe with fw1b-S as footwork teacher); else MIXED (d1).
#   Reported: residual saturation share per sector, peak speeds, settled share.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER
pgrep -f "run-name |distill_latent" > /dev/null && { echo "a trainer is running: not started"; exit 1; }
RUN=p2-speed-01; L=artifacts/train/logs/picklebot_return_stand; R=results/p2speed
T=Picklebot-Footwork-Train-RallyLamR2-G1
PRUN=2026-10-29_16-41-45_rally-22b-readcfg; PCK=model_30200.pt
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
export PICKLEBOT_TRAIN_ENTRY=scripts/diag/footwork_train.py PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_STD_MIN=0.1 \
  PICKLEBOT_LR_PEAK=1e-4 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_KL_GUARD=0.05 PICKLEBOT_LR_TOTAL=0 PICKLEBOT_AGILITY_LOG_EVERY=240
if [ ! -f artifacts/train/$RUN-smoke.exit.json ]; then
  PICKLEBOT_ENVS=1024 PICKLEBOT_WALL_CAP=900 PICKLEBOT_AGILITY_LOG=/tmp/p2-smoke.jsonl bash scripts/diag/agility_train_run.sh \
    $RUN-smoke $T --agent.seed 182 --agent.max-iterations 10 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG
fi
cat artifacts/train/$RUN-smoke.exit.json
grep -q "fw_track_lin_vel" $(ls -d $L/*_$RUN-smoke | tail -1)/params/env.yaml || { echo "smoke: speed kernel missing"; exit 1; }
echo "smoke: fw_track_lin_vel recorded"
if [ ! -f artifacts/train/$RUN.exit.json ]; then
  ( # kill watcher at +150 (iterations counted in Python)
    python - <<'PY' > $R-kill.txt 2>&1
import json, os, sys, tempfile, time
sys.path.insert(0, "scripts/diag")
from falls_by_length import falls_per_1000_env_s
from picklebot_mj import agility_rule as ar
LOG, EXIT = "artifacts/train/p2-speed-01.log", "artifacts/train/p2-speed-01.exit.json"
def blocks():
    try:
        return open(LOG, errors="ignore").read().split("Learning iteration")
    except FileNotFoundError:
        return [""]
while len(blocks()) - 1 < 152:
    if os.path.exists(EXIT):
        sys.exit(0)
    time.sleep(30)
b = blocks()
def rate(lo, hi):
    with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as f:
        f.write("Learning iteration".join(b[lo:hi]))
    try:
        return falls_per_1000_env_s(f.name, envs=4096)[0]
    finally:
        os.unlink(f.name)
r0, r1 = rate(1, 21), rate(131, 151)
rows = ar.read_rows("results/p2speed-train.jsonl")
base = rows[0]["step"]
first = min(rows, key=lambda r: abs(r["step"] - (base + 130 * 24)))
last = min(rows, key=lambda r: abs(r["step"] - (base + 150 * 24)))
c = {k: [y - x for x, y in zip(first["move"][k], last["move"][k])] for k in ("arrived", "timed_out", "fell")}
fin = sum(c["arrived"]) + sum(c["timed_out"]) + sum(c["fell"])
arr = sum(c["arrived"]) / fin if fin else float("nan")
v = "KILL-UNSTABLE" if r1 > 2 * r0 else "KILL-NO-ARRIVE" if not arr >= 0.80 else "CONTINUE"
print(f"+150: falls per 1,000 env-s {r0:.2f} (it 1-20) -> {r1:.2f} (it 131-150); untimed arrival {arr:.3f} -> {v}")
PY
    cat $R-kill.txt
    grep -q "KILL-" $R-kill.txt && pkill -f "run-name p2-speed-01 "
  ) &
  PICKLEBOT_ENVS=4096 PICKLEBOT_WALL_CAP=6000 PICKLEBOT_AGILITY_LOG=$R-train.jsonl bash scripts/diag/agility_train_run.sh $RUN $T \
    --agent.seed 181 --agent.max-iterations 600 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK $ALG
  wait
fi
echo "P2: $(cat artifacts/train/$RUN.exit.json)"; cat $R-kill.txt 2>/dev/null
if grep -q "KILL-" $R-kill.txt 2>/dev/null; then echo "VERDICT: $(grep -o 'KILL-[A-Z-]*' $R-kill.txt)" | tee $R-summary.txt; echo done > artifacts/train/p2speed.done; exit 0; fi
CK=$(ls $(ls -d $L/*_$RUN | tail -1)/model_*.pt | sort -V | tail -1); echo "P2 endpoint $CK"
for arm in base p2; do
  [ -s $R-bridge-$arm.json ] && continue
  c=$L/$PRUN/$PCK; [ $arm = p2 ] && c=$CK
  python scripts/diag/footwork_eval.py --task Picklebot-Footwork-Measure60-RallyLamR2-G1 --checkpoint $c --envs 1024 \
    --seconds 120 --seed 4220246 --move-prob 1.0 --json $R-bridge-$arm.json > $R-bridge-$arm.log 2>&1
done
python - <<'PY' | tee $R-summary.txt
import json
from picklebot_mj import bodyspeed_rule as bsr
spec = json.load(open("results/fw1d-C.json"))["footwork_route"]["sectors"]
out = {}
for arm in ("base", "p2"):
    d = json.load(open(f"results/p2speed-bridge-{arm}.json"))
    c = d["move_drill"]["footwork"]
    s = bsr.sectors(c)
    fin = [x["arrived"] + x["timed_out"] + x["fell"] for x in s]
    out[arm] = {"falls": 1000 * d["robot_falls"] / (d["envs"] * d["sim_seconds"]),
                "worst_arrival": min(x["arrival"] for x in s),
                "fallen_censored_share": (sum(c["fell"]) + sum(c["censored"])) / max(1, sum(x["spots"] for x in s)),
                "R_LB": sum(s[i]["sustained_p50"] / spec[i]["sustained_p50"] for i in (2, 4)) / 2,
                "sustained": [round(x["sustained_p50"], 2) for x in s], "peak": [round(x["peak_p50"], 2) for x in s],
                "settled": [round(c["settled"][i] / max(1, f), 3) for i, f in enumerate(fin)],
                "sat_share": [round(c["sat_steps"][i] / max(1, c["move_steps"][i]), 3) for i in range(8)]}
    print(arm, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in out[arm].items()})
b, p = out["base"], out["p2"]
valid = p["falls"] <= 2 * b["falls"] and p["worst_arrival"] >= 0.80 and p["fallen_censored_share"] <= 0.15
v = "INVALID" if not valid else ("EXPRESSES" if p["R_LB"] >= 0.85 else "CAP-IN-07" if p["R_LB"] <= 0.70 else "MIXED")
print(f"validity: falls {p['falls']:.2f} <= {2 * b['falls']:.2f}, worst arrival {p['worst_arrival']:.3f} >= 0.80, "
      f"fallen+censored {p['fallen_censored_share']:.3f} <= 0.15 -> {'valid' if valid else 'INVALID'}")
print(f"R_LB base {b['R_LB']:.3f} -> P2 {p['R_LB']:.3f}; VERDICT: {v}")
json.dump({**out, "verdict": v, "valid": valid}, open("results/p2speed-summary.json", "w"), indent=1)
PY
echo done > artifacts/train/p2speed.done

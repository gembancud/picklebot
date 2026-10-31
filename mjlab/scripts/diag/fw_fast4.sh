#!/usr/bin/env bash
# D-191 body-ceiling test (the user 2026-10-31: beginners 1-2 m/s, intermediates about 3-4, professionals 4-6 m/s; "keep
# improving the agility"). How fast can this G1 move in simulation when the drill stops capping it at 2.5 m/s?
#   Train: Picklebot-Footwork-Specialist-Fast4-G1 (the specialist's task with the command cap 2.5 -> 4.0 m/s, deadlines
#   from v_req U(1.5, 3.5), spots 2-6 m; pay "settled") from fw1b-S model_16600 (BODY-OK, D-183) with fw1b's algorithm
#   (stock PPO, adaptive, desired KL 0.01, initial 1e-5), 4,096 envs, 1,500 iterations, training seed 183.
#   Kill (training, coded): falls per 1,000 env-s over the last 100 iterations > 8.314 after iteration 100 -> VOID-unstable.
#   Read, paired on dev 4220247: Picklebot-Footwork-Measure60-Fast4-G1 (spots 4-6 m, cap 4.0, 60-s episodes), mean actions,
#   1,024 envs, 120 s, child vs parent fw1b-S model_16600. Validity (D-188): falls <= 2 x parent, worst untimed arrival
#   >= 0.80, (fallen + censored) / spots <= 0.15. Then on min over left / back / right of sustained p50:
#   CEILING-RAISED if >= parent's + 0.30 m/s; CEILING-HELD if <= parent's + 0.10; else MIXED; INVALID if not valid.
#   Reported: per-sector sustained p50 / p90, peak p50 / p90, first-step time p50 (to 1.5 m closer), settled share.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER
pgrep -f "run-name |distill_latent" > /dev/null && { echo "a trainer is running: not started"; exit 1; }
RUN=fw-fast4-01; L=artifacts/train/logs/picklebot_return_stand; R=results/fwfast4
PRUN=2026-10-31_01-16-15_fw1b-S; PCK=model_16600.pt
export PICKLEBOT_TRAIN_ENTRY=scripts/diag/footwork_train.py PICKLEBOT_AGILITY_LOG_EVERY=240 PICKLEBOT_ENVS=4096
if [ ! -f artifacts/train/$RUN.exit.json ]; then
  ( python - <<'PY' > $R-kill.txt 2>&1
import os, sys, tempfile, time
sys.path.insert(0, "scripts/diag")
from falls_by_length import falls_per_1000_env_s
LOG, EXIT = "artifacts/train/fw-fast4-01.log", "artifacts/train/fw-fast4-01.exit.json"
while not os.path.exists(EXIT):
    time.sleep(120)
    try:
        b = open(LOG, errors="ignore").read().split("Learning iteration")
    except FileNotFoundError:
        continue
    if len(b) - 1 < 200:
        continue
    with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as f:
        f.write("Learning iteration".join(b[-100:]))
    r = falls_per_1000_env_s(f.name, envs=4096)[0]
    os.unlink(f.name)
    if r > 8.314:
        print(f"VOID-unstable: falls {r:.2f} per 1,000 env-s over the last 100 of {len(b) - 1} iterations")
        os.system("pkill -f 'run-name fw-fast4-01 '")
        break
PY
  ) &
  PICKLEBOT_AGILITY_LOG=$R-train.jsonl PICKLEBOT_WALL_CAP=7000 bash scripts/diag/agility_train_run.sh $RUN \
    Picklebot-Footwork-Specialist-Fast4-G1 --agent.seed 183 --agent.max-iterations 1500 --agent.resume True \
    --agent.load-run $PRUN --agent.load-checkpoint $PCK --agent.algorithm.learning-rate 1e-5
  wait
fi
echo "train: $(cat artifacts/train/$RUN.exit.json)"; cat $R-kill.txt 2>/dev/null
if grep -q "VOID-unstable" $R-kill.txt 2>/dev/null; then echo "VERDICT: VOID-unstable" | tee $R-summary.txt; echo done > artifacts/train/fwfast4.done; exit 0; fi
CK=$(ls $(ls -d $L/*_$RUN | tail -1)/model_*.pt | sort -V | tail -1); echo "endpoint $CK"
for arm in parent child; do
  [ -s $R-$arm.json ] && continue
  c=$L/$PRUN/$PCK; [ $arm = child ] && c=$CK
  python scripts/diag/footwork_eval.py --task Picklebot-Footwork-Measure60-Fast4-G1 --checkpoint $c --envs 1024 --seconds 120 \
    --seed 4220247 --move-prob 1.0 --json $R-$arm.json > $R-$arm.log 2>&1
done
python - <<'PY' | tee $R-summary.txt
import json
import numpy as np
from picklebot_mj import bodyspeed_rule as bsr
def q(h, f, w):
    h = np.asarray(h); c = np.cumsum(h)
    return None if c[-1] == 0 else float((np.searchsorted(c, f * c[-1]) + 0.5) * w)
out = {}
for arm in ("parent", "child"):
    d = json.load(open(f"results/fwfast4-{arm}.json"))
    c = d["move_drill"]["footwork"]
    s = bsr.sectors(c)
    fin = [x["arrived"] + x["timed_out"] + x["fell"] for x in s]
    out[arm] = {"falls": 1000 * d["robot_falls"] / (d["envs"] * d["sim_seconds"]),
                "worst_arrival": min(x["arrival"] for x in s),
                "fallen_censored_share": (sum(c["fell"]) + sum(c["censored"])) / max(1, sum(x["spots"] for x in s)),
                "sustained_p50": [round(x["sustained_p50"], 2) for x in s],
                "sustained_p90": [round(x["sustained_p90"], 2) for x in s],
                "peak_p50": [round(x["peak_p50"], 2) for x in s],
                "first_step_p50_s": [q(c["first_step_hist"][i], 0.5, c["first_step_bin_s"]) for i in range(8)],
                "settled": [round(c["settled"][i] / max(1, f), 3) for i, f in enumerate(fin)]}
    out[arm]["lbr_min"] = min(s[i]["sustained_p50"] for i in (2, 4, 6))
    print(arm, json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in out[arm].items()}))
p, c = out["parent"], out["child"]
valid = c["falls"] <= 2 * max(p["falls"], 0.5) and c["worst_arrival"] >= 0.80 and c["fallen_censored_share"] <= 0.15
gain = c["lbr_min"] - p["lbr_min"]
v = "INVALID" if not valid else "CEILING-RAISED" if gain >= 0.30 else "CEILING-HELD" if gain <= 0.10 else "MIXED"
print(f"validity -> {'valid' if valid else 'INVALID'}; min(L, B, R) sustained {p['lbr_min']:.2f} -> {c['lbr_min']:.2f} "
      f"({gain:+.2f} m/s); VERDICT: {v}")
json.dump({**out, "verdict": v, "valid": valid, "gain": gain}, open("results/fwfast4-summary.json", "w"), indent=1)
PY
echo done > artifacts/train/fwfast4.done

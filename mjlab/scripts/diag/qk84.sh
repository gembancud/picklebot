#!/usr/bin/env bash
# D-221 (panel round 84: (a) stage 1, 5 of 5; round 84b: form F2, 5 of 5). Footwork-base phase Q, first run: a court-scale
# quickness specialist, read before anything is rebuilt.
#   Train: Q = fw-quick-01 on Picklebot-Footwork-Specialist-Quick-G1 (fw1b-S's task with the read's court spots, md.DIST_RANGE
#   inside md.SPOT_BOX; pay "settled"; cap 2.5 and deadlines V_REQ unchanged; plus the first-step bonus fw_first_step, paid
#   once per spot >= 1.5 m when the pelvis has closed 1.5 m: clamp(1.6 - t, 0, 1) x the arrival bonus weight) from fw1b-S
#   model_16600 with fw_fast4.sh's algorithm (stock PPO, adaptive, initial 1e-5), 4,096 envs, 1,500 iterations, seed 220.
#   Smoke: seed 221, 120 iterations: exit 0, no traceback, fw_first_step paid (nonzero in the log), the early window
#   readable (d1_rule.first_window over 0-100: >= 200 left and back samples each), falls over the last 100 <= 8.314.
#   Kills (training, coded): VOID-unstable (falls per 1,000 env-s over the last 100 iterations > 8.314 after 200, as
#   fw_fast4.sh); KILL-NO-START at +450 (d1_rule.quick_kill: left and back first-step p50 over 400-450 each >= 0.10 s
#   faster than over 0-100).
#   Read, paired on dev 4220373: Picklebot-Footwork-Measure60-Court-G1, mean actions, 1,024 envs, 120 s, Q's endpoint vs
#   fw1b-S -> d1_rule.quick_check: VALID, ARRIVE, SETTLE, FALLS (<= fw1b-S), QUICK (left / back p50 each <= fw1b-S - 0.25 s)
#   -> QUICK-OK / QUICK-FAIL / INVALID. FASTER, every sector's first step and the training windows are reported.
#   Nothing follows automatically: a QUICK-OK goes to the panel for d1c (D-192's kickstart, teacher swapped) as its own entry.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER
RUN=fw-quick-01; SRUN=fw-quick-01-smoke; T=Picklebot-Footwork-Specialist-Quick-G1
L=artifacts/train/logs/picklebot_return_stand; R=results/qk84
PRUN=2026-10-31_01-16-15_fw1b-S; PCK=model_16600.pt
ALG="--agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK --agent.algorithm.learning-rate 1e-5"
export PICKLEBOT_TRAIN_ENTRY=scripts/diag/footwork_train.py PICKLEBOT_AGILITY_LOG_EVERY=240 PICKLEBOT_ENVS=4096
if [ ! -f artifacts/train/$RUN.exit.json ]; then
  pgrep -f "run-name |distill_latent|footwork_eval|stage2_eval|feeder_speed|latent_reach_floor" > /dev/null && { echo "GPU busy: not started"; exit 1; }
fi
echo "D-221: Q = $RUN on $T from fw1b-S $PCK; training seed 220, smoke 221; read dev 4220373" | tee $R-summary.txt

# --- smoke -----------------------------------------------------------------------------------------------------------
if [ ! -f artifacts/train/$SRUN.exit.json ]; then
  PICKLEBOT_AGILITY_LOG=$R-smoke.jsonl PICKLEBOT_WALL_CAP=1500 bash scripts/diag/agility_train_run.sh $SRUN $T \
    --agent.seed 221 --agent.max-iterations 120 $ALG
fi
python - <<'PY' > /tmp/qk84-smoke.txt 2>&1
import json, os, re, sys
sys.path.insert(0, "."); sys.path.insert(0, "scripts/diag")
from picklebot_mj import d1_rule as dr
from falls_by_length import falls_per_1000_env_s
log, ex = "artifacts/train/fw-quick-01-smoke.log", json.load(open("artifacts/train/fw-quick-01-smoke.exit.json"))
t = open(log, errors="ignore").read()
print("exit", ex["exit_code"], "ok" if ex["exit_code"] == 0 else "STOP")
print("traceback", "none ok" if "Traceback" not in t else "found STOP")
pay = [float(x) for x in re.findall(r"Episode_Reward/fw_first_step: ([0-9.eE+-]+)", t)]
print(f"fw_first_step paid: max episode mean {max(pay) if pay else None}", "ok" if pay and max(pay) > 0 else "STOP")
rows = [json.loads(x) for x in open("results/qk84-smoke.jsonl")] if os.path.exists("results/qk84-smoke.jsonl") else []
w = dr.first_window(rows, *dr.QUICK_EARLY, 16600)
good = w is not None and min(w["n"]) >= dr.QUICK_MIN_N and None not in w["p50"]
print(f"early window {dr.QUICK_EARLY}: {w}", "ok" if good else "STOP")
b = t.split("Learning iteration")
import tempfile
with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as f:
    f.write("Learning iteration".join(b[-100:]))
r = falls_per_1000_env_s(f.name, envs=4096)[0]
print(f"falls per 1,000 env-s over the last 100: {r:.3f} (<= 8.314)", "ok" if r <= 8.314 else "STOP")
PY
cat /tmp/qk84-smoke.txt | tee -a $R-summary.txt
if [ "$(grep -c " ok$" /tmp/qk84-smoke.txt)" != 5 ]; then
  echo "VERDICT: SMOKE-FAIL" | tee -a $R-summary.txt; echo done > artifacts/train/qk84.done; exit 0
fi

# --- train with kills -------------------------------------------------------------------------------------------------
if [ ! -f artifacts/train/$RUN.exit.json ]; then
  ( python - <<'PY' > $R-kill.txt 2>&1
import json, os, sys, tempfile, time
sys.path.insert(0, "."); sys.path.insert(0, "scripts/diag")
from picklebot_mj import d1_rule as dr
from falls_by_length import falls_per_1000_env_s
LOG, EXIT, J = "artifacts/train/fw-quick-01.log", "artifacts/train/fw-quick-01.exit.json", "results/qk84-train.jsonl"
done_ns = False
while not os.path.exists(EXIT):
    time.sleep(120)
    try:
        b = open(LOG, errors="ignore").read().split("Learning iteration")
    except FileNotFoundError:
        continue
    n = len(b) - 1
    if n >= 200:
        with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as f:
            f.write("Learning iteration".join(b[-100:]))
        r = falls_per_1000_env_s(f.name, envs=4096)[0]
        os.unlink(f.name)
        if r > 8.314:
            print(f"VOID-unstable: falls {r:.2f} per 1,000 env-s over the last 100 of {n} iterations", flush=True)
            os.system("pkill -f 'run-name fw-quick-01 '")
            break
    if not done_ns and n >= 470 and os.path.exists(J):
        rows = [json.loads(x) for x in open(J)]
        v, line = dr.quick_kill(rows, 16600)
        if v == "NO-DATA":
            continue
        done_ns = True
        print(f"+{n}: " + line, flush=True)
        if v != "CONTINUE":
            os.system("pkill -f 'run-name fw-quick-01 '")
            break
PY
  ) &
  PICKLEBOT_AGILITY_LOG=$R-train.jsonl PICKLEBOT_WALL_CAP=7000 bash scripts/diag/agility_train_run.sh $RUN $T \
    --agent.seed 220 --agent.max-iterations 1500 $ALG
  wait
fi
echo "train: $(cat artifacts/train/$RUN.exit.json)" | tee -a $R-summary.txt; cat $R-kill.txt 2>/dev/null | tee -a $R-summary.txt
if grep -q "^VOID-unstable" $R-kill.txt 2>/dev/null; then echo "VERDICT: VOID-unstable" | tee -a $R-summary.txt; echo done > artifacts/train/qk84.done; exit 0; fi
if grep -q -- "-> KILL-NO-START" $R-kill.txt 2>/dev/null; then echo "VERDICT: KILL-NO-START" | tee -a $R-summary.txt; echo done > artifacts/train/qk84.done; exit 0; fi
if ! grep -q -- "-> CONTINUE" $R-kill.txt 2>/dev/null; then echo "VERDICT: NO-KILL-READ (the +450 line never read; stop, panel)" | tee -a $R-summary.txt; echo done > artifacts/train/qk84.done; exit 0; fi

# --- read, paired on dev 4220373 --------------------------------------------------------------------------------------
CK=$(ls $(ls -d $L/*_$RUN | tail -1)/model_*.pt | sort -V | tail -1); echo "endpoint $CK" | tee -a $R-summary.txt
for arm in fw quick; do
  [ -s $R-$arm.json ] && continue
  c=$L/$PRUN/$PCK; [ $arm = quick ] && c=$CK
  python scripts/diag/footwork_eval.py --task Picklebot-Footwork-Measure60-Court-G1 --checkpoint $c --envs 1024 --seconds 120 \
    --seed 4220373 --move-prob 1.0 --json $R-$arm.json > $R-$arm.log 2>&1
done
python - <<'PY' | tee -a $R-summary.txt
import json, sys
sys.path.insert(0, ".")
from picklebot_mj import d1_rule as dr
t, w = (dr.agility(json.load(open(f"results/qk84-{a}.json"))) for a in ("quick", "fw"))
v, lines = dr.quick_check(t, w)
for x in lines:
    print(x)
print("(reported) first-step p50 by sector, Q:", t["first_step_p50"], "fw1b-S:", w["first_step_p50"])
print("(reported) sustained p50 by sector, Q:", t["sustained_p50"], "fw1b-S:", w["sustained_p50"])
rows = [json.loads(x) for x in open("results/qk84-train.jsonl")]
for lo in range(0, 1500, 250):
    print(f"(reported) training window {lo}-{lo + 250}:", dr.first_window(rows, lo, lo + 250, 16600))
print(f"VERDICT: {v}")
json.dump({"quick": t, "fw": w, "verdict": v}, open("results/qk84-verdict.json", "w"), indent=1)
PY
echo done > artifacts/train/qk84.done

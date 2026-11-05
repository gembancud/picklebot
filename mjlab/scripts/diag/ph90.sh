#!/usr/bin/env bash
# D-227 (panel round 90: (b) 5 of 5, opened with its premise run; (a) runs first, 5 of 5).
#  A. Reported-only read (NOT a score; the frozen read is unchanged): C = rally-d1s3lr3 model_32598 under a set start
#     (--pair-set-start 3.0: each feeder ball held until both robots are within 0.3 m of their spot and slower than
#     0.3 m/s, or 3 s), standard pairs reads on dev 4220380-4220381, pooled; reported beside C's standard reads
#     (D-224's h1r87 reads on 4220375 + 4220377). For the user's set-start ask.
#  B. fw-scratch-01: Picklebot-Footwork-Specialist-Quick2-G1 (D-222's task, unchanged) from a random init (no resume: no
#     model_15900 lineage; supersedes D-006 for this premise test), stock PPO settings (no LR override), 4,096 envs,
#     6,000 iterations; training seed 224, smoke 225 (120 iterations: exit 0, no traceback, no NaN, no resume,
#     fw_first_step present, agility rows with first_step_hist; falls reported only).
#     Kill at +1,800 (d1_rule.scratch_kill): VOID-unstable (falls over the last 100 > 8.314, from +1,800 on) and
#     KILL-NO-START (1,700-1,800 left / back p50 not <= Q2's 400-450 1.2733 / 1.3847 s, n >= 200 each).
#     Gate: d1_rule.quick_check vs fw1b-S on Measure60-Court, mean actions, dev 4220382 -> QUICK-OK / QUICK-FAIL /
#     INVALID. A pass leads to a d1c kickstart as its own entry; a fail closes the in-authority controller route.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER PICKLEBOT_READY_LOG
R=results/ph90; L=artifacts/train/logs/picklebot_return_stand
BASE=/mnt/f/dev/picklebot-mjlab/mjlab/$L/2026-10-31_18-24-20_s5c-d1-fw1bS/model_32854.pt
P=$L/2026-11-04_00-06-34_rally-d1s3lr3/model_32598.pt
FW=$L/2026-10-31_01-16-15_fw1b-S/model_16600.pt
RUN=fw-scratch-01; SRUN=fw-scratch-01-smoke; T=Picklebot-Footwork-Specialist-Quick2-G1
for f in $BASE $P $FW; do [ -f $f ] || { echo "missing $f"; exit 1; }; done
if [ ! -f artifacts/train/$RUN.exit.json ]; then
  pgrep -f "run-name |kickstart_h4|stage2_eval|footwork_eval|feeder_speed|distill_latent|latent_reach_floor" > /dev/null && { echo "GPU busy: not started"; exit 1; }
fi
onbase() { PICKLEBOT_RES_BASE=$BASE PICKLEBOT_LAM_R=2 "$@"; }
stop() { echo "VERDICT: $1" | tee -a $R-summary.txt; echo done > artifacts/train/ph90.done; exit 0; }
[ -s $R-summary.txt ] || echo "D-227: A. C under a set start (reported only), dev 4220380-4220381; B. $RUN from scratch on $T, seeds 224 / 225, gate dev 4220382" > $R-summary.txt

# --- A. set start, reported only ---------------------------------------------------------------------------------------
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120"
for s in 4220380 4220381; do
  [ -s $R-set-$s.json ] || onbase python scripts/stage2_eval.py --checkpoint $P $PA --pair-set-start 3.0 --seed $s --json $R-set-$s.json > $R-set-$s.log 2>&1
done
if ! grep -q "^(reported) set start" $R-summary.txt; then
python - <<'PY' | tee -a $R-summary.txt
import json, sys
sys.path.insert(0, ".")
from picklebot_mj import d1_rule as dr
f = ["results/ph90-set-4220380.json", "results/ph90-set-4220381.json"]
ref = ["results/h1r87-read-4220375.json", "results/h1r87-read-4220377.json"]
for x in dr.set_start_report(f, ref):
    print(x)
rel = [json.load(open(p))["pairs"]["set_start_released"] for p in f]
print(f"(reported) set start feeder balls released [set, timeout]: {rel}")
ok, line = dr.h1_recon(f)
print("(reported) set start " + line)
v, lines = dr.h1_route(f)
print("(reported) set start first hand-off: " + lines[0])
PY
fi

# --- B. smoke -----------------------------------------------------------------------------------------------------------
export PICKLEBOT_TRAIN_ENTRY=scripts/diag/footwork_train.py PICKLEBOT_AGILITY_LOG_EVERY=240 PICKLEBOT_ENVS=4096
if [ ! -f artifacts/train/$SRUN.exit.json ]; then
  PICKLEBOT_AGILITY_LOG=$R-smoke.jsonl PICKLEBOT_WALL_CAP=1500 bash scripts/diag/agility_train_run.sh $SRUN $T \
    --agent.seed 225 --agent.max-iterations 120
fi
python - <<'PY' > /tmp/ph90-smoke.txt 2>&1
import json, os, re, sys
sys.path.insert(0, "."); sys.path.insert(0, "scripts/diag")
from falls_by_length import falls_per_1000_env_s
log, ex = "artifacts/train/fw-scratch-01-smoke.log", json.load(open("artifacts/train/fw-scratch-01-smoke.exit.json"))
t = open(log, errors="ignore").read()
print("exit", ex["exit_code"], "ok" if ex["exit_code"] == 0 else "STOP")
print("traceback", "none ok" if "Traceback" not in t else "found STOP")
print("nan", "none ok" if not re.search(r"\bnan\b", t, re.I) else "found STOP")
print("resume", "none ok" if "load-run" not in open("artifacts/train/fw-scratch-01-smoke.launch.json").read() else "found STOP")
print("fw_first_step present", "ok" if "Episode_Reward/fw_first_step" in t else "STOP")
rows = [json.loads(x) for x in open("results/ph90-smoke.jsonl")] if os.path.exists("results/ph90-smoke.jsonl") else []
print(f"agility rows {len(rows)} with first_step_hist", "ok" if rows and "first_step_hist" in rows[-1].get("move", {}) else "STOP")
print(f"(reported) falls per 1,000 env-s over the run: {falls_per_1000_env_s(log, envs=4096)[0]:.2f}")
PY
cat /tmp/ph90-smoke.txt | tee -a $R-summary.txt
[ "$(grep -c " ok$" /tmp/ph90-smoke.txt)" = 6 ] || stop "SMOKE-FAIL"

# --- B. train with kills ------------------------------------------------------------------------------------------------
if [ ! -f artifacts/train/$RUN.exit.json ]; then
  ( python - <<'PY' > $R-kill.txt 2>&1
import json, os, sys, tempfile, time
sys.path.insert(0, "."); sys.path.insert(0, "scripts/diag")
from picklebot_mj import d1_rule as dr
from falls_by_length import falls_per_1000_env_s
LOG, EXIT, J = "artifacts/train/fw-scratch-01.log", "artifacts/train/fw-scratch-01.exit.json", "results/ph90-train.jsonl"
read = False
while not os.path.exists(EXIT):
    time.sleep(180)
    try:
        b = open(LOG, errors="ignore").read().split("Learning iteration")
    except FileNotFoundError:
        continue
    n = len(b) - 1
    if n < 1810:
        continue
    with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as f:
        f.write("Learning iteration".join(b[-100:]))
    r = falls_per_1000_env_s(f.name, envs=4096)[0]
    os.unlink(f.name)
    if r > 8.314:
        print(f"VOID-unstable: falls {r:.2f} per 1,000 env-s over the last 100 of {n} iterations", flush=True)
        os.system("pkill -f 'run-name fw-scratch-01 '")
        break
    if not read and os.path.exists(J):
        v, line = dr.scratch_kill([json.loads(x) for x in open(J)])
        if v == "NO-DATA":
            continue
        read = True
        print(f"+{n}: " + line + f"; falls {r:.2f}", flush=True)
        if v != "CONTINUE":
            os.system("pkill -f 'run-name fw-scratch-01 '")
            break
PY
  ) &
  PICKLEBOT_AGILITY_LOG=$R-train.jsonl PICKLEBOT_WALL_CAP=30000 bash scripts/diag/agility_train_run.sh $RUN $T \
    --agent.seed 224 --agent.max-iterations 6000
  wait
fi
echo "train: $(cat artifacts/train/$RUN.exit.json)" | tee -a $R-summary.txt; cat $R-kill.txt 2>/dev/null | tee -a $R-summary.txt
grep -q "^VOID-unstable" $R-kill.txt 2>/dev/null && stop "VOID-unstable"
grep -q -- "-> KILL-NO-START" $R-kill.txt 2>/dev/null && stop "KILL-NO-START"
grep -q -- "-> CONTINUE" $R-kill.txt 2>/dev/null || stop "NO-KILL-READ (the +1,800 line never read; panel)"

# --- B. gate, paired on dev 4220382 --------------------------------------------------------------------------------------
CK=$(ls $(ls -d $L/*_$RUN | tail -1)/model_*.pt | sort -V | tail -1); echo "endpoint $CK" | tee -a $R-summary.txt
for arm in fw scratch; do
  [ -s $R-$arm.json ] && continue
  c=$FW; [ $arm = scratch ] && c=$CK
  python scripts/diag/footwork_eval.py --task Picklebot-Footwork-Measure60-Court-G1 --checkpoint $c --envs 1024 --seconds 120 \
    --seed 4220382 --move-prob 1.0 --json $R-$arm.json > $R-$arm.log 2>&1
done
python - <<'PY' | tee -a $R-summary.txt
import json, sys
sys.path.insert(0, ".")
from picklebot_mj import d1_rule as dr
t, w = (dr.agility(json.load(open(f"results/ph90-{a}.json"))) for a in ("scratch", "fw"))
v, lines = dr.quick_check(t, w)
for x in lines:
    print(x)
print("(reported) first-step p50 by sector, scratch:", t["first_step_p50"], "fw1b-S:", w["first_step_p50"])
rows = [json.loads(x) for x in open("results/ph90-train.jsonl")]
for lo in range(0, 6000, 1000):
    print(f"(reported) training window {lo}-{lo + 1000}:", dr.first_window(rows, lo, lo + 1000, 0))
print(f"RESULT {v}")
PY
v=$(grep "^RESULT" $R-summary.txt | tail -1 | cut -d' ' -f2)
stop "$v"

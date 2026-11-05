#!/usr/bin/env bash
# D-229 (panel round 91, 5 of 5 on the order; the user's D-228). Runs after ph90 (D-227 B) is done.
#  1. GPU tests: tests/test_drill_reset.py, tests/test_pair_cut.py.
#  2. Premise read (reported): fw1b-S model_16600 at mean actions on Measure60-Court (standard limits) and on
#     Measure60-Court-Strong (leg / waist / ankle effort x2), dev 4220383, with PICKLEBOT_FW_SAT=1 (share of samples in
#     the first 1.0 s of each move with |qfrc_actuator| >= 0.95 x the joint's effort limit, by group).
#  3. The new frozen set-start read's baseline: C = rally-d1s3lr3 model_32598 on the standard pairs read with
#     --pair-drill-reset, dev 4220385-4220388 pooled; the old read on the same seeds reported alongside.
#  4. fw-act2-01: D-222's Q2 task with the one change effort x2 (Quick2-Strong), from fw1b-S model_16600, D-222's
#     recipe; D-222's smoke / VOID-unstable / KILL-NO-START (quick_kill unchanged); gate quick_check: the child read on
#     Measure60-Court-Strong vs fw1b-S on the standard Measure60-Court, dev 4220384. Saturation reported.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
[ -f artifacts/train/ph90.done ] || { echo "ph90 not done: not started"; exit 1; }
if [ ! -f artifacts/train/fw-act2-01.exit.json ]; then
  pgrep -f "run-name |kickstart_h4|stage2_eval|footwork_eval|feeder_speed|distill_latent|latent_reach_floor" > /dev/null && { echo "GPU busy: not started"; exit 1; }
fi
R=results/sr91; L=artifacts/train/logs/picklebot_return_stand
BASE=/mnt/f/dev/picklebot-mjlab/mjlab/$L/2026-10-31_18-24-20_s5c-d1-fw1bS/model_32854.pt
P=$L/2026-11-04_00-06-34_rally-d1s3lr3/model_32598.pt
FW=$L/2026-10-31_01-16-15_fw1b-S/model_16600.pt
onbase() { PICKLEBOT_RES_BASE=$BASE PICKLEBOT_LAM_R=2 "$@"; }
[ -s $R-summary.txt ] || echo "D-229: premise read dev 4220383; set-start baseline dev 4220385-4220388; fw-act2-01 seeds 226 / 227, gate dev 4220384" > $R-summary.txt
# 1
if ! grep -q "^tests passed" $R-summary.txt; then
  if python -m pytest -q tests/test_drill_reset.py tests/test_pair_cut.py > $R-tests.log 2>&1; then
    echo "tests passed" | tee -a $R-summary.txt
  else
    echo "VERDICT: TESTS-FAIL" | tee -a $R-summary.txt; tail -30 $R-tests.log; echo done > artifacts/train/sr91.done; exit 0
  fi
fi
# 2
for arm in std strong; do
  [ -s $R-premise-$arm.json ] && continue
  MT=Picklebot-Footwork-Measure60-Court-G1; [ $arm = strong ] && MT=Picklebot-Footwork-Measure60-Court-Strong-G1
  PICKLEBOT_FW_SAT=1 python scripts/diag/footwork_eval.py --task $MT --checkpoint $FW --envs 1024 --seconds 120 \
    --seed 4220383 --move-prob 1.0 --json $R-premise-$arm.json > $R-premise-$arm.log 2>&1
done
if ! grep -q "^(reported) premise" $R-summary.txt; then
python - <<'PY' | tee -a $R-summary.txt
import json, sys
sys.path.insert(0, ".")
from picklebot_mj import d1_rule as dr
for arm in ("std", "strong"):
    d = json.load(open(f"results/sr91-premise-{arm}.json"))
    a = dr.agility(d)
    sat = d["move_drill"]["footwork"].get("saturation", {})
    sh = {k: round(v[1] / v[0], 4) if v[0] else None for k, v in sat.items()}
    print(f"(reported) premise fw1b-S {arm}: first-step p50 L/B {a['first_step_p50'][dr.LEFT]}/{a['first_step_p50'][dr.BACK]} s, "
          f"all {a['first_step_p50']}, falls {a['falls']:.3f}, saturation share {sh}")
PY
fi
# 3
PA="--task Picklebot-Latent-Court-Res-G1 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally --pairs --pair-handoff contact --envs 2048 --seconds 120"
for s in 4220385 4220386 4220387 4220388; do
  [ -s $R-set-$s.json ] || onbase python scripts/stage2_eval.py --checkpoint $P $PA --pair-drill-reset --seed $s --json $R-set-$s.json > $R-set-$s.log 2>&1
  [ -s $R-old-$s.json ] || onbase python scripts/stage2_eval.py --checkpoint $P $PA --seed $s --json $R-old-$s.json > $R-old-$s.log 2>&1
done
if ! grep -q "^(reported) set-start baseline" $R-summary.txt; then
python - <<'PY' | tee -a $R-summary.txt
import json, sys
sys.path.insert(0, ".")
from picklebot_mj import d1_rule as dr
S = (4220385, 4220386, 4220387, 4220388)
f = [f"results/sr91-set-{s}.json" for s in S]
old = [f"results/sr91-old-{s}.json" for s in S]
pp = dr.pooled_pairs(f)
k = round(pp["p5"] * pp["rallies"])
lo, hi = dr.wilson(k, pp["rallies"])
print(f"(reported) set-start baseline C: P(5+) {pp['p5']:.4f} (Wilson {lo:.4f}-{hi:.4f}, rallies {pp['rallies']}); "
      f"places {[json.load(open(p))['launch_state']['drill_places'] for p in f]}")
for x in dr.set_start_report(f, old):
    print(x.replace("set start", "set-start (drill reset)").replace("standard", "old read, same seeds"))
print("(reported) per seed P(5+): set " + ", ".join(f"{dr.pooled_pairs([p])['p5']:.3f}" for p in f)
      + "; old " + ", ".join(f"{dr.pooled_pairs([p])['p5']:.3f}" for p in old))
PY
fi
# 4
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER
RUN=fw-act2-01; SRUN=fw-act2-01-smoke; T=Picklebot-Footwork-Specialist-Quick2-Strong-G1
L=artifacts/train/logs/picklebot_return_stand; R=results/act91
PRUN=2026-10-31_01-16-15_fw1b-S; PCK=model_16600.pt
ALG="--agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK --agent.algorithm.learning-rate 1e-5"
export PICKLEBOT_TRAIN_ENTRY=scripts/diag/footwork_train.py PICKLEBOT_AGILITY_LOG_EVERY=240 PICKLEBOT_ENVS=4096
if [ ! -f artifacts/train/$RUN.exit.json ]; then
  pgrep -f "run-name |distill_latent|footwork_eval|stage2_eval|feeder_speed|latent_reach_floor" > /dev/null && { echo "GPU busy: not started"; exit 1; }
fi
echo "D-229 stage 4: $RUN on $T (leg / waist / ankle effort x2) from fw1b-S $PCK; training seed 226, smoke 227; gate dev 4220384" | tee -a $R-summary.txt

# --- smoke -----------------------------------------------------------------------------------------------------------
if [ ! -f artifacts/train/$SRUN.exit.json ]; then
  PICKLEBOT_AGILITY_LOG=$R-smoke.jsonl PICKLEBOT_WALL_CAP=1500 bash scripts/diag/agility_train_run.sh $SRUN $T \
    --agent.seed 227 --agent.max-iterations 120 $ALG
fi
python - <<'PY' > /tmp/act91-smoke.txt 2>&1
import json, os, re, sys
sys.path.insert(0, "."); sys.path.insert(0, "scripts/diag")
from picklebot_mj import d1_rule as dr
from falls_by_length import falls_per_1000_env_s
log, ex = "artifacts/train/fw-act2-01-smoke.log", json.load(open("artifacts/train/fw-act2-01-smoke.exit.json"))
t = open(log, errors="ignore").read()
print("exit", ex["exit_code"], "ok" if ex["exit_code"] == 0 else "STOP")
print("traceback", "none ok" if "Traceback" not in t else "found STOP")
pay = [float(x) for x in re.findall(r"Episode_Reward/fw_first_step: ([0-9.eE+-]+)", t)]
print(f"fw_first_step paid: max episode mean {max(pay) if pay else None}", "ok" if pay and max(pay) > 0 else "STOP")
rows = [json.loads(x) for x in open("results/act91-smoke.jsonl")] if os.path.exists("results/act91-smoke.jsonl") else []
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
cat /tmp/act91-smoke.txt | tee -a $R-summary.txt
if [ "$(grep -c " ok$" /tmp/act91-smoke.txt)" != 5 ]; then
  echo "VERDICT: SMOKE-FAIL" | tee -a $R-summary.txt; echo done > artifacts/train/sr91.done; exit 0
fi

# --- train with kills -------------------------------------------------------------------------------------------------
if [ ! -f artifacts/train/$RUN.exit.json ]; then
  ( python - <<'PY' > $R-kill.txt 2>&1
import json, os, sys, tempfile, time
sys.path.insert(0, "."); sys.path.insert(0, "scripts/diag")
from picklebot_mj import d1_rule as dr
from falls_by_length import falls_per_1000_env_s
LOG, EXIT, J = "artifacts/train/fw-act2-01.log", "artifacts/train/fw-act2-01.exit.json", "results/act91-train.jsonl"
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
            os.system("pkill -f 'run-name fw-act2-01 '")
            break
    if not done_ns and n >= 470 and os.path.exists(J):
        rows = [json.loads(x) for x in open(J)]
        v, line = dr.quick_kill(rows, 16600)
        if v == "NO-DATA":
            continue
        done_ns = True
        print(f"+{n}: " + line, flush=True)
        old = [json.loads(x) for x in open("results/qk85-train.jsonl")]
        for lo, hi in ((30, 60), (60, 100), (400, 450)):
            print(f"(reported) window {lo}-{hi}: act2 {dr.first_window(rows, lo, hi, 16600)} | Q2 (D-222) {dr.first_window(old, lo, hi, 16600)}", flush=True)
        if v != "CONTINUE":
            os.system("pkill -f 'run-name fw-act2-01 '")
            break
PY
  ) &
  PICKLEBOT_AGILITY_LOG=$R-train.jsonl PICKLEBOT_WALL_CAP=7000 bash scripts/diag/agility_train_run.sh $RUN $T \
    --agent.seed 226 --agent.max-iterations 1500 $ALG
  wait
fi
echo "train: $(cat artifacts/train/$RUN.exit.json)" | tee -a $R-summary.txt; cat $R-kill.txt 2>/dev/null | tee -a $R-summary.txt
if grep -q "^VOID-unstable" $R-kill.txt 2>/dev/null; then echo "VERDICT: VOID-unstable" | tee -a $R-summary.txt; echo done > artifacts/train/sr91.done; exit 0; fi
if grep -q -- "-> KILL-NO-START" $R-kill.txt 2>/dev/null; then echo "VERDICT: KILL-NO-START" | tee -a $R-summary.txt; echo done > artifacts/train/sr91.done; exit 0; fi
if ! grep -q -- "-> CONTINUE" $R-kill.txt 2>/dev/null; then echo "VERDICT: NO-KILL-READ (the +450 line never read; stop, panel)" | tee -a $R-summary.txt; echo done > artifacts/train/sr91.done; exit 0; fi

# --- read, paired on dev 4220384 --------------------------------------------------------------------------------------
CK=$(ls $(ls -d $L/*_$RUN | tail -1)/model_*.pt | sort -V | tail -1); echo "endpoint $CK" | tee -a $R-summary.txt
for arm in fw quick; do
  [ -s $R-$arm.json ] && continue
  c=$L/$PRUN/$PCK; MT=Picklebot-Footwork-Measure60-Court-G1
  [ $arm = quick ] && { c=$CK; MT=Picklebot-Footwork-Measure60-Court-Strong-G1; }
  PICKLEBOT_FW_SAT=1 python scripts/diag/footwork_eval.py --task $MT --checkpoint $c --envs 1024 --seconds 120 \
    --seed 4220384 --move-prob 1.0 --json $R-$arm.json > $R-$arm.log 2>&1
done
python - <<'PY' | tee -a $R-summary.txt
import json, sys
sys.path.insert(0, ".")
from picklebot_mj import d1_rule as dr
t, w = (dr.agility(json.load(open(f"results/act91-{a}.json"))) for a in ("quick", "fw"))
v, lines = dr.quick_check(t, w)
for x in lines:
    print(x)
print("(reported) first-step p50 by sector, Q:", t["first_step_p50"], "fw1b-S:", w["first_step_p50"])
print("(reported) sustained p50 by sector, Q:", t["sustained_p50"], "fw1b-S:", w["sustained_p50"])
rows = [json.loads(x) for x in open("results/act91-train.jsonl")]
for lo in range(0, 1500, 250):
    print(f"(reported) training window {lo}-{lo + 250}:", dr.first_window(rows, lo, lo + 250, 16600))
print(f"VERDICT: {v}")
json.dump({"quick": t, "fw": w, "verdict": v}, open("results/act91-verdict.json", "w"), indent=1)
PY
echo done > artifacts/train/sr91.done

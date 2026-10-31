#!/usr/bin/env bash
# D-193 (panel round 60: C then A, coach / motion / RL): d1_base.sh (D-192) with its teacher check replaced. D-192's check
# read TEACHER-SLOW (results/d1-summary.txt, kept as failed): the 1.6 m/s sustained line was mis-calibrated for 0.5-3 m
# spots. Premise check, fresh dev 4220266: fw1b-S and model_15900 on Picklebot-Footwork-Measure60-Court-G1, mean actions
# -> PREMISE-OK if, in left and back, fw1b-S's first-step p50 <= the walker's - 0.25 s and fw1b-S passes D-188 validity
# (worst untimed arrival >= 0.80, fallen + censored <= 0.15); else PREMISE-FAIL (stop; D by the panel's vote). Then
# everything else exactly as D-192 (smoke 185, kickstart s5c-d1-fw1bS seed 184, kill rows 300-360, base gate dev
# 4220250-4220256). Outputs results/d1r-*; done marker artifacts/train/d1run.done.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER
while [ ! -f artifacts/train/fwfast4.done ]; do sleep 60; done
pgrep -f "run-name |distill_latent|footwork_eval|stage2_eval" > /dev/null && { echo "GPU busy: not started"; exit 1; }
L=artifacts/train/logs/picklebot_return_stand; R=results/d1r; RUN=s5c-d1-fw1bS
FW=$L/2026-10-31_01-16-15_fw1b-S/model_16600.pt; WALK=$L/2026-10-06_10-30-12_teacher-move-01/model_15900.pt
PAR_RUN=s5c-18-merge17; PAR=$L/2026-10-16_05-35-35_s5c-18-merge17/model_32874.pt
ARGS="--init $L/2026-10-15_23-08-22_s5c-15-kickstart2/model_31675.pt --hit-teacher $L/2026-10-16_03-26-46_s5c-17-court-l3-more/model_31400.pt --teacher $FW --lam-self 3.0 --hit-loss latent --beta-frac 0"
stop() { echo "VERDICT: $1" | tee -a $R-summary.txt; echo done > artifacts/train/d1run.done; exit 0; }
# 1. premise check (D-193)
for arm in fw walker; do
  [ -s $R-premise-$arm.json ] && continue
  c=$FW; [ $arm = walker ] && c=$WALK
  python scripts/diag/footwork_eval.py --task Picklebot-Footwork-Measure60-Court-G1 --checkpoint $c --envs 1024 --seconds 120 \
    --seed 4220266 --move-prob 1.0 --json $R-premise-$arm.json > $R-premise-$arm.log 2>&1
done
for a in fw walker; do [ -s $R-premise-$a.json ] || stop EVAL-FAIL-premise-$a; done
python - <<'PY' | tee $R-summary.txt
import json
from picklebot_mj import d1_rule as dr
v, lines = dr.premise_check(json.load(open("results/d1r-premise-fw.json")), json.load(open("results/d1r-premise-walker.json")))
print("\n".join(lines)); print(f"PREMISE: {v}")
PY
grep -q "PREMISE: PREMISE-OK" $R-summary.txt || stop PREMISE-FAIL
# 2. smoke + kickstart
if [ ! -f artifacts/train/$RUN-smoke.exit.json ]; then
  bash scripts/kickstart_run.sh $RUN-smoke $ARGS --envs 4096 --max-seconds 240 --seed 185
fi
python - <<'PY' | tee -a $R-summary.txt || stop SMOKE-FAIL
import glob, json, sys
ref = json.load(open(glob.glob("artifacts/train/logs/picklebot_return_stand/*_s5c-18-merge17/kickstart_log_*.json")[0]))["args"]
new = json.load(open(sorted(glob.glob("artifacts/train/logs/picklebot_return_stand/*_s5c-d1-fw1bS-smoke/kickstart_log_*.json"))[-1]))["args"]
free = {"run_name", "teacher", "seed", "envs", "max_seconds", "log_root"}
diff = {k: (ref.get(k), new.get(k)) for k in set(ref) | set(new) if k not in free and ref.get(k) != new.get(k)}
ok = not diff and new["teacher"].endswith("fw1b-S/model_16600.pt") and new["recover"] is False
print(f"smoke: args diff vs s5c-18 {diff}; teacher {new['teacher']} -> {'ok' if ok else 'FAIL'}")
sys.exit(0 if ok else 1)
PY
if [ ! -f artifacts/train/$RUN.exit.json ]; then
  ( python - <<'PY' > $R-kill.txt 2>&1
import os, time
from picklebot_mj import d1_rule as dr
LOG, EXIT = "artifacts/train/s5c-d1-fw1bS.log", "artifacts/train/s5c-d1-fw1bS.exit.json"
while not os.path.exists(EXIT):
    time.sleep(60)
    try:
        k = dr.kick_kill(dr.kick_rows(LOG))
    except FileNotFoundError:
        continue
    if k:
        print(k[1])
        if k[0] != "CONTINUE":
            os.system("pkill -f 'run-name s5c-d1-fw1bS '")
        break
PY
  ) &
  bash scripts/kickstart_run.sh $RUN $ARGS --envs 4096 --max-seconds 6900 --seed 184
  wait
fi
echo "kickstart: $(cat artifacts/train/$RUN.exit.json)" | tee -a $R-summary.txt; cat $R-kill.txt | tee -a $R-summary.txt
grep -q "KILL-" $R-kill.txt && stop "$(grep -o 'KILL-[A-Z-]*' $R-kill.txt)"
DIR=$(ls -d $L/*_$RUN | tail -1); CK=$(ls $DIR/model_*.pt | sort -V | tail -1); echo "endpoint $CK" | tee -a $R-summary.txt
python -c "
from picklebot_mj import d1_rule as dr; r = dr.kick_rows('artifacts/train/$RUN.log')
print(f'iterations {len(r)} (s5c-18: 1,199); final mse_move {r[-1][\"mse_move\"]} (s5c-18: 0.0336), mse_hit {r[-1][\"mse_hit\"]}')" | tee -a $R-summary.txt
# 3. base gate
for arm in parent child; do
  [ -s $R-agility-$arm.json ] && continue
  c=$PAR; [ $arm = child ] && c=$CK
  python scripts/diag/footwork_eval.py --task Picklebot-Footwork-Measure60-L3Base-G1 --checkpoint $c --envs 1024 --seconds 120 \
    --seed 4220250 --move-prob 1.0 --json $R-agility-$arm.json > $R-agility-$arm.log 2>&1
done
[ -s results/stage5c-d1-parent-court.json ] || bash scripts/h5c_eval.sh $PAR_RUN model_32874.pt d1-parent 4220251 \
  Picklebot-Latent-Court-L3-G1 Picklebot-Latent-Drill3-Prior5-L3-G1 > $R-h5c-parent.log 2>&1
[ -s results/stage5c-d1-child-court.json ] || bash scripts/h5c_eval.sh $RUN $(basename $CK) d1-child 4220251 \
  Picklebot-Latent-Court-L3-G1 Picklebot-Latent-Drill3-Prior5-L3-G1 > $R-h5c-child.log 2>&1
for a in agility-parent agility-child; do [ -s $R-$a.json ] || stop EVAL-FAIL-$a; done
python - <<'PY' | tee -a $R-summary.txt
import json
from picklebot_mj import d1_rule as dr
spec = json.load(open("results/fw1d-C.json"))["footwork_route"]["sectors"]
av, a = dr.agility_verdict(json.load(open("results/d1r-agility-child.json")), json.load(open("results/d1r-agility-parent.json")), spec)
for arm in ("parent", "child"):
    print(arm, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in a[arm].items()})
print(f"agility: valid {a['valid']}, first-step L/B no slower {a['first_step_ok']}, R_LB {a['parent']['R_LB']:.3f} -> "
      f"{a['child']['R_LB']:.3f} -> {av}")
p, c = dr.hitting("d1-parent"), dr.hitting("d1-child")
rv, lines, drift = dr.retention(c, p)
print("hitting parent", p); print("hitting child", c); print("\n".join(lines))
print(f"retention: {rv}" + (f"; PROTOCOL-DRIFT (parent main {p['main']:.4f} vs archived {dr.ARCHIVED_MAIN})" if drift else ""))
v = dr.base_verdict(av, rv)
json.dump({"agility": a, "agility_verdict": av, "hitting": {"parent": p, "child": c}, "retention": rv, "drift": drift,
           "verdict": v}, open("results/d1r-summary.json", "w"), indent=1, default=str)
print(f"VERDICT: {v}")
PY
echo done > artifacts/train/d1run.done

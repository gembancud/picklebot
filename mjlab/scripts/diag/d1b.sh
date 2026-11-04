#!/usr/bin/env bash
# D-213 (panel round 77, (ii) 4 of 5): d1b, the base rebuilt with Fast4 as the move-episode teacher. Coded lines:
# picklebot_mj/d1_rule.py (fast4_check; kick_kill, agility_verdict, retention, base_verdict unchanged from D-192).
#  A. Teacher read, dev 4220357: Fast4 (fw-fast4-01 model_18099) and fw1b-S model_16600 on
#     Picklebot-Footwork-Measure60-Court-G1, mean actions, 1,024 envs, 120 s -> D1B-OK / TEACHER-NOT-READY (stop, panel).
#  B. Smoke (training seed 210, 4,096 envs, 240 s): kickstart_log args equal d1's (s5c-d1-fw1bS) except run_name, teacher,
#     seed, envs, max_seconds; teacher = Fast4. Then kickstart s5c-d1b-fast4, training seed 209, d1's flags (no --recover):
#     kill at log rows 300-360 (KILL-NO-FIT / KILL-HIT-INTERFERE).
#  C. Base gate, paired against the d1 base s5c-d1-fw1bS model_32854: agility on Picklebot-Footwork-Measure60-L3Base-G1,
#     dev 4220358; hitting on the D-086 battery (h5c_eval.sh), dev 4220359-4220364 -> BASE-PASS / INVALID / CAP-HELD /
#     REJECTED. A BASE-PASS is not a rally claim and nothing is promoted: the rally re-climb is its own entry.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER PICKLEBOT_PAIR_LOG
pgrep -f "run-name |distill_latent|footwork_eval|stage2_eval|feeder_speed|latent_reach_floor" > /dev/null && { echo "GPU busy: not started"; exit 1; }
L=artifacts/train/logs/picklebot_return_stand; R=results/d1b; RUN=s5c-d1b-fast4
F4=$L/2026-10-31_15-22-10_fw-fast4-01/model_18099.pt; FW=$L/2026-10-31_01-16-15_fw1b-S/model_16600.pt
PAR_RUN=s5c-d1-fw1bS; PAR=$L/2026-10-31_18-24-20_s5c-d1-fw1bS/model_32854.pt
ARGS="--init $L/2026-10-15_23-08-22_s5c-15-kickstart2/model_31675.pt --hit-teacher $L/2026-10-16_03-26-46_s5c-17-court-l3-more/model_31400.pt --teacher $F4 --lam-self 3.0 --hit-loss latent --beta-frac 0"
for f in $F4 $FW $PAR; do [ -f $f ] || { echo "missing $f"; exit 1; }; done
stop() { echo "VERDICT: $1" | tee -a $R-summary.txt; echo done > artifacts/train/d1b.done; exit 0; }
# A. teacher read
for arm in fast4 fw; do
  [ -s $R-teacher-$arm.json ] && continue
  c=$F4; [ $arm = fw ] && c=$FW
  python scripts/diag/footwork_eval.py --task Picklebot-Footwork-Measure60-Court-G1 --checkpoint $c --envs 1024 --seconds 120 \
    --seed 4220357 --move-prob 1.0 --json $R-teacher-$arm.json > $R-teacher-$arm.log 2>&1
done
for a in fast4 fw; do [ -s $R-teacher-$a.json ] || stop EVAL-FAIL-teacher-$a; done
python - <<'PY' | tee $R-summary.txt
import json
from picklebot_mj import d1_rule as dr
t, w = (dr.agility(json.load(open(f"results/d1b-teacher-{a}.json"))) for a in ("fast4", "fw"))
for n, a in (("fast4", t), ("fw1b-S", w)):
    print(n, {k: (round(x, 3) if isinstance(x, float) else x) for k, x in a.items()})
v, lines = dr.fast4_check(t, w)
print("\n".join(lines)); print(f"TEACHER: {v}")
PY
grep -q "TEACHER: D1B-OK" $R-summary.txt || stop TEACHER-NOT-READY
# B. smoke + kickstart
if [ ! -f artifacts/train/$RUN-smoke.exit.json ]; then
  bash scripts/kickstart_run.sh $RUN-smoke $ARGS --envs 4096 --max-seconds 240 --seed 210
fi
python - <<'PY' | tee -a $R-summary.txt || stop SMOKE-FAIL
import glob, json, sys
ref = json.load(open(sorted(glob.glob("artifacts/train/logs/picklebot_return_stand/*_s5c-d1-fw1bS/kickstart_log_*.json"))[-1]))["args"]
new = json.load(open(sorted(glob.glob("artifacts/train/logs/picklebot_return_stand/*_s5c-d1b-fast4-smoke/kickstart_log_*.json"))[-1]))["args"]
free = {"run_name", "teacher", "seed", "envs", "max_seconds", "log_root"}
diff = {k: (ref.get(k), new.get(k)) for k in set(ref) | set(new) if k not in free and ref.get(k) != new.get(k)}
ok = not diff and new["teacher"].endswith("fw-fast4-01/model_18099.pt") and new["recover"] is False
print(f"smoke: args diff vs d1 {diff}; teacher {new['teacher']} -> {'ok' if ok else 'FAIL'}")
sys.exit(0 if ok else 1)
PY
if [ ! -f artifacts/train/$RUN.exit.json ]; then
  ( python - <<'PY' > $R-kill.txt 2>&1
import os, time
from picklebot_mj import d1_rule as dr
LOG, EXIT = "artifacts/train/s5c-d1b-fast4.log", "artifacts/train/s5c-d1b-fast4.exit.json"
while not os.path.exists(EXIT):
    time.sleep(60)
    try:
        k = dr.kick_kill(dr.kick_rows(LOG))
    except FileNotFoundError:
        continue
    if k:
        print(k[1])
        if k[0] != "CONTINUE":
            os.system("pkill -f 'run-name s5c-d1b-fast4 '")
        break
PY
  ) &
  bash scripts/kickstart_run.sh $RUN $ARGS --envs 4096 --max-seconds 6900 --seed 209
  wait
fi
echo "kickstart: $(cat artifacts/train/$RUN.exit.json)" | tee -a $R-summary.txt; cat $R-kill.txt | tee -a $R-summary.txt
grep -q "KILL-" $R-kill.txt && stop "$(grep -o 'KILL-[A-Z-]*' $R-kill.txt)"
DIR=$(ls -d $L/*_$RUN | tail -1); CK=$(ls $DIR/model_*.pt | sort -V | tail -1); echo "endpoint $CK" | tee -a $R-summary.txt
python -c "
from picklebot_mj import d1_rule as dr; r = dr.kick_rows('artifacts/train/$RUN.log')
print(f'iterations {len(r)}; final mse_move {r[-1][\"mse_move\"]}, mse_hit {r[-1][\"mse_hit\"]}')" | tee -a $R-summary.txt
# C. base gate (paired against the d1 base)
for arm in parent child; do
  [ -s $R-agility-$arm.json ] && continue
  c=$PAR; [ $arm = child ] && c=$CK
  python scripts/diag/footwork_eval.py --task Picklebot-Footwork-Measure60-L3Base-G1 --checkpoint $c --envs 1024 --seconds 120 \
    --seed 4220358 --move-prob 1.0 --json $R-agility-$arm.json > $R-agility-$arm.log 2>&1
done
[ -s results/stage5c-d1b-parent-court.json ] || bash scripts/h5c_eval.sh $PAR_RUN model_32854.pt d1b-parent 4220359 \
  Picklebot-Latent-Court-L3-G1 Picklebot-Latent-Drill3-Prior5-L3-G1 > $R-h5c-parent.log 2>&1
[ -s results/stage5c-d1b-child-court.json ] || bash scripts/h5c_eval.sh $RUN $(basename $CK) d1b-child 4220359 \
  Picklebot-Latent-Court-L3-G1 Picklebot-Latent-Drill3-Prior5-L3-G1 > $R-h5c-child.log 2>&1
for a in agility-parent agility-child; do [ -s $R-$a.json ] || stop EVAL-FAIL-$a; done
python - <<'PY' | tee -a $R-summary.txt
import json
from picklebot_mj import d1_rule as dr
spec = json.load(open("results/fw1d-C.json"))["footwork_route"]["sectors"]
av, a = dr.agility_verdict(json.load(open("results/d1b-agility-child.json")), json.load(open("results/d1b-agility-parent.json")), spec)
for arm in ("parent", "child"):
    print(arm, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in a[arm].items()})
print(f"agility: valid {a['valid']}, first-step L/B no slower {a['first_step_ok']}, R_LB {a['parent']['R_LB']:.3f} -> "
      f"{a['child']['R_LB']:.3f} -> {av}")
p, c = dr.hitting("d1b-parent"), dr.hitting("d1b-child")
rv, lines, drift = dr.retention(c, p)
print("hitting parent", p); print("hitting child", c); print("\n".join(lines))
print(f"retention: {rv}" + (f"; PROTOCOL-DRIFT (parent main {p['main']:.4f} vs archived {dr.ARCHIVED_MAIN})" if drift else ""))
v = dr.base_verdict(av, rv)
json.dump({"agility": a, "agility_verdict": av, "hitting": {"parent": p, "child": c}, "retention": rv, "drift": drift,
           "verdict": v}, open("results/d1b-summary.json", "w"), indent=1, default=str)
print(f"VERDICT: {v}")
PY
echo done > artifacts/train/d1b.done

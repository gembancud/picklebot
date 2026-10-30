#!/usr/bin/env bash
# Footwork phase step 1 confirmation (D-182, panel round 52: (a) 5 of 5). Frozen before it runs; one shot, no re-read.
#   Sole candidate: fw1b-S model_16600 (fw1c's B0; fw1c-A is a killed arm, ineligible).
#   Read C (gating): mean actions (scripts/stage2_eval.py, observation corruption off), Picklebot-Footwork-Measure60-G1,
#     1,024 envs, 120 s, development seed 4220212, through scripts/diag/footwork_eval.py: bodyspeed_rule.route unchanged,
#     falls = 1000 robot_falls / (envs x sim_seconds), config check in code.
#     STEP1 = "BODY-OK(mean-action)" if the verdict is BODY-OK, else "not answered (fw1c MIXED stands)".
#   Read CN (reported, not gating): the same with the task's observation corruption kept on (--keep-corruption), seed
#     4220213: splits action noise from observation noise in the stochastic read's held-arrival failure.
#   Heading gate (coach, pre-registered for the NEXT step, not for STEP1): on read C, if more than 20 % of the back,
#     back-left and back-right moves (pooled) are more than 90 deg from facing the net at mid-move, the heading limit
#     comes before step 2's clips.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER
pgrep -f "run-name " > /dev/null && { echo "a trainer is running: not started"; exit 1; }
CK=artifacts/train/logs/picklebot_return_stand/2026-10-31_01-16-15_fw1b-S/model_16600.pt
R=results/fw1d
for read in "C 4220212" "CN 4220213 --keep-corruption"; do
  set -- $read
  tag=$1; seed=$2; shift 2
  [ -s $R-$tag.json ] && { echo "$R-$tag.json exists: not re-read"; continue; }
  python scripts/diag/footwork_eval.py --task Picklebot-Footwork-Measure60-G1 --checkpoint $CK --envs 1024 --seconds 120 \
    --seed $seed --move-prob 1.0 --json $R-$tag.json "$@" > $R-$tag.log 2>&1
  echo "== read $tag (seed $seed $*)"; grep -A30 "^forward " $R-$tag.log | grep -v "^\[INFO\]"
done
python - <<'PY' | tee $R-summary.txt
import json
c = json.load(open("results/fw1d-C.json"))["footwork_route"]
step1 = "BODY-OK(mean-action)" if c["verdict"] == "BODY-OK" else "not answered (fw1c MIXED stands)"
h = json.load(open("results/fw1d-C.json"))["move_drill"]["footwork"]["mid_heading_hist"]
back = [h[i] for i in (3, 4, 5)]
over = sum(sum(x[9:]) for x in back) / max(1, sum(sum(x) for x in back))
print(f"read C verdict {c['verdict']} -> STEP1 = {step1}")
print(f"heading gate: back moves > 90 deg at mid-move {over:.3f} (> 0.20 -> heading limit before step 2): "
      f"{'HEADING-LIMIT-FIRST' if over > 0.20 else 'STEP-2-CLIPS'}")
try:
    cn = json.load(open("results/fw1d-CN.json"))["footwork_route"]
    print("read CN (reported):", cn["verdict"], "untimed min", min(s["arrival"] for s in cn["sectors"]))
except FileNotFoundError:
    print("read CN missing")
json.dump({"step1": step1, "read_C": c["verdict"], "back_over90": over}, open("results/fw1d-summary.json", "w"), indent=1)
PY
echo done > artifacts/train/fw1d.done

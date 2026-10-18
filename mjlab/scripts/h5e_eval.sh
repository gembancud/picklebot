#!/usr/bin/env bash
# Stage 5E evaluation of one fixed endpoint (D-101, frozen). Development seeds S..S+15 only.
# Usage: h5e_eval.sh RUN CKFILE TAG SEED TASK_V2 TASK_COURT TASK_5B   -> results/stage5e-TAG-*.json
#   v2-noisy : drill v2 with the noisy, delayed planner's spot (the gate's per-shot p and group floors), 90 s rallies
#   v2-clean : the same with the clean planner's spot (true ball state and spin)
#   v2-off   : the same without a spot (the robot reads the ball alone)
#   then the Stage 5C battery (h5c_eval.sh on seeds S+10..S+15): court drill (main metric, falls), move-to-spot
#   arrival, Stage 5B drill, recovery, the Stage 5D rally evaluation and style (old reference).
# All drill v2 jobs run with sim-to-real latency and noise on (the task's settings).
set -uo pipefail
cd "$(dirname "$0")/.."
RUN=$1; CK=$2; TAG=$3; S=$4; TV2=$5; TC=$6; T5B=$7; R=results/stage5e-$TAG; FAIL=0
A="--task $TV2 --envs 1024 --seconds 90 --move-prob 0.0 --swing-prob 0.0 --target A --no-hint --rally"
i=0
for P in noisy clean off; do
  bash scripts/stage2_eval.sh $RUN $CK $A --planner $P --seed $((S+i)) --json $R-v2-$P.json > /tmp/h5e_$TAG.log 2>&1
  c=$?; echo "v2-$P: $c"; [ $c -eq 0 ] || FAIL=1; i=$((i+1))
done
bash scripts/h5c_eval.sh $RUN $CK $TAG-5c $((S+10)) $TC $T5B || FAIL=1
~/envs/picklebot-mj/bin/python - "$R" <<'PY'
import json, sys
R = sys.argv[1]
for p in ("noisy", "clean", "off"):
    d = json.load(open(f"{R}-v2-{p}.json"))
    v, r = d["drill_v2"], d["rally"]
    g = {k: (x["legal_return"], x["ci95"][0]) for k, x in v["groups"].items()}
    print(f"v2-{p}: p {v['per_shot_p']} {v['per_shot_ci95']}; groups (p, Wilson low) {g}; "
          f"P(rally>=5) {r['p_reach_5']}; P(rally>=10) {r['p_reach_n']}; falls/episode {v['court_falls_per_episode']}")
PY
exit $FAIL

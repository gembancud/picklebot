#!/usr/bin/env bash
# Diagnostic measure read (D-181) of fw1b arm S's last checkpoint (model_16600, killed at iteration 726 on the D-180
# untimed-arrival kill line): footwork_fw1b.sh's measure() unchanged (Picklebot-Footwork-Measure-G1, spots 3-5 m,
# learning rate 0, 100 iterations, 4,096 envs, stochastic actions), training seed 167. Reported, never a verdict.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER
pgrep -f "run-name " > /dev/null && { echo "a trainer is running: not started"; exit 1; }
R=results/fw1b-S-diag-measure; RUN=2026-10-31_01-16-15_fw1b-S; CK=model_16600.pt
[ -s $R.jsonl ] && { echo "$R.jsonl exists"; exit 1; }
PICKLEBOT_TRAIN_ENTRY=scripts/diag/footwork_train.py PICKLEBOT_LR_PEAK=0 PICKLEBOT_LR_WARMUP=50 PICKLEBOT_LR_TOTAL=0 \
  PICKLEBOT_KL_GUARD=0.05 PICKLEBOT_STD_MIN=0 PICKLEBOT_AGILITY_LOG=$R.jsonl PICKLEBOT_AGILITY_LOG_EVERY=240 \
  PICKLEBOT_ENVS=4096 PICKLEBOT_WALL_CAP=2400 bash scripts/diag/agility_train_run.sh fw1b-S-diag-measure \
  Picklebot-Footwork-Measure-G1 --agent.seed 167 --agent.max-iterations 100 --agent.resume True --agent.load-run $RUN \
  --agent.load-checkpoint $CK --agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO
python - <<'PY' | tee $R.txt
import sys
sys.path.insert(0, "scripts/diag")
from falls_by_length import falls_per_1000_env_s
from picklebot_mj import agility_rule as ar, bodyspeed_rule as bsr
c = ar.window(ar.read_rows("results/fw1b-S-diag-measure.jsonl"), "move", 0.0, 1.0)
falls = falls_per_1000_env_s("artifacts/train/fw1b-S-diag-measure.log", envs=4096)[0]
r = bsr.route(c, falls, [])
for s in r["sectors"]:
    fin = s["arrived"] + s["timed_out"] + s["fell"]
    print(s["name"], "sustained", s["sustained_p50"], "/", s["sustained_p90"], "peak", s["peak_p50"], "untimed", s["arrival"],
          "deadline", round(c["deadline"][s["sector"]] / max(1, fin), 3), "fell", s["fell"], "censored", s["censored"])
print("censored share", r["censored_share"], "falls/1000 env-s", round(falls, 3))
for line in r["lines"]:
    print(" ", line)
print("rule output (diagnostic only):", r["verdict"])
PY
echo done > artifacts/train/fw1b-S-diag-measure.done

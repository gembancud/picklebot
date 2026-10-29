#!/usr/bin/env bash
# Second agility screen (D-172, panel round 48: the first screen's deadline could not be met by construction). Same drill,
# arms, parents, iterations, envs, learning rates and std floors as scripts/diag/agility_screen.sh; one change: the drill's
# deadline arrival is the FIRST ENTRY within 0.25 m of the spot at elapsed <= deadline (no speed or hold condition;
# untimed arrival stays MoveDrill's held arrival; command law unchanged). Tasks Picklebot-Agility-Deadline2-* in
# picklebot_mj/tasks/agility.py. Rule thresholds unchanged; the summary applies the D-172 validity gates (--gates):
# A0 VALID only if 10 <= DA(FR) <= 90 and untimed >= 90 % in every sector, F VALID only if censored / issued <= 10 %.
# Before any arm, the coded CPU positive control (picklebot_mj/agility_control.py: a point mass following the drill's own
# command through a 0.2 s lag) must reach DA >= 90 % in every sector on each task's drill, and the same control on the
# first screen's (hold) drill must stay below 10 %; otherwise nothing is launched.
#   A0 (seed 144): P = run 18b model_29000, lam_r 2 residual, learning rate 0, 100 iterations, 4,096 envs: D0
#   A  (seed 145): P at 1e-4 with P's Adam state, 400 iterations, 4,096 envs
#   F  (seed 146): flat walking teacher teacher-move-01/model_15900 on the same drill (its own task), 1e-4, 400 iterations,
#                  4,096 envs; std floor 0.05
#   B  (seed 147): only if the gated summary says B is triggered: P widened to lam_r 3 with the exact init, 1e-4,
#                  400 iterations, 4,096 envs; agility_screen2.sh B <run-dir-name> <model_N.pt>
# The ball-side (DirTally) arm is not re-run. Counters: results/agility2-<arm>.jsonl (every 240 env steps).
# Usage: bash scripts/diag/agility_screen2.sh [main | B RUN CK | control | summary]
# Refuses while any rally-, anchor48- or agility trainer is alive, and refuses an arm whose output exists.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER
STAGE=${1:-main}
L=artifacts/train/logs/picklebot_return_stand; R=results/agility2
PRUN=2026-10-28_12-03-16_rally-18b-sched; PCK=model_29000.pt
FRUN=2026-10-06_10-30-12_teacher-move-01; FCK=model_15900.pt
TRES=Picklebot-Agility-Deadline2-LamR2-G1; TRES3=Picklebot-Agility-Deadline2-LamR3-G1
TTEA=Picklebot-Agility-Deadline2-Teacher-Move-G1
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
export PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_KL_GUARD=0.05 PICKLEBOT_LR_TOTAL=0 PICKLEBOT_AGILITY_LOG_EVERY=240

busy() { pgrep -f "run-name (rally-|anchor48-|agility)" > /dev/null; }  # rally, anchor48, agility / agility2 trainers
control() { # CPU only (the GPU may be in use): refuse to launch unless the positive control passes on every task
  CUDA_VISIBLE_DEVICES= python -m picklebot_mj.agility_control --task $TRES --task $TRES3 --task $TTEA \
    --json $R-control.json | tee $R-control.txt
  [ "${PIPESTATUS[0]}" -eq 0 ] || { echo "positive control FAILED: no arm launched"; return 1; }
}
arm() { # tag task seed iterations envs lr std_min load_run load_ck
  local tag=$1 task=$2 seed=$3 it=$4 envs=$5 lr=$6 smin=$7 run=$8 ck=$9 out=$R-$1.jsonl
  [ -f $L/$run/$ck ] || { echo "missing checkpoint $L/$run/$ck"; return 1; }
  [ -e $out ] && { echo "$out exists: arm $tag already ran (fresh output only; move it aside to re-run)"; return 1; }
  [ -e artifacts/train/agility2-$tag.log ] && { echo "artifacts/train/agility2-$tag.log exists: arm $tag already ran"; return 1; }
  busy && { echo "a rally-, anchor48- or agility trainer is running: arm $tag not started"; return 1; }
  echo "arm $tag: $task seed $seed, $it iterations, $envs envs, lr $lr, std floor $smin, from $run/$ck"
  PICKLEBOT_LR_PEAK=$lr PICKLEBOT_STD_MIN=$smin PICKLEBOT_AGILITY_LOG=$out PICKLEBOT_SCHED_LOG=$R-$tag-sched.jsonl \
    PICKLEBOT_ENVS=$envs PICKLEBOT_WALL_CAP=3600 bash scripts/diag/agility_train_run.sh agility2-$tag $task \
    --agent.seed $seed --agent.max-iterations $it --agent.resume True --agent.load-run $run --agent.load-checkpoint $ck $ALG
  cat artifacts/train/agility2-$tag.exit.json
  grep -a -E "Traceback|Error" artifacts/train/agility2-$tag.log | head -3
  [ -s $out ] || { echo "arm $tag wrote no counters"; return 1; }
}
summary() { python scripts/diag/agility_summary.py --prefix $R --json $R-summary.json --gates | tee $R-summary.txt; }

case $STAGE in
  main)
    busy && { echo "a rally-, anchor48- or agility trainer is running: not started"; exit 1; }
    control || exit 1
    arm A0 $TRES 144 100 4096 0 0.1 $PRUN $PCK || exit 1
    arm A $TRES 145 400 4096 1e-4 0.1 $PRUN $PCK || exit 1
    arm F $TTEA 146 400 4096 1e-4 0.05 $FRUN $FCK || exit 1
    summary
    echo done > artifacts/train/agility2-screen.done;;
  B)
    BRUN=${2:?B init run dir}; BCK=${3:?B init checkpoint}
    python - $R-summary.json <<'PY' || { echo "B is not triggered by the gated summary: not run"; exit 1; }
import json, sys
sys.exit(0 if json.load(open(sys.argv[1]))["route"]["b_triggered"] else 1)
PY
    control || exit 1
    arm B $TRES3 147 400 4096 1e-4 0.1 $BRUN $BCK || exit 1
    summary;;
  control) control;;
  summary) summary;;
  *) echo "usage: $0 [main | B RUN CK | control | summary]"; exit 2;;
esac

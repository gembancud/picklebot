#!/usr/bin/env bash
# Agility screen (docs/research/footwork-route-2026-10-29.md section 6; training-side, diagnostic only, about 1.6-2 GPU-h
# est.). Move-only deadline drill (picklebot_mj/tasks/deadline_drill.py): spots 1.0-3.0 m, uniform over 8 sectors,
# v_req ~ U(1.2, 2.0) m/s, deadline 0.3 s + d / v_req, command cap v_req, heading free beyond 1 m. Per-sector counters
# go to results/agility-<arm>.jsonl (PICKLEBOT_AGILITY_LOG, every 240 env steps). ScheduledPPO as in
# scripts/diag/train_share_b2.sh (no warm-up, no cooldown, KL guard 0.05, critic warm-up 0). Training seeds 130-134.
#   A0   (seed 130): P = run 18b model_29000, lam_r 2 residual, learning rate 0, 100 iterations, 4,096 envs: D0
#   A    (seed 131): P at 1e-4 with P's Adam state, 400 iterations, 4,096 envs
#   F    (seed 132): flat walking teacher teacher-move-01/model_15900 on the same drill (its own task), 1e-4, 400 iterations,
#                    4,096 envs; std floor 0.05 (its smallest std is 0.066: the usual 0.1 floor would change it at start)
#   BALL (seed 133): rally run 14's task unchanged + feeder-ball direction tally, learning rate 0, 200 iterations, 1,024 envs
#   B    (seed 134): only if the summary says B is triggered (A fails rule 2 and A's LB saturation share >= 25 %): P widened
#                    to lam_r 3 with the exact init (section 5b), 1e-4, 400 iterations, 4,096 envs. The init is not built
#                    here; pass its run dir and checkpoint: agility_screen.sh B <run-dir-name> <model_N.pt>
# The summary (scripts/diag/agility_summary.py) prints the coded PASS / FAIL route (E, C, b, reading, lower the band).
# Usage: bash scripts/diag/agility_screen.sh [main | B RUN CK | summary]
# Do not start while another run uses the GPU (rally run 22): the script refuses if run 22's trainer is alive.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER
STAGE=${1:-main}
L=artifacts/train/logs/picklebot_return_stand; R=results/agility
PRUN=2026-10-28_12-03-16_rally-18b-sched; PCK=model_29000.pt
FRUN=2026-10-06_10-30-12_teacher-move-01; FCK=model_15900.pt
TRES=Picklebot-Agility-Deadline-LamR2-G1; TRES3=Picklebot-Agility-Deadline-LamR3-G1
TTEA=Picklebot-Agility-Deadline-Teacher-Move-G1; TBALL=Picklebot-Agility-DirTally-LamR2-G1
ALG="--agent.algorithm.class-name picklebot_mj.rl.sched_ppo:ScheduledPPO"
export PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_LR_WARMUP=0 PICKLEBOT_KL_GUARD=0.05 PICKLEBOT_LR_TOTAL=0 PICKLEBOT_AGILITY_LOG_EVERY=240

busy() { pgrep -f "run-name rally-" > /dev/null; }  # any rally trainer (run 22b, D-170, and later)
arm() { # tag task seed iterations envs lr std_min load_run load_ck
  local tag=$1 task=$2 seed=$3 it=$4 envs=$5 lr=$6 smin=$7 run=$8 ck=$9 out=$R-$1.jsonl
  [ -f $L/$run/$ck ] || { echo "missing checkpoint $L/$run/$ck"; return 1; }
  [ -s $out ] && { echo "$out exists: arm $tag already ran (fresh output dirs only; move it aside to re-run)"; return 1; }
  busy && { echo "rally run 22 is training: arm $tag not started"; return 1; }
  echo "arm $tag: $task seed $seed, $it iterations, $envs envs, lr $lr, std floor $smin, from $run/$ck"
  PICKLEBOT_LR_PEAK=$lr PICKLEBOT_STD_MIN=$smin PICKLEBOT_AGILITY_LOG=$out PICKLEBOT_SCHED_LOG=$R-$tag-sched.jsonl \
    PICKLEBOT_ENVS=$envs PICKLEBOT_WALL_CAP=3600 bash scripts/diag/agility_train_run.sh agility-$tag $task \
    --agent.seed $seed --agent.max-iterations $it --agent.resume True --agent.load-run $run --agent.load-checkpoint $ck $ALG
  cat artifacts/train/agility-$tag.exit.json
  grep -a -E "Traceback|Error" artifacts/train/agility-$tag.log | head -3
  [ -s $out ] || { echo "arm $tag wrote no counters"; return 1; }
}
summary() { python scripts/diag/agility_summary.py --prefix $R --json $R-summary.json | tee $R-summary.txt; }

case $STAGE in
  main)
    arm A0 $TRES 130 100 4096 0 0.1 $PRUN $PCK || exit 1
    arm A $TRES 131 400 4096 1e-4 0.1 $PRUN $PCK || exit 1
    arm F $TTEA 132 400 4096 1e-4 0.05 $FRUN $FCK || exit 1
    arm BALL $TBALL 133 200 1024 0 0.1 $PRUN $PCK || exit 1
    summary
    echo done > artifacts/train/agility-screen.done;;
  B)
    BRUN=${2:?B init run dir}; BCK=${3:?B init checkpoint}
    python - $R-summary.json <<'PY' || { echo "B is not triggered by the summary: not run"; exit 1; }
import json, sys
sys.exit(0 if json.load(open(sys.argv[1]))["route"]["b_triggered"] else 1)
PY
    arm B $TRES3 134 400 4096 1e-4 0.1 $BRUN $BCK || exit 1
    summary;;
  summary) summary;;
  *) echo "usage: $0 [main | B RUN CK | summary]"; exit 2;;
esac

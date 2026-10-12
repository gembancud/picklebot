#!/usr/bin/env bash
# Training-throughput benchmark (D-065): a few PPO iterations of TASK at several env counts, from scratch into a
# scratch log root. Reports steps/s (rsl_rl's own counter, last iterations), iteration time and GPU utilisation/memory.
# Usage: bench_envs.sh TASK ITERS ENVS...
set -uo pipefail
cd "$(dirname "$0")/.."
source ~/envs/picklebot-mj/bin/activate
export PYTHONWARNINGS=ignore
T=$1; IT=$2; shift 2
mkdir -p artifacts/smoke/bench
for N in "$@"; do
  L=artifacts/smoke/bench/$N.log; G=artifacts/smoke/bench/$N.gpu
  nvidia-smi --query-gpu=utilization.gpu,memory.used,power.draw --format=csv,noheader,nounits -l 2 > $G &
  SMI=$!
  timeout 1500s train $T --env.scene.num-envs $N --agent.max-iterations $IT --agent.logger tensorboard \
    --agent.run-name bench-$N --log-root artifacts/smoke/logs --agent.seed 1 > $L 2>&1 < /dev/null
  kill $SMI 2>/dev/null
  SPS=$(grep -a "Steps per second" $L | tail -3 | awk '{s+=$4} END {printf "%.0f", s/NR}')
  ITT=$(grep -a "Iteration time" $L | tail -3 | awk '{gsub("s","",$3); s+=$3} END {printf "%.2f", s/NR}')
  GPU=$(tail -n +6 $G | awk -F', ' '{u+=$1; if ($2>m) m=$2; p+=$3; n++} END {printf "util %.0f%%, mem max %d MiB, power %.0f W", u/n, m, p/n}')
  ERR=$(grep -aE "Traceback|out of memory|Error" $L | head -1)
  echo "envs $N: $SPS steps/s, $ITT s/iteration, $GPU ${ERR:+[ERROR: $ERR]}"
done

#!/usr/bin/env bash
# Stage 0 throughput benchmark: short G1 flat-velocity runs at several env counts.
# Records mean iteration time (excluding the first 5 warm-up iterations) and peak GPU memory.
# Usage (WSL): bash -l mjlab/scripts/stage0_throughput.sh [iterations] [env counts...]
set -uo pipefail
ITERS="${1:-30}"; shift || true
COUNTS=("${@:-1024 2048 4096 8192}")
[ $# -eq 0 ] && COUNTS=(1024 2048 4096 8192)
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$REPO/mjlab/artifacts/stage0/throughput"
mkdir -p "$OUT"
source "$HOME/envs/picklebot-mj/bin/activate"
export PYTHONWARNINGS=ignore
cd "$REPO/mjlab"
RESULTS="$OUT/results.csv"
echo "num_envs,iterations,steps_per_iter,mean_iter_s,mean_collect_s,mean_learn_s,steps_per_s,peak_gpu_mib,exit_code" > "$RESULTS"
for N in "${COUNTS[@]}"; do
  LOG="$OUT/train-$N.log"; MEM="$OUT/gpu-$N.csv"
  nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -lms 500 > "$MEM" &
  SMI=$!
  train Mjlab-Velocity-Flat-Unitree-G1 \
    --env.scene.num-envs "$N" --agent.max-iterations "$ITERS" \
    --agent.logger tensorboard --agent.seed 1 --agent.run-name "bench-$N" \
    --agent.save-interval 100000 --log-root "$OUT/logs" > "$LOG" 2>&1
  CODE=$?
  kill $SMI 2>/dev/null; wait $SMI 2>/dev/null
  python - "$LOG" "$MEM" "$N" "$ITERS" "$CODE" >> "$RESULTS" <<'EOF'
import re, sys
log, mem, n, iters, code = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
txt = open(log, errors="ignore").read()
def vals(name):
    return [float(x) for x in re.findall(name + r":\s*([\d.]+)s", txt)][5:]
it, co, le = vals("Iteration time"), vals("Collection time"), vals("Learning time")
mean = lambda v: sum(v) / len(v) if v else float("nan")
steps = n * 24
peak = max([int(x) for x in open(mem).read().split() if x.strip().isdigit()] or [0])
print(f"{n},{iters},{steps},{mean(it):.3f},{mean(co):.3f},{mean(le):.3f},{steps/mean(it) if it else float('nan'):.0f},{peak},{code}")
EOF
  tail -1 "$RESULTS"
done

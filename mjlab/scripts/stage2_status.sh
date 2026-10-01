#!/usr/bin/env bash
# Status of a Stage 2 training run: process, latest iteration, key metrics.
RUN="${1:?run name}"
LOG="$(cd "$(dirname "$0")/.." && pwd)/artifacts/stage2/$RUN.log"
if pgrep -f "run-name $RUN" > /dev/null; then echo "process: running"; else echo "process: not running"; fi
grep -E "Learning iteration" "$LOG" | tail -1
grep -E "Mean reward|Mean episode length|Iteration time|Time elapsed|ETA|Episode_Reward/(paddle_contact|legal_return|approach_ball)|Episode_Termination/(fell_over|drill_over|time_out)" "$LOG" | tail -10
grep -E "Traceback|Error" "$LOG" | tail -3

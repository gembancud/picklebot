#!/usr/bin/env bash
# Status of a train_run.sh run. Usage: run_status.sh RUN
RUN="${1:?run}"; D="$(cd "$(dirname "$0")/.." && pwd)/artifacts/train"; LOG="$D/$RUN.log"
if pgrep -f "run-name $RUN" >/dev/null; then echo "process: running"; else echo "process: not running"; fi
[ -f "$D/$RUN.exit.json" ] && cat "$D/$RUN.exit.json"
grep -E "Learning iteration" "$LOG" | tail -1
grep -E "Mean reward|Iteration time|Time elapsed|ETA|Episode_Reward/(paddle_contact|legal_return)|Episode_Termination/fell_over" "$LOG" | tail -7
grep -E "Traceback|Error" "$LOG" | tail -3

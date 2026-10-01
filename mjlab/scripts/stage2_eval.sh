#!/usr/bin/env bash
# Evaluate a run's checkpoint on dev seeds. Usage: stage2_eval.sh RUN CHECKPOINT_FILE [extra stage2_eval.py args]
#   e.g. stage2_eval.sh return-stand-01 model_900.pt --envs 512 --seconds 9 --json out.json
set -uo pipefail
RUN="${1:?run}"; CK="${2:?checkpoint file, e.g. model_900.pt or latest}"; shift 2
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
source "$HOME/envs/picklebot-mj/bin/activate"
export PYTHONWARNINGS=ignore
cd "$REPO/mjlab"
DIR="$(ls -d artifacts/stage2/logs/picklebot_return_stand/*"$RUN"* | tail -1)"
if [ "$CK" = "latest" ]; then CK="$(ls "$DIR"/model_*.pt | sort -V | tail -1)"; else CK="$DIR/$CK"; fi
echo "checkpoint: $CK"
python scripts/stage2_eval.py --checkpoint "$CK" "$@" 2>&1 | grep -v -E "^\[INFO\]|^Module |^\||^\+|^$" | tail -40

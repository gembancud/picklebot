#!/usr/bin/env bash
# Run the picklebot_mj test suite in the WSL env. Usage: bash -l mjlab/scripts/test.sh [pytest args]
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
source "$HOME/envs/picklebot-mj/bin/activate"
export PYTHONWARNINGS=ignore
cd "$REPO/mjlab"
python -m pytest -q "$@"

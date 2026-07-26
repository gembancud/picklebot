#!/usr/bin/env bash
set -euo pipefail

PICKLEBOT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 -m unittest discover \
  -s "$PICKLEBOT_ROOT/scripts/tests" \
  -p "test_phase1b_empirical.py" \
  -v

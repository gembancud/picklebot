#!/usr/bin/env bash
set -euo pipefail

PICKLEBOT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 "$PICKLEBOT_ROOT/scripts/phase1b_empirical.py" \
  audit-close \
  --root "$PICKLEBOT_ROOT"

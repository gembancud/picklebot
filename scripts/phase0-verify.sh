#!/usr/bin/env bash
set -euo pipefail

PICKLEBOT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

"$PICKLEBOT_ROOT/scripts/phase0-editmode.sh"
"$PICKLEBOT_ROOT/scripts/phase0-playmode.sh"
"$PICKLEBOT_ROOT/scripts/phase0-soak.sh"

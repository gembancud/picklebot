#!/usr/bin/env bash
set -euo pipefail

PICKLEBOT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

"$PICKLEBOT_ROOT/scripts/phase1b-empirical-test.sh"
"$PICKLEBOT_ROOT/scripts/phase0-editmode.sh"
"$PICKLEBOT_ROOT/scripts/phase0-playmode.sh"
"$PICKLEBOT_ROOT/scripts/phase1a-editmode.sh"
"$PICKLEBOT_ROOT/scripts/phase1a-playmode.sh"
"$PICKLEBOT_ROOT/scripts/phase1b-editmode.sh"
"$PICKLEBOT_ROOT/scripts/phase1b-playmode.sh"
"$PICKLEBOT_ROOT/scripts/phase1b-evidence.sh"
"$PICKLEBOT_ROOT/scripts/phase1b-soak.sh"

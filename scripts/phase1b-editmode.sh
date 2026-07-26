#!/usr/bin/env bash
set -euo pipefail

PICKLEBOT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PICKLEBOT_UNITY="${PICKLEBOT_UNITY:-/Applications/Unity/Hub/Editor/6000.5.5f1/Unity.app/Contents/MacOS/Unity}"
PICKLEBOT_RESULTS="$PICKLEBOT_ROOT/artifacts/phase1b/tests"

mkdir -p "$PICKLEBOT_RESULTS"

"$PICKLEBOT_UNITY" \
  -batchmode \
  -nographics \
  -forgetProjectPath \
  -projectPath "$PICKLEBOT_ROOT" \
  -runTests \
  -testPlatform EditMode \
  -assemblyNames "Picklebot.Tests.Phase1B.EditMode" \
  -testResults "$PICKLEBOT_RESULTS/editmode-results.xml" \
  -logFile "$PICKLEBOT_RESULTS/editmode.log"

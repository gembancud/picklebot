#!/usr/bin/env bash
set -euo pipefail

PICKLEBOT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PICKLEBOT_UNITY="${PICKLEBOT_UNITY:-/Applications/Unity/Hub/Editor/6000.5.5f1/Unity.app/Contents/MacOS/Unity}"
PICKLEBOT_RESULTS="$PICKLEBOT_ROOT/artifacts/phase1a/tests"

mkdir -p "$PICKLEBOT_RESULTS"

"$PICKLEBOT_UNITY" \
  -batchmode \
  -nographics \
  -forgetProjectPath \
  -projectPath "$PICKLEBOT_ROOT" \
  -runTests \
  -testPlatform PlayMode \
  -assemblyNames "Picklebot.Tests.Phase1A.PlayMode" \
  -testCategory "!Evidence" \
  -testResults "$PICKLEBOT_RESULTS/playmode-results.xml" \
  -logFile "$PICKLEBOT_RESULTS/playmode.log"

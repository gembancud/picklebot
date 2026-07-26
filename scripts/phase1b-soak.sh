#!/usr/bin/env bash
set -euo pipefail

PICKLEBOT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PICKLEBOT_UNITY="${PICKLEBOT_UNITY:-/Applications/Unity/Hub/Editor/6000.5.5f1/Unity.app/Contents/MacOS/Unity}"
PICKLEBOT_RESULTS="$PICKLEBOT_ROOT/artifacts/phase1b/tests"
PICKLEBOT_SOAK_TEST="Picklebot.Tests.Phase1B.PlayMode.Phase1BSoakTests.TenThousandSeededEpisodesPassCalibratedStabilityGate"

mkdir -p "$PICKLEBOT_RESULTS"

if [[ -z "${PICKLEBOT_SOURCE_COMMIT:-}" ]]; then
  PICKLEBOT_SOURCE_COMMIT="$(git -C "$PICKLEBOT_ROOT" rev-parse HEAD 2>/dev/null || true)"
  export PICKLEBOT_SOURCE_COMMIT
fi

"$PICKLEBOT_UNITY" \
  -batchmode \
  -nographics \
  -forgetProjectPath \
  -projectPath "$PICKLEBOT_ROOT" \
  -runTests \
  -testPlatform PlayMode \
  -testFilter "$PICKLEBOT_SOAK_TEST" \
  -testResults "$PICKLEBOT_RESULTS/soak-results.xml" \
  -logFile "$PICKLEBOT_RESULTS/soak.log"

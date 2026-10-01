#!/usr/bin/env bash
# Render a short Stage 1 rig video (headless EGL) into mjlab/artifacts/stage1/.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
source "$HOME/envs/picklebot-mj/bin/activate"
cd "$REPO/mjlab"
mkdir -p artifacts/stage1
MUJOCO_GL=egl PYTHONWARNINGS=ignore python scripts/stage1_rig.py --num-envs 4 --steps 150 \
  --video artifacts/stage1/rig.mp4 > artifacts/stage1/rig-video.log 2>&1
grep -E "video:|Traceback|Error" artifacts/stage1/rig-video.log | head -5
ls -la artifacts/stage1/

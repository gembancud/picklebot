#!/usr/bin/env bash
# Render one clip per stroke type for a player (Stage 5B review): render_strokes.sh PLAYER [VIEW] [DIR]
set -euo pipefail
cd "$(dirname "$0")/../.."
P="${1:?player}"; VIEW="${2:-side}"; DIR="${3:-artifacts/motion/retargeted-v3}"
source ~/envs/picklebot-mj/bin/activate
mkdir -p artifacts/videos/stage5b
for c in Derecha:forehand Reves:backhand VDerecha:forehand_volley VReves:backhand_volley Servicio:serve Remate:smash; do
  src="${c%%:*}"; name="${c##*:}"
  MUJOCO_GL=egl python scripts/motion/render_retarget.py "$DIR/${P}_${src}.csv" \
    "artifacts/videos/stage5b/retarget${TAG:-}-${name}-${VIEW}.mp4" --view "$VIEW" --around-swing 4 --n-stills 8 \
    --stills artifacts/videos/stage5b/stills 2>&1 | tail -1
done

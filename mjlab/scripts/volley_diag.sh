#!/usr/bin/env bash
# Volley diagnostic (Stage 5C): with-hint legal/contact rates for the volley families + a close side video.
# Usage: volley_diag.sh RUN CKFILE TAG SEED
set -uo pipefail
cd "$(dirname "$0")/.."
RUN=$1; CK=$2; TAG=$3; S=$4; T=Picklebot-Latent-Court-G1
bash scripts/stage2_eval.sh $RUN $CK --task $T --envs 512 --seconds 16 --move-prob 0.0 --swing-prob 0.0 --families volley_forehand,volley_backhand --target A --seed $S --json results/stage5c-$TAG-volley-hint.json | tail -4
bash scripts/stage2_eval.sh $RUN $CK --task $T --envs 4 --seconds 12 --move-prob 0.0 --swing-prob 0.0 --families volley_forehand --target A --no-hint --seed $((S+1)) --view side_close --slowmo 2 --video artifacts/videos/h5c/$TAG-volley-fh.mp4 | tail -2

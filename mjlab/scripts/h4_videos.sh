#!/usr/bin/env bash
# Stage 5B review videos (D-064/D-065): continuous Drill 3 play (real balls, every family, no hint, several feeds per
# robot episode) for an H4 candidate with close side and behind cameras, a side-by-side with S-D3-style-c on the
# same feeds/seed, and a backhand-only clip.
# Usage: h4_videos.sh RUN CKFILE TASK TAG SEED   -> artifacts/videos/h4/TAG-{side,behind,vs-sd3stylec,backhand}.mp4
set -uo pipefail
cd "$(dirname "$0")/.."
RUN=$1; CK=$2; T=$3; TAG=$4; S=$5; O=artifacts/videos/h4
mkdir -p $O
A="--envs 1 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --seed $S"
bash scripts/stage2_eval.sh $RUN $CK --task $T $A --view side_close --video $O/$TAG-side.mp4 > /dev/null 2>&1
bash scripts/stage2_eval.sh $RUN $CK --task $T $A --view behind_close --video $O/$TAG-behind.mp4 > /dev/null 2>&1
bash scripts/stage2_eval.sh student-drill3-style-c model_10400.pt --task Picklebot-Student-Drill3-G1 $A --view side_close --video $O/sd3stylec-$S-side.mp4 > /dev/null 2>&1
bash scripts/stage2_eval.sh $RUN $CK --task $T --envs 1 --seconds 16 --move-prob 0.0 --swing-prob 0.0 --families backhand,reach_backhand --target A --no-hint --seed $((S+1)) --view behind_close --video $O/$TAG-backhand.mp4 > /dev/null 2>&1
FF=$(~/envs/picklebot-mj/bin/python -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")
$FF -y -loglevel error -i $O/$TAG-side.mp4 -i $O/sd3stylec-$S-side.mp4 -filter_complex "[0:v][1:v]hstack=inputs=2" $O/$TAG-vs-sd3stylec.mp4
ls -la $O/$TAG-*.mp4

#!/usr/bin/env bash
# Stage 5B review videos (D-064): continuous Drill 3 play (real balls, every family, no hint, several feeds per robot
# episode) for an H4 candidate, side and behind views, plus a side-by-side with S-D3-style-c on the same feeds/seed.
# Usage: h4_videos.sh RUN CKFILE TASK TAG SEED   -> artifacts/videos/h4/TAG-{side,behind,vs-sd3stylec}.mp4
set -uo pipefail
cd "$(dirname "$0")/.."
RUN=$1; CK=$2; T=$3; TAG=$4; S=$5; O=artifacts/videos/h4
mkdir -p $O
A="--envs 1 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --seed $S --slowmo 1.0"
for v in side behind; do
  bash scripts/stage2_eval.sh $RUN $CK --task $T $A --view $v --video $O/$TAG-$v.mp4 > /dev/null 2>&1
done
bash scripts/stage2_eval.sh student-drill3-style-c model_10400.pt --task Picklebot-Student-Drill3-G1 $A --view side --video $O/sd3stylec-$S-side.mp4 > /dev/null 2>&1
FF=$(~/envs/picklebot-mj/bin/python -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")
$FF -y -loglevel error -i $O/$TAG-side.mp4 -i $O/sd3stylec-$S-side.mp4 -filter_complex \
  "[0:v]drawtext=text='H4 (human-motion executor)':x=20:y=20:fontsize=28:fontcolor=white[a];[1:v]drawtext=text='S-D3-style-c (flat student)':x=20:y=20:fontsize=28:fontcolor=white[b];[a][b]hstack=inputs=2" \
  $O/$TAG-vs-sd3stylec.mp4 || \
$FF -y -loglevel error -i $O/$TAG-side.mp4 -i $O/sd3stylec-$S-side.mp4 -filter_complex "[0:v][1:v]hstack=inputs=2" $O/$TAG-vs-sd3stylec.mp4
ls -la $O/$TAG-* $O/sd3stylec-$S-side.mp4

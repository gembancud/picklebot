#!/usr/bin/env bash
# Stage 5C review videos (D-075 step 6): close-camera full-court clips of one executor.
# Usage: h5c_videos.sh RUN CKFILE TASK TAG SEED   -> artifacts/videos/h5c/TAG-*.mp4
#   side / behind : court-wide drill (every family, random court-wide recovery spots, no hint)
#   kitchen       : start at the kitchen line (x = -2.6), short and front-court families
#   move          : move-to-spot drill (spots 0.5-3 m in every direction)
#   rally         : long sequence across the court: court-anchored feeds (rally evaluation), wide side camera
set -uo pipefail
cd "$(dirname "$0")/.."
RUN=$1; CK=$2; T=$3; TAG=$4; S=$5; O=artifacts/videos/h5c
mkdir -p $O
A="--envs 1 --target A --no-hint"
bash scripts/stage2_eval.sh $RUN $CK --task $T $A --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --recovery random --seed $S --view side_close --video $O/$TAG-side.mp4 > /dev/null 2>&1; echo "side $?"
bash scripts/stage2_eval.sh $RUN $CK --task $T $A --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --recovery random --seed $((S+1)) --view behind_close --video $O/$TAG-behind.mp4 > /dev/null 2>&1; echo "behind $?"
bash scripts/stage2_eval.sh $RUN $CK --task $T $A --seconds 20 --move-prob 0.0 --swing-prob 0.0 --families short,reach_forehand,reach_backhand,cross_forehand,cross_backhand,volley_forehand,volley_backhand,lob --start-x -2.6 --seed $((S+2)) --view side_close --video $O/$TAG-kitchen.mp4 > /dev/null 2>&1; echo "kitchen $?"
bash scripts/stage2_eval.sh $RUN $CK --task $T $A --seconds 20 --move-prob 1.0 --swing-prob 0.0 --families every --seed $((S+3)) --view behind_close --video $O/$TAG-move.mp4 > /dev/null 2>&1; echo "move $?"
bash scripts/stage2_eval.sh $RUN $CK --task $T $A --seconds 60 --move-prob 0.0 --swing-prob 0.0 --families every --rally --seed $((S+4)) --view side --video $O/$TAG-rally.mp4 > /dev/null 2>&1; echo "rally $?"
ls -la $O/$TAG-*.mp4

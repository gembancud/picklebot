#!/usr/bin/env bash
# Panel round 49 (D-175): the supervised speed ladder. Evaluation only: no training, no download.
#   Build: on-disk 100STYLE G1 retargets (artifacts/motion/style100-g1: Neutral FW / BW / SW accepted, SR on disk but
#          rejected by the D-101 rule) plus left-right mirrors of SW and SR (mirror_g1_csv.py), time-scaled by
#          csv_to_npz_local.py --input-fps 30*k for k = 1, 1.5, 2, 2.5 (the brief) and 3, 4, 5 (extension: x2.5 of
#          a 0.4-0.6 m/s walk does not reach D-175's 2.0 m/s), merged into a NEW directory artifacts/motion/speed-ladder/.
#   Eval:  H0 (s5c-03b/model_63300) by tracking_eval.py; latent-07 (latent_10651) by tracking_eval.py --latent;
#          latent_barrier_check.py (coverage lam 2 / 5). 4 s windows (--per-stroke), 4 repeats, dev seed 4220130
#          for all three (paired). Then speed_ladder.py summarize applies the D-175 coded rule.
set -euo pipefail
cd "$(dirname "$0")/../.."
source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
SRC=artifacts/motion/style100-g1; O=artifacts/motion/speed-ladder; R=results/speed-ladder; SEED=4220130
H0=artifacts/train/logs/picklebot_tracking/2026-10-14_18-52-53_s5c-03b-h0mirror/model_63300.pt
LAT=artifacts/train/latent/latent-07/latent_10651.pt
TASK=Picklebot-Tracking-SpeedLadder-G1
STEMS="Neutral_FW_train Neutral_FW_ref Neutral_BW_train Neutral_BW_ref Neutral_SW_train Neutral_SW_ref Neutral_SR_train Neutral_SR_ref"
MIRROR="Neutral_SW_train Neutral_SW_ref Neutral_SR_train Neutral_SR_ref"
if [ ! -f $O/speed-ladder.npz ]; then
  [ ! -e $O ] || { echo "$O exists without speed-ladder.npz: inspect it by hand (never overwritten)"; exit 1; }
  mkdir -p $O/csv $O/parts
  for s in $STEMS; do cp -n $SRC/$s.csv $O/csv/; done
  python scripts/motion/mirror_g1_csv.py $SRC $O/csv $MIRROR
  CLIPS=$(echo $STEMS $(for s in $MIRROR; do echo ${s}_mirror; done) | tr ' ' ',')
  PARTS=""
  for k in 1 1.5 2 2.5 3 4 5; do
    fps=$(python -c "print(int(round(30 * $k)))")
    python scripts/motion/csv_to_npz_local.py $O/csv $O/parts/x$k.npz --clips $CLIPS --input-fps $fps --output-fps 50 \
      2>&1 | grep -v "^Motion interpolated" | tail -1
    PARTS="$PARTS $O/parts/x$k.npz:$k"
  done
  python scripts/motion/speed_ladder.py merge $O/speed-ladder.npz $PARTS
fi
python - <<'PY'  # the npz body order starts at the pelvis (speed_ladder.py --pelvis-index 0)
import importlib.util
import mjlab.tasks  # noqa: F401
import picklebot_mj.tasks  # noqa: F401
from mjlab.tasks.registry import load_env_cfg
spec = importlib.util.spec_from_file_location("te", "scripts/motion/tracking_eval.py"); te = importlib.util.module_from_spec(spec)
spec.loader.exec_module(te)
names = te.scene_body_names(load_env_cfg("Picklebot-Tracking-SpeedLadder-G1"))
assert names[0] == "pelvis", names[:3]
print("body 0:", names[0])
PY
python scripts/motion/tracking_eval.py --checkpoint $H0 --task $TASK --per-stroke --repeats 4 --seed $SEED --json $R-h0.json > /tmp/speed-ladder-h0.log 2>&1; echo "H0: $?"
python scripts/motion/tracking_eval.py --latent --checkpoint $LAT --task $TASK --per-stroke --repeats 4 --seed $SEED --json $R-lat07.json > /tmp/speed-ladder-lat.log 2>&1; echo "latent-07: $?"
python scripts/motion/latent_barrier_check.py --latent --checkpoint $LAT --task $TASK --per-stroke --repeats 4 --seed $SEED --json $R-barrier.json > /tmp/speed-ladder-bar.log 2>&1; echo "barrier: $?"
python scripts/motion/speed_ladder.py summarize --motion $O/speed-ladder.npz --h0 $R-h0.json --lat $R-lat07.json \
  --barrier $R-barrier.json --json results/speed-ladder.json --txt results/speed-ladder-summary.txt

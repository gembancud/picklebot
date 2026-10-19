#!/usr/bin/env bash
# Stage 5F controller run C2 (D-111 trigger fired): H1 decoder re-distillation under command delay. One change: the
# latent-07 decoder is re-distilled by DAgger from the delay-robust H0 (C1's endpoint) on the C1 delay task (30 % clean
# episodes, otherwise 5-25 ms command delay); the input normaliser, encoder and prior stay frozen (D-109 item 6).
# Same losses and weights as latent-07 (decoder MSE on the encoder latent, prior BC 0.5, smoothness 0.005); lr 1e-4,
# DAgger beta 1 -> 0 over the first 5 % of iterations, training seed 72.
# Endpoint: iteration 1400 or the last checkpoint before the 7100 s cap.
# Early kill (D-111): at ~30 % (latent_400), clean tracking, 1 repeat, seed 4210502; killed if any source is > 3 points
# below latent-07 on that protocol.
# Gate (D-111, H1): (1) tracking per source at 0/10/20 ms >= latent-07 at 0 ms - 2 points, 100STYLE 57/57 windows;
# (2) zero-shot transfer of Stage 5D run 1 (clean; command 20 ms; cell 40/20); (3) style. Seeds 4210503-4210509.
# Usage: h5f_c2_h1decoder.sh TEACHER_CHECKPOINT
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
TEACHER=${1:?C1 endpoint checkpoint}; RUN=s5f-c2-h1decoder; LAT=artifacts/train/latent/latent-07/latent_10651.pt
D=artifacts/train/latent/$RUN; R=results/stage5f-c2
TE="python scripts/motion/tracking_eval.py --latent --task Picklebot-Tracking-TennisLafan4-Huge-G1 --per-stroke"
$TE --checkpoint $LAT --repeats 1 --seed 4210502 --json $R-parent-early.json > /tmp/c2.log 2>&1; echo "parent early-protocol eval: $?"
( # early-kill watcher
  while [ ! -f $D/latent_400.pt ]; do
    [ -f artifacts/train/$RUN.exit.json ] && { echo "training ended before the early check"; exit 0; }; sleep 60; done
  $TE --checkpoint $D/latent_400.pt --repeats 1 --seed 4210502 --json $R-early.json > /tmp/c2e.log 2>&1
  python - "$R" <<'PY' && echo "early check: pass" || { echo "early check: KILL"; pkill -f "distill_latent.py --out .*$RUN"; }
import json, sys
R = sys.argv[1]
p, e = json.load(open(f"{R}-parent-early.json"))["by_source"], json.load(open(f"{R}-early.json"))["by_source"]
worst = min(e[k] - p[k] for k in p)
print("early: worst source change", round(100 * worst, 1), "points", {k: round(100 * (e[k] - p[k]), 1) for k in p})
sys.exit(0 if worst >= -0.03 else 1)
PY
) > artifacts/train/$RUN-early.log 2>&1 &
bash scripts/latent_run.sh $RUN --teacher $TEACHER --task Picklebot-Tracking-TennisLafan2-Huge-Delay-G1 --init $LAT \
  --decoder-only --iterations 1400 --beta-frac 0.05 --lr 1e-4 --kl-start 0 --kl-end 0 --prior-bc 0.5 --smooth 0.005 \
  --seed 72 --max-seconds 6900
wait
cat artifacts/train/$RUN-early.log
CK=$(ls $D/latent_*.pt | sort -V | tail -1); echo "endpoint $CK"
python - $LAT $CK <<'PY'  # the frozen parts must be bit-identical to latent-07
import sys, torch
a, b = (torch.load(p, map_location="cpu", weights_only=False)["model"] for p in sys.argv[1:3])
diff = [k for k in a if not k.startswith("decoder.") and not torch.equal(a[k], b[k])]
print("frozen parts identical:", not diff, diff[:5])
PY
for d in 0 10 20; do
  $TE --checkpoint $CK --repeats 2 --seed 4210503 --cmd-delay-ms $d --json $R-gate-new-cmd$d.json > /tmp/c2.log 2>&1; echo "gate new cmd$d: $?"
done
$TE --checkpoint $LAT --repeats 2 --seed 4210503 --json $R-gate-old-cmd0.json > /tmp/c2.log 2>&1; echo "gate latent-07 cmd0: $?"
for d in 0 20; do
  python scripts/motion/tracking_eval.py --latent --task Picklebot-Tracking-TennisStyle100-G1 --per-stroke --checkpoint $CK \
    --repeats 2 --seed 4210504 --cmd-delay-ms $d --json $R-gate-new-style100-cmd$d.json > /tmp/c2.log 2>&1; echo "gate new 100style cmd$d: $?"
done
# Zero-shot transfer: Stage 5D run 1 on latent-07 and on the new H1, paired seeds.
T=Picklebot-Latent-Court-Res-G1
C="--task $T --envs 2048 --seconds 24 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --recovery random"
M="--task $T --envs 2048 --seconds 24 --move-prob 1.0 --swing-prob 0.0 --families every --target A --no-hint"
Y="--task $T --envs 1024 --seconds 90 --move-prob 0.0 --swing-prob 0.0 --families every --target A --no-hint --rally"
for who in old new; do
  if [ $who = new ]; then export PICKLEBOT_CONTROLLER=$PWD/$CK; else unset PICKLEBOT_CONTROLLER; fi
  E="bash scripts/stage2_eval.sh s5d-01-rally model_1800.pt"
  $E $C --seed 4210505 --json $R-zs-$who-court.json > /tmp/c2.log 2>&1; echo "zs $who court: $?"
  $E $M --seed 4210506 --json $R-zs-$who-move.json > /tmp/c2.log 2>&1; echo "zs $who move: $?"
  $E $Y --seed 4210507 --json $R-zs-$who-rally.json > /tmp/c2.log 2>&1; echo "zs $who rally: $?"
  $E $M --grid 0 20 --seed 4210506 --json $R-zs-$who-move-c20.json > /tmp/c2.log 2>&1; echo "zs $who move cmd20: $?"
  $E $C --grid 40 20 --seed 4210505 --json $R-zs-$who-court-b40c20.json > /tmp/c2.log 2>&1; echo "zs $who court 40/20: $?"
  DIR="$(ls -d artifacts/train/logs/picklebot_return_stand/*_s5d-01-rally | tail -1)"
  python scripts/motion/style_score.py --checkpoint "$DIR/model_1800.pt" --task $T --seed 4210508 --json $R-zs-$who-style.json > /tmp/c2.log 2>&1; echo "zs $who style: $?"
done

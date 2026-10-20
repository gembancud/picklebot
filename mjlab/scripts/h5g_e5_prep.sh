#!/usr/bin/env bash
# Stage 5G E5 tooling (D-124, panel round 13), evaluation and a probe only:
# (iii) E3's endpoint zero-shot in the E5 ball task (sync-free goals; goal statistics recorded): seed 4216020, 256 envs,
#       30 s, as the E3 smoke test (seed 4216014). Equivalence check: legal returns within E3's interval.
# (iv) Throughput probe: 50 PPO iterations of the E5 task at 4,096 envs from E3's endpoint (training seed 75; the probe
#      checkpoints are never a parent). Bar: <= 3.5 s per iteration.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
CK=artifacts/train/logs/picklebot_latent/2026-10-20_15-12-17_s5g-e3-timed-v3/model_39699.pt
T=Picklebot-Latent-TimedBall-PPO-G1
python scripts/stage2_eval.py --checkpoint $CK --task $T --envs 256 --seconds 30 --move-prob 0.0 --swing-prob 0.0 \
  --families every --target A --no-hint --rally --seed 4216020 --json results/s5g-zs-e3-sync-free.json > /tmp/zs3b.log 2>&1
echo "smoke exit $?"
PICKLEBOT_WALL_CAP=1500 bash scripts/train_run.sh s5g-probe-ball $T --agent.seed 75 --agent.max-iterations 50 \
  --agent.resume True --agent.load-run 2026-10-20_15-12-17_s5g-e3-timed-v3 --agent.load-checkpoint model_39699.pt
cat artifacts/train/s5g-probe-ball.exit.json
grep -a -E "Iteration time|Learning iteration|Computation" artifacts/train/s5g-probe-ball.log | tail -8

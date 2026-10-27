#!/usr/bin/env bash
# KL check (2026-10-27, after D-158): why rsl_rl's adaptive schedule held the learning rate at its 1e-5 floor.
# Two 30-iteration probes from rally run 14 model_27798 on run 14's task, 12,288 envs, with its optimizer, recording
# each action output's share of the KL (picklebot_mj/rl/kl_probe.py). Diagnostic only: no checkpoint is selected.
#   a: the native adaptive schedule (seed 4219950);
#   b: the learning rate held at 1e-4 (seed 4219951). INVALID: the resume loaded the optimizer's 1e-5 after the probe
#      set its rate, so b ran at 1e-5 (a replicate of a without the schedule);
#   b2: b rerun with the rate set at every update (seed 4219952). `kl_probe.sh b2` runs b2 only.
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
T=Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR2-G1
PRUN=2026-10-25_15-06-49_rally-14-lamr2; PCK=model_27798.pt; R=results/kl-probe
ARGS="--agent.max-iterations 30 --agent.resume True --agent.load-run $PRUN --agent.load-checkpoint $PCK --agent.algorithm.class-name picklebot_mj.rl.kl_probe:KLProbePPO"
if [ "${1:-}" = b2 ]; then
  rm -f $R-b2.jsonl
  PICKLEBOT_KL_PROBE_OUT=$R-b2.jsonl PICKLEBOT_KL_FIXED_LR=1e-4 PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=1800 \
    bash scripts/train_run.sh kl-probe-b2 $T --agent.seed 4219952 $ARGS; echo "probe b2: $?"
  echo done > artifacts/train/kl-probe-b2.done; exit 0
fi
rm -f $R-a.jsonl $R-b.jsonl
PICKLEBOT_KL_PROBE_OUT=$R-a.jsonl PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=1800 \
  bash scripts/train_run.sh kl-probe-a $T --agent.seed 4219950 $ARGS; echo "probe a: $?"
PICKLEBOT_KL_PROBE_OUT=$R-b.jsonl PICKLEBOT_KL_FIXED_LR=1e-4 PICKLEBOT_CRITIC_WARMUP=0 PICKLEBOT_ENVS=12288 PICKLEBOT_WALL_CAP=1800 \
  bash scripts/train_run.sh kl-probe-b $T --agent.seed 4219951 $ARGS; echo "probe b: $?"
echo done > artifacts/train/kl-probe.done

#!/usr/bin/env bash
# Student fine-tune (RegPPO, D-042): train_student.sh RUN TASK REF_CKPT [train_run.sh extra args...]
# Pull-back and warm-up settings come from PICKLEBOT_* env vars (defaults for fine-tunes below).
set -uo pipefail
RUN="${1:?run}"; TASK="${2:?task}"; REF="${3:?reference checkpoint}"; shift 3
export PICKLEBOT_REF_CKPT="$REF"
export PICKLEBOT_CRITIC_WARMUP_ITERS="${PICKLEBOT_CRITIC_WARMUP_ITERS:-100}"
export PICKLEBOT_REF_COEF="${PICKLEBOT_REF_COEF:-10}"
export PICKLEBOT_REF_FINAL_COEF="${PICKLEBOT_REF_FINAL_COEF:-1}"
export PICKLEBOT_REF_DECAY_ITERS="${PICKLEBOT_REF_DECAY_ITERS:-1500}"
exec bash "$(dirname "$0")/train_run.sh" "$RUN" "$TASK" "$@"

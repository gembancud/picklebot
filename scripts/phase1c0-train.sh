#!/usr/bin/env bash
set -euo pipefail

PICKLEBOT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PICKLEBOT_ENV_PREFIX="$PICKLEBOT_ROOT/.venv/phase1c0"
PICKLEBOT_RUN_ID="${1:-phase1c0-local-001}"
PICKLEBOT_RESUME_MODE="${2:-}"
PICKLEBOT_ARTIFACT_ROOT="$PICKLEBOT_ROOT/artifacts/phase1c0/$PICKLEBOT_RUN_ID"
PICKLEBOT_AVAILABLE_KIB="$(df -Pk "$PICKLEBOT_ROOT" | awk 'NR == 2 { print $4 }')"
PICKLEBOT_MINIMUM_KIB=$((15 * 1024 * 1024))

if (( PICKLEBOT_AVAILABLE_KIB < PICKLEBOT_MINIMUM_KIB )); then
  echo "Refusing to train: less than 15 GiB free." >&2
  exit 2
fi

if [[ ! -x "$PICKLEBOT_ENV_PREFIX/bin/mlagents-learn" ]]; then
  echo "Trainer environment missing; run scripts/phase1c0-env-create.sh first." >&2
  exit 3
fi

if [[ -n "$PICKLEBOT_RESUME_MODE" && "$PICKLEBOT_RESUME_MODE" != "--resume" ]]; then
  echo "Second argument must be --resume when supplied." >&2
  exit 4
fi

"$PICKLEBOT_ENV_PREFIX/bin/python" - <<'PY'
import inspect
import torch

parameters = inspect.signature(torch.onnx.export).parameters
dynamo = parameters.get("dynamo")
if dynamo is not None and dynamo.default is not False:
    raise SystemExit(
        "Incompatible PyTorch ONNX default: pin torch==2.1.2 from environment.yml."
    )
print(f"Phase 1C0 exporter preflight: torch={torch.__version__}, legacy ONNX path=ready")
PY

mkdir -p "$PICKLEBOT_ARTIFACT_ROOT"

if [[ "$PICKLEBOT_RESUME_MODE" == "--resume" ]]; then
  exec "$PICKLEBOT_ENV_PREFIX/bin/mlagents-learn" \
    "$PICKLEBOT_ROOT/config/phase1c0/picklebot_ppo.yaml" \
    --run-id "$PICKLEBOT_RUN_ID" \
    --results-dir "$PICKLEBOT_ARTIFACT_ROOT/trainer" \
    --resume
fi

exec "$PICKLEBOT_ENV_PREFIX/bin/mlagents-learn" \
  "$PICKLEBOT_ROOT/config/phase1c0/picklebot_ppo.yaml" \
  --run-id "$PICKLEBOT_RUN_ID" \
  --results-dir "$PICKLEBOT_ARTIFACT_ROOT/trainer"

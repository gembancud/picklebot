#!/usr/bin/env bash
set -euo pipefail

PICKLEBOT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PICKLEBOT_CONDA="${CONDA_EXE:-$(command -v conda)}"
PICKLEBOT_ENV_PREFIX="$PICKLEBOT_ROOT/.venv/phase1c0"
export CONDA_PKGS_DIRS="$PICKLEBOT_ROOT/.venv/conda-pkgs"

if [[ -x "$PICKLEBOT_ENV_PREFIX/bin/python" ]]; then
  "$PICKLEBOT_CONDA" env update \
    --prefix "$PICKLEBOT_ENV_PREFIX" \
    --file "$PICKLEBOT_ROOT/config/phase1c0/environment.yml" \
    --prune
else
  "$PICKLEBOT_CONDA" env create \
    --prefix "$PICKLEBOT_ENV_PREFIX" \
    --file "$PICKLEBOT_ROOT/config/phase1c0/environment.yml"
fi

"$PICKLEBOT_CONDA" run --prefix "$PICKLEBOT_ENV_PREFIX" \
  python -c 'import platform; from importlib.metadata import version; actual=(platform.python_version(), version("mlagents"), version("mlagents-envs"), version("grpcio")); expected=("3.10.12", "1.1.0", "1.1.0", "1.48.2"); print("\n".join(actual)); assert actual == expected, (actual, expected)'
"$PICKLEBOT_CONDA" run --prefix "$PICKLEBOT_ENV_PREFIX" \
  mlagents-learn --help >/dev/null

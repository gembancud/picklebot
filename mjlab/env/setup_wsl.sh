#!/usr/bin/env bash
set -euo pipefail
ENV="$HOME/envs/picklebot-mj"
mkdir -p "$HOME/envs"
if [ ! -d "$ENV" ]; then
  uv venv --python 3.12 "$ENV"
fi
source "$ENV/bin/activate"
uv pip install "mjlab==1.6.0"
# picklebot_mj package (editable) with test dependencies
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
uv pip install -e "$REPO/mjlab[dev]"
python - <<'EOF'
import importlib.metadata as m, torch, warp as wp, mujoco
for p in ["mjlab", "mujoco", "mujoco-warp", "warp-lang", "rsl-rl-lib", "torch"]:
    print(p, m.version(p))
print("torch cuda", torch.version.cuda, "available", torch.cuda.is_available(),
      torch.cuda.get_device_name(0) if torch.cuda.is_available() else "-")
wp.init()
print("warp devices", wp.get_cuda_devices())
EOF
uv pip freeze > "$HOME/envs/picklebot-mj-freeze.txt"
which train play 2>/dev/null || ls "$ENV/bin" | head -40

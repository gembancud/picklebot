#!/usr/bin/env python3
"""Create random-weight parity fixtures, not a trained player model."""
from datetime import datetime, timezone
import json

import torch

from player_actor import Actor, ROOT, source_hash


torch.manual_seed(1100001)
model = Actor()
inputs = torch.randn(64, 54)
with torch.no_grad():
    outputs = model(inputs)
folder = ROOT / "artifacts/player-agents" / ("parity-probe-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"))
folder.mkdir(exist_ok=False)
(folder / "actor.json").write_text(json.dumps(model.export(dict(sourceHash=source_hash(), method="random-weight inference test; untrained", trainingSteps=0))))
(folder / "parity-input.json").write_text(json.dumps({"observations": [{"values": row.tolist()} for row in inputs], "expected": [{"values": row.tolist()} for row in outputs]}))
print(folder)

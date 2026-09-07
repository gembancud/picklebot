#!/usr/bin/env python3
"""Create a disclosed exploration start; this operation is not training."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import torch
from player_actor import Actor, ROOT, file_hash, source_hash

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("actor", type=Path)
parser.add_argument("--shot-scale", type=float, default=.2)
args = parser.parse_args()
if not 0 < args.shot_scale <= 1: parser.error("Shot scale must be in (0, 1]")
actor, parent = Actor.load_export(args.actor)
with torch.no_grad():
    actor.layers[-1].weight[3:].mul_(args.shot_scale)
    actor.layers[-1].bias[3:].mul_(args.shot_scale)
metadata = {k: v for k, v in parent.items() if k not in ("layers", "logStd", "version", "observationVersion")}
metadata.update(parentActorHash=file_hash(args.actor), parentTrainingSourceHash=parent["sourceHash"],
                runtimeSourceAtInitialization=source_hash(), shotLogitScale=args.shot_scale,
                method="exploration initialization from saved policy; shot logits rescaled; no new learning updates",
                createdUtc=datetime.now(timezone.utc).isoformat())
# Preserve the historical training source. A later PPO update records its actual runtime source.
folder = ROOT / "artifacts/player-agents" / ("exploration-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"))
folder.mkdir(exist_ok=False)
(folder / "actor.json").write_text(json.dumps(actor.export(metadata)))
(folder / "initialization.json").write_text(json.dumps(dict(metadata, actorHash=file_hash(folder / "actor.json"), initializerHash=file_hash(__file__)), indent=2))
print(folder, flush=True)

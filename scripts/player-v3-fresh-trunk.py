#!/usr/bin/env python3
"""Controlled V3 initialization ablation retaining the original bootstrap heads."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import torch
from player_v3_actor import ActorV3, source_hash
from player_actor import ROOT, file_hash

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('reference',type=Path);parser.add_argument('output',type=Path)
args=parser.parse_args()
if args.output.exists():raise ValueError('Refuse to overwrite a checkpoint')
torch.set_num_threads(2);torch.manual_seed(1300000)
reference,metadata=ActorV3.load(args.reference)
if reference.layers[0].in_features!=124 or reference.layers[-1].out_features!=18:raise ValueError('Upgrade the untrained bootstrap reference to the current 124/18 schema first')
if metadata.get('trainingSteps')!=0:raise ValueError('Use the untrained V3 bootstrap head reference')
actor=ActorV3(reference.layers[0].out_features)
with torch.no_grad():
    for layer in actor.layers[:2]:
        torch.nn.init.orthogonal_(layer.weight,gain=1.0);layer.bias.zero_()
    actor.layers[2].load_state_dict(reference.layers[2].state_dict())
    actor.log_std.copy_(reference.log_std)
data=actor.export(dict(sourceHash=source_hash(),trainingSteps=0,initializationSeed=1300000,
    method='Fresh V3 trunk with all 121 inputs active; unchanged original V3 bootstrap output heads and exploration; no optimization yet',
    bootstrapHeadReferenceHash=file_hash(args.reference),trainerHash=file_hash(Path(__file__)),
    protocolHash=file_hash(ROOT/'config/player-agents/evaluation-v1.json'),createdUtc=datetime.now(timezone.utc).isoformat()))
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(data,indent=2))
print(json.dumps(dict(actor=str(args.output),sha256=file_hash(args.output),sourceHash=data['sourceHash'],trainingSteps=0)))

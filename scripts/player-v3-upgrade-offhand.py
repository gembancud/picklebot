#!/usr/bin/env python3
"""Preserve a 121/17 policy while adding a bounded learned off-hand lift channel."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import torch
from player_v3_actor import ActorV3, source_hash
from player_actor import file_hash

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('parent',type=Path);parser.add_argument('output',type=Path)
args=parser.parse_args()
if args.output.exists():raise ValueError('Preserve historical checkpoint files')
old,metadata=ActorV3.load(args.parent)
if old.layers[0].in_features!=121 or old.layers[-1].out_features!=17:raise ValueError('This migration requires the 121/17 parent schema')
torch.manual_seed(1300300);new=ActorV3(old.layers[0].out_features)
with torch.no_grad():
    new.layers[0].weight.zero_();new.layers[0].weight[:,:121].copy_(old.layers[0].weight)
    new.layers[0].bias.copy_(old.layers[0].bias);new.layers[1].load_state_dict(old.layers[1].state_dict())
    new.layers[2].weight.zero_();new.layers[2].bias.zero_()
    new.layers[2].weight[:17].copy_(old.layers[2].weight);new.layers[2].bias[:17].copy_(old.layers[2].bias)
    new.log_std[:17].copy_(old.log_std);new.log_std[17]=-.7
    x=torch.randn(16,121);expanded=torch.cat((x,torch.zeros(16,3)),dim=1)
    error=float((new(expanded)[:,:17]-old(x)).abs().max())
    assert error<1e-5,error
data=new.export(dict(metadata,sourceHash=source_hash(),parentModelHash=file_hash(args.parent),parentTrainingSourceHash=metadata['sourceHash'],
    method='Original 121 input columns and 17 heads retained; new off-hand lift initialized; no optimization on expanded controls yet',
    schemaTransition=dict(previousObservationVersion=metadata['observationVersion'],previousActionVersion=metadata['actionVersion'],
        retainedHeadMaxError=error,addedFields=['offHand.angle','offHand.rate','active.offHand.lift'],newAction='offHand.lift',
        newHeadMean=0,newHeadLogStd=-.7,scriptHash=file_hash(Path(__file__)),createdUtc=datetime.now(timezone.utc).isoformat())))
args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(data,indent=2),encoding='utf-8')
print(json.dumps(dict(actor=str(args.output),sha256=file_hash(args.output),sourceHash=data['sourceHash'],retainedHeadMaxError=error)))

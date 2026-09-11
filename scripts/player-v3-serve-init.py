#!/usr/bin/env python3
"""Enable exploration of newly unmasked release and underexplored crouch controls."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from player_v3_actor import ActorV3, source_hash
from player_actor import file_hash

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('parent',type=Path);parser.add_argument('output',type=Path)
args=parser.parse_args()
if args.output.exists():raise ValueError('Preserve historical checkpoints')
actor,parent=ActorV3.load(args.parent)
if parent['sourceHash']!=source_hash():raise ValueError('Record any source transition before changing exploration')
data=dict(parent,parentModelHash=file_hash(args.parent),method='Learned tensors retained; release/crouch exploration initialized for serving; no serve optimization yet',
    explorationInitialization=dict(previousLogStd=parent['logStd'],channels=[3,16],newStandardDeviation=1.0,
        reason='Positive-threshold release was vanishingly unlikely with the previous narrow Gaussian; allow learned trials without scheduling release or prescribing movement.',
        scriptHash=file_hash(Path(__file__)),createdUtc=datetime.now(timezone.utc).isoformat()))
data['logStd']=list(parent['logStd']);data['logStd'][3]=data['logStd'][16]=0.0
assert data['layers']==parent['layers']
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(data,indent=2),encoding='utf-8')
print(json.dumps(dict(actor=str(args.output),sha256=file_hash(args.output),sourceHash=data['sourceHash'],learnedLayersUnchanged=True)))

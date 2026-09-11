#!/usr/bin/env python3
"""Transfer unchanged V3 policy tensors to an explicitly revised environment."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from player_v3_actor import ActorV3, source_hash, OBS_VERSION, ACTION_VERSION
from player_actor import file_hash

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('parent',type=Path);parser.add_argument('output',type=Path)
parser.add_argument('--reason',required=True)
args=parser.parse_args()
if args.output.exists():raise ValueError('Refuse to overwrite a checkpoint')
_,parent=ActorV3.load(args.parent)
if (parent['observationVersion'],parent['actionVersion'])!=(OBS_VERSION,ACTION_VERSION):raise ValueError('Use an explicit schema migration before rebinding source')
current=source_hash()
if current==parent['sourceHash']:raise ValueError('No source transition to record')
data=dict(parent,sourceHash=current,parentModelHash=file_hash(args.parent),
    parentTrainingSourceHash=parent['sourceHash'],method='Unchanged V3 tensors transferred; no optimization on new environment yet',
    sourceTransition=dict(previousSourceHash=parent['sourceHash'],newSourceHash=current,reason=args.reason,
        scriptHash=file_hash(Path(__file__)),createdUtc=datetime.now(timezone.utc).isoformat()))
assert data['layers']==parent['layers'] and data['logStd']==parent['logStd']
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(data,indent=2))
print(json.dumps(dict(actor=str(args.output),sha256=file_hash(args.output),sourceHash=current,unchangedTensors=True)))

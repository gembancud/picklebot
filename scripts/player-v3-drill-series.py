#!/usr/bin/env python3
"""Run bounded on-policy drill updates and separate development comparisons."""
import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from player_actor import ROOT, file_hash
from player_v3_actor import source_hash

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('actor',type=Path);parser.add_argument('critic',type=Path)
parser.add_argument('output',type=Path);parser.add_argument('--first-seed',type=int,required=True)
parser.add_argument('--rounds',type=int,default=3);parser.add_argument('--episodes',type=int,default=2048)
parser.add_argument('--task',choices=['reaction-contact','reaction-return','near-return','drop-serve'],default='reaction-contact')
parser.add_argument('--development-first-seed',type=int,default=1100128)
args=parser.parse_args()
if args.output.exists():raise ValueError('Preserve existing experiment directories')
if not 1<=args.rounds<=20 or not 32<=args.episodes<=10000:raise ValueError('Invalid bounded series size')
if not 1000000<=args.first_seed or args.first_seed+args.rounds*args.episodes>1100000:raise ValueError('Training-only seed range required')
shell=shutil.which('pwsh') or shutil.which('powershell')
if not shell:raise ValueError('PowerShell runtime unavailable')
if not 1100000<=args.development_first_seed or args.development_first_seed+128>1200000:
    raise ValueError('Development-only comparison seeds required')
ledger=json.loads((ROOT/'artifacts/player-v3/seed-ledger.json').read_text())
if not any(b['firstSeed']<=args.development_first_seed and args.development_first_seed+128<=b['firstSeed']+b['count'] for b in ledger['developmentBlocks']):
    raise ValueError('Allocate the development comparison block before starting the series')
runtime_source=source_hash();actor=args.actor;critic=args.critic
args.output.mkdir(parents=True)
manifest=dict(status='running',task=args.task,sourceHash=runtime_source,createdUtc=datetime.now(timezone.utc).isoformat(),
    runnerHash=file_hash(Path(__file__)),parentActorHash=file_hash(actor),parentCriticHash=file_hash(critic),developmentFirstSeed=args.development_first_seed,developmentEpisodes=128,rounds=[])
def save(): (args.output/'series.json').write_text(json.dumps(manifest,indent=2))
def run(command):
    subprocess.run(command,cwd=ROOT,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
def collect(model,directory,first,count,split):
    run([shell,'-NoProfile','-File',str(ROOT/'scripts/run-player-v3-drill.ps1'),'-Actor',str(model),'-Output',str(directory),
         '-FirstSeed',str(first),'-Episodes',str(count),'-Split',split,'-Task',args.task])
save()
try:
    for index in range(args.rounds):
        if source_hash()!=runtime_source:raise ValueError('Runtime source changed during series')
        current=args.output/f'round-{index+1:02}'
        first=args.first_seed+index*args.episodes
        ledger_path=ROOT/'artifacts/player-v3/seed-ledger.json'
        ledger=json.loads(ledger_path.read_text())
        if any(first<b['firstSeed']+b['count'] and first+args.episodes>b['firstSeed'] for b in ledger['trainingBlocks']):
            raise ValueError('Training block is already allocated; do not silently recollect')
        ledger['trainingBlocks'].append(dict(firstSeed=first,count=args.episodes,task=args.task,
            purpose=str(current/'rollout'),historicalFreshness='Unverified across older V1/V2; unique within this V3 ledger'))
        ledger_path.write_text(json.dumps(ledger,indent=2))
        print(json.dumps(dict(round=index+1,status='collecting',firstSeed=first,episodes=args.episodes)),flush=True)
        collect(actor,current/'rollout',first,args.episodes,'training')
        print(json.dumps(dict(round=index+1,status='optimizing')),flush=True)
        run([sys.executable,str(ROOT/'scripts/player-v3-ppo.py'),str(current/'rollout'),str(actor),str(current/'checkpoint'),
             '--critic',str(critic),'--learning-rate','0.00002','--batch','512'])
        actor=current/'checkpoint/actor.json';critic=current/'checkpoint/critic.pt'
        collect(actor,current/'development',args.development_first_seed,128,'development')
        run([sys.executable,str(ROOT/'scripts/player_v3_rollouts.py'),str(current/'development'),str(actor)])
        training=json.loads((current/'checkpoint/training.json').read_text())
        validation=json.loads((current/'development/validation.json').read_text())
        entry=dict(round=index+1,actor=str(actor),actorHash=file_hash(actor),optimizerSteps=training['optimizerSteps'],
            training=training['summary'],development=validation)
        manifest['rounds'].append(entry);save()
        print(json.dumps(dict(round=index+1,status='evaluated',outcomes=validation['outcomes'])),flush=True)
    manifest['status']='complete'
except BaseException as error:
    manifest['status']='failed';manifest['failure']=str(error)
    raise
finally:save()

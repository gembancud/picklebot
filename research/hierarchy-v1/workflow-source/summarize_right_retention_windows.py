from pathlib import Path
from collections import defaultdict
import argparse,json,hashlib
R=Path('F:/dev/picklebot');B=R/'artifacts/hierarchy-v1/right-retention-01'
parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,default=B/'training');parser.add_argument('--output',type=Path);args=parser.parse_args()
groups=defaultdict(lambda:dict(episodes=0,legal=0,decisions=0));windows=defaultdict(lambda:defaultdict(lambda:dict(episodes=0,legal=0,decisions=0)));sources={}
for worker in sorted(args.evidence.glob('worker-*')):
    if not (worker/'episodes.jsonl').exists():continue
    startup=json.loads((worker/'worker-startup.json').read_text(encoding='utf-8'))
    raw=(worker/'episodes.jsonl').read_bytes();lines=raw.splitlines();lines=lines if raw.endswith(b'\n') else lines[:-1]
    sources[worker.name]=dict(snapshotHash=hashlib.sha256(raw).hexdigest(),completedLines=len(lines))
    for ordinal,line in enumerate(lines):
        e=json.loads(line);idx=(e['seed']-startup['firstSeed'])%256
        group='familiar' if idx<64 else 'prior' if idx<128 else 'right-focus'
        keys=['all',group]
        if group=='right-focus':keys+=[f"right-focus/{e['task']}/seat{e['player']}"]
        for key in keys:
            for row in [groups[key],windows[str(ordinal//512)][key]]:
                row['episodes']+=1;row['legal']+=e['outcome'] in ('legal_return','legal_serve');row['decisions']+=e['decisions']
for block in [groups,*windows.values()]:
    for row in block.values():
        row['legalRate']=row['legal']/row['episodes'];row['decisionShare']=row['decisions']/max(1,block['all']['decisions'])
out=dict(groups=dict(groups),windows={k:dict(v) for k,v in windows.items()},snapshots=sources,limitation='Windows use 512 completed episodes per worker; partial windows are retained and identified by counts. Episode decisions approximate collected exposure; shutdown tails and live incomplete trajectories may differ from PPO samples. No gradient-share claim.',final=bool((args.evidence/'run-complete.json').exists()))
if args.output:
    assert out['final'],'Only freeze final training windows after completion'
    with args.output.open('x',encoding='utf-8') as f:json.dump(out,f,indent=2)
print(json.dumps({k:v for k,v in groups.items() if '/' not in k},indent=2))

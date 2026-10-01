"""Read completed training logs; describe coverage, not frozen-policy competence."""
from pathlib import Path
from collections import defaultdict
import json, hashlib

root=Path('F:/dev/picklebot/artifacts/hierarchy-v1/smooth-distance-01/execution-smooth-distance-01')
cells=defaultdict(lambda: {'attempts':[0,0], 'legal':[0,0], 'landingsInA':[0,0], 'landingsInB':[0,0]})
hashes={}
for w in range(8):
    paths=[root/f'worker-{w:02}'/n for n in ['episodes.jsonl','execution-goals.jsonl']]
    data=[]
    for p in paths:
        hashes[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
        data.append({r['seed']:r for r in (json.loads(l) for l in p.read_text().splitlines())})
    episodes,goals=data
    assert set(episodes)==set(goals)
    for seed,e in episodes.items():
        g=goals[seed];serve=e['task']=='stationary-serve'
        region=int(g['targetZ']>4.5) if serve else int(g['targetX']>0)
        key=json.dumps([e['task'],e['player'],e['serveFromLeft'] if serve else None,e['feedDifficulty'],e['movementPattern'],e['movementRegion'],e['movementRange']],separators=(',',':'))
        c=cells[key];c['attempts'][region]+=1;c['legal'][region]+=int(g['legalLanding'])
        if g['legalLanding']:
            for r in [0,1]:
                tx=g['targetX'] if serve else (-1.2 if r==0 else 1.2)
                tz=(3.3 if r==0 else 5.4) if serve else 3.8
                hit=(g['landingX']-tx)**2+(g['landingZ']-tz)**2<=1
                c['landingsIn'+('A' if r==0 else 'B')][region]+=int(hit)

report={
 'status':'descriptive_training_coverage',
 'limitations':['Changing stochastic policies during training; not frozen evaluation.',
 'Cells use recorded reset descriptors, not proof of identical initial full physical state.',
 'Observed success establishes some support within a cell; failure does not prove physical impossibility.'],
 'inputHashes':hashes,'cells':dict(cells),
 'summary':{'cells':len(cells),'bothInstructionsSeen':sum(all(c['attempts']) for c in cells.values()),
 'atLeastOneLegalLandingInEachRegion':sum(sum(c['landingsInA'])>0 and sum(c['landingsInB'])>0 for c in cells.values()),
 'attemptsByInstruction':[sum(c['attempts'][i] for c in cells.values()) for i in [0,1]]}
}
dest=Path(__file__).with_name('training-target-coverage.json')
with dest.open('x',encoding='utf-8') as f:json.dump(report,f,indent=2)
print(json.dumps(report['summary']))

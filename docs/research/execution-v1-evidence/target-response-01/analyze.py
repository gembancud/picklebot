"""Analyze predeclared counterfactual evaluation; never infer aiming from action changes alone."""
from pathlib import Path
import json, hashlib, statistics

root=Path('F:/dev/picklebot')
audit=root/'artifacts/hierarchy-v1/target-response-01'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def rows(p): return [json.loads(s) for s in p.read_text(encoding='utf-8-sig').splitlines() if s.strip()]
results=[]
for model in ['ExecutionV1Initial','ExecutionV1Smoke01']:
    conditions=[]
    for side in [-1,1]:
        folder=audit/f'{model}-{side}'
        report=read(folder/'report.json')
        assert report['status']=='seed_budget_complete' and not report['failure']
        decisions=rows(folder/'decisions.jsonl')
        first={}
        for d in decisions: first.setdefault(d['seed'],d)
        goals=rows(folder/'execution-goals.jsonl'); episodes=rows(folder/'episodes.jsonl')
        assert len(first)==len(goals)==len(episodes)==64
        assert all(d['observation'][132]==1 and len(d['observation'])==136 for d in decisions)
        conditions.append((first,decisions,goals,episodes))
    a,b=conditions
    deltas=[]
    for seed in a[0]:
        x,y=a[0][seed],b[0][seed]
        assert x['observationTick']==y['observationTick']==0
        assert x['observation'][:133]==y['observation'][:133]
        assert x['observation'][134:]==y['observation'][134:]
        assert x['observation'][133]!=y['observation'][133]
        deltas.append(max(abs(p-q) for p,q in zip(x['continuous'],y['continuous'])))
    if model=='ExecutionV1Initial':
        assert max(deltas)==0
        # Target bonus changes episode reward; all physical outcomes must agree.
        ea={e['seed']:{k:v for k,v in e.items() if k!='reward'} for e in a[3]}
        eb={e['seed']:{k:v for k,v in e.items() if k!='reward'} for e in b[3]}
        assert ea==eb,'Negative-control physical outcomes changed'
        da={(d['seed'],d['observationTick']):d for d in a[1]}
        db={(d['seed'],d['observationTick']):d for d in b[1]}
        assert da.keys()==db.keys()
        assert all(da[k]['continuous']==db[k]['continuous'] and da[k]['observation'][:124]==db[k]['observation'][:124] for k in da)
    result=dict(model=model,modelHash=hashlib.sha256((root/f'Assets/Picklebot/PlayerLearning/Models/{model}.onnx').read_bytes()).hexdigest(),
        identicalPhysicalResets=64,firstActionMaxAbsoluteDelta=max(deltas),firstActionMedianMaxAbsoluteDelta=statistics.median(deltas),
        firstActionsChanged=sum(d>1e-6 for d in deltas),conditions=[])
    for side,(_,_,g,e) in zip([-1,1],conditions):
        legal=[x for x in g if x['legalLanding']]
        result['conditions'].append(dict(side=side,attempts=64,legal=len(legal),targets=sum(x['targetHit'] for x in g),
            meanDistanceGivenLegal=statistics.mean(x['distance'] for x in legal)))
    results.append(result)
out=dict(status='counterfactual_completed',results=results,negativeControlExact=True,
    interpretation='Goal sensitivity is separate from goal accuracy. Small action changes do not prove useful aiming. This is a reused development screen, not final acceptance.',promoted=False)
with (audit/'verification.json').open('x',encoding='utf-8') as f: json.dump(out,f,indent=2)
print(json.dumps(out,indent=2))

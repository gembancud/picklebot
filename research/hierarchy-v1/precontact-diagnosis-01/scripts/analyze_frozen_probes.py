from pathlib import Path
import json,hashlib
from collections import defaultdict
import numpy as np
R=Path('F:/dev/picklebot');B=R/'artifacts/hierarchy-v1/precontact-frozen-training-01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def rows(p):return {r['seed']:r for r in map(json.loads,p.read_text().splitlines())}
def key(ob):return np.asarray(ob,dtype='<f4').tobytes()
def main():
    runs={};inputs={};metrics={}
    for mode in ['deterministic','sampled']:
        folder=B/mode/'worker-00';assert read(B/mode/'verification.json')['actorCriticNormalizationOptimizerUnchanged']
        eps=rows(folder/'episodes.jsonl');assert sorted(eps)==list(range(1000000,1000512))
        first={}
        with (folder/'decisions.jsonl').open() as stream:
            for line in stream:
                row=json.loads(line)
                if row['observationTick']==0:
                    assert row['seed'] not in first;first[row['seed']]=row
        assert set(first)==set(eps)
        for name in ['episodes.jsonl','decisions.jsonl','report.json','execution-goals.jsonl']:inputs[str((folder/name).relative_to(R))]=sha(folder/name)
        groups={'all':list(eps.values()),'focus':[r for r in eps.values() if r['movementPattern']=='axes']}
        for cm,ran in [(6.25,.015625),(12.5,.03125),(18.75,.046875),(25,.0625)]:
            groups[f'{cm}cm']=[r for r in eps.values() if r['movementPattern']=='axes' and r['movementRange']==ran]
            for reg,label in [(3,'left'),(5,'right'),(1,'shallow'),(7,'deep')]:groups[f'{cm}cm/{label}']=[r for r in groups[f'{cm}cm'] if r['movementRegion']==reg]
        metrics[mode]={g:dict(attempts=len(rs),legal=sum(r['outcome'] in ('legal_return','legal_serve') for r in rs),contact=sum(r['faceContact'] for r in rs),crossed=sum(r['netCrossed'] for r in rs)) for g,rs in groups.items()}
        runs[mode]=(eps,first)
    for seed in runs['deterministic'][1]:assert key(runs['deterministic'][1][seed]['observation'])==key(runs['sampled'][1][seed]['observation'])
    # Compare actual common observation/goal states across Python deterministic inference
    # and the completed Unity deterministic development evaluation. Seed IDs differ.
    index=defaultdict(list)
    for seed,row in runs['deterministic'][1].items():index[key(row['observation'])].append(seed)
    matches=[]
    for condition in ['A','B']:
        folder=R/f'artifacts/hierarchy-v1/precontact-alignment-01/evaluation/wide/ExecutionV1PrecontactFinal01/{condition}'
        first=read(folder/'first-decisions.json');eps=rows(folder/'episodes.jsonl')
        for seedstr,row in first.items():
            for source_seed in index.get(key(row['observation']),[]):
                old=runs['deterministic'][1][source_seed]
                matches.append(dict(trainingSeed=source_seed,developmentSeed=int(seedstr),condition=condition,firstActionMaxDifference=float(np.max(np.abs(np.asarray(row['physical'])-np.asarray(old['physical'])))),sameOutcome=runs['deterministic'][0][source_seed]['outcome']==eps[int(seedstr)]['outcome']))
    summary=dict(conditions=metrics,paired512InitialObservationsExact=True,noLearningUpdatesVerified=True,commonFullObservationMatches=len(matches),commonFirstActionMaxDifference=max((m['firstActionMaxDifference'] for m in matches),default=None),commonOutcomeAgreements=sum(m['sameOutcome'] for m in matches),matches=matches,inputs=inputs,scriptHash=sha(Path(__file__)),limitations=['Used training seeds, not acceptance or generalization.','One sampled action rollout per feed; small per-direction25cm cells.','Raw training-to-wide aggregate rates differ in feed distance and task/player frequencies; compare matched states or stratified cells.','Matching full first observation does not prove hidden physics and subsequent decision timing are identical.'],promotion=False)
    with (B/'analysis.json').open('x') as f:json.dump(summary,f,indent=2)
    print(json.dumps({k:v for k,v in summary.items() if k not in ('matches','inputs','conditions')},indent=2))
    print({mode:{g:v for g,v in m.items() if g in ('focus','25cm','25cm/right','25cm/deep')} for mode,m in metrics.items()})
if __name__=='__main__':main()

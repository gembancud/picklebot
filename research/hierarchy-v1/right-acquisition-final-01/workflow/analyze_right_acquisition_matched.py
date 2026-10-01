"""Paired acquisition diagnostic; never substitutes for the full retention batteries."""
from pathlib import Path
import json,hashlib
import numpy as np
import analyze_movement_progress as old
R=Path('F:/dev/picklebot');B=R/'artifacts/hierarchy-v1/right-acquisition-01'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    inputs={};w,f,h=old.load_helpers(R,inputs);seeds=list(range(1109849,1110361))
    specs=[read(B/'acquisition-baseline-evaluation.json'),read(B/'acquisition-final-evaluation.json')]
    runs={};models=[s['model']['model'] for s in specs]
    for spec in specs:
        identity=spec['model'];model=identity['model']
        assert spec['firstSeed']==seeds[0] and spec['count']==512
        assert sha(R/identity['assetPath'])==identity['modelHash'] and sha(R/identity['checkpoint'])==identity['checkpointHash']
        for condition in ['A','B']:
            folder=B/'evaluation/acquisition'/model/condition
            for name in (*f.FILES,'summary.json'):f.record_input(R,folder/name,inputs)
            ep=f.read_rows(folder/'episodes.jsonl',seeds);goals=f.read_rows(folder/'execution-goals.jsonl',seeds)
            first={int(k):v for k,v in read(folder/'first-decisions.json').items()};report=read(folder/'report.json');side=read(folder/'model-identity.json')
            assert sorted(first)==seeds and report['completedEpisodes']==512 and report['status']=='seed_budget_complete' and not report['failure']
            assert report['task']=='right-return-acquisition' and report['movementRange']==.0625 and not report['precontactAlignmentReward'] and not report['movementForwardProgressReward']
            assert all(side[k]==identity[k] for k in ['model','step','modelHash','checkpointHash','trainingSourceIdentity']) and side['sourceIdentity']==spec['runtimeSourceIdentity']
            for seed in seeds:
                e,g=ep[seed],goals[seed];obs=first[seed]['observation'];assert len(obs)==136 and np.isfinite(obs).all()
                assert e['movementPattern']=='lateral-right' and e['movementRange']==.0625 and e['movementRegion']==5
                assert not e['precontactAlignmentRewardEnabled'] and e['precontactShapingReward']==0 and not e['movementForwardProgressRewardEnabled']
                assert e['task'] in ('rally-air-feed','rally-bounce-feed') and e['outcome']==g['outcome'] and e['outcome'] not in ('exception','infeasible')
                legal=e['outcome']=='legal_return';assert g['legalLanding']==legal and g['hasLanding']==legal
                assert not legal or e['faceContact'] and e['netCrossed']
                assert g['targetHit']==h.hit(g,g) and g['radius']==1 and g['targetLayout']=='two-regions'
                assert np.allclose(h.target(g),[-1.2 if condition=='A' else 1.2,3.8],rtol=0,atol=2e-6)
                if legal:assert abs(np.linalg.norm(h.landing(g)-h.target(g))-g['distance'])<2e-5
            for task in ('rally-air-feed','rally-bounce-feed'):
                for seat in range(4):assert sum(e['task']==task and e['player']==seat for e in ep.values())==64
            runs[model,condition]=(ep,goals,first)
    keys={s:f.physical_key(runs[models[0],'A'][2][s]['observation']) for s in seeds}
    for model in models:
        for c in ['A','B']:
            for s in seeds:
                assert keys[s]==f.physical_key(runs[model,c][2][s]['observation'])
                assert np.array_equal(np.asarray(runs[model,c][2][s]['observation'],dtype=np.float32),np.asarray(runs[models[0],c][2][s]['observation'],dtype=np.float32))
    groups={'all':seeds}
    for task in ('rally-air-feed','rally-bounce-feed'):
        groups[task]=[s for s in seeds if runs[models[0],'A'][0][s]['task']==task]
        for seat in range(4):groups[f'{task}/seat{seat}']=[s for s in groups[task] if runs[models[0],'A'][0][s]['player']==seat]
    results={}
    for group,chosen in groups.items():
        summary={}
        for model in models:
            causal,gains=h.causal([runs[model,'A'][1][s] for s in chosen],[runs[model,'B'][1][s] for s in chosen])
            summary[model]=dict(conditions={c:dict(attempts=len(chosen),legal=sum(runs[model,c][1][s]['legalLanding'] for s in chosen),targetHits=sum(runs[model,c][1][s]['targetHit'] for s in chosen),contacts=sum(runs[model,c][0][s]['faceContact'] for s in chosen),netCrossings=sum(runs[model,c][0][s]['netCrossed'] for s in chosen)) for c in ['A','B']},causal=causal,uniqueClusterAssignmentGain=f.unique_cluster_ci(h,gains,chosen,keys))
        results[group]=dict(models=summary,pairedChanges={c:h.paired_changes_for([runs[models[0],c][1][s] for s in chosen],[runs[models[1],c][1][s] for s in chosen]) for c in ['A','B']})
    assert not read(R/'artifacts/player-v3/seed-ledger.json')['finalSeedsConsumed']
    for rel,digest in inputs.items():assert sha(R/rel)==digest
    out=B/'results';out.mkdir(exist_ok=True)
    with (out/'acquisition-analysis.json').open('x') as stream:json.dump(dict(groups=results,uniquePhysicalObservationClusters=len(set(keys.values())),inputSha256=inputs,scriptHash=sha(Path(__file__)),fullRetentionEvaluationRequired=True,masteryAccepted=False,promoted=False,finalSeedsConsumed=False),stream,indent=2)
    print(json.dumps(results['all'],indent=2))
if __name__=='__main__':main()

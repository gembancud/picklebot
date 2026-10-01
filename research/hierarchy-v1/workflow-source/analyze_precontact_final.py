"""Compare the fixed precontact endpoint against preserved same-feed baselines."""
from pathlib import Path
import json, hashlib
from collections import Counter
import numpy as np
import analyze_movement_progress as old
R=Path('F:/dev/picklebot'); B=R/'artifacts/hierarchy-v1/precontact-alignment-01'
FINAL='ExecutionV1PrecontactFinal01'; PARENT=old.PARENT; CONTROL=old.CONTROL
MODELS=(PARENT,CONTROL,FINAL)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def compact(episodes,goals):
    paths=[ep['travelBeforeContact'][ep['player']] for ep in episodes if len(ep.get('travelBeforeContact',[]))>ep['player']]
    return dict(attempts=len(episodes),legal=sum(g['legalLanding'] for g in goals),targets=sum(g['targetHit'] for g in goals),acceptedContacts=sum(ep['faceContact'] for ep in episodes),netCrossings=sum(ep['netCrossed'] for ep in episodes),actualVolleyContacts=sum(ep['faceContact'] and ep['contactWasVolley'] for ep in episodes),actualAfterBounceRallyContacts=sum(ep['task'] in ('rally-air-feed','rally-bounce-feed') and ep['faceContact'] and not ep['contactWasVolley'] for ep in episodes),rootPathMeasuredAttempts=len(paths),rootPathThroughContactOrTerminationMeanMetres=float(np.mean(paths)) if paths else None)
def main():
    inputs={};w,f,h=old.load_helpers(R,inputs)
    selected=read(B/'selected-models.json');identity=selected['final']
    assert selected['planHash']==sha(B/'plan.json') and selected['trainingProofHash']==sha(B/'training/run-complete.json')
    for k,v in [('assetPath','modelHash'),('checkpoint','checkpointHash')]:assert sha(R/identity[k])==identity[v]
    for rel,digest in read(B/'source-records.json')['files'].items():assert sha(R/rel)==digest
    assert not read(R/'artifacts/player-v3/seed-ledger.json')['finalSeedsConsumed']
    fixture=read(R/'artifacts/hierarchy-v1/wide-movement-fixture-01/fixture/wide-fixture-0000.json')
    desc={x['seed']:x for x in fixture['planned']};output={}
    reset_fields=('task','player','feedDifficulty','feedLowering','feedLateralOffset','initialHoldLift','serveFromLeft','movementFeed','movementRegion','movementRange','movementTiming','movementStartVariation','movementPattern')
    for battery,n,start,conditions in [('narrow',256,1109593,('A','B','random')),('wide',512,1109849,('A','B'))]:
        runs={};seeds=list(range(start,start+n))
        for model in MODELS:
            for condition in conditions:
                base=(B/f'evaluation/{battery}' if model==FINAL else R/f'artifacts/hierarchy-v1/axes-recovery-01/evaluation/{battery}' if model==CONTROL else R/('artifacts/hierarchy-v1/fresh-placement-01/evaluation' if battery=='narrow' else 'artifacts/hierarchy-v1/wide-movement-fixture-01/evaluation'))
                folder=base/model/condition
                for name in (*f.FILES,'summary.json'):f.record_input(R,folder/name,inputs)
                eps=f.read_rows(folder/'episodes.jsonl',seeds);goals=f.read_rows(folder/'execution-goals.jsonl',seeds)
                first={int(k):v for k,v in read(folder/'first-decisions.json').items()};report=read(folder/'report.json');sidecar=read(folder/'model-identity.json')
                assert sorted(first)==seeds and report['status']=='seed_budget_complete' and report['completedEpisodes']==n and not report['failure']
                assert not report['trainerConnected'] and report['contract']==f.CONTRACT
                if model==FINAL:
                    assert all(sidecar[k]==identity[k] for k in ('model','step','modelHash','checkpointHash','sourceIdentity'))
                    assert not report['precontactAlignmentReward'] and not report['movementForwardProgressReward']
                for seed in seeds:
                    ep,g,ob=eps[seed],goals[seed],np.asarray(first[seed]['observation'],dtype=np.float32)
                    assert ob.shape==(136,) and np.isfinite(ob).all() and len(first[seed]['physical'])==18
                    assert ep['outcome']==g['outcome'] and ep['outcome'] not in ('exception','infeasible')
                    legal=ep['outcome'] in ('legal_return','legal_serve')
                    assert g['legalLanding']==legal and g['hasLanding']==legal and g['targetHit']==h.hit(g,g)
                    assert ep['player']==g['player']==first[seed]['player']
                    assert g['contract']==f.CONTRACT and g['rewardMode']=='linear-radius'
                    assert not legal or ep['faceContact'] and ep['netCrossed']
                    if ep['task']=='receive-feed':assert not ep['faceContact'] or ep['incomingServeLanded']
                    if ep['task']=='stationary-serve':assert not legal or ep['serveAccepted']
                    if ep['contactWasVolley']:assert ep['faceContact'] and ep['task'] in w.DRILLS[2:]
                    if legal:assert abs(np.linalg.norm(h.landing(g)-h.target(g))-g['distance'])<2e-5
                    else:assert g['distance']==-1 and g['landingX']==g['landingZ']==0
                    if model==FINAL:
                        assert not ep['precontactAlignmentRewardEnabled'] and ep['precontactShapingReward']==0 and ep['precontactTransitions']==0
                        assert not ep['movementForwardProgressRewardEnabled'] and ep['movementPositionReward']==0
                runs[model,condition]=(eps,goals,first,report)
        keys={seed:f.physical_key(runs[PARENT,'A'][2][seed]['observation']) for seed in seeds}
        for model in MODELS:
            for condition in conditions:
                eps,goals,first,report=runs[model,condition];reference=runs[PARENT,condition]
                for seed in seeds:
                    assert np.array_equal(np.asarray(first[seed]['observation'],dtype=np.float32),np.asarray(reference[2][seed]['observation'],dtype=np.float32))
                    assert f.physical_key(first[seed]['observation'])==keys[seed]
                    assert all(eps[seed][k]==reference[0][seed][k] for k in reset_fields)
                    assert np.array_equal(h.target(goals[seed]),h.target(reference[1][seed])) and goals[seed]['radius']==reference[1][seed]['radius']
        ep=runs[PARENT,'A'][0];groups={'all':seeds}
        for task in w.DRILLS:groups['drill/'+task]=[s for s in seeds if ep[s]['task']==task]
        for side,flag in [('left',True),('right',False)]:groups['serve/'+side]=[s for s in seeds if ep[s]['task']=='stationary-serve' and ep[s]['serveFromLeft']==flag]
        if battery=='wide':
            for direction in w.DIRECTIONS:groups['axis/'+direction]=[s for s in seeds if desc[s]['direction']==direction]
            for cm in (25,50,75,100):groups[f'shift/{cm}cm']=[s for s in seeds if desc[s]['centimetres']==cm]
            groups['axis/all']=[s for s in seeds if desc[s]['challenge']]
            for direction in w.DIRECTIONS:
                for cm in (25,50,75,100):groups[f'axis/{direction}/{cm}cm']=[s for s in seeds if desc[s]['direction']==direction and desc[s]['centimetres']==cm]
        details={}
        for group,chosen in groups.items():
            if not chosen:continue
            values={};gains={}
            for model in MODELS:
                causal,gains[model]=h.causal([runs[model,'A'][1][s] for s in chosen],[runs[model,'B'][1][s] for s in chosen])
                values[model]=dict(counts={c:compact([runs[model,c][0][s] for s in chosen],[runs[model,c][1][s] for s in chosen]) for c in conditions},causal=causal,clusterAssignmentGain=f.unique_cluster_ci(h,gains[model],chosen,keys))
                values[model]['failureStages']={c:dict(Counter('legal' if runs[model,c][1][s]['legalLanding'] else 'no_contact' if not runs[model,c][0][s]['faceContact'] else 'contact_without_crossing' if not runs[model,c][0][s]['netCrossed'] else 'crossed_not_legal' for s in chosen)) for c in conditions}
                if model==FINAL:
                    values[model]['contactNormalAlignment']={c:w.values_summary([runs[model,c][0][s]['faceContactNormalAlignment'] for s in chosen if runs[model,c][0][s]['faceContact'] and runs[model,c][0][s]['faceContactNormalAlignment']>=0]) for c in conditions}
            changes={model:dict(assignmentGain=h.ci(gains[FINAL]-gains[model]),conditions={c:h.paired_changes_for([runs[model,c][1][s] for s in chosen],[runs[FINAL,c][1][s] for s in chosen]) for c in conditions}) for model in (PARENT,CONTROL)}
            details[group]=dict(models=values,finalMinusBaseline=changes)
        output[battery]=dict(groups=details,pairedFullObservationsAndTargetsVerified=True,resets=n)
    for rel,digest in inputs.items():assert sha(R/rel)==digest
    target=B/'results';target.mkdir(exist_ok=True)
    with (target/'analysis.json').open('x') as stream:json.dump(dict(model=identity,batteries=output,inputSha256=inputs,analysisHash=sha(Path(__file__)),promoted=False,masteryAccepted=False,finalSeedsConsumed=False,limitations=['Reused development anchors; not held-out final acceptance.','One seeded reward arm; no independent training replication.','Wide50-100cm cases exceed25cm focus training range.','Conditional landing response excludes failures; outcome counts retain all attempts.']),stream,indent=2)
    for battery,data in output.items():
        print(battery,json.dumps({g:{m:v['counts'] for m,v in row['models'].items()} for g,row in data['groups'].items() if g in ('all','axis/all','axis/right','serve/left','serve/right')}))
if __name__=='__main__':main()

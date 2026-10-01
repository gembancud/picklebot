"""Freeze an unused-ledger development cohort before observing its policy outcomes."""
from pathlib import Path
import json,hashlib,datetime,shutil
root=Path('F:/dev/picklebot');here=Path(__file__).parent
base=root/'artifacts/hierarchy-v1/fresh-placement-01'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
ledger_path=root/'artifacts/player-v3/seed-ledger.json';ledger=read(ledger_path)
assert ledger['finalSeedsConsumed']==[]
first,count=1109593,256
for key,entries in ledger.items():
    if isinstance(entries,list):
        for entry in entries:
            if isinstance(entry,dict) and 'firstSeed' in entry and 'count' in entry:
                lo,n=int(entry['firstSeed']),int(entry['count'])
                assert max(lo,first)>=min(lo+n,first+count),f'Already allocated {key}: {entry}'
assert 1100000<=first and first+count<=1200000
assert not base.exists();base.mkdir()
source=read(root/'artifacts/hierarchy-v1/smooth-distance-01/source-records.json')
assert all(sha(root/n)==h for n,h in source['files'].items())
models=['ExecutionV1Initial','ExecutionV1SmoothContinuedFinal01']
records={
 models[0]:dict(modelHash='bc6f8be16b791a2cd253b150b3f4c4c2492cdc0e65f94fa305ab4addefe78d51',checkpointHash='2c1dcfab6c32d3e98dfd334863f5670c09cef2edfb8bf51483bba4abe683cb9f',step=0,checkpoint='training/snapshots/execution-v1-initial.pt'),
 models[1]:dict(modelHash='40047704eaf92ae933e861abfbe4c6f262a4595685ca985e3c1a185804ed13cb',checkpointHash='93029a5bfe5a13815f47d1487ff15c3e9455516ee3b5609d9e38f0c0f82e778d',step=1048609,checkpoint='training/snapshots/execution-v1-smooth-continued-final-01.pt')}
for model,r in records.items():
    r.update(model=model,assetPath=f'Assets/Picklebot/PlayerLearning/Models/{model}.onnx',sourceIdentity=source['sourceIdentity'])
    assert sha(root/r['assetPath'])==r['modelHash'] and sha(root/r['checkpoint'])==r['checkpointHash']
prior='artifacts/hierarchy-v1/two-regions-01/evaluation/ExecutionV1Initial/A/first-decisions.json'
plan=dict(version='fresh-placement-screen-01',createdAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 sourceIdentity=source['sourceIdentity'],firstSeed=first,seedCount=count,models=models,modelIdentities=records,
 conditions=['A','B','random'],evaluationRewardMode='linear-radius',
 priorObservationInputs={prior:sha(root/prior)},expectedPriorUniqueObservations=150,
 physicalRecipe=dict(task='movement-maintenance',maximumReturnDifficulty=.25,movementRange=.025,movementPattern='lateral',movementRehearsalRange=.1,movementRecoveryMix=True,interleavedRecovery=True,movementTiming=0,movementStartVariation=0,fixedServeSides='both'),
 screening=dict(maximumPerDrillLegalDrop=.05,requireUniqueClusterGainCiLowerAboveZero=True,
 rules=['Reset-weighted assignment gain paired95% lower >0','Equal-weight unique-physical-observation cluster assignment gain95% lower >0','Both A/B target rates exceed the same-cohort initializer','No per-drill legal-rate drop greater than5percentage points in any condition'],
 interpretation='Diagnostic confirmation of target responsiveness and retention. Full mastery and target feasibility remain unproven even if this screen passes.'),
 novelty=dict(fingerprint='First124 physical observation values cast to float32; exclude goals,seedID and actions',
 prior='Union of the pinned old observation inputs',
 report=['Exact within-cohort unique vectors and multiplicities','Exact overlap with prior vectors','Novel/repeated subsets by drill','Nearest-prior maximum absolute feature difference; thresholds1e-5 and1e-4 are descriptive, not a success filter'],
 interpretation='New ledger IDs are not proof of new situations. Preserve all256 attempts in the primary analysis; do not select cases based on success. Same observed state does not prove equality of every hidden simulator variable.',
 constructorPrediction={'repeatedPotential':184,'potentiallyNovelMaximum':72,'basis':'Fixed serves/familiar/local focus and easy receives repeat at zero timing/start variation; court-grid and varied receive cases may change. Prediction must be checked against actual observations.'}),
 freshness=dict(scope='Unused within the current V3 ledger; olderV1/V2 historical freshness remains unverified',ledgerBeforeHash=sha(ledger_path)),
 finalSeedsConsumed=False,masteryAccepted=False,automaticPromotion=False)
with (base/'plan.json').open('x',encoding='utf-8') as f:json.dump(plan,f,indent=2)
shutil.copy2(root/'artifacts/hierarchy-v1/smooth-distance-01/source-records.json',base/'source-records.json')
shutil.copy2(ledger_path,base/'seed-ledger-before.json')
script_hashes={}
for model,short in [(models[0],'initial'),(models[1],'final')]:
    r=records[model]
    for condition in plan['conditions']:
        code=(here/f'continued-final-{condition}.cs').read_text(encoding='utf-8-sig')
        code=code.replace(models[1],model).replace('smooth-continued-01/evaluation','fresh-placement-01/evaluation')
        code=code.replace('run.FirstSeed=1108985;','run.FirstSeed=1109593;')
        code=code.replace(records[models[1]]['modelHash'],r['modelHash']).replace(records[models[1]]['checkpointHash'],r['checkpointHash'])
        code=code.replace('step=1048609,','step='+str(r['step'])+',')
        out=here/f'fresh-{short}-{condition}.cs';out.write_text(code,encoding='utf-8',newline='\n')
        script_hashes[out.name]=sha(out)
for mode in ['prepare_scene','restore_editor']:
    code=(here/f'continued-{mode}.cs').read_text(encoding='utf-8-sig').replace('smooth-continued-01/','fresh-placement-01/')
    out=here/f'fresh-{mode}.cs';out.write_text(code,encoding='utf-8',newline='\n');script_hashes[out.name]=sha(out)
with (base/'script-hashes.json').open('x',encoding='utf-8') as f:json.dump(script_hashes,f,indent=2)
ledger['developmentBlocks'].append(dict(firstSeed=first,count=count,run='artifacts/hierarchy-v1/fresh-placement-01',purpose='Predeclared frozen initializer vs1048609 candidate; same physical recovery mixture, pairedA/B/random, measured physical-observation novelty and cluster-aware uncertainty. Diagnostic only; no promotion or final seeds.'))
ledger_path.write_text(json.dumps(ledger,indent=2),encoding='utf-8',newline='\n')
with (base/'allocation.json').open('x',encoding='utf-8') as f:json.dump(dict(firstSeed=first,count=count,ledgerBeforeHash=plan['freshness']['ledgerBeforeHash'],ledgerAfterHash=sha(ledger_path),planHash=sha(base/'plan.json'),finalSeedsConsumed=False),f,indent=2)
print(json.dumps({'plan':str(base/'plan.json'),'firstSeed':first,'count':count,'scriptCount':len(script_hashes)}))

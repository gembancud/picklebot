from pathlib import Path
import json,hashlib
root=Path('F:/dev/picklebot');base=root/'artifacts/hierarchy-v1/smooth-distance-01';old=root/'artifacts/hierarchy-v1/two-regions-01';here=Path(__file__).parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=read(base/'source-records.json');assert (base/'build-verification.json').exists()
plan=read(old/'plan.json')
oldsource=read(old/'source-records.json')['sourceIdentity']
baselinefiles=[p for m in ['ExecutionV1Initial','ExecutionV1TwoRegions01'] for p in (old/'evaluation'/m).rglob('*') if p.is_file()]
baselinefiles += [old/'source-records.json',old/'audit/analysis.json']
plan.update(version='smooth-distance-placement-screen-01',candidate='ExecutionV1SmoothDistance01',linearControl='ExecutionV1TwoRegions01',
    sourceIdentity=source['sourceIdentity'],baselineRoot=str(old),baselineInputSha256={p.relative_to(old).as_posix():sha(p) for p in baselinefiles},
    modelSourceIdentities={'ExecutionV1Initial':oldsource,'ExecutionV1TwoRegions01':oldsource,'ExecutionV1SmoothDistance01':source['sourceIdentity']},
    baselineReuse='Frozen prior256-case initializer and linear-trained A/B/random evidence retained with original source and hashes. New32-episode frozen-policy linear/smooth trajectory parity plus20Unitychecks supports reuse; baseline was not rerun on new source.',
    training='Only placement bonus changes from linear inside radius to0.25*exp(-distance/2m), legal landings only. Same target centers/radius1m, physical recovery schedule, base rewards, initializer, PPO settings and262144 budget.',
    evaluationRewardMode='linear-radius',trainingRewardMode='smooth-distance-2m',
    sourceChanges='Opt-in terminal reward mode, validation/evidence/stats and tests; controls/feed/observations unchanged. Unity analytics define settled before source hashing.',
    modelHashes={'ExecutionV1Initial':sha(root/'Assets/Picklebot/PlayerLearning/Models/ExecutionV1Initial.onnx'),'ExecutionV1TwoRegions01':sha(root/'Assets/Picklebot/PlayerLearning/Models/ExecutionV1TwoRegions01.onnx')},
    interpretation='Compare against initializer for acquired target following, and historical linear-trained model for a single-run reward-recipe comparison; not robust multi-seed evidence.')
with (base/'plan.json').open('x',encoding='utf-8') as f:json.dump(plan,f,indent=2)
manifest=read(root/'config/mlagents/execution-v1-two-regions-workers.json')
manifest['placementRewardMode']='smooth-distance-2m'
(root/'config/mlagents/execution-v1-smooth-distance-workers.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(root/'config/mlagents/execution-v1-smooth-distance.yaml').write_text((root/'config/mlagents/execution-v1-two-regions.yaml').read_text(),encoding='utf-8')
s=(root/'tools/mlagents-training/run_execution_two_regions_v1.py').read_text()
s=s.replace("BASE=ROOT/'artifacts/hierarchy-v1/two-regions-01'","BASE=ROOT/'artifacts/hierarchy-v1/smooth-distance-01'")
s=s.replace('execution-two-regions-02','execution-smooth-distance-01').replace('execution-v1-two-regions','execution-v1-smooth-distance').replace('5605','5635')
s=s.replace("x['radius']==1 and x['hasLanding']", "x['radius']==1 and x['rewardMode']=='smooth-distance-2m' and x['hasLanding']")
s=s.replace('two discrete target regions, radius1.0.','two discrete target regions, radius1.0, smooth legal-distance feedback.')
(root/'tools/mlagents-training/run_execution_smooth_distance_v1.py').write_text(s,encoding='utf-8')
template=(here/'two_regions_evaluate_template.cs').read_text().replace('artifacts/hierarchy-v1/two-regions-01','artifacts/hierarchy-v1/smooth-distance-01')
template=template.replace('goals.SampleShotTargets=true;', 'goals.RewardMode=Picklebot.PlayerLearning.PlayerExecutionDrillsV1.LinearReward;goals.SampleShotTargets=true;')
for condition,region in [('A',0),('B',1),('random',-1)]:
    code=template.replace('__MODEL__',plan['candidate']).replace('__CONDITION__',condition).replace('__REGION__',str(region)).replace('__SOURCE__',source['sourceIdentity'])
    (here/f'smooth-{condition}.cs').write_text(code,encoding='utf-8')
ledgerpath=root/'artifacts/player-v3/seed-ledger.json';ledger=read(ledgerpath)
assert not ledger['finalSeedsConsumed']
ledger.setdefault('developmentReuses',[]).append(dict(firstSeed=1108985,count=256,run=str(base.relative_to(root)),purpose='Smooth legal-distance reward final candidate: pairedA/B plus unchangedrandom retention; initializer/linearcontrol frozen evidence reused'))
ledgerpath.write_text(json.dumps(ledger,indent=2),encoding='utf-8')
print(json.dumps({k:plan[k] for k in ['version','sourceIdentity','trainingRewardMode','evaluationRewardMode','baselineReuse']},indent=2))

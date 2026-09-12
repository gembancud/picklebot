from pathlib import Path
import json
root=Path('F:/dev/picklebot');base=root/'artifacts/hierarchy-v1/two-regions-01'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
assert (base/'build-verification.json').exists()
plan=dict(version='two-regions-placement-screen-01',parent='ExecutionV1Initial',candidate='ExecutionV1TwoRegions01',
    sourceIdentity=read(base/'source-records.json')['sourceIdentity'],experiences=262144,
    training='Same movement-maintenance recovery schedule and PPO settings as execution-placement-01; target layout two-regions, radius 1.0; fixed initializer and fresh optimizer',
    firstSeed=1108985,baseResetCount=256,developmentSeedsReused=True,finalSeedsConsumed=False,
    evaluation=['Each base reset repeated with regions A and B, for parent and final candidate','Unchanged random-target radius1.5 retention screen on same complete recovery cycle'],
    outcome='Per drill/region and service side: legal/all attempts, legal target hits/all attempts, secondary conditional distance. Central vs actual movement separated.',
    causal='All-pair requested-minus-opposite region assignment gain, illegal attempts zero; signed landing shift on both-legal pairs plus its denominator. Initializer negative control must cancel.',
    candidateSelection='Final checkpoint only; no searching intermediate checkpoints after seeing these results',
    screening='Promising only if all-pair assignment gain has positive95% paired-bootstrap lower bound, both regions improve target hit rate vs parent, and no drill legal-rate point estimate drops more than5percentage points. This is a development screening rule, not mastery acceptance.',
    acceptance='No automatic promotion. Confirm promising results on fresh development cases and an independent training run before setting final mastery acceptance. No target/feed feasibility claim from geometry alone.')
with (base/'plan.json').open('x',encoding='utf-8') as f:json.dump(plan,f,indent=2)
manifest=read(root/'config/mlagents/execution-v1-workers.json')
manifest.update(executionContract=plan['sourceIdentity'] if False else 'execution-v1-136obs-16continuous-release',
    optimizerDiagnostics=False,targetLayout='two-regions',sampleShotTargets=True,targetRadius=1.0,legalTargetReward=.25)
(root/'config/mlagents/execution-v1-two-regions-workers.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
yaml=(root/'config/mlagents/execution-v1-placement.yaml').read_text()
(root/'config/mlagents/execution-v1-two-regions.yaml').write_text(yaml,encoding='utf-8')
launcher=(root/'tools/mlagents-training/run_execution_placement_v1.py').read_text()
launcher=launcher.replace("BASE=ROOT/'artifacts/hierarchy-v1'","BASE=ROOT/'artifacts/hierarchy-v1/two-regions-01'")
launcher=launcher.replace('execution-placement-01','execution-two-regions-01').replace('execution-v1-placement.yaml','execution-v1-two-regions.yaml').replace('execution-v1-workers.json','execution-v1-two-regions-workers.json').replace('5415','5425')
launcher=launcher.replace("init=BASE/'execution-init-01'","init=ROOT/'artifacts/hierarchy-v1/execution-init-01'")
launcher=launcher.replace('targetRadius=1.5','targetRadius=1.0').replace('same physical curriculum, independently sampled targets.','same physical curriculum, two discrete target regions, radius1.0.')
(root/'tools/mlagents-training/run_execution_two_regions_v1.py').write_text(launcher,encoding='utf-8')
ledgerpath=root/'artifacts/player-v3/seed-ledger.json';ledger=read(ledgerpath)
assert not ledger['finalSeedsConsumed']
ledger.setdefault('developmentReuses',[]).append(dict(firstSeed=1108985,count=256,run=str(base.relative_to(root)),purpose='Predeclared full recovery-cycle region swaps and random-target retention, initializer vs final candidate'))
ledgerpath.write_text(json.dumps(ledger,indent=2),encoding='utf-8')
print(json.dumps(plan,indent=2))

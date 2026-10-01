from pathlib import Path
import json, hashlib, shutil
root=Path('F:/dev/picklebot')
base=root/'artifacts/hierarchy-v1'
def rows(p): return [json.loads(s) for s in p.read_text(encoding='utf-8-sig').splitlines() if s.strip()]
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
all_results=[]
for model,folder in [('ExecutionV1Initial','placement-dev-01'),('ExecutionV1Smoke01','placement-dev-01'),('ExecutionV1Placement01','placement-dev-02')]:
    path=base/folder/model
    g=rows(path/'execution-goals.jsonl'); e=rows(path/'episodes.jsonl')
    assert len(g)==len(e)==64 and read(path/'report.json')['status']=='seed_budget_complete'
    byseed={x['seed']:x for x in e}
    targets=[(x['seed'],x['targetX'],x['targetZ'],x['radius']) for x in g]
    if not all_results: baseline_targets=sorted(targets)
    else: assert sorted(targets)==baseline_targets
    groups={}
    for x in g:
        ep=byseed[x['seed']]
        name=ep['task']+('/movement' if ep['movementFeed'] else '/familiar')
        row=groups.setdefault(name,dict(attempts=0,legal=0,targets=0))
        row['attempts']+=1; row['legal']+=int(x['legalLanding']); row['targets']+=int(x['targetHit'])
    all_results.append(dict(model=model,attempts=64,legal=sum(x['legalLanding'] for x in g),targets=sum(x['targetHit'] for x in g),groups=groups))
report=dict(status='completed_development_evaluation',models=all_results,matchedTargets=True,promoted=False,
    limitation='64 reused development seeds; no final acceptance or robust generalization claim. Movement category also includes central feeds.')
with (base/'placement-dev-02/verification.json').open('x',encoding='utf-8') as f:json.dump(report,f,indent=2)
dest=root/'docs/research/execution-v1-evidence'
for name in ['placement-dev-02','target-response-placement-01']:
    out=dest/name;out.mkdir(exist_ok=False)
    for item in (base/name).iterdir():
        if item.is_file() and item.suffix in ['.json','.cs']:shutil.copy2(item,out/item.name)
        if item.is_dir():
            (out/item.name).mkdir()
            for n in ['episodes.jsonl','execution-goals.jsonl','report.json']:shutil.copy2(item/n,out/item.name/n)
train=base/'execution-placement-01'
(dest/'execution-placement-01').mkdir(exist_ok=False)
for n in ['verification.json','evaluation-plan.json','launch.json','manifest.json','process-result.json']:
    shutil.copy2(train/n,dest/'execution-placement-01'/n)
ckpt=root/'artifacts/mlagents/execution-placement-01/PicklebotExecutionV1/checkpoint.pt'
shutil.copy2(ckpt,root/'training/snapshots/execution-v1-placement-01.pt')
identity=dict(checkpointHash=hashlib.sha256(ckpt.read_bytes()).hexdigest(),
    modelHash=hashlib.sha256((root/'Assets/Picklebot/PlayerLearning/Models/ExecutionV1Placement01.onnx').read_bytes()).hexdigest(),
    sourceIdentity=read(base/'source-records.json')['sourceIdentity'],promoted=False)
(root/'training/snapshots/execution-v1-placement-01.json').write_text(json.dumps(identity,indent=2),encoding='utf-8')
ledgerpath=root/'artifacts/player-v3/seed-ledger.json';ledger=read(ledgerpath)
assert not ledger['finalSeedsConsumed']
ledger.setdefault('developmentReuses',[]).append(dict(firstSeed=1109529,count=64,
    run='artifacts/hierarchy-v1/placement-dev-02 + target-response-placement-01',purpose='Longer execution placement retention and target response development screen'))
ledgerpath.write_text(json.dumps(ledger,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))

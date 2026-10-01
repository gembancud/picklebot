from pathlib import Path
import json,hashlib,shutil,math
root=Path('F:/dev/picklebot');base=root/'artifacts/hierarchy-v1/smooth-distance-01';here=Path(__file__).parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
analysis=read(base/'audit/analysis.json');train=read(base/'execution-smooth-distance-01/verification.json')
source=read(base/'source-records.json');plan=read(base/'plan.json')
assert analysis['status']=='complete_development_screen' and not analysis['promoted']
assert all(sha(root/n)==h for n,h in source['files'].items())
model=root/'Assets/Picklebot/PlayerLearning/Models/ExecutionV1SmoothDistance01.onnx'
assert sha(model)==train['modelHash']
audited=legal=outside=0
worker_inputs=[]
for worker in range(8):
    path=base/f'execution-smooth-distance-01/worker-{worker:02}/execution-goals.jsonl'
    worker_count=0
    for line in path.read_text().splitlines():
        r=json.loads(line);assert r['rewardMode']=='smooth-distance-2m'
        expected=.25*math.exp(-r['distance']/2) if r['legalLanding'] else 0
        assert abs(r['bonus']-expected)<2e-7
        assert r['targetHit']==(r['legalLanding'] and r['distance']<=r['radius'])
        worker_count+=1;audited+=1;legal+=int(r['legalLanding']);outside+=int(r['legalLanding'] and not r['targetHit'] and r['bonus']>0)
    expected_worker=next(w for w in train['workers'] if w['worker']==worker)
    assert worker_count==expected_worker['episodes']
    worker_inputs.append(dict(worker=worker,episodes=worker_count,path=f'training-workers/worker-{worker:02}-execution-goals.jsonl',sha256=sha(path)))
assert audited==train['episodes'] and legal==train['legalLandings']
bonus_audit=dict(episodes=audited,legalLandings=legal,legalMissesWithPositiveFeedback=outside,formulaVerified=True,successCriterionUnchanged=True,workerInputs=worker_inputs)
with (base/'audit/training-bonus.json').open('x',encoding='utf-8') as f:json.dump(bonus_audit,f,indent=2)
dest=root/'docs/research/execution-v1-evidence/smooth-distance-01';dest.mkdir(exist_ok=False)
(dest/'training-workers').mkdir()
for item in worker_inputs:
    source_path=base/f'execution-smooth-distance-01/worker-{item["worker"]:02}/execution-goals.jsonl'
    shutil.copy2(source_path,dest/item['path'])
    assert sha(dest/item['path'])==item['sha256']
for name in ['plan.json','source-records.json']:shutil.copy2(base/name,dest/name)
shutil.copy2(base/'audit/analysis.json',dest/'analysis.json');shutil.copy2(base/'audit/training-bonus.json',dest/'training-bonus.json')
shutil.copy2(root/'artifacts/hierarchy-v1/smooth-distance-tests.xml',dest/'integration-tests.xml')
for name in ['verification.json','launch.json','manifest.json','process-result.json']:
    shutil.copy2(base/'execution-smooth-distance-01'/name,dest/('training-'+name))
for condition in ['A','B','random']:
    out=dest/'ExecutionV1SmoothDistance01'/condition;out.mkdir(parents=True)
    for name in ['episodes.jsonl','execution-goals.jsonl','first-decisions.json','report.json','summary.json']:
        shutil.copy2(base/'evaluation/ExecutionV1SmoothDistance01'/condition/name,out/name)
checkpoint=root/'artifacts/mlagents/execution-smooth-distance-01/PicklebotExecutionV1/checkpoint.pt'
assert sha(checkpoint)==train['checkpointHash']
shutil.copy2(checkpoint,root/'training/snapshots/execution-v1-smooth-distance-01.pt')
identity=dict(modelHash=sha(model),checkpointHash=sha(checkpoint),sourceIdentity=source['sourceIdentity'],promoted=False,masteryAccepted=False)
(root/'training/snapshots/execution-v1-smooth-distance-01.json').write_text(json.dumps(identity,indent=2),encoding='utf-8')
workflow=root/'research/hierarchy-v1/smooth-distance-01';workflow.mkdir(exist_ok=False)
for name in ['install_smooth_reward.py','build_smooth_distance.py','prepare_smooth_campaign.py','analyze_smooth_distance.py','archive_smooth_distance.py','smooth-A.cs','smooth-B.cs','smooth-random.cs']:
    shutil.copy2(here/name,workflow/name)
counts=analysis['summaries']['all'];candidate='ExecutionV1SmoothDistance01';gain=analysis['causal']['all'][candidate]['assignmentGain']
lines=['# Smooth-distance placement experiment','',
'This experiment changes only the added placement reward. A legal landing receives 0.25 × exp(−distance / 2 m); attempts without a legal landing receive zero placement bonus. Legal landings outside the target still receive graded feedback. The 1 m target-hit criterion, target centers, body controls, base legal rewards, physical drill mix, initializer and 262,144-step budget remain the same as the prior two-region recipe.','',
'20 Unity integration checks passed. A frozen-policy linear-versus-smooth comparison preserved observations, actions, physical episode outcomes, target hits and landing coordinates. It verified positive feedback on legal misses without converting them into successes.','',
f'Training completed at **{train["experiences"]:,} experiences** across 8 workers × 16 courts. The actual worker records passed the formula audit: {outside}/{audited} completed attempts were legal target misses receiving the new feedback. Nonzero bonus is not a target-success metric.','',
'The new candidate was evaluated in Unity on 256 paired development resets under A, B and unchanged random targets. Evaluation used the old linear reward mode; reward cannot influence this frozen-policy evaluation. Initializer and earlier linear-trained results were reused with verified file hashes and their original source identities; they were not rerun.','',
'| Model | A legal / target hits | B legal / target hits | Random legal / target hits |','|---|---:|---:|---:|']
for name,label in [('ExecutionV1Initial','Initializer'),('ExecutionV1TwoRegions01','Linear trained'),(candidate,'Smooth trained')]:
    cells=[f'{counts[name][c]["legal"]} / {counts[name][c]["targets"]}' for c in ['A','B','random']]
    lines.append('| '+label+' | '+' | '.join(cells)+' |')
lines += ['',f'The candidate requested-versus-opposite-region assignment gain was **{gain["mean"]:.4f}**, paired-bootstrap 95% interval **[{gain["ci95"][0]:.4f}, {gain["ci95"][1]:.4f}]**. Illegal attempts contribute zero; identical target-blind shots cancel.',
f'Predeclared promising screen: **{analysis["screen"]["promising"]}**. Checks: `{json.dumps(analysis["screen"]["tests"])}`. No promotion or mastery acceptance.','',
'Per-drill, service-side, region, movement and player results, plus paired differences against both the initializer and the earlier linear-trained policy, are recorded in the analysis. This is one training run per recipe and a reused development cohort with repeated geometries. It does not establish robust recipe superiority, broad movement mastery, or final acceptance. Final evaluation seeds remain unused.','',
'[Analysis and paired comparisons](execution-v1-evidence/smooth-distance-01/analysis.json) · [Frozen plan](execution-v1-evidence/smooth-distance-01/plan.json) · [Actual reward audit](execution-v1-evidence/smooth-distance-01/training-bonus.json) · [Prior baseline evidence](execution-v1-evidence/two-regions-01/analysis.json)']
(root/'docs/research/execution-v1-smooth-distance.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(dict(report='docs/research/execution-v1-smooth-distance.md',bonusAudit=bonus_audit,screen=analysis['screen']['tests'],promising=analysis['screen']['promising'],identity=identity),indent=2))


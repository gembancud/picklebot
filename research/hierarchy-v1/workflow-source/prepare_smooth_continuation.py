from pathlib import Path
import hashlib,json,shutil,datetime
root=Path('F:/dev/picklebot');here=Path(__file__).parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=root/'artifacts/hierarchy-v1/smooth-distance-01'
base=root/'artifacts/hierarchy-v1/smooth-continued-01'
assert not base.exists();base.mkdir()
config=root/'config/mlagents/execution-v1-smooth-continued.yaml'
text=(root/'config/mlagents/execution-v1-smooth-distance.yaml').read_text(encoding='utf-8-sig')
assert text.count('    init_path:')==1
text='\n'.join(line for line in text.splitlines() if not line.startswith('    init_path:'))+'\n'
text=text.replace('max_steps: 262144','max_steps: 1048576').replace('checkpoint_interval: 32768','checkpoint_interval: 262144').replace('keep_checkpoints: 2','keep_checkpoints: 4')
with config.open('x',encoding='utf-8',newline='\n') as f:f.write(text)
train=read(old/'execution-smooth-distance-01/verification.json')
source=read(old/'source-records.json');build=read(old/'build-verification.json')
baseline_files={}
for relative in ['two-regions-01/evaluation/ExecutionV1Initial','smooth-distance-01/evaluation/ExecutionV1SmoothDistance01']:
    for p in sorted((root/'artifacts/hierarchy-v1'/relative).rglob('*')):
        if p.is_file():baseline_files[str(p.relative_to(root)).replace('\\','/')]=sha(p)
plan=dict(
 createdAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 hypothesis='The 32-buffer initial exposure may be too short for useful target conditioning. Extend the same policy and reward recipe with full optimizer state; inspect fixed checkpoints rather than selecting a lucky result.',
 parentRun='execution-smooth-distance-01',runId='execution-smooth-continued-01',
 sourceIdentity=source['sourceIdentity'],buildIdentity=build['buildIdentity'],
 parentCheckpointHash=train['checkpointHash'],parentModelHash=train['modelHash'],
 initialStep=262179,targetGlobalStep=1048576,configHash=sha(config),trainingSeed=19013,basePort=5655,workerCount=8,
 configPath=str(config.relative_to(root)).replace('\\','/'),
 sourceRecordPath='artifacts/hierarchy-v1/smooth-distance-01/source-records.json',
 buildRecordPath='artifacts/hierarchy-v1/smooth-distance-01/build-verification.json',
 resume={'framework':'pinned ML-Agents --resume','init_path':'removed because it takes precedence over resume in the installed loader',
 'preserved':['actor','critic','normalization','Adam optimizer','global step'],
 'notPreserved':['live Unity state','in-flight rollout buffer','Python/Unity process RNG progression'],
 'trainingResetReuse':{'firstSeed':1000000,'seedsPerWorker':12288,'workers':8},
 'checkpointPaths':'Copy into an isolated results directory and rewrite checkpoint-manager paths; never permit retention to delete parent files'},
 evaluation={'split':'reused development anchor','firstSeed':1108985,'baseResets':256,'conditions':['A','B','random'],
 'rewardMode':'linear-radius','midpointSelection':'Retained numbered checkpoint nearest 524288, within 8192 steps; lower step wins a tie; determined from step numbers before evaluating performance.',
 'finalSelection':'Final exported checkpoint at or above1048576 and below1056768. No best-of-checkpoint selection.',
 'baselineInputs':baseline_files,
 'comparisons':['initializer','262179-experience parent'],
 'screen':['Final assignment gain paired-bootstrap95% lower >0','Both A and B target rates exceed the initializer','No per-drill legal rate drop greater than5percentage points versus initializer or immediate parent in any condition'],
 'midpointUse':'Diagnostic trajectory only; final selection remains fixed.',
 'freshDevelopment':'Only after promising development response; separately predeclare reset coverage. Final seeds remain reserved.'},
 limits={'wallSeconds':2400,'restartAttempts':0,'automaticPromotion':False,'architectureChanges':False,'scriptedActions':False},
 limitations=['One continuing training lineage; not a replicated recipe comparison.','Input diagnostic covers first decisions only.','Existing movement screen covers small feed shifts and does not establish broad positioning mastery.'],
 finalSeedsConsumed=False,masteryAccepted=False
)
with (base/'plan.json').open('x',encoding='utf-8') as f:json.dump(plan,f,indent=2)
for name in ['goal_path_diagnostic.py','goal_path_diagnostic.json']:
    shutil.copy2(here/name,root/'research/hierarchy-v1/smooth-distance-01'/name)
shutil.copy2(here/'goal_path_diagnostic.json',root/'docs/research/execution-v1-evidence/smooth-distance-01/goal-path-diagnostic.json')
report=root/'docs/research/execution-v1-smooth-distance.md'
text=report.read_text(encoding='utf-8')
text+='\nThe checkpoint/observation diagnostic found correct target encodings, nonzero learned actor/critic goal weights and retained normalized target separation. CPU commands matched recorded Unity commands within 6 × 10⁻⁷. Every first-state pair retained some goal sensitivity after clipping; the median largest per-channel change was 0.00594 for smooth versus 0.00425 for linear. These first-decision checks do not diagnose later swing decisions or establish correct PPO credit assignment. [Raw diagnostic](execution-v1-evidence/smooth-distance-01/goal-path-diagnostic.json). The next bounded experiment extends the same smooth recipe with full checkpoint resume to roughly 1M total experiences.\n'
report.write_text(text,encoding='utf-8',newline='\n')
print(json.dumps({'plan':str(base/'plan.json'),'configHash':sha(config),'targetStep':plan['targetGlobalStep']}))

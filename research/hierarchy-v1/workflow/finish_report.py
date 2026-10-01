from pathlib import Path
import collections, hashlib, json, shutil, xml.etree.ElementTree as ET
ROOT=Path('F:/dev/picklebot');BASE=ROOT/'artifacts/hierarchy-v1';HERE=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=lambda p:[json.loads(s) for s in p.read_text().splitlines() if s.strip()]
source=read(BASE/'source-records.json')
assert all(sha(ROOT/n)==h for n,h in source['files'].items()),'Runtime source changed'
checks=ET.parse(BASE/'integration-tests.xml').getroot().attrib
assert checks['result']=='Passed' and int(checks['total'])==17
train=read(BASE/'execution-goals-smoke-01/verification.json')
assert train['status']=='completed_learning_check'
assert read(BASE/'evaluation-editor-restored.json')['restored']
stats=[];pairs={}
for name in ['ExecutionV1Initial','ExecutionV1Smoke01']:
    path=BASE/'placement-dev-01'/name
    episodes=rows(path/'episodes.jsonl');goals=rows(path/'execution-goals.jsonl')
    assert len(episodes)==len(goals)==64
    assert read(path/'report.json')['status']=='seed_budget_complete'
    assert len({e['seed'] for e in episodes})==64
    assert all(e['seed']==g['seed'] and e['player']==g['player'] for e,g in zip(episodes,goals))
    targets={g['seed']:(g['player'],g['targetX'],g['targetZ'],g['radius']) for g in goals}
    if pairs:assert targets==pairs
    else:pairs=targets
    buckets=collections.defaultdict(lambda:[0,0,0])
    for e,g in zip(episodes,goals):
        assert e['outcome'] not in ['exception','infeasible']
        key=e['task']+(' / movement' if e['movementFeed'] else ' / familiar')
        buckets[key][0]+=1;buckets[key][1]+=g['legalLanding'];buckets[key][2]+=g['targetHit']
    stats.append(dict(model=name,attempts=64,legal=sum(g['legalLanding'] for g in goals),hits=sum(g['targetHit'] for g in goals),byTask=dict(buckets),modelHash=sha(ROOT/'Assets/Picklebot/PlayerLearning/Models'/(name+'.onnx'))))
record=dict(status='development_screen_complete',sourceIdentity=source['sourceIdentity'],models=stats,targetsMatchedBySeed=True,
    trialsPerModel=64,trainingExperiences=train['experiences'],promotion=False,
    interpretation='One additional legal landing and target hit in a small development cohort; no robust improvement claim.')
(BASE/'placement-dev-01/verification.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
evidence=ROOT/'docs/research/execution-v1-evidence';evidence.mkdir(parents=True,exist_ok=True)
for src,name in [(BASE/'source-records.json','source-records.json'),(BASE/'execution-init-01/initialization.json','initialization.json'),(BASE/'execution-goals-smoke-01/verification.json','training.json'),(BASE/'placement-dev-01/verification.json','evaluation.json'),(BASE/'placement-dev-01/plan.json','plan.json'),(BASE/'integration-tests.xml','integration-tests.xml')]:shutil.copyfile(src,evidence/name)
for name in ['ExecutionV1Initial','ExecutionV1Smoke01']:
    (evidence/name).mkdir(exist_ok=True)
    for filename in ['episodes.jsonl','execution-goals.jsonl','report.json']:
        shutil.copyfile(BASE/'placement-dev-01'/name/filename,evidence/name/filename)
lines=['# Execution-goal integration','',
    'First stage of the strategy/execution design, 12 September 2026. The strategy actor is not implemented yet.','',
    'The executor accepts 12 additional goal features while retaining the original physical controls. A warm start preserved actor and critic outputs exactly across 512 probes; the exported initializer also reproduced the previous model’s 32 paired Unity drill outcomes. New target inputs have a verified gradient path.','',
    'Validation: 17 Unity integration tests and 300 Python regression tests passed. An isolated worker build completed. PPO then ran for **32,776 experiences** on **8 workers × 16 courts**; all workers contributed private player episodes, and the shot-coordinate weights changed. The optimizer and experience counter were freshly initialized.','',
    '## Fixed development screen','',
    '| Model | Legal landings / 64 | Target hits / 64 |','|---|---:|---:|',
    '| Initialized executor | 53 | 20 |','| After short training | 54 | 21 |','',
    'Both models saw the same 64 reset/target seeds, covering serves, bounced and airborne returns, and movement returns. Targets used a 1.5 m radius. This small one-seed screen establishes that the trained export runs; the one-attempt difference does not establish better aiming or robust skill retention. No model was promoted.','',
    '| Drill | Attempts per model | Initial legal / target | Trained legal / target |','|---|---:|---:|---:|']
for key,a in sorted(stats[0]['byTask'].items()):
    b=stats[1]['byTask'][key];lines.append(f'| {key} | {a[0]} | {a[1]} / {a[2]} | {b[1]} / {b[2]} |')
lines+=['','The initial build produced a valid binary but failed during empty-scene cleanup. That failed attempt was retained; the helper was corrected and a fresh build completed with matching source hashes. The task-owned evaluation Editor was restored and closed.','',
    'Next: evaluate goal responsiveness (changing only the requested target), then train placement with repeated checks of familiar skills. Movement-goal, recovery, cover and yield training remain ahead of learned strategy and paired play.','',
    '[Contract and workflow](../HIERARCHICAL_CONTROL.md) · [Evaluation evidence](execution-v1-evidence/evaluation.json) · [Training verification](execution-v1-evidence/training.json)']
(ROOT/'docs/research/execution-v1-integration.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
p=ROOT/'docs/HIERARCHICAL_CONTROL.md';p.write_text(p.read_text()+'\n[First integration results](research/execution-v1-integration.md): contract, warm-start parity, actual PPO learning and a small exported-model screen.\n',encoding='utf-8')
p=ROOT/'docs/CURRENT_STATE.md';s=p.read_text();p.write_text('''# Execution-goal stage implemented

12 September 2026, branch `feat/hierarchical-control`. The executor now accepts movement and shot goals. The initial shot-goal training check completed (32,776 experiences); its 64-attempt development screen changed from 53 to 54 legal landings and 20 to 21 target hits. This is an integration result, not a demonstrated aiming breakthrough. No new model is promoted.

The strategy actor and movement/recover/cover/yield training remain unimplemented. [Design](HIERARCHICAL_CONTROL.md) · [Tests and measurements](research/execution-v1-integration.md)

The previous published baseline follows for comparison.

---
'''+s,encoding='utf-8')
# Preserve the exact runner used before removing its dependency on a local old manifest.
runner=ROOT/'tools/mlagents-training/run_execution_smoke_v1.py'
shutil.copyfile(runner,BASE/'execution-goals-smoke-01/runner.py')
template=read(ROOT/'artifacts/player-v3/critic-key-control-s1-01-train/manifest.json')
for key in ['sourceIdentity','buildIdentity','modelHash','evidenceRoot']:template[key]='filled-by-launcher'
(ROOT/'config/mlagents/execution-v1-workers.json').write_text(json.dumps(template,indent=2),encoding='utf-8')
s=runner.read_text().replace("ROOT/'artifacts/player-v3/critic-key-control-s1-01-train/manifest.json'","ROOT/'config/mlagents/execution-v1-workers.json'")
runner.write_text(s,encoding='utf-8')
archive=ROOT/'research/hierarchy-v1/workflow';archive.mkdir(parents=True,exist_ok=True)
for p in HERE.iterdir():
    if p.suffix in ['.py','.cs','.md','.yaml']:shutil.copyfile(p,archive/p.name)
(archive.parent/'README.md').write_text('# First execution-goal campaign\n\nHistorical orchestration and evaluation source for the first integration. Scripts retain local machine paths and exclusive output assumptions; do not rerun them against completed directories. Maintained environment code is in `Assets/Picklebot/PlayerLearning`, and the initializer/runner in `tools/mlagents-training`. See `docs/HIERARCHICAL_CONTROL.md` and the integration report.\n',encoding='utf-8')
snapshots=[]
for src,name in [(BASE/'execution-init-01/checkpoint.pt','execution-v1-initial.pt'),(ROOT/'artifacts/mlagents/execution-goals-smoke-01/PicklebotExecutionV1/checkpoint.pt','execution-v1-smoke-01.pt')]:
    dst=ROOT/'training/snapshots'/name;shutil.copyfile(src,dst);snapshots.append(dict(file=name,sha256=sha(dst)))
(ROOT/'training/snapshots/execution-v1.json').write_text(json.dumps(snapshots,indent=2),encoding='utf-8')
print(json.dumps(record,indent=2))

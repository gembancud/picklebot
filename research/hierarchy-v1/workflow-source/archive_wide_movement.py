"""Preserve the completed wider movement diagnostic, including the failed script."""
from pathlib import Path
import json, hashlib, shutil, subprocess

root = Path('F:/dev/picklebot')
here = Path(__file__).resolve().parent
base = root / 'artifacts/hierarchy-v1/wide-movement-fixture-01'
evidence = root / 'docs/research/execution-v1-evidence/wide-movement-01'
workflow = root / 'research/hierarchy-v1/wide-movement-01'
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
plan, source = read(base/'plan.json'), read(base/'source-records.json')
summary, analysis = read(base/'fixture-summary.json'), read(base/'audit/analysis.json')
assert plan['diagnosticOnly'] and not plan['masteryAccepted'] and not analysis['masteryAccepted']
assert summary['outcomeAllowed'] and summary['seedCount']==512
assert read(base/'candidate-evaluation-editor-restored.json')['restored']
assert all(sha(root/name)==digest for name,digest in source['files'].items())
assert read(root/'artifacts/player-v3/seed-ledger.json')['finalSeedsConsumed']==[]
assert sha(root/'artifacts/player-v3/seed-ledger.json')==read(base/'allocation.json')['ledgerAfterHash']
assert not evidence.exists() and not workflow.exists()
copies = {}
canonical = {}
canonical_kind = {}
git_args=['git','-c','safe.directory=F:/dev/picklebot','-C',str(root)]
source_commit=subprocess.check_output(git_args+['rev-parse','HEAD'],text=True).strip()
tree={}
for entry in subprocess.check_output(git_args+['ls-tree','-r','-z','HEAD']).split(b'\0'):
    if entry:
        metadata,name=entry.split(b'\t',1)
        tree[name.decode('utf-8')]=metadata.split()[2].decode('ascii')
for name,expected in source['files'].items():
    path=root/name
    content=path.read_bytes()
    git_hash=hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest()
    assert tree.get(name)==git_hash, f'Runtime source is not preserved at current commit: {name}'
    canonical[path.resolve()]=expected
    canonical_kind[path.resolve()]='runtime source at '+source_commit
def queue(original, target):
    assert original.is_file() and not target.exists(), str(original)
    if target in copies:
        assert copies[target][1]==sha(original)
    copies[target]=(original,sha(original))

for model, identity in plan['modelIdentities'].items():
    for field, digest_field in [('assetPath','modelHash'),('checkpoint','checkpointHash')]:
        path=root/identity[field]
        assert sha(path)==identity[digest_field]
        canonical[path.resolve()] = identity[digest_field]
        canonical_kind[path.resolve()]='canonical model/checkpoint'
    for condition in plan['conditions']:
        report=read(base/'evaluation'/model/condition/'report.json')
        assert report['status']=='seed_budget_complete' and report['completedEpisodes']==512
for path in base.rglob('*'):
    if path.is_file(): queue(path,evidence/path.relative_to(base))
queue(root/'artifacts/player-v3/seed-ledger.json',evidence/'seed-ledger-after.json')
for filename, expected in read(base/'script-hashes.json').items():
    assert sha(here/filename)==expected
    queue(here/filename,workflow/filename)
for filename, record in read(base/'fixture-script-revision-01.json')['files'].items():
    assert sha(here/filename)==record['sha256']
    assert sha(here/record['original'])==record['originalSha256']
    queue(here/filename,workflow/filename)
for filename in ['prepare_wide_movement.py','fix_wide_fixture_script.py','freeze_wide_fixture.py',
                 'summarize_wide_fixture.py','analyze_wide_movement.py','wide_movement_fixture.cs','wide_movement_plan.md',
                 'archive_wide_movement.py','report_wide_movement.py']:
    queue(here/filename,workflow/filename)
assert sha(here/'summarize_wide_fixture.py')==summary['analysisScriptSha256']
assert sha(here/'analyze_wide_movement.py')==analysis['analysisScriptSha256']

input_coverage={}
for collector in [summary,analysis]:
    for key,expected in collector['inputSha256'].items():
        path=Path(key)
        if not path.is_absolute(): path=root/path
        path=path.resolve()
        assert sha(path)==expected, key
        if path in canonical:
            input_coverage[key]={'mode':canonical_kind[path],'sha256':expected,'path':path.relative_to(root).as_posix()}
            continue
        found=next((target for target,(original,digest) in copies.items() if original.resolve()==path),None)
        if found is None:
            if path.is_relative_to(root): relative=path.relative_to(root)
            elif path.is_relative_to(here): relative=Path('workspace')/path.relative_to(here)
            else: raise ValueError(f'Unclassified evidence dependency: {path}')
            found=workflow/'dependencies'/relative
            queue(path,found)
        input_coverage[key]={'mode':'byte-preserved copy','sha256':expected,'path':found.relative_to(root).as_posix()}

evidence.mkdir(parents=True,exist_ok=False)
workflow.mkdir(parents=True,exist_ok=False)
records=[]
for target,(original,expected) in sorted(copies.items(),key=lambda item:str(item[0])):
    assert sha(original)==expected and not target.exists()
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(original,target)
    assert sha(target)==expected
    records.append({'source':str(original),'archivePath':target.relative_to(root).as_posix(),'sha256':expected})
for target,(original,expected) in copies.items(): assert sha(original)==sha(target)==expected
for path,expected in canonical.items(): assert sha(path)==expected
assert all(sha(root/name)==digest for name,digest in source['files'].items())
manifest=dict(status='complete_byte_preserved_archive',files=records,analysisInputCoverage=input_coverage,
    sourceIdentity=source['sourceIdentity'],sourceGitCommit=source_commit,planHash=sha(base/'plan.json'),analysisHash=sha(base/'audit/analysis.json'),
    report={'path':'docs/research/execution-v1-wide-movement.md','sha256':sha(root/'docs/research/execution-v1-wide-movement.md')},
    fullResetCount=512,conditions=plan['conditions'],models=plan['models'],allAttemptsIncluded=True,
    originalFailedInspectionScriptPreserved=True,simulationSourceChanged=False,finalSeedsConsumed=False,masteryAccepted=False)
with (evidence/'archive-manifest.json').open('x',encoding='utf-8') as handle: json.dump(manifest,handle,indent=2)
with (workflow/'README.md').open('x',encoding='utf-8') as handle:
    handle.write('# Wider movement diagnostic\n\n'
       'Reset geometry was inspected without policy actions or physics ticks, then two frozen models were compared on512 paired cases underA/B goals. Nominal feed shifts are25/50/75/100cm left/right/shallow/deep; recorded root travel determines actual movement.\n\n'
       'The first inspection script failed compilation before executing. Its original and corrected versions and revision hashes are preserved. No simulation source or model changed. These scripts contain original Windows paths and are historical workflow evidence.\n\n'
       'All completed attempts and sparse cells remain in docs/research/execution-v1-evidence/wide-movement-01. No mastery or promotion is implied.\n')
print(json.dumps({'evidence':str(evidence),'workflow':str(workflow),'files':len(records),'analysisInputsCovered':len(input_coverage),'masteryAccepted':False}))

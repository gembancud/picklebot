"""Preserve verified continuation outcomes and report them without promotion."""
from pathlib import Path
import json,hashlib,shutil,gzip
root=Path('F:/dev/picklebot');here=Path(__file__).parent
base=root/'artifacts/hierarchy-v1/smooth-continued-01'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
analysis=read(base/'audit/analysis.json');train=read(base/'training/verification.json');selected=read(base/'selected-models.json');plan=read(base/'plan.json')
assert analysis['status']=='complete_development_screen' and not analysis['promoted']
assert train['status']=='completed_continuation_check' and train['resumeStateExact'] and train['parentRunUnchanged']
source=read(root/plan['sourceRecordPath'])
assert all(sha(root/n)==h for n,h in source['files'].items())
assert read(base/'candidate-evaluation-editor-restored.json')['restored']
dest=root/'docs/research/execution-v1-evidence/smooth-continued-01';dest.mkdir(exist_ok=False)
for name in ['plan.json','selected-models.json']:shutil.copy2(base/name,dest/name)
shutil.copy2(base/'audit/analysis.json',dest/'analysis.json')
for name in ['verification.json','process-result.json','resume-load-proof.json','launch.json','manifest.json','status-remap.json','parent-result-inputs.json']:
    shutil.copy2(base/'training'/name,dest/('training-'+name))
worker_folder=dest/'training-workers';worker_folder.mkdir()
compressed=[]
for relative,expected in train['workerInputSha256'].items():
    p=base/'training'/relative
    assert sha(p)==expected
    if p.name in ['episodes.jsonl','execution-goals.jsonl']:
        out=worker_folder/(relative.replace('/','-')+'.gz')
        raw=p.read_bytes();out.write_bytes(gzip.compress(raw,mtime=0))
        assert gzip.decompress(out.read_bytes())==raw
        compressed.append(dict(originalRelativePath=relative,uncompressedSha256=expected,archivePath=str(out.relative_to(dest)).replace('\\','/'),compressedSha256=sha(out)))
    else:
        out=worker_folder/relative.replace('/','-');shutil.copy2(p,out)
with (dest/'training-input-archive.json').open('x',encoding='utf-8') as f:json.dump(compressed,f,indent=2)
for label,identity in selected.items():
    checkpoint=root/identity['checkpoint'];model=root/f'Assets/Picklebot/PlayerLearning/Models/{identity["model"]}.onnx'
    assert sha(checkpoint)==identity['checkpointHash'] and sha(model)==identity['modelHash']
    snapshot=root/f'training/snapshots/execution-v1-smooth-continued-{label}-01.pt'
    assert not snapshot.exists();shutil.copy2(checkpoint,snapshot)
    snapshot.with_suffix('.json').write_text(json.dumps({**identity,'promoted':False,'masteryAccepted':False},indent=2),encoding='utf-8')
    for condition in ['A','B','random']:
        out=dest/identity['model']/condition;out.mkdir(parents=True)
        for name in ['episodes.jsonl','execution-goals.jsonl','first-decisions.json','report.json','summary.json','model-identity.json']:
            shutil.copy2(base/'evaluation'/identity['model']/condition/name,out/name)
workflow=root/'research/hierarchy-v1/smooth-continued-01'
for name in ['prepare_continuation_evaluation.py','analyze_smooth_continuation.py','archive_smooth_continuation.py']:
    shutil.copy2(here/name,workflow/name)
for label in ['mid','final']:
    for condition in ['A','B','random']:shutil.copy2(here/f'continued-{label}-{condition}.cs',workflow/f'continued-{label}-{condition}.cs')
counts=analysis['summaries']['all'];final=selected['final']['model'];mid=selected['mid']['model']
gain=analysis['causal']['all'][final]['assignmentGain'];tests=analysis['screen']['tests']
labels=[('ExecutionV1Initial','Initializer'),('ExecutionV1SmoothDistance01','262,179 experiences'),(mid,f'Midpoint: {selected["mid"]["step"]:,}'),(final,f'Final: {selected["final"]["step"]:,}')]
lines=['# Longer unchanged placement training','',
f'The continuation completed at **{train["experiences"]:,} total experiences**, adding **{train["newExperiences"]:,}** to the smooth-distance policy. Body controls, physical drill mixture, target geometry, PPO hyperparameters and reward recipe were unchanged. Eight workers each ran sixteen courts.','',
'The maintained trainer resumed actor, critic, normalizers, Adam and global step from an isolated full checkpoint. The installed-loader preflight restored all registered state exactly, actual logs confirmed step 262,179, final parameter/optimizer counters advanced, and the completed parent files remained unchanged. Processes, unfinished rollouts and RNG progression restarted; training reset IDs were reused.','',
f'The midpoint (**{selected["mid"]["step"]:,}**) and final (**{selected["final"]["step"]:,}**) were selected using the predeclared step rule. Each was evaluated on the same 256 A/B/random development resets. The midpoint describes the trajectory; the final checkpoint remains the selection even if an earlier checkpoint scored higher. Initializer and immediate-parent evidence were reused with verified hashes and original source identities.','',
'| Model | A legal / target hits | B legal / target hits | Random legal / target hits |','|---|---:|---:|---:|']
for model,label in labels:
    lines.append('| '+label+' | '+' | '.join(f'{counts[model][c]["legal"]} / {counts[model][c]["targets"]}' for c in ['A','B','random'])+' |')
lines+=['',f'Final requested-versus-opposite-region assignment gain: **{gain["mean"]:.5f}**, paired-bootstrap 95% interval **[{gain["ci95"][0]:.5f}, {gain["ci95"][1]:.5f}]**.',
f'Predeclared promising screen: **{analysis["screen"]["promising"]}**. Checks: `{json.dumps(tests)}`. No promotion or mastery acceptance.','',
'The screen checks per-drill legal retention against both the initializer and immediate parent across all three conditions. A pooled success rate cannot substitute for these checks. Actual landing coordinates determine target hits; training bonus is not a target-success metric.','',
'These are reused development cases from one continuing lineage, with repeated geometries and mostly small feed shifts. This does not establish broad court positioning, kitchen-boundary judgment, robust recipe superiority or final mastery. Final acceptance seeds remain unused. The reward/episode inputs are preserved as lossless gzip files with both compressed and uncompressed hashes.','',
'[Full analysis](execution-v1-evidence/smooth-continued-01/analysis.json) · [Plan](execution-v1-evidence/smooth-continued-01/plan.json) · [Training verification](execution-v1-evidence/smooth-continued-01/training-verification.json) · [Worker input archive](execution-v1-evidence/smooth-continued-01/training-input-archive.json) · [Remaining coverage](drill-mastery-coverage.md)']
(root/'docs/research/execution-v1-smooth-continued.md').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({'report':'docs/research/execution-v1-smooth-continued.md','counts':{m:{c:{k:counts[m][c][k] for k in ['legal','targets']} for c in ['A','B','random']} for m,_ in labels},'screen':tests,'finalAssignmentGain':gain},indent=2))

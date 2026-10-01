from pathlib import Path
import json,hashlib,gzip,shutil
R=Path('F:/dev/picklebot');W=Path(__file__).resolve().parent;B=R/'artifacts/hierarchy-v1/right-acquisition-01';V=W.parents[1]/'outputs/right-acquisition-review-01'
out=R/'research/hierarchy-v1/right-acquisition-final-01'
assert not out.exists() and (V/'index.html').exists()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
assert read(B/'evaluation-process/complete.json')['completed']==7
assert not read(R/'artifacts/player-v3/seed-ledger.json')['finalSeedsConsumed']
out.mkdir();inputs={}
def save(src,dst):
    dst.parent.mkdir(parents=True,exist_ok=True);inputs[str(src)]=sha(src)
    if src.suffix in ('.jsonl','.log') or src.name=='first-decisions.json':
        with src.open('rb') as a,gzip.open(str(dst)+'.gz','wb') as b:shutil.copyfileobj(a,b)
        with gzip.open(str(dst)+'.gz','rb') as b:assert hashlib.sha256(b.read()).hexdigest()==inputs[str(src)]
    else:shutil.copyfile(src,dst);assert sha(dst)==inputs[str(src)]
for name in ['plan.json','source-records.json','selected-models.json','acquisition-baseline-evaluation.json','acquisition-final-evaluation.json','candidate-evaluation-scene-before.json','candidate-evaluation-editor-restored.json']:
    save(B/name,out/name)
for folder in ['evaluation','results','evaluation-process']:
    for src in (B/folder).rglob('*'):
        if src.is_file():save(src,out/src.relative_to(B))
for src in (B/'training').glob('*'):
    if src.is_file() and src.suffix in ('.json','.yaml','.log'):save(src,out/'training'/src.name)
for worker in (B/'training').glob('worker-*'):
    for name in ['worker-startup.json','report.json','episodes.jsonl','execution-goals.jsonl','worker-ready.json','worker-quit.json']:
        if (worker/name).exists():save(worker/name,out/'training'/worker.name/name)
for src in W.glob('*right_acquisition*.py'):save(src,out/'workflow'/src.name)
for src in W.glob('*right-acquisition*.cs'):save(src,out/'workflow'/src.name)
for src in W.glob('acquisition-matched-*.cs'):save(src,out/'workflow'/src.name)
for src in V.glob('*'):
    if src.is_file():save(src,out/'viewer'/src.name)
image_hashes={}
for role in ['baseline','final']:
    assert read(V/role/'complete.json')['status']=='complete_verified_replay'
    for src in (V/role).rglob('*'):
        if src.is_file():
            if src.suffix=='.jpg':image_hashes[src.relative_to(V).as_posix()]=sha(src)
            else:save(src,out/'viewer'/src.relative_to(V))
(out/'image-inventory.json').write_bytes(json.dumps(dict(root=str(V),sha256=image_hashes,imagesRetainedAtOriginalLocalPaths=True),indent=2).encode())
(out/'inputs.json').write_bytes(json.dumps(inputs,indent=2).encode())
report=R/'docs/research/execution-v1-right-acquisition-final.md'
s=report.read_text(encoding='utf-8').replace('Actual eight-case before/after recordings are being assembled separately; they must show the retention regression alongside the narrow success.','Actual eight-case before/after recordings completed with exact parity on both 512-attempt replays. The viewer includes full retention results alongside narrow success: `outputs/right-acquisition-review-01/index.html` in the Codex workspace. Analysis and evidence are archived in `research/hierarchy-v1/right-acquisition-final-01`; image hashes pin the preserved local JPEGs.')
report.write_bytes(s.encode())
state=R/'docs/CURRENT_STATE.md'
head='''# Active drill-mastery goal: acquisition verified; retention failed

Rightward-only training completed and all seven evaluations passed evidence validation. The endpoint learned eight canonical rightward 25 cm situations (512 repeated attempts legal under each target), but earlier skills collapsed: narrow A/B/random 23/21/21 out of256 versus parent234/235/235; wide A/B32/30 out of512 versus285/288. Both serving sides fell to zero. Wider rightward returns improved0→15/64, while other directions regressed. No mastery or policy promotion; target assignment gain interval across eight unique situations includes zero.

Both checkpoints and full results are preserved. Actual before/after eight-case recordings match all512 replay outcomes for each model. Viewer: workspace `outputs/right-acquisition-review-01/index.html`, with retention losses displayed beside acquisition scores. Training and evaluation runner are finished; the task-owned Editor scene setup was restored and closure requested.

Next: prepare a bounded shared-policy maintenance-plus-rightward acquisition experiment from common parent1048609. Keep familiar/prior rehearsal and concentrate the focus slots on fixed right25cm. Validate the reset schedule and worker before launch. No next run launched yet. Broader movement, mandatory-bounce variations, kitchen behavior, aiming, attainable acceptance criteria and repeated final acceptance remain open. Final seeds unused.

[Completed report](research/execution-v1-right-acquisition-final.md). Evidence: `research/hierarchy-v1/right-acquisition-final-01`.

---

'''
state.write_bytes((head+state.read_text(encoding='utf-8')).encode())
goal=R/'docs/DRILL_MASTERY_GOAL.md';s=goal.read_text(encoding='utf-8');start=s.index('Current work:');end=s.index('\n\nApp status:',start)
s=s[:start]+'Current work: Rightward acquisition completed at2,097,175 with all seven evaluations. It learned the eight canonical right25cm cases but lost earlier skills, including serving. The checkpoint is preserved without promotion. Next prepare a maintenance-plus-concentrated-rightward experiment from the common parent, validating reset coverage before launch. Broader mastery, useful target following and acceptance thresholds remain unproven; final seeds unused. [Completed comparison](research/execution-v1-right-acquisition-final.md).'+s[end:];goal.write_bytes(s.encode())
print(json.dumps(dict(archive=str(out),files=len(inputs),images=len(image_hashes))))

from pathlib import Path
import json,gzip,shutil,hashlib
R=Path('F:/dev/picklebot');W=Path(__file__).resolve().parent;B=R/'artifacts/hierarchy-v1/right-retention-01';A=R/'research/hierarchy-v1/right-retention-launch-01'
assert not A.exists();A.mkdir();inputs={}
def save(src,dst):
    dst.parent.mkdir(parents=True,exist_ok=True);inputs[str(src)]=hashlib.sha256(src.read_bytes()).hexdigest()
    if src.suffix in ('.jsonl','.log'):
        with src.open('rb') as x,gzip.open(str(dst)+'.gz','wb') as y:shutil.copyfileobj(x,y)
    else:shutil.copyfile(src,dst)
for name in ['plan.json','source-records.json','build-verification.json','build-launch.json']:
    save(B/name,A/name)
for src in (B/'baseline-fixture').rglob('*'):
    if src.is_file() and src.suffix in ('.json','.jsonl','.log','.yaml'):save(src,A/src.relative_to(B))
for name in ['process.json','launch.json','config.yaml','manifest.json','resume-load-proof.json','parent-inputs.json','status-remap.json']:
    save(B/'training'/name,A/'training'/name)
for name in ['freeze_right_retention_plan.py','summarize_right_retention_windows.py','run_right_retention.py','archive_right_retention_launch.py']:
    save(W/name,A/'workflow'/name)
(A/'inputs.json').write_bytes(json.dumps(inputs,indent=2).encode())
pid=json.loads((B/'training/process.json').read_text(encoding='utf-8'))['pid']
doc=R/'docs/CURRENT_STATE.md'
head=f'''# Active drill-mastery goal: rightward acquisition with maintenance running

`execution-right-retention-01` resumed common parent1048609 toward fixed2097152. Episode-start allocation:50% fixed25cm rightward rally returns,25% familiar serves/receives/rally returns,25% prior-court returns.8 workers x16 courts; original interleaving, PPO, controls and rewards; no movement shaping. Runner34316, trainer{pid} at launch; verify current processes before treating this historical note as live.

18 Unity tests passed. Built-worker frozen512-case fixture passed without learned-state changes: familiar125/128 legal, prior87/128, right0/256; canonical serves32/32. Decision shares were28.6% familiar,25.2% prior,46.2% focus, illustrating episode/transition differences. Full-state resume preflight passed before launch. Evidence and pinned plan: `research/hierarchy-v1/right-retention-launch-01`.

After completion, select the mandatory endpoint and run acquisitionA/B plus original narrowA/B/random and wideA/B. Require acquisition and per-drill retention together before advancing; aiming, wider movement, kitchen/mandatory-bounce coverage and repeated mastery acceptance remain open. No promotion or automatic extension; final seeds unused.

---

'''
doc.write_bytes(head.encode()+doc.read_bytes())
goal=R/'docs/DRILL_MASTERY_GOAL.md';s=goal.read_text(encoding='utf-8');start=s.index('Current work:');end=s.index('\n\nApp status:',start)
s=s[:start]+'Current work: The mixed rightward acquisition/retention experiment is running from common parent 1,048,609 toward fixed 2,097,152. Eighteen Unity tests and the frozen built-worker fixture passed. Familiar and prior-court practice accompany fixed rightward 25 cm returns in one shared policy. The endpoint requires matched acquisition and all five retention evaluations. No mastery or promotion; final seeds remain unused. Plan: `research/hierarchy-v1/right-retention-launch-01/plan.json`.'+s[end:];goal.write_bytes(s.encode())
print(A)

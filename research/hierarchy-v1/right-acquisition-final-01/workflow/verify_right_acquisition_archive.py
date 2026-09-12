from pathlib import Path
import json,hashlib,gzip
R=Path('F:/dev/picklebot');W=Path(__file__).resolve().parent;B=R/'artifacts/hierarchy-v1/right-acquisition-01';V=W.parents[1]/'outputs/right-acquisition-review-01';A=R/'research/hierarchy-v1/right-acquisition-final-01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
inputs=json.loads((A/'inputs.json').read_text(encoding='utf-8'));n=0
for path,digest in inputs.items():
    src=Path(path)
    if src.is_relative_to(B):dst=A/src.relative_to(B)
    elif src.is_relative_to(V):dst=A/'viewer'/src.relative_to(V)
    elif src.is_relative_to(W):dst=A/'workflow'/src.name
    else:raise AssertionError(src)
    if src.suffix in ('.jsonl','.log') or src.name=='first-decisions.json':
        with gzip.open(str(dst)+'.gz','rb') as f:assert hashlib.sha256(f.read()).hexdigest()==digest
    else:assert sha(dst)==digest,dst
    n+=1
images=json.loads((A/'image-inventory.json').read_text(encoding='utf-8'))['sha256']
for p,digest in images.items():assert sha(V/p)==digest
assert len(images)==1024
for role in ['baseline','final']:
    x=json.loads((V/role/'complete.json').read_text(encoding='utf-8'));assert x['matchesReference']==512
assert not json.loads((R/'artifacts/player-v3/seed-ledger.json').read_text(encoding='utf-8'))['finalSeedsConsumed']
quality=dict(archivedFilesVerified=n,localImagesVerified=len(images),replaysMatched=1024,inspectedFrames=['baseline/clips/A-1109849/frame-0000-1.jpg','final/clips/A-1109849/frame-0020-1.jpg','final/clips/A-1109849/frame-0033-0.jpg'],frameObservations='Player, paddle and ball visible in close view; full court view shows ball flight. These are constrained-body drill recordings, not proof of natural biomechanics.',javascriptSyntaxChecked=True,htmlRenderedInspection=False,finalSeedsConsumed=False,promoted=False)
(A/'archive-verification.json').write_bytes(json.dumps(quality,indent=2).encode())
print(json.dumps(quality))

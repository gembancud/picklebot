from pathlib import Path
import json,hashlib,importlib.util,torch
R=Path('F:/dev/picklebot'); B=R/'artifacts/hierarchy-v1/right-acquisition-01'; A=B/'training'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
proof=read(A/'run-complete.json')
helper=R/'tools/mlagents-training/run_smooth_continuation.py'
assert sha(helper)=='c4454b1c7e69b50386ece91167edcc5d67def34886247079cb0c25fbe633d715'
spec=importlib.util.spec_from_file_location('helper',helper);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
h.TARGET=2097152;h.BUFFER=8192
parent=R/'artifacts/mlagents/execution-smooth-continued-01'
assert h.tree_hashes(parent)==read(A/'parent-inputs.json')
final=R/'artifacts/mlagents/execution-right-acquisition-01/PicklebotExecutionV1/checkpoint.pt'
assert sha(final)==proof['checkpointHash']
step,changes=h.audit_final_states(torch.load(parent/'PicklebotExecutionV1/checkpoint.pt',map_location='cpu',weights_only=False),torch.load(final,map_location='cpu',weights_only=False))
source=read(B/'source-records.json')
for rel,digest in source['files'].items():assert sha(R/rel)==digest
workers,goals,inputs=h.audit_workers(A,read(A/'manifest.json'),source,read(B/'build-verification.json'))
assert len(goals)==proof['episodes'] and step==proof['step']
assert not read(R/'artifacts/player-v3/seed-ledger.json')['finalSeedsConsumed']
out=dict(step=step,stateChanges=changes,workers=workers,episodes=len(goals),inputHashes=inputs,parentUnchanged=True,finalSeedsConsumed=False,promoted=False,scriptHash=sha(Path(__file__)))
with (A/'extended-verification.json').open('x') as f:json.dump(out,f,indent=2)
print(json.dumps(dict(step=step,episodes=len(goals),stateChanges=changes),indent=2))

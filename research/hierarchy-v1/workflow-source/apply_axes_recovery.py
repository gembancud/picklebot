"""Install the reviewed opt-in curriculum patch and its portable regression fixture."""
from pathlib import Path
import ast,hashlib,json,shutil
root=Path('F:/dev/picklebot');here=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
metadata=read(here/'axes-recovery-patch.json')
assert sha(here/'axes-recovery-opt-in.patch')==metadata['patchSha256']
assert read(root/'docs/research/execution-v1-evidence/wide-movement-review-01/archive-manifest.json')['status']=='complete_recording_evidence_archive'
tree=ast.parse((here/'prepare_axes_recovery_patch.py').read_text())
replacements=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='replacements' for t in n.targets))
outputs={}
for name,changes in replacements.items():
    path=root/name;record=metadata['changedFiles'][name]
    assert sha(path)==record['oldSha256']
    content=path.read_text(encoding='utf-8')
    for before,after in changes:
        assert content.count(before)==1
        content=content.replace(before,after)
    raw=content.replace('\n','\r\n').encode()
    assert hashlib.sha256(raw).hexdigest()==record['proposedCrlfSha256']
    outputs[path]=raw
tests=root/'Assets/Picklebot/PlayerLearning/Tests'
test=tests/'PlayerAxesRecoveryIntegrationV3Tests.cs'
golden=tests/'Fixtures/axes-recovery-golden.json'
assert not test.exists() and not golden.exists()
assert sha(here/'axes-recovery-golden.json')==metadata['goldenSha256']
for path,raw in outputs.items():path.write_bytes(raw)
golden.parent.mkdir(parents=True,exist_ok=True)
shutil.copy2(here/test.name,test);shutil.copy2(here/golden.name,golden)
record=dict(status='applied_for_testing',patchHash=metadata['patchSha256'],files={p.relative_to(root).as_posix():sha(p) for p in list(outputs)+[test,golden]})
with (here/'axes-applied.json').open('x',encoding='utf-8') as h:json.dump(record,h,indent=2)
print(json.dumps(record))

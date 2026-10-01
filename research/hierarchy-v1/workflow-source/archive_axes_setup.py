"""Preserve the exact checked curriculum, setup plan and build/test provenance."""
from pathlib import Path
import hashlib,json,shutil
root=Path('F:/dev/picklebot');here=Path(__file__).resolve().parent
base=root/'artifacts/hierarchy-v1/axes-recovery-01'
dest=root/'docs/research/execution-v1-evidence/axes-recovery-01/setup'
workflow=root/'research/hierarchy-v1/axes-recovery-01'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=read(base/'plan.json');source=read(base/'source-records.json')
assert plan['sourceIdentity']==source['sourceIdentity']
assert all(sha(root/p)==h for p,h in source['files'].items())
assert not dest.exists() and not workflow.exists()
records=[]
def copy(src,target):
    assert src.is_file() and not target.exists()
    target.parent.mkdir(parents=True,exist_ok=True)
    digest=sha(src);shutil.copy2(src,target);assert sha(target)==digest
    records.append({'source':str(src),'path':target.relative_to(root).as_posix(),'sha256':digest})
for name in ['plan.json','source-records.json','build-verification.json','build-launch.json','build-console.log']:
    copy(base/name,dest/name)
copy(root/'artifacts/hierarchy-v1/axes-recovery-tests-03.xml',dest/'integration-tests.xml')
for name in ['axes-test-console.log','axes-test-console-02.log','axes-test-console-03.log',
             'axes-test-editor-failed-01.log','axes-test-editor-failed-02.log','axes-test-editor-passed-03.log',
             'axes-test-project-settings-before-restore.asset','axes-applied.json']:
    copy(here/name,dest/name)
for name in ['axes-recovery-opt-in.patch','axes-recovery-patch.json','axes-recovery-golden.json',
             'PlayerAxesRecoveryIntegrationV3Tests.cs','PlayerAxesRecoveryIntegrationV3Tests.newtonsoft-failed.cs',
             'PlayerAxesRecoveryIntegrationV3Tests.scenehandle-failed.cs','build_axes_recovery.py',
             'prepare_axes_recovery.py','run_axes_recovery.py','apply_axes_recovery.py',
             'prepare_axes_recovery_patch.py','axes-recovery-sequence.md','archive_axes_setup.py']:
    copy(here/name,workflow/name)
record=dict(status='verified_axes_setup_archived',sourceIdentity=source['sourceIdentity'],files=records,
    tests={'passed':14,'failedCompileAttempts':2,'failures':'Test-only missing Newtonsoft reference and Unity6.5 SceneHandle type; corrected before all14 tests passed.'},
    projectSettings='Unity test runner removed only SENTIS_ANALYTICS_ENABLED; prior exact bytes restored before source capture and build.',
    curriculum='Focusaxes6.25–25cm; existing25/25/50mixture, olddefaultlateral preserved',
    initialStep=plan['initialStep'],targetGlobalStep=plan['targetGlobalStep'],masteryAccepted=False)
with (dest/'archive-manifest.json').open('x',encoding='utf-8') as h:json.dump(record,h,indent=2)
print(json.dumps({'setup':str(dest),'files':len(records),'sourceIdentity':source['sourceIdentity']}))

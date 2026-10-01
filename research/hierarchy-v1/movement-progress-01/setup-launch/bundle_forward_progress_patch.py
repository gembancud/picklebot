"""Bundle already-reviewed workspace proposals; project inputs are read-only."""
from pathlib import Path
import difflib
import hashlib
import json
import re

HERE=Path(__file__).resolve().parent
OUT=HERE/'forward-progress-proposal'
ROOT=Path('F:/dev/picklebot')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

runtime=json.loads((OUT/'runtime-manifest.json').read_text())
records={row['path']:row for row in runtime['files']}
tests=json.loads((HERE/'forward-progress-tests'/'test-proposal.json').read_text())
for entry in tests['files']:
    source=Path(entry['workspacePath'])
    path=entry['path']
    assert not (ROOT/path).exists(),path
    data=source.read_text(encoding='utf-8-sig').replace('\r\n','\n').replace('\n','\r\n').encode('utf-8')
    dest=OUT/'proposed'/path
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(data)
    records[path]={'path':path,'oldSha256':None,'newSha256':sha(dest)}

patch=[]
changed={}
added={}
for path,row in records.items():
    dest=OUT/'proposed'/path
    assert sha(dest)==row['newSha256'],path
    if row['oldSha256'] is not None:
        assert sha(ROOT/path)==row['oldSha256'],path
        old=(OUT/'base'/path).read_text(encoding='utf-8-sig')
    else:
        assert not (ROOT/path).exists(),path
        old=''
    new=dest.read_text(encoding='utf-8-sig')
    patch.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),
        fromfile='a/'+path if row['oldSha256'] else '/dev/null',tofile='b/'+path))
    item={'oldSha256':row['oldSha256'],'proposedSha256':sha(dest),'workspacePath':str(dest)}
    (changed if row['oldSha256'] else added)[path]=item

patchpath=OUT/'movement-forward-progress.patch'
patchpath.write_text(''.join(patch),encoding='utf-8',newline='\n')
prefix='Picklebot.PlayerLearning.Tests.'
required={
    prefix+'PlayerAxesRecoveryIntegrationV3Tests':9,
    prefix+'PlayerRecoveryScheduleV3Tests':3,
    prefix+'PlayerInterleavedRecoveryV3Tests':2,
    'Picklebot.PlayerControlsIntegration.Tests.PlayerReturnProgressV3Tests':2,
    **tests['requiredPassedTestClasses'],
}
filters=[
    prefix+'PlayerAxesRecoveryIntegrationV3Tests',
    prefix+'PlayerRecoveryScheduleV3Tests.MixtureBalancesEverySeatRangeAndExplicitlyOversamplesLeftBounce',
    prefix+'PlayerRecoveryScheduleV3Tests.ScheduledResetMatchesDirectDrillIncludingObservationsAndReward',
    prefix+'PlayerRecoveryScheduleV3Tests.WorkerValidationRejectsIncompleteOrIncompatibleRecoveryAndKeepsOldModeOptIn',
    prefix+'PlayerInterleavedRecoveryV3Tests.InterleavingPreservesEveryOriginalSeedAcrossAllWorkerCycles',
    prefix+'PlayerInterleavedRecoveryV3Tests.EverySlidingSixteenStartsRetainsTheExactGroupMixture',
    'Picklebot.PlayerControlsIntegration.Tests.PlayerReturnProgressV3Tests',
    *tests['requiredPassedTestClasses'],
]
meta={'status':'workspace_proposal_not_applied_not_unity_tested',
      'oldSourceIdentity':'557040f9cec6f4825aa263e192de05d98388962b98a022d3add8c47a064f057f',
      'patchPath':str(patchpath),'patchSha256':sha(patchpath),
      'changedFiles':changed,'addedFiles':added,
      'requiredPassedTestClasses':required,'testFilter':';'.join(filters),
      'testFilterItems':filters,'testPlan':tests,
      'configurationFlag':'movementForwardProgressReward',
      'scope':'NewMovementChallenge only; familiar and prior-court reward paths remain off',
      'bonusCap':0.25,'default':False,
      'limitations':['Unity compilation and all proposed tests remain to be run by root.',
                     'The shaping signal does not establish legal returns or model improvement.']}
out=OUT/'patch-metadata.json'
out.write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'metadata':str(out),'patchSha256':sha(patchpath),
                  'changed':len(changed),'added':len(added),
                  'minimumExpectedCases':sum(required.values())}))

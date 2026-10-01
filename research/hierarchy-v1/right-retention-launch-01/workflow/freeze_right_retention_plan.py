from pathlib import Path
import json,hashlib
R=Path('F:/dev/picklebot');W=Path(__file__).resolve().parent;B=R/'artifacts/hierarchy-v1/right-retention-01'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
fixture=B/'baseline-fixture/deterministic/verification.json';proof=read(fixture)
assert proof['resetContractVerified'] and proof['actorCriticNormalizationOptimizerUnchanged'] and proof['episodes']==512
assert not (B/'plan.json').exists() and not (B/'training').exists()
eps=[json.loads(s) for s in (B/'baseline-fixture/deterministic/worker-00/episodes.jsonl').read_text(encoding='utf-8').splitlines()]
serves=[e for e in eps if e['task']=='stationary-serve'];assert len(serves)==32 and all(e['outcome']=='legal_serve' for e in serves),'Parent serving fixture regressed; investigate before training'
groups={}
for name,select in [('familiar',lambda i:i<64),('prior',lambda i:64<=i<128),('right-focus',lambda i:i>=128)]:
    rows=[e for e in eps if select((e['seed']-1000000)%256)]
    groups[name]=dict(episodes=len(rows),legal=sum(e['outcome'] in ('legal_return','legal_serve') for e in rows),decisions=sum(e['decisions'] for e in rows))
plan=dict(run='execution-right-retention-01',parentStep=1048609,targetStep=2097152,maximumWallSeconds=3600,runnerHash=sha(W/'run_right_retention.py'),fixtureVerificationHash=sha(fixture),sourceIdentity=read(B/'source-records.json')['sourceIdentity'],buildIdentity=read(B/'build-verification.json')['buildIdentity'],baseline=groups,episodeStartMix=dict(rightFocus=.5,familiar=.25,prior=.25),selection='Fixed endpoint, no peak selection',samePolicyRequired=True,requiredEvaluations=['acquisition-A512','acquisition-B512','narrow-A256','narrow-B256','narrow-random256','wide-A512','wide-B512'],developmentAdvanceGate=dict(canonicalRight='All eight unique situations legal under both targets',legacyRetention='No narrow drill/condition loses more than5 percentage points vs common parent; no lost canonical serves or receive successes in16-case cohorts',notMastery=True),finalAcceptanceSeedsUsed=False,promotion=False)
with (B/'plan.json').open('x',encoding='utf-8') as f:json.dump(plan,f,indent=2)
print(json.dumps(groups,indent=2))

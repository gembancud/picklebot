"""Reserve one broader development battery before reset or policy observations."""
from pathlib import Path
import json, hashlib, datetime, shutil

root = Path('F:/dev/picklebot')
here = Path(__file__).resolve().parent
relative = 'artifacts/hierarchy-v1/wide-movement-fixture-01'
base = root / relative
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
ledger_path = root / 'artifacts/player-v3/seed-ledger.json'
ledger = read(ledger_path)
first, count = 1109849, 512
assert ledger['finalSeedsConsumed'] == [] and 1100000 <= first and first + count <= 1200000
for name, entries in ledger.items():
    if isinstance(entries, list):
        for entry in entries:
            if isinstance(entry, dict) and 'firstSeed' in entry and 'count' in entry:
                lo, n = int(entry['firstSeed']), int(entry['count'])
                assert max(lo, first) >= min(lo+n, first+count), f'Already allocated {name}: {entry}'
assert not base.exists()
prior_path = root / 'artifacts/hierarchy-v1/fresh-placement-01/plan.json'
prior = read(prior_path)
source_path = root / 'artifacts/hierarchy-v1/fresh-placement-01/source-records.json'
source = read(source_path)
assert source['sourceIdentity'] == prior['sourceIdentity']
assert all(sha(root / name) == expected for name, expected in source['files'].items())
for identity in prior['modelIdentities'].values():
    assert sha(root / identity['assetPath']) == identity['modelHash']
    assert sha(root / identity['checkpoint']) == identity['checkpointHash']

scripts = {}
fixture_path = here / 'wide_movement_fixture.cs'
fixture = fixture_path.read_text(encoding='utf-8-sig')
assert f'FirstSeed={first}, SeedCount={count}' in fixture
assert relative in fixture
for ordinal in range(0, count, 64):
    scripts[f'wide-fixture-{ordinal:04}.cs'] = fixture.replace('InspectFirstOrdinal=0, InspectCount=64', f'InspectFirstOrdinal={ordinal}, InspectCount=64')
for short in ('initial', 'final'):
    for condition in ('A', 'B'):
        code = (here / f'fresh-{short}-{condition}.cs').read_text(encoding='utf-8-sig')
        code = code.replace('fresh-placement-01/', 'wide-movement-fixture-01/')
        code = code.replace('run.FirstSeed=1109593;run.SeedCount=256;', f'run.FirstSeed={first};run.SeedCount={count};')
        code = code.replace('run.MovementRange=.025f;run.MovementPattern="lateral";run.MovementRehearsalRange=.1f;', 'run.MovementRange=.25f;run.MovementPattern="axes";run.MovementRehearsalRange=0;')
        code = code.replace('run.MovementRecoveryMix=true;run.InterleavedRecovery=true;', 'run.MovementRecoveryMix=false;run.InterleavedRecovery=false;')
        code = code.replace('goals.Completed!=256||first.Count!=256', 'goals.Completed!=512||first.Count!=512')
        code = code.replace('tick<200000', 'tick<400000')
        guard = ('var fixtureCheck=Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText("F:/dev/picklebot/' + relative + '/fixture-summary.json"));\n'
                 'if((bool?)fixtureCheck["outcomeAllowed"]!=true || (int?)fixtureCheck["seedCount"]!=512)throw new System.InvalidOperationException("Wide reset fixture must pass before policy evaluation");\n')
        code = guard + code
        assert 'MovementRange=.025f' not in code and 'first.Count!=256' not in code
        scripts[f'wide-{short}-{condition}.cs'] = code
for mode in ('prepare_scene', 'restore_editor'):
    scripts[f'wide-{mode}.cs'] = (here / f'fresh-{mode}.cs').read_text(encoding='utf-8-sig').replace('fresh-placement-01/', 'wide-movement-fixture-01/')
assert all(not (here / name).exists() for name in scripts)

plan = dict(version='wide-movement-diagnostic-01', createdAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    sourceIdentity=source['sourceIdentity'], firstSeed=first, seedCount=count,
    models=prior['models'], modelIdentities=prior['modelIdentities'], conditions=['A','B'],
    evaluationRewardMode='linear-radius', diagnosticOnly=True,
    physicalRecipe=dict(task='movement-maintenance', maximumReturnDifficulty=.25, movementRange=.25,
        movementPattern='axes', movementRehearsalRange=0, movementRecoveryMix=False, interleavedRecovery=False,
        movementTiming=0, movementStartVariation=0, movementPositionReward=0, fixedServeSides='both'),
    fixture=dict(batchSize=64, batchOrdinals=list(range(0,count,64)),
        outputPattern='fixture/wide-fixture-{ordinal:04d}.json',
        templateSha256=sha(fixture_path), templatePath=str(fixture_path),
        requirement='Inspect all initialized physical resets before policy outcomes; no actions or simulation ticks. Record violations, overlaps and sparse coverage. Do not replace hard cases based on outcomes.'),
    expectedSchedule=dict(fixedServes=64, requiredBounceReceives=64, familiarAir=64, familiarBounce=64, axisAir=128, axisBounce=128,
        directions=['left','right','shallow','deep'], nominalShiftCm=[25,50,75,100],
        interpretation='Local nominal feed shift from the initial paddle face, not actual contact displacement or necessary root travel; sampled axes can leave sparse joint cells.'),
    analysis=dict(primary=['Legal return rate per drill/direction/distance and player', 'Measured root path before contact and net contact displacement',
                          'Paired target assignment gain and actual landing matrix', 'Within-battery physical observation duplicates',
                          'Current candidate minus initializer on matched resets; retain every attempt'],
        uncertainty='Pointwise paired bootstrap and descriptive sparse-cell counts; no new mastery threshold or automatic promotion.'),
    freshness=dict(scope='Unused within current V3 ledger only; older V1/V2 freshness unverified', ledgerBeforeHash=sha(ledger_path)),
    provenance=dict(modelSelectionPlan=str(prior_path.relative_to(root)).replace('\\','/'), modelSelectionPlanHash=sha(prior_path)),
    finalSeedsConsumed=False, masteryAccepted=False, automaticPromotion=False)

base.mkdir(parents=True, exist_ok=False)
with (base / 'plan.json').open('x',encoding='utf-8') as handle: json.dump(plan,handle,indent=2)
shutil.copy2(source_path, base / 'source-records.json')
shutil.copy2(ledger_path, base / 'seed-ledger-before.json')
shutil.copy2(fixture_path, base / 'fixture-template.cs')
script_hashes = {}
for name, code in scripts.items():
    with (here / name).open('x',encoding='utf-8',newline='\n') as handle: handle.write(code)
    script_hashes[name] = sha(here / name)
with (base / 'script-hashes.json').open('x',encoding='utf-8') as handle: json.dump(script_hashes,handle,indent=2)
ledger['developmentBlocks'].append(dict(firstSeed=first,count=count,run=relative,
    purpose='Reset-only broad axes fixture, then frozen initializer versus1048609 executor A/B evaluation;25/50/75/100cm nominal lateral/depth shifts and familiar-skill retention. Diagnostic; no final seeds.'))
ledger_path.write_text(json.dumps(ledger,indent=2),encoding='utf-8',newline='\n')
with (base / 'allocation.json').open('x',encoding='utf-8') as handle:
    json.dump(dict(firstSeed=first,count=count,ledgerBeforeHash=plan['freshness']['ledgerBeforeHash'],ledgerAfterHash=sha(ledger_path),planHash=sha(base/'plan.json'),finalSeedsConsumed=False),handle,indent=2)
print(json.dumps(dict(plan=str(base/'plan.json'),firstSeed=first,seedCount=count,scriptCount=len(scripts))))

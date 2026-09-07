"""Check retained Unity evaluation evidence against current runtime and model."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / 'Assets/Picklebot/Rally/Models/rally-policy.json'
runtime = ROOT / 'Assets/Picklebot/Rally'
source = '\n'.join(str(p.relative_to(ROOT)) + '\n' + p.read_text()
                   for p in sorted(runtime.glob('*.cs')))
source_hash = hashlib.sha256(source.encode()).hexdigest()
model_hash = hashlib.sha256(MODEL.read_bytes()).hexdigest()
manifest = json.loads((MODEL.parent / 'rally-policy.manifest.json').read_text())
assert manifest['weights_sha256'] == model_hash, 'Model no longer matches training provenance'
assert manifest['trainer_sha256'] == hashlib.sha256((ROOT / 'scripts/rally-train.py').read_bytes()).hexdigest()
reports = []
for label in ['neural-final', 'zero-action-final']:
    report = json.loads((ROOT / f'artifacts/rally/validation/{label}.json').read_text())
    assert report['runtimeSourceSha256'] == source_hash, 'Stale simulator evidence'
    assert report['policySha256'] == model_hash, 'Stale model evidence'
    assert report['episodes'] == 100
    assert [r['seed'] for r in report['results']] == list(range(820000, 820100))
    assert report['successAtTen'] == sum(r['returns'] >= 10 for r in report['results'])
    # Inspect the actual physical collision sequence. A serve has two table
    # bounces, then alternating paddle/table pairs for every completed return.
    for episode in report['results']:
        events = [event.split()[1] for event in episode['events']]
        if episode['returns']:
            assert events[:2] == ['Table', 'Table']
            server = 1 if episode['seed'] % 2 == 0 else -1
            landing_sides = [1 if float(event.split()[2].split(',')[2]) > 0 else -1
                             for event in episode['events'] if event.split()[1] == 'Table']
            assert landing_sides[:2] == [server, -server]
            for i in range(episode['returns']):
                expected = 'PaddleNear' if (-server) * (-1)**i == -1 else 'PaddleFar'
                assert events[2+2*i:4+2*i] == [expected, 'Table'], (episode['seed'], events)
                assert landing_sides[2+i] == server * (-1)**i
    reports.append(report)
neural, baseline = reports
tests = json.loads((ROOT / 'artifacts/rally/validation/rule-and-export-tests.json').read_text())
assert tests['status'] == 'completed' and tests['summary']['passed'] == 7 and tests['summary']['failed'] == 0
repeat = json.loads((ROOT / 'artifacts/rally/validation/repeatability-final.json').read_text())
assert repeat['runtimeSourceSha256'] == source_hash and repeat['policySha256'] == model_hash
assert repeat['results'] == neural['results'][:3], 'Acceptance serves did not reproduce exactly'
assert neural['actionSource'] == 'trained-neural-policy-both-paddles'
assert baseline['actionSource'] == 'zero-action-baseline'
assert neural['successAtTen'] >= 3
assert neural['firstReturnSuccess'] > baseline['firstReturnSuccess']
assert neural['meanReturns'] > baseline['meanReturns']
print(json.dumps({'verified': True, 'neural_success_at_ten': neural['successAtTen'],
    'neural_first_return_success': neural['firstReturnSuccess'],
    'baseline_first_return_success': baseline['firstReturnSuccess'],
    'episodes_per_policy': 100, 'best_returns': neural['bestReturns'],
    'policy_sha256': model_hash, 'runtime_source_sha256': source_hash}, indent=2))

"""Check the provisional assisted-match model and retained Unity evidence."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
model_path = ROOT / 'Assets/Picklebot/Match/Models/agents.json'
model = json.loads(model_path.read_text())
sources = sorted(p for folder in ['Match', 'Inspection', 'Core', 'Simulation']
                 for p in (ROOT / 'Assets/Picklebot' / folder).rglob('*.cs'))
source = '\n'.join(str(p.relative_to(ROOT)) + '\n' + p.read_text() for p in sources)
digest = hashlib.sha256(source.encode()).hexdigest()
assert model['sourceHash'] == digest, 'Model source changed'
assert model['version'] == 'pickleball-assisted-selfplay-v1'
assert model['episodes'] == 500
for side in ['orange', 'blue']:
    assert model[side]['updates'] > 0
    assert len(model[side]['weights']) == 30
    assert any(abs(w) > .001 for w in model[side]['weights'])
assert model['orange']['weights'] != model['blue']['weights']
training = json.loads((ROOT / 'artifacts/match/training.json').read_text())
assert training['sourceHash'] == digest
assert training['configurationHash'] == model['configurationHash']
assert training['modelHash'] == 'fresh-zero-weights'
assert [p['seed'] for p in training['points']] == list(range(860000, 860500))
assert model['orange']['updates'] == model['blue']['updates'] == sum(p['winner'] != 0 for p in training['points'])
for name in ['policy-tests', 'physics-tests']:
    tests = json.loads((ROOT / 'artifacts/match' / f'{name}.json').read_text())
    assert tests['status'] == 'completed'
    assert tests['summary']['total'] == tests['summary']['passed'] == 4
    assert tests['summary']['failed'] == tests['summary']['skipped'] == 0
reports = {}
for label in ['validation', 'centre', 'stationary']:
    r = json.loads((ROOT / 'artifacts/match' / f'{label}.json').read_text())
    assert r['sourceHash'] == digest and r['configurationHash'] == model['configurationHash']
    assert r['modelHash'] == hashlib.sha256(model_path.read_bytes()).hexdigest()
    assert r['empiricalCalibration'] is False
    points = r['points']
    assert len(points) >= 30
    assert [p['seed'] for p in points] == list(range(870000, 870000 + len(points)))
    for point in points:
        assert point['winner'] in [-1, 0, 1]
        assert (point['winner'] == 0) == (point['reason'] == 'Time cap')
        assert point['hits'] == sum(c['surface'] in ['PaddleNear', 'PaddleFar'] for c in point['contacts'])
        assert all(d['action'] in range(5) and len(d['observation']) == 6 for d in point['decisions'])
    reports[label] = points
trained = reports['validation']
assert sum(p['hits'] >= 2 for p in trained) >= len(trained) / 2, 'Too few points have two paddle contacts'
competition_gate = sum(p['winner'] != 0 for p in trained) >= len(trained) / 2
assert all(p['hits'] == 0 for p in reports['stationary'])
print(json.dumps(dict(source_and_physics_checks_verified=True, competition_gate_passed=competition_gate, contact_control='scripted assistance',
    training_points=model['episodes'], validation_points=len(trained),
    mean_paddle_hits=statistics.mean(p['hits'] for p in trained),
    winners=dict(Counter(p['winner'] for p in trained)),
    terminal_reasons=dict(Counter(p['reason'] for p in trained)),
    action_counts=dict(Counter(d['action'] for p in trained for d in p['decisions'])),
    empirical_calibration=False), indent=2))
assert competition_gate, 'Competitive checkpoint gate failed: fewer than half of validation points awarded a point'

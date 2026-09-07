"""Check retained inspection evidence. This does not prove empirical calibration."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
report = json.loads((ROOT / 'artifacts/inspection/verification.json').read_text())
assert report['version'] == 'pickleball-inspection-v1-provisional'
assert report['empiricalCalibration'] is False
expected = sorted(str(p.relative_to(ROOT))
                  for folder in ['Inspection', 'Core', 'Simulation']
                  for p in (ROOT / 'Assets/Picklebot' / folder).rglob('*.cs'))
assert sorted(report['sourceFiles']) == expected, 'Source inventory changed'
assert len(report['sourceFiles']) == len(report['sourceHashes'])
for path, digest in zip(report['sourceFiles'], report['sourceHashes']):
    assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, f'Stale evidence: {path}'
for name, total in [('rule-tests', 12), ('physics-tests', 16)]:
    tests = json.loads((ROOT / 'artifacts/inspection' / f'{name}.json').read_text())
    assert tests['status'] == 'completed'
    assert tests['summary']['total'] == tests['summary']['passed'] == total
    assert tests['summary']['failed'] == tests['summary']['skipped'] == 0
presets = {p['preset']: p for p in report['presets']}
assert len(presets) == 7
court = presets['CourtDrop']
assert court['reboundComplete'] and .30 < court['reboundBottom'] < .46
assert sum(c['surface'] == 'CourtSurface' for c in court['contacts']) >= 2
granite = presets['GraniteDrop']
assert granite['reboundComplete'] and .65 < granite['reboundBottom'] < .85
assert granite['contacts'][0]['surface'] == 'Granite reference slab'
contacts = {}
for name in ['FlatContact', 'BrushUp', 'BrushDown']:
    contacts[name] = next(c for c in presets[name]['contacts'] if c['surface'] == 'PaddleNear')
    assert contacts[name]['incomingVelocity']['z'] < 0 < contacts[name]['velocity']['z']
assert contacts['BrushUp']['spin']['x'] * contacts['BrushDown']['spin']['x'] < 0
serve = presets['Serve']['contacts'][0]
assert serve['surface'] == 'CourtSurface'
assert -3.048 <= serve['point']['x'] < 0 and 2.1336 < serve['point']['z'] <= 6.7056
assert all(3.99 < p['seconds'] < 4.01 for p in presets.values())
print(json.dumps(dict(verified=True, empirical_calibration=False, tests_passed=28,
    configuration_hash=report['configurationHash'],
    first_court_rebound_bottom_m=court['reboundBottom'],
    first_granite_rebound_bottom_m=granite['reboundBottom']), indent=2))

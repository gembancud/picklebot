"""Verify the explicitly recorded CLI package migration against the original baseline."""
import hashlib
import json
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    baseline_path = ROOT / 'artifacts/player-agents/baseline-manifest.json'
    migration = json.loads((ROOT / 'config/windows-tooling-migration.json').read_text())
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    if digest(baseline_path) != migration['originalBaselineSha256']:
        raise SystemExit('Original baseline manifest changed.')
    expected = json.loads(baseline_path.read_text())['files']
    overrides = migration['packageFiles']
    if set(overrides) != {'Packages/manifest.json', 'Packages/packages-lock.json'}:
        raise SystemExit('Only the two package files may differ in this tooling migration.')
    expected.update(overrides)
    snapshot = runpy.run_path(str(ROOT / 'scripts/player-agents-baseline.py'))['snapshot']()
    changed = sorted(k for k in set(snapshot) | set(expected) if snapshot.get(k) != expected.get(k))
    if changed:
        raise SystemExit('Unexpected baseline changes:\n' + '\n'.join(changed))
    print('CLI tooling migration verified: 61 original baseline files unchanged; 2 exact package updates. Original manifest preserved.')


if __name__ == '__main__':
    main()

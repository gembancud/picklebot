"""Verify D-031 source identity and preserved historical evidence; never rewrite it."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import subprocess

from player_actor import contact_source_hash, player_source_hash, team_source_hash

ROOT = Path(__file__).resolve().parents[1]


def verify(unity=None):
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    record = json.loads((ROOT / 'config/windows-source-migration.json').read_text())
    baseline = ROOT / 'artifacts/player-agents/baseline-manifest.json'
    if digest(baseline) != record['originalBaselineSha256']:
        raise RuntimeError('Original baseline manifest changed')
    tooling_path = ROOT / 'config/windows-tooling-migration.json'
    if digest(tooling_path) != record['toolingRecordSha256']:
        raise RuntimeError('Original tooling migration record changed')
    tooling = json.loads(tooling_path.read_text())
    overrides = record['baselineSourceFiles']
    if set(overrides) != {
        'Assets/Picklebot/Doubles/Editor/ContactTraining.cs',
        'Assets/Picklebot/DoublesTraining/Editor/TeamTraining.cs',
        'scripts/doubles-verify.py',
    }:
        raise RuntimeError('Unexpected source migration scope')
    expected = json.loads(baseline.read_text())['files']
    expected.update(tooling['packageFiles'])
    expected.update(overrides)
    snapshot = runpy.run_path(str(ROOT / 'scripts/player-agents-baseline.py'))['snapshot']()
    changed = sorted(k for k in set(snapshot) | set(expected) if snapshot.get(k) != expected.get(k))
    if changed:
        raise RuntimeError('Unexpected baseline changes: ' + ', '.join(changed))
    for section in ('implementationFiles', 'preservedArtifacts'):
        for name, value in record[section].items():
            if digest(ROOT / name) != value:
                raise RuntimeError(f'{section} changed: {name}')
    hashes = dict(contact=contact_source_hash(ROOT), player=player_source_hash(ROOT), team=team_source_hash(ROOT))
    if hashes != record['newSourceHashes']:
        raise RuntimeError('Current source differs from the verified migration')
    if unity:
        code = ('return new {contact=Picklebot.Doubles.Editor.ContactTraining.SourceHash(),'
                'player=Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash(),'
                'team=Picklebot.DoublesTraining.Editor.TeamTraining.SourceHash()};')
        response = subprocess.run([unity, 'command', 'eval', code, '--project-path', str(ROOT), '--format', 'json'],
                                  cwd=ROOT, check=True, capture_output=True, text=True, timeout=45)
        envelope = json.loads(response.stdout)
        if not envelope.get('success'):
            raise RuntimeError('Unity CLI failed: ' + str(envelope.get('errors')))
        data = envelope['data']
        if Path(data['target']['projectPath']).resolve() != ROOT.resolve():
            raise RuntimeError('CLI selected a different project')
        if not data['result'].get('success') or data['result']['result'] != hashes:
            raise RuntimeError('Unity and Python source identities differ')
    return {'passed': True, 'unityCompared': bool(unity), 'sourceHashes': hashes,
            'baselineFilesUnchanged': len(snapshot) - len(overrides) - len(tooling['packageFiles']),
            'baselineSourceChangesRecorded': len(overrides), 'packageChangesRecorded': len(tooling['packageFiles']),
            'preservedArtifacts': len(record['preservedArtifacts'])}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--unity', nargs='?', const='unity', help='Also compare live Unity hashes; optional CLI executable path')
    args = parser.parse_args()
    print(json.dumps(verify(args.unity), indent=2))

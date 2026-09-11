"""Reproduce the pinned ML-Agents environment without changing the legacy Pixi env."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-source-only', action='store_true')
    args = parser.parse_args()
    training = ROOT / 'tools/mlagents-training'
    pin = json.loads((training / 'source-pin.json').read_text())
    source = training / 'vendor/ml-agents'
    if not source.exists():
        source.mkdir(parents=True)
        commands = [
            ['init'], ['remote', 'add', 'origin', pin['repository']],
            ['fetch', '--depth', '1', '--filter=blob:none', 'origin', pin['revision']],
            ['sparse-checkout', 'init', '--cone'],
            ['sparse-checkout', 'set', 'ml-agents', 'ml-agents-envs', 'config/ppo', 'config/poca',
             'Project/Assets/ML-Agents/Examples/3DBall/Scripts', 'Project/Assets/ML-Agents/Examples/SharedAssets/Scripts'],
            ['checkout', '--detach', pin['revision']],
        ]
        for command in commands:
            subprocess.run(['git', '-C', str(source), *command], check=True)
    actual = subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    dirty = subprocess.check_output(['git','-C',str(source),'status','--porcelain','--untracked-files=no'],text=True).strip()
    if actual != pin['revision'] or dirty:
        raise RuntimeError('Trainer source differs from the pinned, unmodified revision. Preserve and inspect it.')
    print(json.dumps({'sourceRevision':actual,'trackedSourceUnmodified':True}), flush=True)
    if not args.verify_source_only:
        pixi = shutil.which('pixi') or str(ROOT.parent / 'tools/pixi/bin/pixi.exe')
        subprocess.run([pixi,'install','--locked','--manifest-path',str(training/'pixi.toml')],check=True)

if __name__ == '__main__':
    main()

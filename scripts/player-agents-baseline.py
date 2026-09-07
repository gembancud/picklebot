#!/usr/bin/env python3
"""Freeze or verify the prior doubles baseline without changing its files."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts/player-agents/baseline-manifest.json"


def snapshot():
    paths = set()
    for folder in ("Doubles", "DoublesTraining", "Core", "Simulation"):
        for path in (ROOT / "Assets/Picklebot" / folder).rglob("*"):
            if path.is_file() and path.suffix in (".cs", ".json", ".asmdef"):
                paths.add(path)
    for path in (
        "Assets/Picklebot/Scenes/PickleballDoubles.unity",
        "Packages/manifest.json", "Packages/packages-lock.json",
        "ProjectSettings/TimeManager.asset", "scripts/doubles-verify.py",
        "artifacts/doubles/contact-validation.json",
        "artifacts/doubles/teams-trained.json",
        "artifacts/doubles/teams-random.json",
    ):
        paths.add(ROOT / path)
    return {
        p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(paths)
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    files = snapshot()
    if MANIFEST.exists():
        saved = json.loads(MANIFEST.read_text())
        changed = sorted(k for k in set(files) | set(saved["files"])
                         if files.get(k) != saved["files"].get(k))
        if changed:
            raise SystemExit("Baseline changed; do not overwrite its manifest:\n"
                             + "\n".join(changed))
        print(f"Baseline unchanged: {len(files)} files.")
        return
    if args.check:
        raise SystemExit("No baseline manifest. Run without --check to freeze it.")
    result = subprocess.run([sys.executable, "scripts/doubles-verify.py"],
                            cwd=ROOT, check=True, capture_output=True, text=True)
    model = json.loads((ROOT / "Assets/Picklebot/Doubles/Models/contact.json").read_text())
    value = {
        "schema": "player-agents-baseline-v1",
        "createdUtc": datetime.now(timezone.utc).isoformat(),
        "configurationHash": model["configurationHash"],
        "files": files,
        "baselineVerification": result.stdout,
        "limits": "Baseline evidence only; not player-agent training or physical calibration.",
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("x") as output:
        json.dump(value, output, indent=2)
        output.write("\n")
    print(f"Frozen {len(files)} baseline files: {MANIFEST}")


if __name__ == "__main__":
    main()

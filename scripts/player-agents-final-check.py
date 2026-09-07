#!/usr/bin/env python3
"""Verify saved final baseline reports. Does not run games or accept the full goal."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from player_acceptance import audit_baseline, validate_runner_artifacts
from player_actor import Actor, ROOT, file_hash, source_hash


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("actor", type=Path)
    parser.add_argument("reports", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    # Reserve a new artifact before inspection. A failed audit is also retained.
    with args.output.open("x") as output:
        result = dict(createdUtc=datetime.now(timezone.utc).isoformat(), status="invalid_evidence",
                      actor=str(args.actor), reportPaths=[str(path) for path in args.reports],
                      verifierHash=file_hash(__file__), checksHash=file_hash(ROOT / "scripts/player_acceptance.py"),
                      baselineChecksPassed=False,
                      remainingChecks=["older opponent", "coverage probes", "movement ablation", "physical tests", "playable scene"])
        code = 2
        try:
            _, actor = Actor.load_export(args.actor)
            protocol_path = ROOT / "config/player-agents/evaluation-v1.json"
            manifest_path = ROOT / "artifacts/player-agents/baseline-manifest.json"
            protocol = json.loads(protocol_path.read_text()); manifest = json.loads(manifest_path.read_text())
            for path, expected_hash in manifest["files"].items():
                if file_hash(ROOT / path) != expected_hash:
                    raise ValueError("Frozen baseline changed: " + path)
            expected = dict(sourceHash=source_hash(), actorHash=file_hash(args.actor),
                            configurationHash=manifest["configurationHash"], protocolHash=file_hash(protocol_path),
                            contactModelHash=file_hash(ROOT / "Assets/Picklebot/Doubles/Models/contact.json"),
                            baselineManifestHash=file_hash(manifest_path),
                            opponentHash=file_hash(ROOT / "Assets/Picklebot/Doubles/Models/teams.json"))
            for key in ("sourceHash", "configurationHash", "protocolHash", "contactModelHash", "baselineManifestHash"):
                if actor.get(key) != expected[key]:
                    raise ValueError("Final actor provenance mismatch: " + key)
            if type(actor.get("trainingSteps")) is not int or actor["trainingSteps"] <= 0:
                raise ValueError("Final actor has no recorded training")
            parity_path = args.actor.parent / "unity-parity.json"
            parity = json.loads(parity_path.read_text())
            if (parity.get("passed") is not True or parity["actorHash"] != expected["actorHash"]
                    or parity["sourceHash"] != expected["sourceHash"] or parity["cases"] < 1
                    or not 0 <= parity["maximumError"] < .0001
                    or parity["inputHash"] != file_hash(args.actor.parent / "parity-input.json")):
                raise ValueError("Missing or stale actor export parity")
            reports = [json.loads(path.read_text()) for path in args.reports]
            plans = {validate_runner_artifacts(path, report, ROOT, file_hash) for path, report in zip(args.reports, reports)}
            if len(plans) != 1:
                raise ValueError("Final reports must come from one reserved evaluation run")
            result.update(expected, trainingSteps=actor["trainingSteps"], parityHash=file_hash(parity_path),
                          reportHashes=[file_hash(path) for path in args.reports])
            result.update(audit_baseline(reports, protocol, expected))
            result["status"] = "baseline_pass" if result["baselineChecksPassed"] else "baseline_fail"
            code = 0 if result["baselineChecksPassed"] else 1
        except (OSError, ValueError, KeyError, TypeError) as error:
            result["error"] = str(error)
        json.dump(result, output, indent=2)
        print(json.dumps(result), flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main())

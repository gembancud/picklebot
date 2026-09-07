#!/usr/bin/env python3
"""Read-only artifact and paired-player checks for a completed partner report."""
import argparse
import json
from pathlib import Path
from player_actor import ROOT, file_hash, source_hash
from player_partner import audit_partner_games


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    if report.get("status") != "complete" or report.get("split") != "development" or report.get("sourceHash") != source_hash():
        raise ValueError("Partner report is not complete on the current runtime")
    paths = {"candidateHash": Path(report["candidatePath"]), "olderHash": Path(report["olderPath"]),
             "planHash": ROOT / report["planPath"], "collectorHash": ROOT / report["collectorSnapshotPath"],
             "protocolHash": ROOT / "config/player-agents/partner-evaluation-v1.json"}
    for field, path in paths.items():
        if file_hash(path) != report[field]: raise ValueError("Partner artifact hash mismatch: " + field)
    candidate = json.loads(paths["candidateHash"].read_text())
    older = json.loads(paths["olderHash"].read_text())
    if (report["candidateHash"] == report["olderHash"] or candidate.get("sourceHash") != report["sourceHash"]
            or older.get("sourceHash") != report.get("olderTrainingSourceHash")
            or report.get("historicalOlderPolicy") != (older.get("sourceHash") != report["sourceHash"])):
        raise ValueError("Saved policy source or historical-opponent label changed")
    plan = json.loads(paths["planHash"].read_text())
    protocol = json.loads(paths["protocolHash"].read_text())
    for field in ("sourceHash", "candidateHash", "olderHash", "protocolHash", "collectorHash"):
        if plan.get(field) != report[field]: raise ValueError("Partner plan provenance mismatch: " + field)
    manifest_path = ROOT / "artifacts/player-agents/baseline-manifest.json"
    if file_hash(manifest_path) != plan["manifestHash"] or file_hash(ROOT / "Assets/Picklebot/Doubles/Models/contact.json") != plan["contactHash"]:
        raise ValueError("Frozen baseline or contact manifest changed")
    for path, expected in json.loads(manifest_path.read_text())["files"].items():
        if file_hash(ROOT / path) != expected: raise ValueError("Frozen baseline changed: " + path)
    result = audit_partner_games(report, plan, protocol)
    print(json.dumps(dict(reportHash=file_hash(args.report), **result), indent=2))


if __name__ == "__main__": main()

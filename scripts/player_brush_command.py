"""Audit paired flat-brush command diagnostics. Never promote a model."""
import argparse
import json
import math
from pathlib import Path

from player_contact_outcomes import summarize, summarize_execution, summarize_fault_context
from player_ppo import validate_motor_metrics


def validate_parameters(report, frozen):
    bias = report.get("flatBrushBias")
    if (report.get("version") != "player-brush-command-v1" or type(bias) not in (int, float)
            or bias not in (0, 5) or report.get("flatPitchOffsetDegrees") != 0
            or report.get("experimentalContactOverride") is not (bias != frozen["strokes"][0]["brushBias"])):
        raise ValueError("Unexpected brush diagnostic or override label")
    actual = report.get("candidateContactParameters")
    if not isinstance(actual, list) or len(actual) != len(frozen["strokes"]):
        raise ValueError("Missing stroke parameter records")
    for kind, before in enumerate(frozen["strokes"]):
        if set(actual[kind]) != set(before):
            raise ValueError("Stroke parameter schema changed")
        for key, old in before.items():
            expected = bias if kind == 0 and key == "brushBias" else old
            value = actual[kind][key]
            if type(value) not in (int, float) or not math.isfinite(value) or abs(value - expected) > 1e-5:
                raise ValueError("Unreported stroke parameter change")


def validate_pair(original, control, candidate):
    for key in ("sourceHash", "configurationHash", "actorHash", "actorTrainingSourceHash",
                "historicalCandidate", "contactHash", "opponentHash", "baselineManifestHash",
                "protocolHash", "seedBase", "caseCount", "maximumRalliesPerCase", "sampledActor", "sampledBaseline"):
        if key not in original or original[key] != control.get(key) or original[key] != candidate.get(key):
            raise ValueError("Unpaired diagnostic condition: " + key)
    if control.get("flatBrushBias") != 5 or candidate.get("flatBrushBias") != 0:
        raise ValueError("Expected original and zero-brush pair")
    if original["rallies"] != control["rallies"] or original["games"] != control["games"]:
        raise ValueError("Control did not reproduce the original physical trace")
    if control.get("collectorHash") != candidate.get("collectorHash"):
        raise ValueError("Paired collectors differ")


def validate_report(path):
    from player_actor import ROOT, file_hash, source_hash
    report = json.loads(path.read_text())
    if (report.get("status") != "complete" or report.get("error") is not None
            or report.get("split") != "development" or report.get("sourceHash") != source_hash()
            or report.get("caseCount") != 4 or len(report.get("games", [])) != 4
            or report.get("maximumRalliesPerCase") != 16 or report.get("sampledActor") is not False
            or report.get("sampledBaseline") is not True or not 1100000 <= report.get("seedBase", -1) <= 1199996):
        raise ValueError("Incomplete or changed diagnostic schedule")
    for i, game in enumerate(report["games"]):
        if (game["gameSeed"] != report["seedBase"] + i or game["candidateTeam"] != i % 2
                or game["reason"] not in ("game complete", "requested diagnostic limit")
                or game["complete"] is not (game["winner"] >= 0)):
            raise ValueError("Game identity or completion differs")
        rows = [r for r in report["rallies"] if r["gameSeed"] == game["gameSeed"]]
        if len(rows) != game["rallies"] or any(not r["resolved"] or r["candidateTeam"] != i % 2 for r in rows):
            raise ValueError("Incomplete or wrong-team rally records")
    checks = {"actorHash": ROOT / report["actorPath"], "collectorHash": ROOT / report["collectorSnapshotPath"],
        "contactHash": ROOT / "Assets/Picklebot/Doubles/Models/contact.json",
        "opponentHash": ROOT / "Assets/Picklebot/Doubles/Models/teams.json",
        "baselineManifestHash": ROOT / "artifacts/player-agents/baseline-manifest.json",
        "protocolHash": ROOT / "config/player-agents/evaluation-v1.json",
        "swingSourceHash": ROOT / report["swingSourcePath"], "planSourceHash": ROOT / report["planSourcePath"]}
    for key, target in checks.items():
        if file_hash(target) != report[key]:
            raise ValueError("Changed diagnostic artifact: " + key)
    actor = json.loads(checks["actorHash"].read_text())
    if (actor["sourceHash"] != report["actorTrainingSourceHash"]
            or report["historicalCandidate"] is not (actor["sourceHash"] != source_hash())):
        raise ValueError("Historical actor provenance changed")
    frozen = json.loads(checks["contactHash"].read_text())
    if report["version"] == "player-brush-command-v1":
        validate_parameters(report, frozen)
    else:
        from player_contact_outcomes import validate_contact_override
        if report["version"] != "player-contact-outcomes-v1":
            raise ValueError("Unknown original trace version")
        validate_contact_override(report, frozen)
    validate_motor_metrics(report)
    return report


def main():
    from player_actor import file_hash, source_hash
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path)
    parser.add_argument("control", type=Path)
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    paths = (args.original, args.control, args.candidate)
    original, control, candidate = [validate_report(path) for path in paths]
    validate_pair(original, control, candidate)
    results = []
    for report in (control, candidate):
        results.append(dict(flatBrushBias=report["flatBrushBias"], rallies=len(report["rallies"]),
            rallyWins=sum(r["winner"] == r["candidateTeam"] for r in report["rallies"]),
            completeGames=sum(g["complete"] for g in report["games"]),
            completeGameWins=sum(g["complete"] and g["winner"] == g["candidateTeam"] for g in report["games"]),
            shots=summarize(report), execution=summarize_execution(report), faultContext=summarize_fault_context(report)))
    print(json.dumps(dict(sourceHash=source_hash(), verifierHash=file_hash(__file__),
        reports=[dict(path=str(p),sha256=file_hash(p)) for p in paths], evidenceChecksPassed=True,
        originalControlTraceExact=True, results=results,
        limitation="Paired short diagnosis. Partial games are not complete matches. No automatic model or stroke promotion."), indent=2))


if __name__ == "__main__": main()

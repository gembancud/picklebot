"""Verify diagnostic output substitution. Never export or promote a mixed policy."""
import argparse
import json
import math
from pathlib import Path

from player_actor import Actor, ROOT, file_hash, source_hash
from player_contact_outcomes import summarize, summarize_execution, summarize_fault_context, validate_contact_override
from player_ppo import validate_motor_metrics
from player_skill_retention import validate_replayed_action


def validate_substitution(mode, rows, seed_base):
    fields = dict(none=(), movement=("moveX", "moveZ"), attempt=("attempt",), shot=("shot",))
    if mode not in fields or not rows:
        raise ValueError("Invalid or empty ablation")
    seen = set(); changed = 0
    for row in rows:
        seed, player, tick, rally = (row[k] for k in ("gameSeed", "player", "observationTick", "rally"))
        if (any(type(v) is not int for v in (seed, player, tick, rally))
                or not seed_base <= seed < seed_base + 4 or player not in range(4)
                or player // 2 != (seed-seed_base) % 2 or row["candidateTeam"] != player // 2
                or tick < 0 or tick % 12 or row["applyTick"] != tick + 6 or not 0 <= rally < 16):
            raise ValueError("Invalid ablation decision ownership or timing")
        key = seed, rally, tick, player
        if key in seen:
            raise ValueError("Duplicate decision")
        seen.add(key)
        obs = row["observation"]
        if len(obs) != 54 or any(type(v) not in (int, float) or not math.isfinite(v) for v in obs):
            raise ValueError("Invalid own-player observation")
        for name in ("original", "reference", "applied"):
            action = row[name]
            if (set(action) != {"moveX", "moveZ", "attempt", "shot"}
                    or type(action["attempt"]) is not bool or type(action["shot"]) is not int
                    or not 0 <= action["shot"] < 9
                    or any(type(action[k]) not in (int, float) or not math.isfinite(action[k]) for k in ("moveX", "moveZ"))
                    or math.hypot(action["moveX"], action["moveZ"]) > 1.00001):
                raise ValueError("Invalid recorded action")
        for field in row["original"]:
            expected = row["reference"] if field in fields[mode] else row["original"]
            if row["applied"][field] != expected[field]:
                raise ValueError("Substitution changed an unselected component or used the wrong source")
        changed += row["applied"] != row["original"]
    if any((seed, rally, tick, player ^ 1) not in seen for seed, rally, tick, player in seen):
        raise ValueError("Missing teammate decision")
    return changed


def main():
    import torch
    torch.set_num_threads(2)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    expected = dict(version="player-action-ablation-v1", diagnosticOnly=True, status="complete", error=None,
        split="development", seedBase=1198000, caseCount=4, maximumRalliesPerCase=16,
        sampledActor=False, sampledBaseline=True, flatPitchOffsetDegrees=0, experimentalContactOverride=False,
        physicsHz=240, decisionTicks=12, actionLatencyTicks=6)
    if any(report.get(k) != v for k, v in expected.items()) or report["sourceHash"] != source_hash():
        raise ValueError("Wrong diagnostic schedule or runtime")
    checks = {"contactHash": "Assets/Picklebot/Doubles/Models/contact.json",
        "opponentHash": "Assets/Picklebot/Doubles/Models/teams.json",
        "protocolHash": "config/player-agents/evaluation-v1.json",
        "baselineManifestHash": "artifacts/player-agents/baseline-manifest.json",
        "baseCollectorHash": "scripts/player-contact-outcomes.cs",
        "collectorHash": report["collectorSnapshotPath"], "swingSourceHash": report["swingSourcePath"],
        "planSourceHash": report["planSourcePath"], "actorHash": report["actorPath"], "referenceHash": report["referencePath"]}
    for key, name in checks.items():
        path = (ROOT / name).resolve(); path.relative_to(ROOT)
        if file_hash(path) != report[key]:
            raise ValueError("Changed artifact: " + key)
    if report["collectorHash"] != file_hash(ROOT / "scripts/player-action-ablation.cs"):
        raise ValueError("Collector changed")
    validate_contact_override(report, json.loads((ROOT / checks["contactHash"]).read_text()))
    if len(report["games"]) != 4:
        raise ValueError("Missing diagnostic cases")
    for i, game in enumerate(report["games"]):
        if (game["gameSeed"] != 1198000 + i or game["candidateTeam"] != i % 2
                or game["reason"] not in ("game complete", "requested diagnostic limit")):
            raise ValueError("Incomplete case or wrong ownership")
    validate_motor_metrics(report)
    rows = report["decisions"]
    if report["decisionRows"] != len(rows):
        raise ValueError("Missing decisions")
    changed = validate_substitution(report["mode"], rows, report["seedBase"])
    x = torch.tensor([r["observation"] for r in rows])
    for role, path_key, source_key, history_key in (
            ("original", "actorPath", "actorTrainingSourceHash", "historicalCandidate"),
            ("reference", "referencePath", "referenceTrainingSourceHash", "historicalReference")):
        actor, metadata = Actor.load_export(ROOT / report[path_key])
        if (metadata["sourceHash"] != report[source_key]
                or report[history_key] is not (metadata["sourceHash"] != report["sourceHash"])):
            raise ValueError("Wrong actor provenance")
        for key, report_key in (("configurationHash", "configurationHash"), ("contactModelHash", "contactHash"),
                                ("protocolHash", "protocolHash"), ("baselineManifestHash", "baselineManifestHash")):
            if metadata[key] != report[report_key]: raise ValueError("Wrong actor settings")
        with torch.no_grad():
            out = actor(x); moves = actor.movement(out[:, :2]); shots = out[:, 3:].argmax(-1)
        for i, row in enumerate(rows):
            validate_replayed_action(row[role], moves[i], bool(out[i, 2] >= 0), int(shots[i]))
    print(json.dumps(dict(reportHash=file_hash(args.report), verifierHash=file_hash(__file__), mode=report["mode"],
        sourceHash=source_hash(), actorHash=report["actorHash"], referenceHash=report["referenceHash"],
        decisionsReplayed=len(rows), changedDecisions=changed, rallies=len(report["rallies"]),
        rallyWins=sum(r["winner"] == r["candidateTeam"] for r in report["rallies"]),
        **summarize(report), faultContext=summarize_fault_context(report), execution=summarize_execution(report)), indent=2))


if __name__ == "__main__": main()

"""Audit paired development coverage and actor-only short returns. Never promote a model."""
import argparse
import json
import math
from pathlib import Path

from player_ppo import validate_motor_metrics


def coverage(report):
    expected = dict(status="complete", error=None, fixtureVersion="coverage-development-v1",
                    split="development", seedBase=1115000, lanes=[-2.6, -.2, .2, 2.6], depths=[3.5, 6],
                    physicsHz=240, decisionTicks=12, actionLatencyTicks=6,
                    incomingCanonicalPosition=[0, 1.2, .4], incomingCanonicalVelocity=[0, 1.2, -8])
    if any(report.get(k) != v for k, v in expected.items()) or len(report.get("cases", [])) != 48:
        raise ValueError("Incomplete or changed coverage schedule")
    modes = ["learned", "movement_disabled", "diagnostic_teacher"]
    for index, case in enumerate(report["cases"]):
        fixture = index // 3
        identity = dict(mode=modes[index % 3], seed=1115000 + fixture, candidateTeam=fixture // 8,
                        lane=expected["lanes"][fixture % 4], depth=expected["depths"][fixture // 4 % 2])
        if any(case.get(k) != v for k, v in identity.items()):
            raise ValueError("Coverage identity or pairing changed")
        if any(type(case.get(k)) is not bool for k in ("legalHit", "legalLanding")):
            raise ValueError("Missing coverage outcomes")
        if case["legalLanding"] and not case["legalHit"]:
            raise ValueError("A landing requires a legal contact")
        # Stationary opponents use the same independent motor in this fixture.
        validate_motor_metrics(dict(games=[{**case, "candidateTeam": team} for team in (0, 1)]))
        decisions = case.get("decisions", [])
        if not decisions:
            raise ValueError("Missing recorded coverage decisions")
        seen = set()
        for decision in decisions:
            player, tick = decision["player"], decision["observationTick"]
            if (type(player) is not int or player not in range(4) or player // 2 != case["candidateTeam"]
                    or type(tick) is not int or tick < 0 or tick % 12
                    or decision["applyTick"] != tick + 6 or (player, tick) in seen
                    or len(decision["observation"]) != 54
                    or not all(type(x) in (int, float) and math.isfinite(x) for x in decision["observation"])):
                raise ValueError("Coverage observation ownership or decision timing changed")
            seen.add((player, tick))
        if any((player ^ 1, tick) not in seen for player, tick in seen):
            raise ValueError("Missing paired teammate decision")
        if case["mode"] == "movement_disabled":
            distances = case.get("movementDistance", [])
            if len(distances) != 4 or any(not math.isfinite(v) or v < 0 or v > .0001 for v in distances):
                raise ValueError("Movement-disabled control moved")
    return report["cases"]


def compare(parent, candidate):
    for key in ("sourceHash", "configurationHash", "contactModelHash", "protocolHash", "scriptHash"):
        if not parent.get(key) or parent[key] != candidate.get(key):
            raise ValueError("Coverage conditions differ: " + key)
    if parent.get("actorHash") == candidate.get("actorHash"):
        raise ValueError("Retention needs two different saved actors")
    a, b = coverage(parent), coverage(candidate)
    groups = []
    for team in (0, 1):
        for depth in (3.5, 6):
            def counts(cases):
                selected = [c for c in cases if c["mode"] == "learned" and c["candidateTeam"] == team and c["depth"] == depth]
                return dict(cases=len(selected), contacts=sum(c["legalHit"] for c in selected),
                            legalLandings=sum(c["legalLanding"] for c in selected))
            before, after = counts(a), counts(b)
            regressions = [k for k in ("contacts", "legalLandings") if after[k] < before[k]]
            groups.append(dict(team=team, depth=depth, parent=before, candidate=after, regressions=regressions))
    return dict(retentionChecksPassed=not any(g["regressions"] for g in groups), groups=groups,
                limitation="Development fixture retention only. A pass does not prove match strength or complete the goal.")


def actor_only_short(report, records, candidate_hash):
    if (report.get("status") != "complete" or report.get("split") != "development"
            or report.get("skillProfile") != "kitchen" or report.get("actorHash") != candidate_hash
            or report.get("teacherProbability") != 0 or report.get("teacherDecisions") != 0
            or report.get("actorDecisions") != len(records) or report.get("rows") != len(records)
            or not records or any(row.get("executedBy") != "actor" for row in records)):
        raise ValueError("Short-ball results are not this candidate's actor-only development run")
    results = report["gameResults"]
    return dict(cases=len(results), contacts=sum(g["legalHit"] for g in results),
                legalLandings=sum(g["legalLanding"] for g in results),
                kitchenGroundstrokes=sum(g["legalKitchenGroundstroke"] for g in results), teacherDecisions=0)


def validate_replayed_action(action, move, attempt, shot):
    for axis, key in enumerate(("moveX", "moveZ")):
        value = action.get(key)
        if (type(value) not in (int, float) or not math.isfinite(value)
                or not math.isfinite(float(move[axis])) or abs(float(move[axis]) - value) > .0001):
            raise ValueError("Recorded movement differs from the saved actor")
    if action.get("attempt") is not attempt or type(action.get("shot")) is not int or action["shot"] != shot:
        raise ValueError("Recorded hit or shot differs from the saved actor")


def main():
    import torch
    torch.set_num_threads(2)
    from player_actor import Actor, ROOT, file_hash, source_hash, teacher_data
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parent_coverage", type=Path)
    parser.add_argument("candidate_coverage", type=Path)
    parser.add_argument("candidate_short", type=Path)
    args = parser.parse_args()
    paths = [args.parent_coverage, args.candidate_coverage, args.candidate_short]
    reports = [json.loads(p.read_text()) for p in paths]
    parent, candidate, short = reports
    for report in reports:
        if report["sourceHash"] != source_hash(): raise ValueError("Stale runtime source")
        if report["contactModelHash"] != file_hash(ROOT / "Assets/Picklebot/Doubles/Models/contact.json"):
            raise ValueError("Contact model changed")
        if report["protocolHash"] != file_hash(ROOT / "config/player-agents/evaluation-v1.json"):
            raise ValueError("Evaluation protocol changed")
    for report in (parent, candidate):
        actor_path = (ROOT / report["actorPath"]).resolve(); actor_path.relative_to(ROOT)
        _, metadata = Actor.load_export(actor_path)
        if (file_hash(actor_path) != report["actorHash"] or metadata["sourceHash"] != report["actorTrainingSourceHash"]
                or report["historicalCandidate"] is not (metadata["sourceHash"] != report["sourceHash"])
                or report["scriptHash"] != file_hash(ROOT / "scripts/player-coverage-probe.cs")):
            raise ValueError("Coverage actor or collector provenance changed")
        for key in ("configurationHash", "contactModelHash", "protocolHash"):
            if metadata[key] != report[key]: raise ValueError("Coverage actor settings changed")
    if candidate["historicalCandidate"] or short["configurationHash"] != candidate["configurationHash"]:
        raise ValueError("Candidate must use current, matching runtime settings")
    result = compare(parent, candidate)
    x, _, _, data_hash = teacher_data(args.candidate_short, "development")
    records = [json.loads(line) for line in (ROOT / short["dataPath"]).read_text().splitlines()]
    short_result = actor_only_short(short, records, candidate["actorHash"])
    validate_motor_metrics(dict(games=[{**g, "candidateTeam": team} for g in short["gameResults"] for team in (0, 1)]))
    actor, metadata = Actor.load_export(ROOT / candidate["actorPath"])
    if metadata["sourceHash"] != short["actorTrainingSourceHash"]:
        raise ValueError("Short-ball actor provenance changed")
    with torch.no_grad():
        output = actor(x); moves = actor.movement(output[:, :2]); shots = output[:, 3:].argmax(dim=1)
    for index, row in enumerate(records):
        validate_replayed_action(row["appliedAction"], moves[index], bool(output[index, 2] >= 0), int(shots[index]))
    print(json.dumps(dict(verifierHash=file_hash(__file__), sourceHash=source_hash(),
        reports=[dict(path=str(p), sha256=file_hash(p)) for p in paths], shortDataHash=data_hash,
        candidateHash=candidate["actorHash"], parentHash=parent["actorHash"], actorOnlyActionsReplayed=len(records),
        shortBall=short_result, **result), indent=2))
    return 0 if result["retentionChecksPassed"] else 1


if __name__ == "__main__": raise SystemExit(main())

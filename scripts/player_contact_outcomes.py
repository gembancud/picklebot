"""Read-only classification of recorded, physical player shot outcomes."""
import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path


def classify_shot(shot, events):
    index = shot["eventIndex"]
    if not 0 <= index < len(events):
        raise ValueError("Missing shot event")
    origin = events[index]
    if origin["kind"] != "hit" or origin["player"] != shot["player"] or origin["time"] != shot["time"]:
        raise ValueError("Shot and rule event differ")
    team = shot["player"] // 2
    for event in events[index + 1:]:
        if event["kind"] == "bounce":
            point = event["position"]
            error = math.hypot(point[0] - shot["target"][0], point[2] - shot["target"][2])
            return dict(outcome="legal landing", targetError=error if shot["planned"] else None)
        if event["kind"] == "hit":
            return dict(outcome="intercepted before landing", targetError=None)
        if event["kind"] in ("fault", "late volley fault"):
            owner = "opponent" if event["winner"] == team else "candidate"
            return dict(outcome=f"{owner} fault before landing / {event['fault']}", targetError=None)
        if event["kind"] == "training time limit - no point":
            return dict(outcome="truncated before landing", targetError=None)
    return dict(outcome="no recorded landing or interception", targetError=None)


def summarize(report):
    counts = Counter(); grouped = defaultdict(Counter); errors = []; total = 0
    for rally in report["rallies"]:
        expected = {i for i, event in enumerate(rally["events"])
                    if event["kind"] == "hit" and event["player"] // 2 == rally["candidateTeam"]}
        actual = [shot["eventIndex"] for shot in rally["shots"]]
        if set(actual) != expected or len(actual) != len(expected):
            raise ValueError("Missing, duplicate or wrong-team shot trace")
        for shot in rally["shots"]:
            result = classify_shot(shot, rally["events"]); total += 1
            counts[result["outcome"]] += 1
            grouped[(shot["phaseBefore"], shot["selectedShot"])][result["outcome"]] += 1
            if result["targetError"] is not None:
                if not math.isfinite(result["targetError"]): raise ValueError("Non-finite target error")
                errors.append(result["targetError"])
    measured_hits = sum(sum(g["metrics"]["legalHits"][g["candidateTeam"]*2:g["candidateTeam"]*2+2]) for g in report["games"])
    if measured_hits != total: raise ValueError("Trace and per-player legal-hit counts differ")
    return dict(candidateShots=total, outcomes=dict(counts), plannedLandingCount=len(errors),
                meanPlannedLandingError=sum(errors)/len(errors) if errors else None,
                byPhaseAndShot=[dict(phase=phase, shot=shot, outcomes=dict(value))
                                for (phase, shot), value in sorted(grouped.items())],
                limitation="Actual next-event outcomes only. A legal landing can still be followed by a lost rally.")


def summarize_execution(report):
    """Describe measured execution; do not infer the cause of a missed target.

    Spin signs and thresholds match the existing contact-training diagnostic.
    Missing fields in older traces are counted, never replaced with zeros.
    Multiple contacts remain separate physical events, not extra legal shots.
    """
    groups = {}

    def vector(value):
        if not isinstance(value, list) or len(value) != 3 or not all(
                isinstance(x, (int, float)) and math.isfinite(x) for x in value):
            raise ValueError("Invalid execution vector")
        return value

    def scalar(value):
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("Invalid execution scalar")
        return value

    def mean(values):
        return sum(values) / len(values) if values else None

    for rally in report["rallies"]:
        for shot in rally["shots"]:
            result = classify_shot(shot, rally["events"])
            selected = shot["selectedShot"]
            if not isinstance(selected, int) or not 0 <= selected < 9:
                raise ValueError("Invalid selected shot")
            row = groups.setdefault(selected, dict(shots=0, outcomes=Counter(), surfaces=Counter(),
                missingContactTraces=0, plannedSpeed=[], actualNormalSpeed=[], delay=[], depthError=[],
                spin=[], spinCorrect=0, missingSpin=0, verticalOutgoing=0))
            row["shots"] += 1; row["outcomes"][result["outcome"]] += 1
            plan_fields = ("plannedNormal", "paddleVelocity", "plannedSwing", "plannedImpactAt", "time")
            if shot["planned"] and all(name in shot for name in plan_fields):
                normal = vector(shot["plannedNormal"]); velocity = vector(shot["paddleVelocity"])
                length = math.sqrt(sum(x*x for x in normal))
                if length < 1e-6: raise ValueError("Missing planned normal direction")
                row["plannedSpeed"].append(scalar(shot["plannedSwing"]))
                row["actualNormalSpeed"].append(sum(n*v for n, v in zip(normal, velocity)) / length)
                row["delay"].append(scalar(shot["time"]) - scalar(shot["plannedImpactAt"]))
            if result["targetError"] is not None:
                landing = next(e for e in rally["events"][shot["eventIndex"]+1:] if e["kind"] == "bounce")
                point = vector(landing["position"]); target = vector(shot["target"])
                attack_sign = 1 if shot["player"] // 2 == 0 else -1
                row["depthError"].append((point[2] - target[2]) * attack_sign)
            contacts = shot.get("contacts")
            if not contacts:
                row["missingContactTraces"] += 1
                continue
            for contact in contacts:
                row["surfaces"][contact["surface"]] += 1
                if "outgoing" not in contact or "spin" not in contact:
                    row["missingSpin"] += 1
                    continue
                outgoing = vector(contact["outgoing"]); spin = vector(contact["spin"])
                horizontal_speed = math.hypot(outgoing[0], outgoing[2])
                if horizontal_speed < 1e-6:
                    row["verticalOutgoing"] += 1
                    continue
                # dot(spin, normalized cross(world up, outgoing velocity)).
                signed_spin = (spin[0]*outgoing[2] - spin[2]*outgoing[0]) / horizontal_speed
                row["spin"].append(signed_spin)
                correct = abs(signed_spin) < 25 if selected < 5 else signed_spin > 5 if selected < 7 else signed_spin < -5
                row["spinCorrect"] += int(correct)
    return dict(byShot=[dict(shot=shot, kind="flat" if shot < 5 else "topspin" if shot < 7 else "slice",
        shots=row["shots"], outcomes=dict(row["outcomes"]), contactSurfaces=dict(row["surfaces"]),
        missingContactTraces=row["missingContactTraces"], plannedExecutionSamples=len(row["plannedSpeed"]),
        meanPlannedNormalSpeed=mean(row["plannedSpeed"]), meanActualNormalSpeed=mean(row["actualNormalSpeed"]),
        meanContactDelaySeconds=mean(row["delay"]), legalPlannedLandings=len(row["depthError"]),
        meanDepthError=mean(row["depthError"]), spinSamples=len(row["spin"]),
        meanSignedSpin=mean(row["spin"]), spinDirectionOrFlatnessPassed=row["spinCorrect"],
        missingSpinContacts=row["missingSpin"], verticalOutgoingContacts=row["verticalOutgoing"])
        for shot, row in sorted(groups.items())],
        limitation="Contact-level spin signs use the existing diagnostic thresholds, not real-ball calibration. "
                   "Negative depth error means short. Timing and velocity differences do not prove their cause. "
                   "Multiple physical contacts can belong to one legal shot.")


def validate_contact_override(report, frozen):
    """Old reports have no override. New trials must disclose every change."""
    offset = report.get("flatPitchOffsetDegrees", 0)
    if not isinstance(offset, (int, float)) or not math.isfinite(offset) or abs(offset) > 6:
        raise ValueError("Invalid diagnostic contact override")
    if "candidateContactParameters" not in report:
        if offset != 0 or report.get("experimentalContactOverride", False):
            raise ValueError("Unreported candidate contact parameters")
        return
    if report.get("experimentalContactOverride") is not (offset != 0):
        raise ValueError("Contact override label differs")
    actual = report["candidateContactParameters"]
    if not isinstance(actual, list) or len(actual) != 3:
        raise ValueError("Missing candidate stroke parameters")
    for kind, parameters in enumerate(frozen["strokes"]):
        if set(actual[kind]) != set(parameters): raise ValueError("Contact parameter schema changed")
        for key, value in parameters.items():
            expected = value + offset if kind == 0 and key == "pitch" else value
            measured = actual[kind][key]
            if not isinstance(measured, (int, float)) or not math.isfinite(measured) or abs(measured - expected) > 1e-5:
                raise ValueError("Unreported contact parameter change")


def summarize_fault_context(report):
    """Separate incoming-ball body faults from faults after the team's own hit.

    This records event order, not the physical cause of a collision.
    A hit does not imply a legal landing or a successful return.
    """
    faults = Counter(); body = []
    for rally in report["rallies"]:
        team = rally["candidateTeam"]
        if type(team) is not int or team not in (0, 1):
            raise ValueError("Invalid candidate team")
        last_hit = None; bounced = False
        previous_time = -float("inf")
        for event in rally["events"]:
            time = event["time"]
            if type(time) not in (int, float) or not math.isfinite(time) or time < previous_time:
                raise ValueError("Invalid event time or order")
            previous_time = time
            if event["kind"] == "hit":
                if type(event["player"]) is not int or event["player"] not in range(4):
                    raise ValueError("Invalid legal hitter")
                last_hit = event; bounced = False
            elif event["kind"] == "bounce":
                bounced = True
            elif event["kind"] in ("fault", "late volley fault"):
                if type(event["winner"]) is not int or event["winner"] not in (0, 1):
                    raise ValueError("Unresolved fault ownership")
                if event["winner"] == team:
                    continue
                faults[event["fault"]] += 1
                if event["fault"] != "BodyContact":
                    continue
                player = event["player"]
                if type(player) is not int or player not in range(4) or player // 2 != team:
                    raise ValueError("Body fault player and losing team differ")
                relation = ("before recorded hit" if last_hit is None else
                            "after opponent hit" if last_hit["player"] // 2 != team else
                            "after own hit" if last_hit["player"] == player else "after teammate hit")
                body.append(dict(gameSeed=rally.get("gameSeed"), rally=rally.get("rally"),
                    player=player, context=relation, bounceSinceHit=bounced,
                    lastHitter=last_hit["player"] if last_hit else None,
                    secondsSinceHit=time - last_hit["time"] if last_hit else None))
    return dict(candidateFaults=dict(faults), bodyFaultsByContext=dict(Counter(x["context"] for x in body)),
                bodyFaults=body,
                limitation="Observed event order only. No causal claim about movement, shot choice or collision geometry.")


def main():
    from player_actor import ROOT, file_hash, source_hash
    from player_ppo import validate_motor_metrics
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path); args = parser.parse_args()
    report = json.loads(args.report.read_text())
    if report.get("version") != "player-contact-outcomes-v1" or report["status"] != "complete" or report["split"] != "development":
        raise ValueError("Not a completed contact diagnosis")
    if report["sourceHash"] != source_hash() or report["caseCount"] != 4 or len(report["games"]) != 4:
        raise ValueError("Source or diagnostic case count changed")
    for index, game in enumerate(report["games"]):
        if game["gameSeed"] != report["seedBase"] + index or game["candidateTeam"] != index % 2:
            raise ValueError("Diagnostic schedule changed")
        if game["reason"] not in ("game complete", "requested diagnostic limit"):
            raise ValueError("Incomplete physical rally in diagnosis")
    checks = {"actorHash": ROOT / report["actorPath"], "collectorHash": ROOT / report["collectorSnapshotPath"],
              "contactHash": ROOT / "Assets/Picklebot/Doubles/Models/contact.json",
              "opponentHash": ROOT / "Assets/Picklebot/Doubles/Models/teams.json",
              "baselineManifestHash": ROOT / "artifacts/player-agents/baseline-manifest.json",
              "protocolHash": ROOT / "config/player-agents/evaluation-v1.json"}
    for field, path in checks.items():
        if file_hash(path) != report[field]: raise ValueError("Changed diagnosis artifact: " + field)
    if "swingSourceHash" in report and file_hash(ROOT / report["swingSourcePath"]) != report["swingSourceHash"]:
        raise ValueError("Changed swing source snapshot")
    if "planSourceHash" in report and file_hash(ROOT / report["planSourcePath"]) != report["planSourceHash"]:
        raise ValueError("Changed contact-plan source snapshot")
    actor = json.loads(checks["actorHash"].read_text())
    validate_contact_override(report, json.loads(checks["contactHash"].read_text()))
    if (actor["sourceHash"] != report.get("actorTrainingSourceHash", report["sourceHash"])
            or report.get("historicalCandidate", False) != (actor["sourceHash"] != report["sourceHash"])):
        raise ValueError("Actor training source or historical label differs")
    validate_motor_metrics(report)
    print(json.dumps(dict(reportHash=file_hash(args.report),
                         flatPitchOffsetDegrees=report.get("flatPitchOffsetDegrees", 0),
                         experimentalContactOverride=report.get("experimentalContactOverride", False),
                         **summarize(report),
                         execution=summarize_execution(report),
                         faultContext=summarize_fault_context(report)), indent=2))


if __name__ == "__main__": main()

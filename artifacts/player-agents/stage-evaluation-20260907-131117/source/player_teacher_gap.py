"""Matched teacher/actor diagnostic. Development shadow labels never enter training."""
import argparse
from collections import Counter
import json
from pathlib import Path

from player_shot_quality import audit_trace, outcome, finite


def validate_pair(report, reference):
    expected = dict(version="player-teacher-gap-v1", status="complete", error=None,
                    split="development-diagnostic", fixtures=32, modes=2, seedBase=1199000,
                    expectedCases=64, physicsHz=240, decisionTicks=12, actionLatencyTicks=6,
                    maximumSeconds=6, sampledActor=False)
    if any(report.get(k) != v for k, v in expected.items()) or len(report.get("rows", [])) != 64:
        raise ValueError("Incomplete or changed teacher-gap schedule")
    for field in ("sourceHash", "configurationHash", "contactHash", "teamsHash", "protocolHash", "baselineHash"):
        if report[field] != reference[field]:
            raise ValueError("Teacher-gap inputs differ from the reference")
    ignored = {"index", "mode", "tracePath"}
    for fixture in range(32):
        teacher, actor = report["rows"][fixture*2:fixture*2+2]
        control = reference["rows"][fixture*11+9]
        for mode, row in enumerate((teacher, actor)):
            expected_row = dict(index=fixture*2+mode, fixture=fixture, mode=mode,
                                fixedCanonicalShot=-1 if mode == 0 else -2, gameSeed=1199000+fixture,
                                candidateTeam=fixture%2, profile="deep" if fixture < 16 else "kitchen", completeGame=False)
            if any(type(row.get(k)) is not type(v) or row.get(k) != v for k, v in expected_row.items()):
                raise ValueError("Changed case identity")
            if (type(row.get("legalHit")) is not bool or type(row.get("legalLanding")) is not bool
                    or (row["legalHit"], row["legalLanding"]) != outcome(row["events"], row["candidateTeam"])
                    or (row["outcome"] == "legal landing") != row["legalLanding"]):
                raise ValueError("Case outcome differs from events")
            if (type(row.get("ticks")) is not int or not 1 <= row["ticks"] <= 1441
                    or row.get("decisions") != 4*((row["ticks"]-1)//12+1)
                    or not finite(row.get("seconds")) or abs(row["seconds"]-row["ticks"]/240) > .0003
                    or row.get("metrics", {}).get("physicsSteps") != row["ticks"]):
                raise ValueError("Physical duration or decision count changed")
            for field in ("canonicalBall", "canonicalVelocity", "playerStarts", "initialObservations"):
                if row[field] != control[field]:
                    raise ValueError("Initial fixture changed")
        if ({k: v for k, v in teacher.items() if k not in ignored}
                != {k: v for k, v in control.items() if k not in ignored}):
            raise ValueError("Sampled-teacher physical control differs")


def audit(path, reference_path):
    import torch
    from player_actor import ROOT, Actor, file_hash, source_hash
    from player_shot_quality import audit as verify_reference
    from player_ppo import validate_motor_metrics
    from player_skill_retention import validate_replayed_action
    torch.set_num_threads(2)
    reference_audit = verify_reference(reference_path)
    reference = json.loads(reference_path.read_text())
    report = json.loads(path.read_text()); validate_pair(report, reference)
    if report["sourceHash"] != source_hash():
        raise ValueError("Runtime changed")
    for pk, hk in (("actorPath", "actorHash"), ("collectorSnapshotPath", "collectorHash")):
        artifact = (ROOT/report[pk]).resolve(); artifact.relative_to(ROOT)
        if file_hash(artifact) != report[hk]:
            raise ValueError("Changed actor or collector")
    actor, metadata = Actor.load_export(ROOT/report["actorPath"]); actor.eval()
    if (metadata["sourceHash"] != report["actorTrainingSourceHash"]
            or report["historicalCandidate"] != (metadata["sourceHash"] != report["sourceHash"])
            or metadata["configurationHash"] != report["configurationHash"]
            or metadata["contactModelHash"] != report["contactHash"]
            or metadata["protocolHash"] != report["protocolHash"]
            or metadata["baselineManifestHash"] != report["baselineHash"] or metadata["trainingSteps"] <= 0):
        raise ValueError("Actor provenance changed")
    validate_motor_metrics(dict(games=[dict(candidateTeam=team, metrics=r["metrics"])
                                      for r in report["rows"] for team in (0, 1)]))
    rows, replay = [], []
    for row in report["rows"]:
        trace = (ROOT/row["tracePath"]).resolve(); trace.relative_to(ROOT)
        if file_hash(trace) != row["traceHash"]:
            raise ValueError("Changed physical trace")
        def collect(decision):
            if row["mode"] == 1 and decision["player"]//2 == row["candidateTeam"]:
                replay.append(decision)
        measured = audit_trace(trace, row, allow_shadow=row["mode"] == 1, on_decision=collect)
        rows.append(dict(index=row["index"], **measured))
    with torch.no_grad():
        for offset in range(0, len(replay), 1024):
            batch = replay[offset:offset+1024]
            output = actor(torch.tensor([r["observation"] for r in batch], dtype=torch.float32))
            moves = actor.movement(output[:, :2]); shots = output[:, 3:].argmax(-1)
            for i, row in enumerate(batch):
                validate_replayed_action(row["action"], moves[i], bool(output[i, 2] >= 0), int(shots[i]))
    groups = []
    for profile in ("deep", "kitchen"):
        for team in (0, 1):
            subset = [r for r in report["rows"] if r["profile"] == profile and r["candidateTeam"] == team]
            groups.append(dict(profile=profile, candidateTeam=team,
                modes=[dict(mode=mode, cases=8, hits=sum(r["legalHit"] for r in subset if r["mode"] == mode),
                    legalLandings=sum(r["legalLanding"] for r in subset if r["mode"] == mode),
                    outcomes=dict(Counter(r["outcome"] for r in subset if r["mode"] == mode))) for mode in (0, 1)],
                teacherSuccessActorFailure=[r["fixture"] for r in subset if r["mode"] == 0 and r["legalLanding"]
                                           and not report["rows"][r["index"]+1]["legalLanding"]]))
    return dict(reportPath=str(path), reportHash=file_hash(path), referenceReportHash=reference_audit["reportHash"],
                actorHash=report["actorHash"], cases=64, exactTeacherControls=32,
                verifiedActorDecisions=len(replay), motorChecksPassed=True, groups=groups, traces=rows,
                limitation=report["limitation"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path); parser.add_argument("reference", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.report, args.reference), indent=2))

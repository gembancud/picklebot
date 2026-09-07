"""Audit physical selector cases and replay every choice from player-owned inputs."""
import argparse
from collections import Counter
import json
from pathlib import Path

import torch

from player_actor import Actor, ROOT, file_hash, source_hash
from player_skill_gate import SkillGate, load_experts, selected_outputs
from player_shot_quality import audit as audit_reference, audit_trace, finite
from player_teacher_gap import validate_pair
from player_ppo import validate_motor_metrics
from player_skill_retention import validate_replayed_action


def validate_selection(record, logit, choice, output):
    if (not finite(record.get("gateLogit")) or abs(record["gateLogit"]-float(logit)) > .0001
            or type(record.get("selectedExpert")) is not int or record["selectedExpert"] != int(choice)):
        raise ValueError("Recorded selector differs from own-observation inference")
    validate_replayed_action(record["action"], Actor.movement(output[:2]), bool(output[2] >= 0), int(output[3:].argmax()))


def audit(path, reference_path):
    torch.set_num_threads(2)
    reference_check = audit_reference(reference_path)
    reference = json.loads(reference_path.read_text()); report = json.loads(path.read_text())
    if report.get("version") != "player-skill-gate-probe-v1":
        raise ValueError("Expected an explicit selector experiment report")
    # The physical fixture/teacher-control contract is unchanged. This does not
    # pass a selector through the actor loader or claim it is a single actor.
    validate_pair(dict(report, version="player-teacher-gap-v1"), reference)
    if report["sourceHash"] != source_hash():
        raise ValueError("Runtime changed")
    for pk, hk in (("gatePath", "gateHash"), ("actorPath", "actorHash"), ("shortActorPath", "shortActorHash"),
                   ("collectorSnapshotPath", "collectorHash"), ("parityPath", "parityHash")):
        artifact = (ROOT/report[pk]).resolve(); artifact.relative_to(ROOT)
        if file_hash(artifact) != report[hk]:
            raise ValueError("Changed selector artifact: " + pk)
    gate, metadata = SkillGate.load_export(ROOT/report["gatePath"]); gate.eval()
    experts = load_experts(metadata)
    for key, field in (("sourceHash", "sourceHash"), ("configurationHash", "configurationHash"),
                       ("contactModelHash", "contactHash"), ("protocolHash", "protocolHash"), ("baselineManifestHash", "baselineHash")):
        if metadata[key] != report[field]:
            raise ValueError("Selector provenance changed: " + key)
    if (metadata["experts"][0]["sha256"] != report["actorHash"]
            or metadata["experts"][1]["sha256"] != report["shortActorHash"]
            or metadata["experts"][0]["trainingSourceHash"] != report["actorTrainingSourceHash"]
            or report["historicalCandidate"] is not (report["actorTrainingSourceHash"] != report["sourceHash"])):
        raise ValueError("Selector experts differ from the collector")
    folder = (ROOT/report["gatePath"]).parent
    if file_hash(folder/"plan.json") != metadata["planHash"] or metadata["trainingSteps"] <= 0:
        raise ValueError("Selector has no matching training plan")
    for name, digest in metadata["trainerSources"].items():
        snapshot = (folder/"trainer-source"/name).resolve(); snapshot.relative_to(folder.resolve())
        if file_hash(snapshot) != digest:
            raise ValueError("Selector trainer snapshot changed")
    for bank in metadata["sources"]:
        bank_path = (ROOT/bank["report"]).resolve(); bank_path.relative_to(ROOT)
        if file_hash(bank_path) != bank["reportHash"]:
            raise ValueError("Selector bank report changed")
        bank_report = json.loads(bank_path.read_text())
        if file_hash(ROOT/bank_report["dataPath"]) != bank["dataHash"]:
            raise ValueError("Selector bank data changed")
    validate_motor_metrics(dict(games=[dict(candidateTeam=t, metrics=r["metrics"]) for r in report["rows"] for t in (0, 1)]))
    traces = []; replay = []; choices = []
    for row in report["rows"]:
        trace = (ROOT/row["tracePath"]).resolve(); trace.relative_to(ROOT)
        if file_hash(trace) != row["traceHash"]:
            raise ValueError("Selector physical trace changed")
        previous = {}; row_choices = Counter(); row_switches = 0
        def collect(decision):
            nonlocal row_switches
            if row["mode"] == 1 and decision["player"]//2 == row["candidateTeam"]:
                replay.append(decision); player = decision["player"]; selected = decision.get("selectedExpert")
                if type(selected) is not int or selected not in (0, 1):
                    raise ValueError("Missing player selector choice")
                row_choices[selected] += 1
                if player in previous and previous[player] != selected: row_switches += 1
                previous[player] = selected
            elif "selectedExpert" in decision or "gateLogit" in decision:
                raise ValueError("Selector affected a control or opponent decision")
        traces.append(dict(index=row["index"], **audit_trace(trace, row, allow_shadow=row["mode"] == 1, on_decision=collect)))
        if row["mode"] == 1:
            choices.append(dict(fixture=row["fixture"], profile=row["profile"], counts=dict(row_choices), switches=row_switches))
    with torch.no_grad():
        for offset in range(0, len(replay), 1024):
            batch = replay[offset:offset+1024]
            logits, selected, outputs = selected_outputs(gate, experts, torch.tensor([d["observation"] for d in batch]))
            for i, decision in enumerate(batch): validate_selection(decision, logits[i], selected[i], outputs[i])
    groups = []
    for profile in ("deep", "kitchen"):
        for team in (0, 1):
            subset = [r for r in report["rows"] if r["profile"] == profile and r["candidateTeam"] == team]
            groups.append(dict(profile=profile, candidateTeam=team,
                modes=[dict(mode=m, cases=8, hits=sum(r["legalHit"] for r in subset if r["mode"] == m),
                            legalLandings=sum(r["legalLanding"] for r in subset if r["mode"] == m),
                            outcomes=dict(Counter(r["outcome"] for r in subset if r["mode"] == m))) for m in (0, 1)]))
    return dict(reportPath=str(path), reportHash=file_hash(path), referenceReportHash=reference_check["reportHash"],
                gateHash=report["gateHash"], cases=64, exactTeacherControls=32, verifiedSelectorDecisions=len(replay),
                motorChecksPassed=True, groups=groups, choices=choices, traces=traces, limitation=report["limitation"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path); parser.add_argument("reference", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.report, args.reference), indent=2))

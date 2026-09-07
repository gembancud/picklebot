"""Audit matched real serve-return controls and replay independent actor decisions."""
import argparse
from collections import Counter
import json
import math
import numpy as np
from pathlib import Path
import torch
from player_actor import Actor, ROOT, file_hash, source_hash
from player_ppo import log_probability, validate_motor_metrics
from player_skill_retention import validate_replayed_action


def event_outcome(events, server, receiver):
    served = landed = hit = returned = False
    for event in events:
        if event["kind"] == "serve":
            if served or event["player"] != server: raise ValueError("Invalid serve event")
            served = True
        elif event["kind"] == "hit":
            if not landed or hit or event["player"] != receiver: raise ValueError("Invalid first return event")
            hit = True
        elif event["kind"] == "bounce":
            if not served: raise ValueError("Bounce before serve")
            if hit: returned = True
            else: landed = True
    return dict(serveLanded=landed, returnHit=hit, returnLanded=returned)


def validate_replacement(original, teacher, action, mode, is_receiver):
    if mode not in range(5): raise ValueError("Unknown action control")
    expected = dict(original)
    if mode < 2 and teacher is not None: raise ValueError("Unexpected teacher input")
    if mode >= 2:
        if teacher is None or set(teacher) != set(original): raise ValueError("Missing teacher action")
        if (type(teacher["attempt"]) is not bool or type(teacher["shot"]) is not int
                or not 0 <= teacher["shot"] <= 8
                or any(not math.isfinite(teacher[k]) for k in ("moveX","moveZ"))
                or teacher["moveX"]**2+teacher["moveZ"]**2 > 1.00001):
            raise ValueError("Invalid teacher action")
    if mode == 2 and original != teacher: raise ValueError("Teacher control differs")
    if is_receiver and mode == 3:
        expected.update(moveX=teacher["moveX"], moveZ=teacher["moveZ"])
    if is_receiver and mode == 4: expected["shot"] = teacher["shot"]
    if action != expected: raise ValueError("Action replacement changed an unselected component")


def validate_sample_action(sample, action):
    """PlayerDecisionLoop validates the already bounded actor action a second time."""
    if set(sample) != set(action) or any(sample[k] != action[k] for k in ("attempt", "shot")):
        raise ValueError("Recorded action differs from actor sample")
    if sample == action: return
    values = torch.tensor([sample["moveX"], sample["moveZ"]], dtype=torch.float32)
    norm = values.square().sum().sqrt()
    # Only accept the float32 unit-circle normalization case, not arbitrary drift.
    if not torch.isfinite(values).all() or not 1 <= float(norm) <= 1.000001:
        raise ValueError("Recorded action differs from actor sample")
    normalized = values / norm
    if any(not math.isfinite(action[k]) or abs(action[k]-float(normalized[i])) > 0.0000002
           for i,k in enumerate(("moveX", "moveZ"))):
        raise ValueError("Recorded action differs from actor sample")


def validate_contact_execution(row):
    execution = row.get("returnContactExecution")
    if not row["returnHit"]:
        if execution is not None: raise ValueError("Contact execution without a hit")
        return
    if execution is None: raise ValueError("Missing contact execution")
    before, after = execution["before"], execution["after"]
    hit = next(e for e in row["events"] if e["kind"] == "hit")
    if (after["tick"] != before["tick"]+1 or abs(after["time"]-before["time"]-1/240)>.00001
            or abs(after["time"]-hit["time"])>.00001): raise ValueError("Contact execution timing differs")
    for state in (before,after):
        for key in ("time","impactAt","phase","swingSpeed"):
            if not math.isfinite(state[key]): raise ValueError("Non-finite contact state")
        if abs(state["phase"]-(state["time"]-state["impactAt"]))>.00001: raise ValueError("Contact phase differs")
        for key in ("impact","normal","bodyPosition","bodyVelocity","paddlePosition","paddleVelocity",
                    "paddleNormal","requestedMovement","appliedMovement","ball","ballVelocity"):
            if len(state[key])!=3 or not all(math.isfinite(v) for v in state[key]): raise ValueError("Invalid contact vector")
        if type(state["paddleStepFeasible"]) is not bool or not state["paddleStepFeasible"]:
            raise ValueError("Infeasible contact paddle step")


def validate_window_action(decision, mode, receiver):
    original, teacher, action = (decision[k] for k in ("original", "teacherAction", "action"))
    state = decision["windowState"]
    if (type(state["planned"]) is not bool or type(state["hits"]) is not int
            or not all(math.isfinite(state[k]) for k in ("time", "impactAt"))):
        raise ValueError("Invalid window state")
    at, now = np.float32(state["impactAt"]), np.float32(state["time"])
    expected_gate = bool(decision["player"] == receiver and state["hits"] == 1 and state["planned"]
                         and now >= at-np.float32(.20) and now <= at+np.float32(.055))
    if type(decision["controlWindow"]) is not bool or decision["controlWindow"] != expected_gate:
        raise ValueError("Wrong movement control window")
    # Validate the teacher and ordinary actor controls using the existing strict checks.
    validate_replacement(original, teacher, original, mode, False)
    expected = dict(original)
    if expected_gate and mode == 3: expected.update(moveX=0, moveZ=0)
    if expected_gate and mode == 4: expected.update(moveX=teacher["moveX"], moveZ=teacher["moveZ"])
    if action != expected: raise ValueError("Window control changed an unselected action")


def contact_point_metrics(row):
    validate_contact_execution(row)
    if not row["returnHit"]: return None
    state = row["returnContactExecution"]; a, b = state["before"], state["after"]
    def vector(record,key):
        v=np.asarray(record[key],dtype=np.float64)
        if v.shape!=(3,) or not np.isfinite(v).all(): raise ValueError("Invalid contact point vector")
        return v
    velocity = vector(b,"paddleVelocity")
    angular = vector(b,"paddleAngularVelocity")
    contact_velocity = velocity+np.cross(angular,vector(state,"point")-vector(b,"paddlePosition"))
    if np.max(np.abs(contact_velocity-vector(state,"pointVelocity")))>.0001:
        raise ValueError("Contact point velocity replay differs")
    normal = vector(b,"normal"); physical_normal=vector(state,"contactNormal")
    old_hand = vector(a,"hand")-vector(a,"shoulder"); reach=float(np.linalg.norm(old_hand))
    radial=old_hand/max(reach,1e-10)
    body_velocity=vector(b,"bodyVelocity")
    stopped_limit=math.sqrt(40*max(0,.60-reach))+float(body_velocity@radial)
    return dict(fixture=row["fixture"],mode=row["mode"],fault=row["fault"],phaseSeconds=b["phase"],
        selectedShot=b["selectedShot"],plannedSwingSpeed=b["swingSpeed"],
        centreNormalSpeed=float(velocity@normal),pointPlannedNormalSpeed=float(contact_velocity@normal),
        pointPhysicalNormalSpeed=float(contact_velocity@physical_normal),angularSpeed=float(np.linalg.norm(angular)),
        rotationNormalContribution=float((contact_velocity-velocity)@normal),
        handReachBefore=reach,handReachAfter=float(np.linalg.norm(vector(b,"hand")-vector(b,"shoulder"))),
        paddleAcceleration=float(np.linalg.norm(velocity-vector(a,"paddleVelocity"))*240),
        stoppedPostureBrakingSlack=stopped_limit-float(velocity@radial))


def audit(path):
    torch.set_num_threads(2)
    report = json.loads(path.read_text())
    action_probe = report.get("version") == "player-serve-action-probe-v1"
    contact_probe = report.get("version") == "player-serve-contact-probe-v1"
    window_probe = report.get("version") == "player-serve-window-probe-v1"
    mode_count = 5 if action_probe or window_probe else 3
    stem = "player-serve-window-probe" if window_probe else "player-serve-action-probe" if action_probe else "player-serve-contact-probe" if contact_probe else "player-serve-return-probe"
    collector = "scripts/" + stem + ".cs"
    expected = dict(version=stem+"-v1", status="complete", error=None,
        split="development-diagnostic", fixtures=12, modes=mode_count, expectedCases=12*mode_count, seedBase=1198000,
        physicsHz=240, decisionTicks=12, actionLatencyTicks=6, maximumSeconds=12)
    if any(report.get(k) != v for k, v in expected.items()) or len(report["rows"]) != 12*mode_count:
        raise ValueError("Incomplete or changed serve-return probe")
    if window_probe and (report.get("windowBeforeSeconds")!=.2 or report.get("windowAfterSeconds")!=.055):
        raise ValueError("Window bounds changed")
    if report["sourceHash"] != source_hash(): raise ValueError("Runtime changed")
    for name, digest in report["frozen"].items():
        if file_hash(ROOT/name) != digest: raise ValueError("Probe input changed")
    if file_hash(ROOT/report["collectorSnapshotPath"]) != report["frozen"][collector]:
        raise ValueError("Collector snapshot changed")
    actor, metadata = Actor.load_export(ROOT/report["actorPath"])
    if (report["actorHash"] != file_hash(ROOT/report["actorPath"])
            or metadata["sourceHash"] != report["sourceHash"]
            or metadata["configurationHash"] != report["configurationHash"]):
        raise ValueError("Actor provenance differs")
    reference = None
    if action_probe or contact_probe or window_probe:
        reference_path = ROOT/report["referencePath"]
        reference = json.loads(reference_path.read_text())
        if (reference.get("version") != "player-serve-return-probe-v1"
                or file_hash(reference_path) != report["referenceHash"]
                or reference["actorHash"] != report["actorHash"]):
            raise ValueError("Wrong original serve control")
        audit(reference_path)
    validate_motor_metrics(dict(opponentMode="older actor / sampled", games=[
        dict(candidateTeam=0, metrics=r["metrics"]) for r in report["rows"]]))
    replay = []; teacher_decisions = 0; serve_error = 0.; point_metrics = []; controlled_decisions = [0]*mode_count
    for fixture in range(12):
        controls = report["rows"][fixture*mode_count:fixture*mode_count+mode_count]
        for mode, row in enumerate(controls):
            if (row["index"] != fixture*mode_count+mode or row["fixture"] != fixture or row["mode"] != mode
                    or row["seed"] != 1198000+fixture or row["server"] != fixture//3
                    or row["receiver"]//2 == row["server"]//2
                    or row["initial"] != controls[0]["initial"] or row["setupSteps"] != controls[0]["setupSteps"]):
                raise ValueError("Matched starting state differs")
            if reference is not None and mode < 3:
                original_control = reference["rows"][fixture*3+mode]
                for key in ("initial","setupSteps","serveContact","events","contacts","ticks","decisions"):
                    if row[key] != original_control[key]: raise ValueError("Original control changed: " + key)
            if not 1 <= row["ticks"] <= 2881 or abs(row["seconds"]-row["ticks"]/240) > .001:
                raise ValueError("Physical duration differs")
            flags = event_outcome(row["events"], row["server"], row["receiver"])
            if any(row[k] != v for k, v in flags.items()): raise ValueError("Outcome differs from rule events")
            if contact_probe: validate_contact_execution(row)
            if window_probe: point_metrics.append(contact_point_metrics(row))
            a, b = controls[0]["serveContact"], row["serveContact"]
            if a is None or b is None: raise ValueError("Missing physical serve")
            differences = [abs(a["time"]-b["time"])] + [abs(x-y) for key in ("ball", "velocity") for x,y in zip(a[key],b[key])]
            serve_error = max(serve_error, *differences)
            trace = ROOT/row["tracePath"]
            if file_hash(trace) != row["traceHash"]: raise ValueError("Decision trace changed")
            decisions = [json.loads(line) for line in trace.read_text().splitlines()]
            if len(decisions) != row["decisions"]: raise ValueError("Decision count differs")
            previous = [-1]*4
            for decision in decisions:
                player, tick = decision["player"], decision["observationTick"]
                if (player not in range(4) or len(decision["observation"]) != 54 or tick % 12
                        or decision["applyTick"] != tick+6 or tick <= previous[player]
                        or not all(math.isfinite(v) for v in decision["observation"])):
                    raise ValueError("Invalid independent observation or action timing")
                previous[player] = tick
                if action_probe or window_probe:
                    if window_probe:
                        validate_window_action(decision,mode,row["receiver"])
                        if decision["controlWindow"] and mode>=3: controlled_decisions[mode]+=1
                    else: validate_replacement(decision["original"],decision["teacherAction"],decision["action"],mode,player==row["receiver"])
                    decision = dict(decision, action=decision["original"])
                if mode == 2:
                    if decision["sample"] is not None: raise ValueError("Teacher was labelled as actor")
                    teacher_decisions += 1
                else:
                    validate_sample_action(decision["sample"]["action"], decision["action"])
                    replay.append((mode, decision))
    if not math.isfinite(serve_error) or serve_error > .0001: raise ValueError("Physical serve controls differ")
    maximum_error = 0.
    with torch.no_grad():
        for start in range(0, len(replay), 1024):
            batch = replay[start:start+1024]; rows = [r for mode,r in batch]
            obs = torch.tensor([r["observation"] for r in rows])
            raw = torch.tensor([[r["sample"]["rawX"], r["sample"]["rawZ"]] for r in rows])
            hit = torch.tensor([float(r["action"]["attempt"]) for r in rows])
            shot = torch.tensor([r["action"]["shot"] for r in rows])
            logp, _ = log_probability(actor, obs, raw, hit, shot)
            expected_logp = torch.tensor([r["sample"]["logProbability"] for r in rows])
            maximum_error = max(maximum_error, float((logp-expected_logp).abs().max()))
            output = actor(obs); moves = actor.movement(raw)
            for i, (mode, row) in enumerate(batch):
                validate_replayed_action(row["action"], moves[i], bool(hit[i]), int(shot[i]))
                if mode != 1:
                    validate_replayed_action(row["action"], actor.movement(output[i,:2]), bool(output[i,2]>=0), int(output[i,3:].argmax()))
    if not math.isfinite(maximum_error) or maximum_error > .001: raise ValueError("Actor likelihood replay failed")
    groups = []
    for mode in range(mode_count):
        rows = [r for r in report["rows"] if r["mode"] == mode]
        groups.append(dict(mode=mode, cases=len(rows), serveLandings=sum(r["serveLanded"] for r in rows),
            returnHits=sum(r["returnHit"] for r in rows), returnLandings=sum(r["returnLanded"] for r in rows),
            faults=dict(Counter(r["fault"] for r in rows)),
            seats=[dict(server=s, hits=sum(r["returnHit"] for r in rows if r["server"]==s),
                        landings=sum(r["returnLanded"] for r in rows if r["server"]==s)) for s in range(4)]))
    return dict(reportPath=str(path), reportHash=file_hash(path), actorHash=report["actorHash"], sourceHash=report["sourceHash"],
        cases=12*mode_count, matchedOriginalControlCases=36 if action_probe or contact_probe or window_probe else None,
        referenceReportHash=report.get("referenceHash"),
        matchedPhysicalServeMaximumError=serve_error, actorDecisionsReplayed=len(replay),
        actorLogProbabilityMaximumError=maximum_error, teacherDecisions=teacher_decisions,
        motorChecksPassed=True, groups=groups, wallSeconds=report["wallSeconds"], limitation=report["limitation"],
        **(dict(contactPointMetrics=point_metrics,controlledDecisions=controlled_decisions,
                motorDiagnosticLimitation="Stopped-posture braking slack is a reconstructed candidate bound, not a record of which projection trial executed.") if window_probe else {}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("report", type=Path)
    print(json.dumps(audit(parser.parse_args().report), indent=2))

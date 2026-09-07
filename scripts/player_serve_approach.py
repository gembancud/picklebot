"""Compare audited receiver trajectories before either side makes a return contact.

Teacher trajectories are diagnostic controls, not labels for the actor's own state.
"""
import argparse
import json
import math
from pathlib import Path
import torch
from player_actor import Actor, ROOT, file_hash
from player_serve_return import audit as audit_returns


def geometry(observation):
    if len(observation) != 54 or not all(math.isfinite(x) for x in observation):
        raise ValueError("Expected 54 finite player observations")
    o = observation
    feet = [o[0]*4.2, 0., o[1]*8.1]
    ball = [feet[0]+o[4]*8.4, o[5]*3, feet[2]+o[6]*16.2]
    paddle = [feet[0]+o[25], o[26]*2, feet[2]+o[27]]
    return dict(feet=feet, ball=ball, paddle=paddle,
                paddleRelative=[o[25], o[26]*2, o[27]])


def paired_prefix(actor_rows, teacher_rows, stop_seconds):
    teacher = {r["observationTick"]: r for r in teacher_rows}
    pairs = [(r, teacher[r["observationTick"]]) for r in actor_rows
             if r["observationTick"] in teacher
             and r["observationTick"]/240 < stop_seconds
             and r["observation"][40] == 1
             and teacher[r["observationTick"]]["observation"][40] == 1]
    if not pairs:
        raise ValueError("No common pre-contact serve-flight decisions")
    maximum = max(math.dist(geometry(a["observation"])["ball"],
                            geometry(t["observation"])["ball"]) for a,t in pairs)
    if maximum > .001:
        raise ValueError("Pre-contact ball paths differ")
    return pairs, maximum


def analyze(path):
    verified = audit_returns(path)
    report = json.loads(path.read_text())
    model, _ = Actor.load_export(ROOT/report["actorPath"])
    results = []
    for fixture in range(12):
        teacher = report["rows"][fixture*3+2]
        receiver = teacher["receiver"]
        def decisions(row):
            return [r for r in map(json.loads, (ROOT/row["tracePath"]).read_text().splitlines())
                    if r["player"] == receiver]
        teacher_rows = decisions(teacher)
        for mode in (0, 1):
            actor = report["rows"][fixture*3+mode]
            stop = min(e["time"] for row in (actor,teacher) for e in row["events"]
                       if e["kind"] in ("hit", "fault"))
            pairs, ball_error = paired_prefix(decisions(actor), teacher_rows, stop)
            last_tick = pairs[-1][0]["observationTick"]
            window = [(a,t) for a,t in pairs if a["observationTick"] >= last_tick-48]
            a,t = pairs[-1]; ag,tg = geometry(a["observation"]),geometry(t["observation"])
            with torch.no_grad():
                tx = torch.tensor([t["observation"] for a,t in window],dtype=torch.float32)
                outputs = model(tx)
                teacher_moves = torch.tensor([[t["action"]["moveX"],t["action"]["moveZ"]] for a,t in window])
                forced_error = float((model.movement(outputs[:,:2])-teacher_moves).square().mean())
                shot_agreement = float((outputs[:,3:].argmax(-1) == torch.tensor([t["action"]["shot"] for a,t in window])).float().mean())
            results.append(dict(fixture=fixture,mode=mode,server=actor["server"],receiver=receiver,
                actorHit=actor["returnHit"],actorLanding=actor["returnLanded"],actorFault=actor["fault"],
                teacherHit=teacher["returnHit"],teacherLanding=teacher["returnLanded"],
                pairedDecisions=len(pairs),maximumBallPathError=ball_error,lastCommonTick=last_tick,
                lastCommonSeconds=last_tick/240,stopSeconds=stop,
                actorGeometry=ag,teacherGeometry=tg,feetDistance=math.dist(ag["feet"],tg["feet"]),
                forwardFeetDifference=ag["feet"][2]-tg["feet"][2],
                lateralFeetDifference=ag["feet"][0]-tg["feet"][0],
                actorAction=a["action"],teacherAction=t["action"],
                teacherStateMovementMSE=forced_error,teacherStateShotAgreement=shot_agreement))
    return dict(reportPath=str(path),reportHash=file_hash(path),actorHash=report["actorHash"],
        sourceHash=report["sourceHash"],analysisSourceHash=file_hash(__file__),
        verifiedActorDecisions=verified["actorDecisionsReplayed"],motorChecksPassed=verified["motorChecksPassed"],
        rows=results,limitation="All geometry is in each receiver's canonical metres. Positive Z is forward toward the opponent. Last common decision is before either return contact or fault, not the exact contact instant. Paddle position is its transform, not collision-surface clearance. Teacher-state prediction error is not an optimal-action label for the actor's different state. Association does not isolate movement from shot choice. Diagnostic data must not enter training.")


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("report",type=Path)
    print(json.dumps(analyze(parser.parse_args().report),indent=2))

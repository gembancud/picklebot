"""Audit paired teacher shot choices. Hindsight coverage is not learned performance."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def vector(value, size=3):
    if not isinstance(value, list) or len(value) != size or not all(finite(v) for v in value):
        raise ValueError("Invalid diagnostic vector")
    return value


def outcome(events, team):
    hit = next((i for i, e in enumerate(events) if e["kind"] == "hit" and e["player"]//2 == team), None)
    if hit is None:
        return False, False
    for event in events[hit+1:]:
        if event["kind"] == "bounce":
            return True, (0 if event["position"][2] < 0 else 1) != team
        if event["kind"] in ("hit", "fault", "late volley fault"):
            return True, False
    return True, False


def summarize(report):
    expected = dict(version="player-shot-quality-v1", status="complete", error=None,
                    split="development-diagnostic", fixtures=32, modes=11, seedBase=1199000,
                    expectedCases=352, physicsHz=240, decisionTicks=12, actionLatencyTicks=6, maximumSeconds=6)
    if any(report.get(k) != v for k, v in expected.items()) or len(report.get("rows", [])) != 352:
        raise ValueError("Incomplete or changed shot-quality schedule")
    rows = report["rows"]
    initial_keys = ("canonicalBall", "canonicalVelocity", "playerStarts", "initialObservations")
    ignored = {"index", "mode", "tracePath"}
    opportunities = []
    for fixture in range(32):
        cases = rows[fixture*11:fixture*11+11]
        for mode, row in enumerate(cases):
            identity = dict(index=fixture*11+mode, fixture=fixture, mode=mode,
                            fixedCanonicalShot=-1 if mode == 9 else 0 if mode == 10 else mode,
                            gameSeed=1199000+fixture, candidateTeam=fixture%2,
                            profile="deep" if fixture < 16 else "kitchen", completeGame=False)
            if any(type(row.get(k)) is not type(v) or row.get(k) != v for k, v in identity.items()):
                raise ValueError("Changed case identity")
            if any(row[k] != cases[0][k] for k in initial_keys):
                raise ValueError("Shot choices do not share the same initial state")
            vector(row["canonicalBall"]); vector(row["canonicalVelocity"])
            if len(row["playerStarts"]) != 4 or len(row["initialObservations"]) != 4:
                raise ValueError("Missing player state")
            for start, observation in zip(row["playerStarts"], row["initialObservations"]):
                vector(start); vector(observation, 54)
            hit, landing = outcome(row["events"], row["candidateTeam"])
            if (type(row.get("legalHit")) is not bool or type(row.get("legalLanding")) is not bool
                    or row["legalHit"] != hit or row["legalLanding"] != landing
                    or (row["outcome"] == "legal landing") != landing):
                raise ValueError("Outcome disagrees with rule events")
            if type(row.get("ticks")) is not int or not 1 <= row["ticks"] <= 1441:
                raise ValueError("Invalid physical duration")
            if row.get("decisions") != 4*((row["ticks"]-1)//12+1):
                raise ValueError("Decision count changed")
            if not finite(row.get("seconds")) or abs(row["seconds"]-row["ticks"]/240) > .0003:
                raise ValueError("Changed elapsed physical time")
            if row.get("metrics", {}).get("physicsSteps") != row["ticks"]:
                raise ValueError("Motor and physical step counts differ")
        if ({k: v for k, v in cases[0].items() if k not in ignored}
                != {k: v for k, v in cases[10].items() if k not in ignored}):
            raise ValueError("Repeated fixed-zero control differs")
        legal = [r["mode"] for r in cases[:9] if r["legalLanding"]]
        opportunities.append(dict(fixture=fixture, profile=cases[0]["profile"], team=fixture%2,
                                  fixedLegalShots=legal, fixedZeroLegal=cases[0]["legalLanding"],
                                  sampledTeacherLegal=cases[9]["legalLanding"]))
    groups = []
    for profile in ("deep", "kitchen"):
        for team in (0, 1):
            subset = [r for r in rows if r["profile"] == profile and r["candidateTeam"] == team]
            matched = [o for o in opportunities if o["profile"] == profile and o["team"] == team]
            groups.append(dict(profile=profile, candidateTeam=team, fixtures=len(matched),
                byMode=[dict(mode=mode, hits=sum(r["legalHit"] for r in subset if r["mode"] == mode),
                    legalLandings=sum(r["legalLanding"] for r in subset if r["mode"] == mode),
                    outcomes=dict(Counter(r["outcome"] for r in subset if r["mode"] == mode))) for mode in range(10)],
                hindsightAnyFixedLanding=sum(bool(o["fixedLegalShots"]) for o in matched),
                sampledMissButFixedSuccess=[o["fixture"] for o in matched if not o["sampledTeacherLegal"] and o["fixedLegalShots"]],
                zeroMissButOtherSuccess=[o["fixture"] for o in matched if not o["fixedZeroLegal"] and o["fixedLegalShots"]]))
    return dict(cases=352, exactRepeatedControls=32, groups=groups, opportunities=opportunities,
                limitation=report.get("limitation"))


def audit_trace(path, row, *, allow_shadow=False, on_decision=None):
    steps, decisions = 0, 0
    previous_time = None
    previous = [[0., 0., 0.] for _ in range(4)]
    previous_paddle = [[0., 0., 0.] for _ in range(4)]
    peaks = dict(bodySpeed=0., bodyAcceleration=0., paddleSpeed=0., paddleAcceleration=0., reach=0., angularSpeed=0.)
    limits = dict(bodySpeed=3.801, bodyAcceleration=14.05, paddleSpeed=12.01, paddleAcceleration=100.1, reach=.6201, angularSpeed=12.01)
    last_events = None
    pending_shadow = None
    shadow = dict(decisions=0, movementSquaredError=0., attemptAgreements=0,
                  teacherHitActorLeave=0, teacherLeaveActorHit=0, shotAgreements=0)
    with path.open() as stream:
        for line in stream:
            record = json.loads(line)
            if pending_shadow is not None and record["type"] != "shadow-teacher":
                raise ValueError("Missing diagnostic shadow label")
            if record["type"] == "shadow-teacher":
                if not allow_shadow or pending_shadow is None:
                    raise ValueError("Unexpected shadow label")
                prior = pending_shadow; pending_shadow = None
                if record["player"] != prior["player"] or record["tick"] != prior["tick"]:
                    raise ValueError("Shadow label belongs to another player or time")
                a, label = prior["action"], record["action"]
                if (not finite(label["moveX"]) or not finite(label["moveZ"])
                        or math.hypot(label["moveX"], label["moveZ"]) > 1.00001
                        or type(label["attempt"]) is not bool or type(label["shot"]) is not int
                        or not 0 <= label["shot"] <= 8):
                    raise ValueError("Invalid shadow action")
                shadow["decisions"] += 1
                shadow["movementSquaredError"] += (a["moveX"]-label["moveX"])**2 + (a["moveZ"]-label["moveZ"])**2
                shadow["attemptAgreements"] += a["attempt"] == label["attempt"]
                shadow["teacherHitActorLeave"] += label["attempt"] and not a["attempt"]
                shadow["teacherLeaveActorHit"] += a["attempt"] and not label["attempt"]
                shadow["shotAgreements"] += a["shot"] == label["shot"]
                continue
            if record["type"] == "decision":
                player = decisions % 4
                if (record["player"] != player or record["tick"] != steps or steps % 12 != 0
                        or record["applyTick"] != steps+6):
                    raise ValueError("Changed decision ownership or timing")
                observation = vector(record["observation"], 54)
                if steps == 0 and observation != row["initialObservations"][player]:
                    raise ValueError("Initial observation differs from the actual decision")
                a = record["action"]
                if (not finite(a["moveX"]) or not finite(a["moveZ"])
                        or math.hypot(a["moveX"], a["moveZ"]) > 1.00001
                        or type(a["attempt"]) is not bool or type(a["shot"]) is not int or not 0 <= a["shot"] <= 8):
                    raise ValueError("Invalid player action")
                if player//2 != row["candidateTeam"]:
                    if a != dict(moveX=0., moveZ=0., attempt=False, shot=0):
                        raise ValueError("Stationary opponent action changed")
                elif a["attempt"] and row["fixedCanonicalShot"] >= 0 and a["shot"] != row["fixedCanonicalShot"]:
                    raise ValueError("Fixed shot was not executed in canonical coordinates")
                if on_decision is not None:
                    on_decision(record)
                if allow_shadow and player//2 == row["candidateTeam"]:
                    pending_shadow = record
                decisions += 1
                continue
            if record["type"] != "step" or record["tick"] != steps+1:
                raise ValueError("Changed physical step sequence")
            if decisions != 4*(steps//12+1):
                raise ValueError("Missing player decisions before physics")
            steps += 1
            if not finite(record["time"]) or (previous_time is not None and abs(record["time"]-previous_time-1/240) > .000002):
                raise ValueError("Changed physics timestep")
            previous_time = record["time"]
            for name in ("ball", "velocity", "spin"):
                vector(record[name])
            if len(record["players"]) != 4:
                raise ValueError("Missing player motor trace")
            for i, p in enumerate(record["players"]):
                for name in ("position", "velocity", "paddle", "paddleVelocity", "angularVelocity", "hand", "shoulder"):
                    vector(p[name])
                vector(p["rotation"], 4)
                values = dict(bodySpeed=math.dist(p["velocity"], [0, 0, 0]),
                    bodyAcceleration=math.dist(p["velocity"], previous[i])*240,
                    paddleSpeed=math.dist(p["paddleVelocity"], [0, 0, 0]),
                    paddleAcceleration=math.dist(p["paddleVelocity"], previous_paddle[i])*240,
                    reach=math.dist(p["hand"], p["shoulder"]), angularSpeed=math.dist(p["angularVelocity"], [0, 0, 0]))
                for key, value in values.items():
                    if value > limits[key]:
                        raise ValueError(f"Case {row['index']}, step {steps}, player {i}: {key}={value}")
                    peaks[key] = max(peaks[key], value)
                previous[i] = p["velocity"]; previous_paddle[i] = p["paddleVelocity"]
            last_events = record["events"]
    if pending_shadow is not None or steps != row["ticks"] or decisions != row["decisions"] or last_events != row["events"]:
        raise ValueError("Trace and case summary differ")
    return dict(steps=steps, decisions=decisions, peaks=peaks, shadow=shadow)


def audit(path):
    from player_actor import ROOT, file_hash, source_hash
    from player_ppo import validate_motor_metrics
    report = json.loads(path.read_text()); result = summarize(report)
    if report["sourceHash"] != source_hash():
        raise ValueError("Runtime source changed")
    for pk, hk in (("collectorSnapshotPath", "collectorHash"), ("contactPath", "contactHash"),
                   ("teamsPath", "teamsHash"), ("protocolPath", "protocolHash"), ("baselinePath", "baselineHash")):
        source = (ROOT / report[pk]).resolve(); source.relative_to(ROOT)
        if file_hash(source) != report[hk]:
            raise ValueError("Changed diagnostic input or snapshot")
    validate_motor_metrics(dict(games=[dict(candidateTeam=team, metrics=row["metrics"])
                                      for row in report["rows"] for team in (0, 1)]))
    steps, decisions, peaks = 0, 0, {}
    for row in report["rows"]:
        trace = (ROOT / row["tracePath"]).resolve(); trace.relative_to(ROOT)
        if file_hash(trace) != row["traceHash"]:
            raise ValueError("Physical trace changed")
        measured = audit_trace(trace, row)
        steps += measured["steps"]; decisions += measured["decisions"]
        for key, value in measured["peaks"].items():
            peaks[key] = max(peaks.get(key, 0.), value)
    return dict(reportPath=str(path), reportHash=file_hash(path), verifiedSteps=steps,
                verifiedDecisions=decisions, measuredPeaks=peaks, motorChecksPassed=True, **result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.report), indent=2))

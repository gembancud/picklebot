"""Describe saved match contacts. Never infer exact impact pose from a post-step pose."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import subprocess
import sys

from player_contact_outcomes import classify_shot


def vector(value):
    if (not isinstance(value, list) or len(value) != 3
            or any(type(v) not in (float, int) or not math.isfinite(v) for v in value)):
        raise ValueError("Invalid contact geometry vector")
    return value


def scalar(value):
    if type(value) not in (float, int) or not math.isfinite(value):
        raise ValueError("Invalid contact geometry scalar")
    return value


def sub(a, b):
    return [x-y for x, y in zip(a, b)]


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def unit(v):
    length = math.sqrt(dot(v, v))
    if length < 1e-8:
        raise ValueError("Missing direction")
    return [x/length for x in v]


def distribution(values):
    if not values:
        return None
    values = sorted(values)
    def percentile(fraction):
        index = (len(values)-1)*fraction
        low, high = math.floor(index), math.ceil(index)
        return values[low]*(high-index) + values[high]*(index-low) if low != high else values[low]
    return dict(count=len(values), minimum=values[0], p10=percentile(.1), median=percentile(.5),
                p90=percentile(.9), maximum=values[-1], mean=sum(values)/len(values))


def analyze(report):
    rows, skipped = [], Counter()
    for rally in report["rallies"]:
        for shot in rally["shots"]:
            outcome = classify_shot(shot, rally["events"])["outcome"]
            if not shot["planned"]:
                skipped["unplanned"] += 1
                continue
            if len(shot.get("contacts", [])) != 1:
                skipped["not exactly one contact"] += 1
                continue
            contact = shot["contacts"][0]
            paddle = vector(shot["paddlePosition"])
            grip = sub(vector(shot["hand"]), paddle)
            # GripLocal = (0, -.1397, 0). This recovers only the local Y axis.
            if abs(math.sqrt(dot(grip, grip)) - .1397) > .0001:
                raise ValueError("Recorded hand no longer matches the paddle grip")
            up = [-x for x in unit(grip)]
            normal = unit(vector(shot["plannedNormal"]))
            measured_normal = unit(vector(contact["normal"]))
            point = vector(contact["point"])
            linear = vector(shot["paddleVelocity"])
            angular = vector(shot["paddleAngularVelocity"])
            offset = sub(point, paddle)
            angular_velocity = cross(angular, offset)
            point_velocity = [v+w for v, w in zip(linear, angular_velocity)]
            planned_speed = scalar(shot["plannedSwing"])
            normal_angle = math.degrees(math.acos(max(-1., min(1., dot(normal, measured_normal)))))
            rows.append(dict(gameSeed=rally["gameSeed"], rally=rally["rally"],
                eventIndex=shot["eventIndex"], player=shot["player"], shot=shot["selectedShot"],
                lowContact=shot["lowContact"], surface=contact["surface"], outcome=outcome,
                delayMs=(scalar(shot["time"])-scalar(shot["plannedImpactAt"]))*1000,
                plannedToMeasuredNormalDegrees=normal_angle,
                postStepContactLocalY=dot(offset, up),
                postStepFaceCenterLongitudinalOffset=dot(offset, up)-.0635,
                linearNormalSpeed=dot(linear, normal), pointNormalSpeed=dot(point_velocity, normal),
                plannedNormalSpeed=planned_speed, normalSpeedError=dot(point_velocity, normal)-planned_speed,
                angularNormalSpeed=dot(angular_velocity, normal)))
    fields = ("delayMs", "plannedToMeasuredNormalDegrees", "postStepFaceCenterLongitudinalOffset",
              "linearNormalSpeed", "pointNormalSpeed", "plannedNormalSpeed", "normalSpeedError",
              "angularNormalSpeed")
    groups = []
    for low, outcome in sorted({(r["lowContact"], r["outcome"]) for r in rows}):
        selected = [r for r in rows if (r["lowContact"], r["outcome"]) == (low, outcome)]
        groups.append(dict(lowContact=low, outcome=outcome, contacts=len(selected),
            surfaces=dict(Counter(r["surface"] for r in selected)),
            measuredNormalWithinOneDegree=sum(r["plannedToMeasuredNormalDegrees"] <= 1 for r in selected),
            distributions={key: distribution([r[key] for r in selected]) for key in fields}))
    return dict(contacts=len(rows), skipped=dict(skipped), groups=groups, rows=rows,
                limitation="Saved post-physics-step paddle and grip pose, not exact time-of-impact pose. "
                "Only the paddle local Y axis is recovered. Normal error compares the recorded contact normal "
                "with the planned normal, not the measured face orientation. Point velocity uses the recorded "
                "post-step linear and angular velocity, as the current contact transfer does. "
                "Associations with landing outcomes do not establish cause or improved match strength.")


def audit(path):
    from player_actor import ROOT, file_hash
    # Reuse the complete source/model/motor/ownership checks before geometry analysis.
    verified = subprocess.run([sys.executable, str(ROOT / "scripts/player_contact_outcomes.py"), str(path)],
                              cwd=ROOT, check=True, text=True, capture_output=True)
    prior = json.loads(verified.stdout)
    report = json.loads(path.read_text())
    if file_hash(path) != prior["reportHash"]:
        raise ValueError("Report changed after verification")
    return dict(reportPath=str(path), reportHash=prior["reportHash"], sourceHash=report["sourceHash"],
                actorHash=report["actorHash"], **analyze(report))


if __name__ == "__main__":
    from player_actor import ROOT, file_hash
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", type=Path, nargs="+")
    args = parser.parse_args()
    print(json.dumps(dict(version="player-contact-geometry-audit-v1",
        analyzerHash=file_hash(Path(__file__)), verifierHash=file_hash(ROOT / "scripts/player_contact_outcomes.py"),
        geometry=dict(gripLocal=[0, -.1397, 0], faceCenterLocal=[0, .0635, 0],
                      source="Current PlayerBody.GripLocal and factory face placement, covered by sourceHash"),
        reports=[audit(p) for p in args.reports]), indent=2))

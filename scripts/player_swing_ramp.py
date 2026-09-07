"""Audit isolated swing timing. This does not select a runtime or policy model."""
import argparse
import json
import math
from pathlib import Path

from player_contact_fit import summarize as summarize_contact


def summarize(report):
    if (report.get("version") != "player-swing-ramp-probe-v1"
            or report.get("status") != "complete" or report.get("error") is not None
            or report.get("split") != "diagnostic" or report.get("expectedCases") != 72
            or len(report.get("rows", [])) != 72
            or report.get("modes") != ["runtime", "local-control", "ramp-120ms"]):
        raise ValueError("Incomplete or changed swing ramp schedule")
    rows = report["rows"]
    excluded = {"index", "mode", "tracePath"}
    changed = []
    for fixture in range(24):
        original, control, ramp = rows[fixture*3:fixture*3+3]
        for mode, row in enumerate((original, control, ramp)):
            expected = dict(index=fixture*3+mode, fixture=fixture, mode=mode,
                            player=fixture//12*2, shot=[4, 6, 8][fixture%3],
                            depth=[3.5, 4.5, 5.5, 6.5][fixture//3%4])
            if any(type(row.get(k)) is not type(v) or row.get(k) != v for k, v in expected.items()):
                raise ValueError("Changed fixture identity")
            if type(row.get("ticks")) is not int or row["ticks"] <= 0:
                raise ValueError("Missing physical steps")
        if ({k: v for k, v in original.items() if k not in excluded}
                != {k: v for k, v in control.items() if k not in excluded}):
            raise ValueError(f"Local control differs from runtime in fixture {fixture}")
        if original["traceHash"] != ramp["traceHash"]:
            changed.append(fixture)
    # Reuse the established limits and landing checks without changing their bounds.
    paired = dict(report, version="player-contact-fit-probe-v1", expectedCases=48, rows=[])
    for row in rows:
        if row["mode"] == 1:
            continue
        paired["rows"].append(dict(row, index=len(paired["rows"]), fitted=row["mode"] == 0))
    physical = summarize_contact(paired)
    def original_index(index):
        return index // 2 * 3 + (0 if index % 2 == 0 else 2)
    for failure in physical["unsafeCases"]:
        failure["index"] = original_index(failure["index"])
    for group in physical["groups"]:
        group["mode"] = "runtime" if group["mode"] == "frozen fit" else "ramp-120ms"
        for failure in group["failures"]:
            failure["index"] = original_index(failure["index"])
    return dict(cases=72, exactControlCases=24, changedRampFixtures=changed,
                motorChecksPassed=physical["motorChecksPassed"], unsafeCases=physical["unsafeCases"],
                groups=physical["groups"],
                limitation="Stationary fixtures with player colliders disabled after the first legal hit. "
                           "No match, learned-policy, human-limit, or ball-calibration claim.")


def validate_trace(samples, row):
    if len(samples) != row["ticks"]:
        raise ValueError("Trace length changed")
    vectors = ("ball", "velocity", "spin", "feet", "bodyVelocity", "shoulder", "hand", "paddle",
               "paddleVelocity", "angularVelocity", "leftFoot", "rightFoot", "impact", "normal")
    bounds = dict(speed=12.01, acceleration=100.1, reach=.6201, angularSpeed=12.01, movement=.0001)
    peaks = dict.fromkeys(bounds, 0.)
    violations = []
    previous = [0., 0., 0.]
    for tick, sample in enumerate(samples, 1):
        if type(sample.get("ticks")) is not int or sample["ticks"] != tick:
            raise ValueError("Trace tick sequence changed")
        for key in (*vectors, "rotation"):
            values = sample.get(key)
            if (not isinstance(values, list) or len(values) != (4 if key == "rotation" else 3)
                    or any(type(v) not in (float, int) or not math.isfinite(v) for v in values)):
                raise ValueError("Invalid physical vector")
        if type(sample.get("time")) not in (float, int) or not math.isfinite(sample["time"]):
            raise ValueError("Invalid physics time")
        if tick > 1 and abs(sample["time"] - samples[tick-2]["time"] - 1/240) > .000002:
            raise ValueError("Changed physics timestep")
        velocity = sample["paddleVelocity"]
        values = dict(speed=math.dist(velocity, [0, 0, 0]),
                      acceleration=math.dist(velocity, previous)*240,
                      reach=math.dist(sample["hand"], sample["shoulder"]),
                      angularSpeed=math.dist(sample["angularVelocity"], [0, 0, 0]),
                      movement=math.dist(sample["feet"], samples[0]["feet"]))
        previous = velocity
        for key, value in values.items():
            peaks[key] = max(peaks[key], value)
            if value > bounds[key]:
                violations.append(dict(tick=tick, field=key, value=value, bound=bounds[key]))
    return dict(peaks=peaks, violations=violations)


def audit(path):
    from player_actor import ROOT, file_hash, source_hash
    report = json.loads(path.read_text())
    result = summarize(report)
    if report["sourceHash"] != source_hash():
        raise ValueError("Runtime source changed")
    for path_key, hash_key in (("collectorSnapshotPath", "collectorHash"),
                               ("contactPath", "contactHash"), ("runtimeSwingPath", "runtimeSwingHash")):
        artifact = (ROOT / report[path_key]).resolve()
        artifact.relative_to(ROOT)
        if file_hash(artifact) != report[hash_key]:
            raise ValueError("Diagnostic source or snapshot changed")
    count = 0
    peaks = {}
    unsafe = []
    for row in report["rows"]:
        trace = (ROOT / row["tracePath"]).resolve()
        trace.relative_to(ROOT)
        if file_hash(trace) != row["traceHash"]:
            raise ValueError("Physical trace changed")
        samples = [json.loads(line) for line in trace.read_text().splitlines()]
        trace_audit = validate_trace(samples, row)
        for key, value in trace_audit["peaks"].items():
            peaks[key] = max(peaks.get(key, 0.), value)
        if trace_audit["violations"]:
            unsafe.append(dict(index=row["index"], violations=trace_audit["violations"]))
        count += len(samples)
    result["motorChecksPassed"] &= not unsafe
    result.update(measuredTracePeaks=peaks, unsafeTraceCases=unsafe)
    return dict(reportPath=str(path), reportHash=file_hash(path), verifiedPhysicalSteps=count, **result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    result = audit(args.report)
    print(json.dumps(result, indent=2))
    if not result["motorChecksPassed"]:
        raise SystemExit(1)

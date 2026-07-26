#!/usr/bin/env python3
"""Validate and fit Picklebot Phase 1B empirical calibration inputs.

This tool intentionally accepts only normalized, provenance-bearing measurements.
Simulator-generated traces are not valid calibration input.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import statistics
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FLIGHT = ROOT / "docs/reference/phase1b/flight/traces.jsonl"
DEFAULT_COURT = ROOT / "docs/reference/phase1b/acrylic-court/impacts.jsonl"
DEFAULT_DROP = ROOT / "docs/reference/phase1b/official-drop/procedure.json"
DEFAULT_EVIDENCE = ROOT / "docs/evidence/phase1b"

SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
SPIN_TARGETS_RAD_S = (2.0 * math.pi * 5.0, 2.0 * math.pi * 10.0)
SPIN_TARGET_TOLERANCE_RAD_S = math.pi
ZERO_SPIN_TOLERANCE_RAD_S = 0.5
LOW_SPEED_COVERAGE_MPS = 5.5
HIGH_SPEED_COVERAGE_MPS = 14.5
COURT_HALF_WIDTH_M = 3.048
COURT_HALF_LENGTH_M = 6.7056

Vec3 = tuple[float, float, float]
State = tuple[Vec3, Vec3, Vec3]


class CalibrationInputError(ValueError):
    """Raised when empirical input cannot qualify for Phase 1B."""


@dataclass(frozen=True)
class FitParameters:
    drag_coefficient: float
    lift_coefficient_slope: float
    maximum_lift_coefficient: float
    angular_decay_rate: float

    def as_dict(self) -> dict[str, float]:
        return {
            "dragCoefficient": self.drag_coefficient,
            "liftCoefficientSlope": self.lift_coefficient_slope,
            "maximumLiftCoefficient": self.maximum_lift_coefficient,
            "angularDecayRate": self.angular_decay_rate,
        }


def _error(location: str, message: str) -> CalibrationInputError:
    return CalibrationInputError(f"{location}: {message}")


def _require_object(value: Any, location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _error(location, "must be an object")
    return value


def _require_array(value: Any, location: str) -> list[Any]:
    if not isinstance(value, list):
        raise _error(location, "must be an array")
    return value


def _require_string(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _error(location, "must be a non-empty string")
    return value


def _require_number(value: Any, location: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _error(location, "must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise _error(location, "must be finite")
    return result


def _require_positive(value: Any, location: str) -> float:
    result = _require_number(value, location)
    if result <= 0.0:
        raise _error(location, "must be greater than zero")
    return result


def _require_timestamp(value: Any, location: str) -> str:
    result = _require_string(value, location)
    try:
        datetime.fromisoformat(result.replace("Z", "+00:00"))
    except ValueError as exc:
        raise _error(location, "must be an ISO-8601 date-time") from exc
    return result


def _require_sha256(value: Any, location: str) -> str:
    result = _require_string(value, location)
    if not SHA256_RE.fullmatch(result):
        raise _error(location, "must be a lowercase SHA-256 digest")
    return result


def _require_enum(value: Any, allowed: set[str], location: str) -> str:
    result = _require_string(value, location)
    if result not in allowed:
        raise _error(location, f"must be one of {sorted(allowed)}")
    return result


def _vector(value: Any, location: str) -> Vec3:
    obj = _require_object(value, location)
    return (
        _require_number(obj.get("x"), f"{location}.x"),
        _require_number(obj.get("y"), f"{location}.y"),
        _require_number(obj.get("z"), f"{location}.z"),
    )


def _approval(value: Any, location: str) -> dict[str, Any]:
    obj = _require_object(value, location)
    if obj.get("authority") != "USA Pickleball":
        raise _error(f"{location}.authority", "must be 'USA Pickleball'")
    source = _require_string(obj.get("sourceUrl"), f"{location}.sourceUrl")
    if "equipment.usapickleball.org" not in source:
        raise _error(
            f"{location}.sourceUrl",
            "must identify the current USA Pickleball approved-ball list or entry",
        )
    _require_timestamp(obj.get("verifiedAt"), f"{location}.verifiedAt")
    return obj


def _provenance(
    value: Any,
    location: str,
    uncertainty_key: str,
) -> dict[str, Any]:
    obj = _require_object(value, location)
    _require_enum(
        obj.get("kind"),
        {"project-physical-capture", "published-raw-trace"},
        f"{location}.kind",
    )
    _require_string(obj.get("source"), f"{location}.source")
    _require_timestamp(obj.get("capturedAt"), f"{location}.capturedAt")
    _require_string(obj.get("method"), f"{location}.method")
    uncertainty = _require_number(
        obj.get(uncertainty_key),
        f"{location}.{uncertainty_key}",
    )
    if uncertainty < 0.0:
        raise _error(f"{location}.{uncertainty_key}", "must be non-negative")
    _require_sha256(obj.get("rawArtifactSha256"), f"{location}.rawArtifactSha256")
    _require_sha256(
        obj.get("coordinateArtifactSha256"),
        f"{location}.coordinateArtifactSha256",
    )
    return obj


def _ball(value: Any, location: str, require_holes: bool = True) -> dict[str, Any]:
    obj = _require_object(value, location)
    _require_string(obj.get("model"), f"{location}.model")
    _require_string(obj.get("sampleId"), f"{location}.sampleId")
    if require_holes:
        holes = _require_number(obj.get("holeCount"), f"{location}.holeCount")
        if holes != 40.0:
            raise _error(f"{location}.holeCount", "must be 40")
    _require_positive(obj.get("massKg"), f"{location}.massKg")
    _require_positive(obj.get("diameterM"), f"{location}.diameterM")
    _approval(obj.get("approval"), f"{location}.approval")
    return obj


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise _error(str(path), "file does not exist")
    records: list[dict[str, Any]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise _error(f"{path}:{line_number}", f"invalid JSON: {exc}") from exc
        records.append(_require_object(value, f"{path}:{line_number}"))
    if not records:
        raise _error(str(path), "must contain at least one JSON record")
    return records


def _norm(value: Vec3) -> float:
    return math.sqrt(sum(component * component for component in value))


def _sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _mul(value: Vec3, scale: float) -> Vec3:
    return (value[0] * scale, value[1] * scale, value[2] * scale)


def _dot(a: Vec3, b: Vec3) -> float:
    return sum(left * right for left, right in zip(a, b))


def _cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def validate_flight_dataset(path: Path, require_coverage: bool = True) -> list[dict[str, Any]]:
    traces = _load_jsonl(path)
    trace_ids: set[str] = set()
    classes = {"zero": 0, "topspin": 0, "backspin": 0}
    arcs: set[str] = set()
    launch_speeds: list[float] = []
    spin_speeds: list[float] = []
    ball_models: set[str] = set()

    for index, trace in enumerate(traces):
        location = f"{path}:record[{index}]"
        trace_id = _require_string(trace.get("traceId"), f"{location}.traceId")
        if trace_id in trace_ids:
            raise _error(f"{location}.traceId", f"duplicate trace ID '{trace_id}'")
        trace_ids.add(trace_id)
        spin_class = _require_enum(
            trace.get("spinClass"),
            set(classes),
            f"{location}.spinClass",
        )
        arc_class = _require_enum(
            trace.get("arcClass"),
            {"low", "medium", "high"},
            f"{location}.arcClass",
        )
        if trace.get("coordinateFrame") != "picklebot-world-v1":
            raise _error(
                f"{location}.coordinateFrame",
                "must be 'picklebot-world-v1'",
            )
        classes[spin_class] += 1
        arcs.add(arc_class)
        _provenance(
            trace.get("provenance"),
            f"{location}.provenance",
            "positionUncertaintyMeters",
        )
        ball = _ball(trace.get("ball"), f"{location}.ball")
        ball_models.add(ball["model"])

        environment = _require_object(
            trace.get("environment"),
            f"{location}.environment",
        )
        _require_number(environment.get("temperatureC"), f"{location}.environment.temperatureC")
        _require_positive(
            environment.get("airDensityKgM3"),
            f"{location}.environment.airDensityKgM3",
        )
        _vector(environment.get("windVelocityMps"), f"{location}.environment.windVelocityMps")

        initial = _require_object(trace.get("initialState"), f"{location}.initialState")
        initial_position = _vector(initial.get("positionM"), f"{location}.initialState.positionM")
        initial_velocity = _vector(initial.get("velocityMps"), f"{location}.initialState.velocityMps")
        initial_spin = _vector(
            initial.get("angularVelocityRadS"),
            f"{location}.initialState.angularVelocityRadS",
        )
        launch_speeds.append(_norm(initial_velocity))
        spin_magnitude = _norm(initial_spin)
        if spin_class == "zero" and spin_magnitude > ZERO_SPIN_TOLERANCE_RAD_S:
            raise _error(
                f"{location}.initialState.angularVelocityRadS",
                f"zero-spin trace exceeds {ZERO_SPIN_TOLERANCE_RAD_S} rad/s",
            )
        if spin_class != "zero":
            if spin_magnitude <= ZERO_SPIN_TOLERANCE_RAD_S:
                raise _error(
                    f"{location}.initialState.angularVelocityRadS",
                    "spinning trace is indistinguishable from zero spin",
                )
            spin_speeds.append(spin_magnitude)

        samples = _require_array(trace.get("samples"), f"{location}.samples")
        if len(samples) < 3:
            raise _error(f"{location}.samples", "must contain at least three samples")
        previous_time = -math.inf
        first_position: Vec3 | None = None
        for sample_index, sample_value in enumerate(samples):
            sample = _require_object(sample_value, f"{location}.samples[{sample_index}]")
            time_s = _require_number(sample.get("timeS"), f"{location}.samples[{sample_index}].timeS")
            if time_s < 0.0 or time_s <= previous_time:
                raise _error(
                    f"{location}.samples[{sample_index}].timeS",
                    "must be non-negative and strictly increasing",
                )
            position = _vector(
                sample.get("positionM"),
                f"{location}.samples[{sample_index}].positionM",
            )
            if first_position is None:
                if abs(time_s) > 1e-9:
                    raise _error(f"{location}.samples[0].timeS", "must be zero")
                first_position = position
            previous_time = time_s
        uncertainty = float(trace["provenance"]["positionUncertaintyMeters"])
        if first_position is None or _norm(_sub(first_position, initial_position)) > max(
            uncertainty,
            1e-6,
        ):
            raise _error(
                f"{location}.samples[0].positionM",
                "must match initialState.positionM within stated uncertainty",
            )

        terminal = _require_object(trace.get("terminal"), f"{location}.terminal")
        _require_enum(
            terminal.get("classification"),
            {"NearCourtLanding", "FarCourtLanding", "OutOfBoundsLanding"},
            f"{location}.terminal.classification",
        )
        flight_time = _require_positive(
            terminal.get("flightTimeS"),
            f"{location}.terminal.flightTimeS",
        )
        if flight_time < previous_time:
            raise _error(
                f"{location}.terminal.flightTimeS",
                "cannot precede the final trajectory sample",
            )
        _vector(terminal.get("landingPositionM"), f"{location}.terminal.landingPositionM")

    if require_coverage:
        if classes["zero"] < 6 or classes["topspin"] < 3 or classes["backspin"] < 3:
            raise _error(
                str(path),
                "requires at least 6 zero-spin, 3 topspin, and 3 backspin traces",
            )
        if arcs != {"low", "medium", "high"}:
            raise _error(str(path), "must cover low, medium, and high arcs")
        if min(launch_speeds) > LOW_SPEED_COVERAGE_MPS:
            raise _error(str(path), "does not cover the approximately 5 m/s launch point")
        if max(launch_speeds) < HIGH_SPEED_COVERAGE_MPS:
            raise _error(str(path), "does not cover the approximately 15 m/s launch point")
        for target in SPIN_TARGETS_RAD_S:
            if not any(abs(value - target) <= SPIN_TARGET_TOLERANCE_RAD_S for value in spin_speeds):
                raise _error(
                    str(path),
                    f"does not cover spin near {target:.5f} rad/s within "
                    f"{SPIN_TARGET_TOLERANCE_RAD_S:.5f} rad/s",
                )
        if len(ball_models) != 1:
            raise _error(str(path), "must use one named reference ball model")
    return traces


def validate_court_dataset(path: Path) -> list[dict[str, Any]]:
    impacts = _load_jsonl(path)
    trial_ids: set[str] = set()
    case_counts = {"vertical": 0, "shallow": 0, "spun": 0}
    surfaces: set[tuple[str, str, str]] = set()
    ball_models: set[str] = set()

    for index, impact in enumerate(impacts):
        location = f"{path}:record[{index}]"
        trial_id = _require_string(impact.get("trialId"), f"{location}.trialId")
        if trial_id in trial_ids:
            raise _error(f"{location}.trialId", f"duplicate trial ID '{trial_id}'")
        trial_ids.add(trial_id)
        case_type = _require_enum(
            impact.get("caseType"),
            set(case_counts),
            f"{location}.caseType",
        )
        case_counts[case_type] += 1
        if impact.get("coordinateFrame") != "picklebot-world-v1":
            raise _error(
                f"{location}.coordinateFrame",
                "must be 'picklebot-world-v1'",
            )
        _provenance(
            impact.get("provenance"),
            f"{location}.provenance",
            "velocityUncertaintyMps",
        )
        surface = _require_object(impact.get("surface"), f"{location}.surface")
        system = _require_string(surface.get("system"), f"{location}.surface.system")
        base = _require_string(surface.get("base"), f"{location}.surface.base")
        place = _require_string(surface.get("location"), f"{location}.surface.location")
        _require_string(surface.get("condition"), f"{location}.surface.condition")
        surfaces.add((system, base, place))
        ball = _ball(impact.get("ball"), f"{location}.ball")
        ball_models.add(ball["model"])

        conditions = _require_object(impact.get("conditions"), f"{location}.conditions")
        _require_number(conditions.get("temperatureC"), f"{location}.conditions.temperatureC")
        humidity = _require_number(
            conditions.get("relativeHumidityPercent"),
            f"{location}.conditions.relativeHumidityPercent",
        )
        if humidity < 0.0 or humidity > 100.0:
            raise _error(
                f"{location}.conditions.relativeHumidityPercent",
                "must be between 0 and 100",
            )

        incoming = _require_object(impact.get("incoming"), f"{location}.incoming")
        outgoing = _require_object(impact.get("outgoing"), f"{location}.outgoing")
        incoming_velocity = _vector(
            incoming.get("velocityMps"),
            f"{location}.incoming.velocityMps",
        )
        outgoing_velocity = _vector(
            outgoing.get("velocityMps"),
            f"{location}.outgoing.velocityMps",
        )
        _vector(
            incoming.get("angularVelocityRadS"),
            f"{location}.incoming.angularVelocityRadS",
        )
        _vector(
            outgoing.get("angularVelocityRadS"),
            f"{location}.outgoing.angularVelocityRadS",
        )
        if incoming_velocity[1] >= 0.0:
            raise _error(f"{location}.incoming.velocityMps.y", "must be downward")
        if outgoing_velocity[1] <= 0.0:
            raise _error(f"{location}.outgoing.velocityMps.y", "must be upward")

        samples = _require_array(impact.get("samples"), f"{location}.samples")
        if len(samples) < 3:
            raise _error(f"{location}.samples", "must contain at least three samples")
        previous_time = -math.inf
        for sample_index, sample_value in enumerate(samples):
            sample = _require_object(sample_value, f"{location}.samples[{sample_index}]")
            time_s = _require_number(
                sample.get("timeS"),
                f"{location}.samples[{sample_index}].timeS",
            )
            if time_s <= previous_time:
                raise _error(
                    f"{location}.samples[{sample_index}].timeS",
                    "must be strictly increasing",
                )
            previous_time = time_s
            _vector(
                sample.get("ballCenterM"),
                f"{location}.samples[{sample_index}].ballCenterM",
            )

    missing = {case_type: 5 - count for case_type, count in case_counts.items() if count < 5}
    if missing:
        raise _error(str(path), f"requires at least five trials per case; missing {missing}")
    if len(surfaces) != 1:
        raise _error(str(path), "must use one named acrylic surface system/base/location")
    if len(ball_models) != 1:
        raise _error(str(path), "must use one named reference ball model")
    return impacts


def validate_drop_procedure(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise _error(str(path), "file does not exist")
    try:
        procedure = _require_object(
            json.loads(path.read_text(encoding="utf-8")),
            str(path),
        )
    except json.JSONDecodeError as exc:
        raise _error(str(path), f"invalid JSON: {exc}") from exc
    _require_string(procedure.get("procedureId"), f"{path}.procedureId")
    if procedure.get("authority") != "USA Pickleball":
        raise _error(f"{path}.authority", "must be 'USA Pickleball'")
    _require_string(procedure.get("source"), f"{path}.source")
    _require_timestamp(procedure.get("publishedAt"), f"{path}.publishedAt")
    _require_timestamp(procedure.get("retrievedAt"), f"{path}.retrievedAt")
    _require_sha256(procedure.get("documentSha256"), f"{path}.documentSha256")
    datum = _require_enum(
        procedure.get("releaseDatum"),
        {"ball-top", "ball-center", "ball-bottom"},
        f"{path}.releaseDatum",
    )
    release_height = _require_number(
        procedure.get("releaseReferenceHeightM"),
        f"{path}.releaseReferenceHeightM",
    )
    if abs(release_height - 1.9812) > 1e-9:
        raise _error(f"{path}.releaseReferenceHeightM", "must equal 78 inches (1.9812 m)")
    diameter = _require_positive(procedure.get("ballDiameterM"), f"{path}.ballDiameterM")
    center_height = _require_positive(
        procedure.get("initialBallCenterHeightM"),
        f"{path}.initialBallCenterHeightM",
    )
    expected_center = {
        "ball-top": release_height - diameter / 2.0,
        "ball-center": release_height,
        "ball-bottom": release_height + diameter / 2.0,
    }[datum]
    if abs(center_height - expected_center) > 1e-6:
        raise _error(
            f"{path}.initialBallCenterHeightM",
            f"must equal {expected_center:.9f} m for the selected release datum",
        )
    if procedure.get("reboundMeasurementDatum") != "ball-top":
        raise _error(f"{path}.reboundMeasurementDatum", "must be 'ball-top'")
    expected_constants = {
        "minimumReboundTopHeightM": 0.762,
        "maximumReboundTopHeightM": 0.8636,
        "minimumTemperatureC": 18.3333333333,
        "maximumTemperatureC": 23.8888888889,
    }
    for key, expected in expected_constants.items():
        actual = _require_number(procedure.get(key), f"{path}.{key}")
        if abs(actual - expected) > 1e-8:
            raise _error(f"{path}.{key}", f"must equal {expected}")
    _require_string(procedure.get("datumEvidence"), f"{path}.datumEvidence")
    return procedure


def validate_all(flight_path: Path, court_path: Path, drop_path: Path) -> dict[str, Any]:
    flights = validate_flight_dataset(flight_path)
    impacts = validate_court_dataset(court_path)
    procedure = validate_drop_procedure(drop_path)
    flight_models = {trace["ball"]["model"] for trace in flights}
    court_models = {impact["ball"]["model"] for impact in impacts}
    if flight_models != court_models:
        raise _error(
            "reference profile",
            "flight and court inputs must use the same named ball model",
        )
    return {
        "flightTraceCount": len(flights),
        "courtImpactCount": len(impacts),
        "dropProcedureId": procedure["procedureId"],
        "referenceBallModel": next(iter(flight_models)),
        "passed": True,
    }


def _derivative(state: State, trace: dict[str, Any], parameters: FitParameters) -> State:
    _, velocity, omega = state
    environment = trace["environment"]
    ball = trace["ball"]
    wind = _vector(environment["windVelocityMps"], "windVelocityMps")
    relative = _sub(velocity, wind)
    speed = _norm(relative)
    acceleration = (0.0, -9.81, 0.0)
    if speed >= 0.01:
        direction = _mul(relative, 1.0 / speed)
        radius = float(ball["diameterM"]) / 2.0
        area = math.pi * radius * radius
        pressure_area = (
            0.5
            * float(environment["airDensityKgM3"])
            * area
            * speed
            * speed
        )
        drag = _mul(
            direction,
            -pressure_area * parameters.drag_coefficient,
        )
        perpendicular_spin = _sub(omega, _mul(direction, _dot(omega, direction)))
        perpendicular_magnitude = _norm(perpendicular_spin)
        lift = (0.0, 0.0, 0.0)
        if perpendicular_magnitude > 1e-12:
            spin_parameter = radius * perpendicular_magnitude / speed
            lift_coefficient = min(
                parameters.maximum_lift_coefficient,
                parameters.lift_coefficient_slope * spin_parameter,
            )
            lift_direction_raw = _cross(perpendicular_spin, relative)
            lift_direction = _mul(lift_direction_raw, 1.0 / _norm(lift_direction_raw))
            lift = _mul(lift_direction, pressure_area * lift_coefficient)
        acceleration = _add(
            acceleration,
            _mul(_add(drag, lift), 1.0 / float(ball["massKg"])),
        )
    angular_derivative = _mul(omega, -parameters.angular_decay_rate)
    return (velocity, acceleration, angular_derivative)


def _state_add(state: State, derivative: State, scale: float) -> State:
    return tuple(  # type: ignore[return-value]
        _add(value, _mul(delta, scale))
        for value, delta in zip(state, derivative)
    )


def _rk4_step(
    state: State,
    step: float,
    trace: dict[str, Any],
    parameters: FitParameters,
) -> State:
    k1 = _derivative(state, trace, parameters)
    k2 = _derivative(_state_add(state, k1, step * 0.5), trace, parameters)
    k3 = _derivative(_state_add(state, k2, step * 0.5), trace, parameters)
    k4 = _derivative(_state_add(state, k3, step), trace, parameters)
    result: list[Vec3] = []
    for value, d1, d2, d3, d4 in zip(state, k1, k2, k3, k4):
        weighted = _add(_add(d1, _mul(d2, 2.0)), _add(_mul(d3, 2.0), d4))
        result.append(_add(value, _mul(weighted, step / 6.0)))
    return (result[0], result[1], result[2])


def _initial_state(trace: dict[str, Any]) -> State:
    initial = trace["initialState"]
    return (
        _vector(initial["positionM"], "initial.positionM"),
        _vector(initial["velocityMps"], "initial.velocityMps"),
        _vector(initial["angularVelocityRadS"], "initial.angularVelocityRadS"),
    )


def _integrate(
    state: State,
    duration: float,
    trace: dict[str, Any],
    parameters: FitParameters,
    maximum_step: float = 1.0 / 480.0,
) -> State:
    remaining = duration
    while remaining > 1e-12:
        step = min(maximum_step, remaining)
        state = _rk4_step(state, step, trace, parameters)
        remaining -= step
    return state


def _sample_errors(
    trace: dict[str, Any],
    parameters: FitParameters,
) -> tuple[list[float], State]:
    state = _initial_state(trace)
    elapsed = 0.0
    errors: list[float] = []
    for sample in trace["samples"]:
        sample_time = float(sample["timeS"])
        state = _integrate(state, sample_time - elapsed, trace, parameters)
        reference = _vector(sample["positionM"], "sample.positionM")
        errors.append(_norm(_sub(state[0], reference)))
        elapsed = sample_time
    return errors, state


def _objective(traces: Sequence[dict[str, Any]], parameters: FitParameters) -> float:
    squared: list[float] = []
    for trace in traces:
        errors, _ = _sample_errors(trace, parameters)
        squared.extend(value * value for value in errors)
    return sum(squared) / len(squared)


def _golden_minimize(function: Any, low: float, high: float, iterations: int = 34) -> float:
    ratio = (math.sqrt(5.0) - 1.0) / 2.0
    left = high - ratio * (high - low)
    right = low + ratio * (high - low)
    left_value = function(left)
    right_value = function(right)
    for _ in range(iterations):
        if left_value <= right_value:
            high = right
            right = left
            right_value = left_value
            left = high - ratio * (high - low)
            left_value = function(left)
        else:
            low = left
            left = right
            left_value = right_value
            right = low + ratio * (high - low)
            right_value = function(right)
    return (low + high) / 2.0


def fit_parameters(traces: Sequence[dict[str, Any]]) -> FitParameters:
    zero = [trace for trace in traces if trace["spinClass"] == "zero"]
    spinning = [trace for trace in traces if trace["spinClass"] != "zero"]
    base = FitParameters(0.30, 0.195, 0.25, 0.05)
    drag = _golden_minimize(
        lambda value: _objective(
            zero,
            FitParameters(value, 0.0, base.maximum_lift_coefficient, 0.0),
        ),
        0.25,
        0.35,
    )
    slope = base.lift_coefficient_slope
    decay = base.angular_decay_rate
    for _ in range(4):
        slope = _golden_minimize(
            lambda value: _objective(
                spinning,
                FitParameters(drag, value, base.maximum_lift_coefficient, decay),
            ),
            0.0,
            1.0,
        )
        decay = _golden_minimize(
            lambda value: _objective(
                spinning,
                FitParameters(drag, slope, base.maximum_lift_coefficient, value),
            ),
            0.0,
            2.0,
        )
    return FitParameters(drag, slope, base.maximum_lift_coefficient, decay)


def _simulate_landing(
    trace: dict[str, Any],
    parameters: FitParameters,
) -> tuple[float, Vec3]:
    state = _initial_state(trace)
    radius = float(trace["ball"]["diameterM"]) / 2.0
    elapsed = 0.0
    step = 1.0 / 480.0
    previous = state
    while elapsed < 10.0:
        previous = state
        state = _rk4_step(state, step, trace, parameters)
        elapsed += step
        if state[0][1] <= radius and state[1][1] < 0.0:
            previous_y = previous[0][1]
            current_y = state[0][1]
            fraction = 1.0
            if abs(current_y - previous_y) > 1e-12:
                fraction = (radius - previous_y) / (current_y - previous_y)
                fraction = min(1.0, max(0.0, fraction))
            position = _add(
                previous[0],
                _mul(_sub(state[0], previous[0]), fraction),
            )
            return elapsed - step + step * fraction, position
    raise CalibrationInputError(f"{trace['traceId']}: simulated ball did not land within 10 s")


def _classify_landing(position: Vec3) -> str:
    if (
        abs(position[0]) <= COURT_HALF_WIDTH_M
        and abs(position[2]) <= COURT_HALF_LENGTH_M
    ):
        return "FarCourtLanding" if position[2] >= 0.0 else "NearCourtLanding"
    return "OutOfBoundsLanding"


def fit_report(
    traces: Sequence[dict[str, Any]],
    bootstrap_samples: int,
) -> dict[str, Any]:
    parameters = fit_parameters(traces)
    vacuum = FitParameters(0.0, 0.0, 0.0, 0.0)
    trace_reports: list[dict[str, Any]] = []
    fitted_squared: list[float] = []
    vacuum_squared: list[float] = []
    for trace in traces:
        errors, _ = _sample_errors(trace, parameters)
        vacuum_errors, _ = _sample_errors(trace, vacuum)
        fitted_squared.extend(value * value for value in errors)
        vacuum_squared.extend(value * value for value in vacuum_errors)
        landing_time, landing_position = _simulate_landing(trace, parameters)
        reference_landing = _vector(
            trace["terminal"]["landingPositionM"],
            "terminal.landingPositionM",
        )
        rms = math.sqrt(sum(value * value for value in errors) / len(errors))
        maximum = max(errors)
        landing_error = _norm(_sub(landing_position, reference_landing))
        flight_time_error = abs(landing_time - float(trace["terminal"]["flightTimeS"]))
        simulated_classification = _classify_landing(landing_position)
        classification_agrees = (
            simulated_classification == trace["terminal"]["classification"]
        )
        passed = (
            rms <= 0.15
            and maximum <= 0.30
            and landing_error <= 0.20
            and flight_time_error <= 0.05
            and classification_agrees
        )
        trace_reports.append(
            {
                "traceId": trace["traceId"],
                "spinClass": trace["spinClass"],
                "arcClass": trace["arcClass"],
                "rmsPositionErrorM": rms,
                "maximumPositionErrorM": maximum,
                "vacuumRmsPositionErrorM": math.sqrt(
                    sum(value * value for value in vacuum_errors) / len(vacuum_errors)
                ),
                "landingPointErrorM": landing_error,
                "flightTimeErrorS": flight_time_error,
                "referenceTerminalClassification": trace["terminal"]["classification"],
                "simulatedTerminalClassification": simulated_classification,
                "terminalClassificationAgrees": classification_agrees,
                "passed": passed,
            }
        )

    uncertainties: dict[str, float | None] = {
        "dragCoefficient": None,
        "liftCoefficientSlope": None,
        "maximumLiftCoefficient": None,
        "angularDecayRate": None,
    }
    uncertainty_method = "not-estimated"
    if bootstrap_samples >= 2:
        generator = random.Random(20260727)
        zero = [trace for trace in traces if trace["spinClass"] == "zero"]
        top = [trace for trace in traces if trace["spinClass"] == "topspin"]
        back = [trace for trace in traces if trace["spinClass"] == "backspin"]
        fitted: list[FitParameters] = []
        for _ in range(bootstrap_samples):
            sample = (
                generator.choices(zero, k=len(zero))
                + generator.choices(top, k=len(top))
                + generator.choices(back, k=len(back))
            )
            fitted.append(fit_parameters(sample))
        uncertainties = {
            "dragCoefficient": statistics.stdev(value.drag_coefficient for value in fitted),
            "liftCoefficientSlope": statistics.stdev(
                value.lift_coefficient_slope for value in fitted
            ),
            "maximumLiftCoefficient": 0.0,
            "angularDecayRate": statistics.stdev(value.angular_decay_rate for value in fitted),
        }
        uncertainty_method = (
            f"deterministic stratified bootstrap, n={bootstrap_samples}, seed=20260727"
        )

    fitted_rms = math.sqrt(sum(fitted_squared) / len(fitted_squared))
    vacuum_rms = math.sqrt(sum(vacuum_squared) / len(vacuum_squared))
    all_traces_pass = all(report["passed"] for report in trace_reports)
    aerodynamic_improvement = fitted_rms < vacuum_rms
    return {
        "fitVersion": "phase1b-empirical-fit-v0",
        "model": "quadratic-drag-linear-signed-spin-lift-v1",
        "integrator": "independent-rk4-480hz",
        "parameters": parameters.as_dict(),
        "standardUncertainty": uncertainties,
        "uncertaintyMethod": uncertainty_method,
        "traceCount": len(traces),
        "aggregateRmsPositionErrorM": fitted_rms,
        "vacuumAggregateRmsPositionErrorM": vacuum_rms,
        "aerodynamicImprovement": aerodynamic_improvement,
        "allTraceThresholdsPass": all_traces_pass,
        "qualifiesForFlightClose": (
            all_traces_pass
            and aerodynamic_improvement
            and bootstrap_samples >= 2
        ),
        "traces": trace_reports,
    }


def court_report(impacts: Sequence[dict[str, Any]]) -> dict[str, Any]:
    cases: dict[str, list[dict[str, float]]] = {
        "vertical": [],
        "shallow": [],
        "spun": [],
    }
    for impact in impacts:
        incoming_velocity = _vector(impact["incoming"]["velocityMps"], "incoming.velocityMps")
        outgoing_velocity = _vector(impact["outgoing"]["velocityMps"], "outgoing.velocityMps")
        incoming_spin = _vector(
            impact["incoming"]["angularVelocityRadS"],
            "incoming.angularVelocityRadS",
        )
        outgoing_spin = _vector(
            impact["outgoing"]["angularVelocityRadS"],
            "outgoing.angularVelocityRadS",
        )
        cases[impact["caseType"]].append(
            {
                "normalRestitution": outgoing_velocity[1] / -incoming_velocity[1],
                "incomingTangentialSpeedMps": math.hypot(
                    incoming_velocity[0],
                    incoming_velocity[2],
                ),
                "outgoingTangentialSpeedMps": math.hypot(
                    outgoing_velocity[0],
                    outgoing_velocity[2],
                ),
                "spinMagnitudeChangeRadS": _norm(outgoing_spin) - _norm(incoming_spin),
            }
        )
    summaries: dict[str, Any] = {}
    for case_type, records in cases.items():
        restitutions = [record["normalRestitution"] for record in records]
        tangential_ratios = [
            record["outgoingTangentialSpeedMps"]
            / record["incomingTangentialSpeedMps"]
            for record in records
            if record["incomingTangentialSpeedMps"] > 1e-9
        ]
        summaries[case_type] = {
            "trials": len(records),
            "meanNormalRestitution": statistics.mean(restitutions),
            "standardDeviationNormalRestitution": statistics.stdev(restitutions),
            "meanTangentialSpeedRatio": (
                statistics.mean(tangential_ratios) if tangential_ratios else None
            ),
            "records": records,
        }
    return {
        "fitVersion": "phase1b-acrylic-targets-v0",
        "note": (
            "These are measured response targets. Unity material coefficients "
            "must still be searched and replayed against every trace."
        ),
        "cases": summaries,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def close_audit(root: Path) -> dict[str, Any]:
    failures: list[str] = []
    try:
        references = validate_all(
            root / DEFAULT_FLIGHT.relative_to(ROOT),
            root / DEFAULT_COURT.relative_to(ROOT),
            root / DEFAULT_DROP.relative_to(ROOT),
        )
    except CalibrationInputError as exc:
        references = None
        failures.append(str(exc))

    config_path = root / "Assets/Picklebot/Core/SimulationConfigV1.cs"
    config_text = config_path.read_text(encoding="utf-8")
    if re.search(r"CalibrationState\s*=\s*ProvisionalCalibrationState", config_text):
        failures.append("SimulationConfigV1 default calibration state is still provisional")

    protocol_path = root / "Assets/Picklebot/Evaluation/Phase1CProtocolV0.cs"
    protocol_text = protocol_path.read_text(encoding="utf-8")
    if 'EnvironmentDependency = "env-v1"' not in protocol_text:
        failures.append("Phase1C protocol does not depend on env-v1")
    if "FinalEvaluationRequest" in protocol_text:
        failures.append("Phase1C final-evaluation request API exists before experiment freeze")

    evidence = root / DEFAULT_EVIDENCE.relative_to(ROOT)
    required = [
        "summary.json",
        "calibration-manifest.json",
        "ball-drop.jsonl",
        "flight-traces.jsonl",
        "paddle-contact.jsonl",
        "court-net-contact.jsonl",
    ]
    for relative in required:
        if not (evidence / relative).is_file():
            failures.append(f"missing closing evidence: docs/evidence/phase1b/{relative}")

    head = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    tag_result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "-q", "--verify", "refs/tags/env-v1^{}"],
        check=False,
        capture_output=True,
        text=True,
    )
    tag_commit = tag_result.stdout.strip() if tag_result.returncode == 0 else None
    if tag_commit is None:
        failures.append("local env-v1 tag does not exist")
    elif tag_commit != head:
        failures.append(f"env-v1 tag points to {tag_commit}, not HEAD {head}")

    summary: dict[str, Any] | None = None
    summary_path = evidence / "summary.json"
    if summary_path.is_file():
        try:
            summary = _require_object(
                json.loads(summary_path.read_text(encoding="utf-8")),
                str(summary_path),
            )
        except (json.JSONDecodeError, CalibrationInputError) as exc:
            failures.append(f"invalid closing summary: {exc}")
        if summary is not None:
            required_summary_strings = [
                "configurationHash",
                "physicsSettingsHash",
                "phase1CProtocolHash",
                "unityVersion",
                "platform",
                "hardware",
                "generatedAtUtc",
            ]
            for key in required_summary_strings:
                if not isinstance(summary.get(key), str) or not summary[key].strip():
                    failures.append(f"closing summary lacks non-empty {key}")
            if summary.get("evidenceState") != "closing-source-exact":
                failures.append("closing summary evidenceState is not closing-source-exact")
            if summary.get("closeEligible") is not True:
                failures.append("closing summary closeEligible is not true")
            if summary.get("environmentVersion") != "env-v1":
                failures.append("closing summary environmentVersion is not env-v1")
            if summary.get("sourceCommit") != head:
                failures.append("closing summary sourceCommit does not equal HEAD")
            if summary.get("environmentTag") != "env-v1":
                failures.append("closing summary environmentTag is not env-v1")
            if summary.get("configurationVersion") != "physics-calibration-v0":
                failures.append(
                    "closing summary configurationVersion is not physics-calibration-v0"
                )
            if summary.get("calibrationState") in (None, "", "provisional-unfitted"):
                failures.append("closing summary calibrationState is provisional or absent")
            if summary.get("phase1CProtocolVersion") != "phase1c-protocol-v0":
                failures.append(
                    "closing summary phase1CProtocolVersion is not phase1c-protocol-v0"
                )
            required_gates = [
                "geometry",
                "officialBallDrop",
                "acrylicCourtReference",
                "flightTrajectories",
                "paddleSurrogate",
                "courtAndNetContacts",
                "determinismAndStability",
                "readinessAndAllocation",
                "sourceExactReproduction",
                "envV1Freeze",
                "phase1CProtocol",
            ]
            gates = summary.get("gates")
            if not isinstance(gates, dict):
                failures.append("closing summary lacks gates object")
            else:
                for gate_name in required_gates:
                    gate = gates.get(gate_name)
                    if (
                        not isinstance(gate, dict)
                        or gate.get("passed") is not True
                        or not isinstance(gate.get("evidence"), list)
                        or not gate["evidence"]
                        or not all(
                            isinstance(item, str) and item.strip()
                            for item in gate["evidence"]
                        )
                    ):
                        failures.append(
                            f"closing summary gate {gate_name} lacks passed evidence"
                        )
            reference_hashes = summary.get("referenceSha256")
            if not isinstance(reference_hashes, dict) or len(reference_hashes) < 3:
                failures.append("closing summary lacks at least three reference hashes")
            elif not all(
                isinstance(value, str) and SHA256_RE.fullmatch(value)
                for value in reference_hashes.values()
            ):
                failures.append("closing summary contains an invalid reference SHA-256")
            limitations = summary.get("limitations")
            if (
                not isinstance(limitations, list)
                or not limitations
                or not all(isinstance(value, str) and value.strip() for value in limitations)
            ):
                failures.append("closing summary lacks explicit limitations")
            artifact_hashes = summary.get("artifactSha256")
            if not isinstance(artifact_hashes, dict):
                failures.append("closing summary lacks artifactSha256 object")
            else:
                for relative in required[1:]:
                    path = evidence / relative
                    if path.is_file() and artifact_hashes.get(relative) != _sha256(path):
                        failures.append(f"closing summary hash mismatch for {relative}")

    manifest_path = evidence / "calibration-manifest.json"
    if manifest_path.is_file():
        try:
            manifest = _require_object(
                json.loads(manifest_path.read_text(encoding="utf-8")),
                str(manifest_path),
            )
            if manifest.get("profile") != "outdoor-40-hole-v0":
                failures.append("closing calibration manifest profile is incorrect")
            if manifest.get("calibrationState") in (None, "", "provisional-unfitted"):
                failures.append("closing calibration manifest remains provisional")
            if manifest.get("qualifiesForClose") is not True:
                failures.append("closing calibration manifest does not qualify for close")
            parameters = manifest.get("parameters")
            if not isinstance(parameters, list) or len(parameters) < 8:
                failures.append("closing calibration manifest has fewer than eight parameters")
            else:
                parameter_names: set[str] = set()
                for index, parameter_value in enumerate(parameters):
                    if not isinstance(parameter_value, dict):
                        failures.append(
                            f"closing calibration parameter {index} is not an object"
                        )
                        continue
                    parameter_names.add(str(parameter_value.get("parameter", "")))
                    required_parameter_values = [
                        "parameter",
                        "unit",
                        "sourceKind",
                        "source",
                        "fittingMethod",
                        "calibratedAt",
                    ]
                    if not all(
                        isinstance(parameter_value.get(key), str)
                        and parameter_value[key].strip()
                        for key in required_parameter_values
                    ):
                        failures.append(
                            f"closing calibration parameter {index} lacks provenance"
                        )
                    try:
                        uncertainty = float(parameter_value["standardUncertainty"])
                        value = float(parameter_value["value"])
                        if (
                            not math.isfinite(uncertainty)
                            or uncertainty < 0.0
                            or not math.isfinite(value)
                        ):
                            raise ValueError
                    except (KeyError, TypeError, ValueError):
                        failures.append(
                            f"closing calibration parameter {index} has invalid value/uncertainty"
                        )
                    if parameter_value.get("status") != "accepted":
                        failures.append(
                            f"closing calibration parameter {index} is not accepted"
                        )
                required_parameters = {
                    "dragCoefficient",
                    "liftCoefficientSlope",
                    "angularDecayRate",
                    "graniteRestitution",
                    "courtRestitution",
                    "paddleRestitution",
                    "netRestitution",
                    "courtDynamicFriction",
                }
                missing_parameters = sorted(required_parameters - parameter_names)
                if missing_parameters:
                    failures.append(
                        "closing calibration manifest lacks parameters: "
                        + ", ".join(missing_parameters)
                    )
        except (json.JSONDecodeError, CalibrationInputError) as exc:
            failures.append(f"invalid closing calibration manifest: {exc}")

    worktree = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if worktree.strip():
        failures.append("worktree is not clean")

    return {
        "auditVersion": "phase1b-close-audit-v0",
        "sourceCommit": head,
        "environmentTagCommit": tag_commit,
        "references": references,
        "closingEvidenceDirectory": str(evidence),
        "failures": failures,
        "passed": not failures,
    }


def _write_json(path: Path | None, value: dict[str, Any]) -> None:
    rendered = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if path is None:
        sys.stdout.write(rendered)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")
    print(path)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate all empirical inputs")
    validate.add_argument("--flight", type=Path, default=DEFAULT_FLIGHT)
    validate.add_argument("--court", type=Path, default=DEFAULT_COURT)
    validate.add_argument("--drop", type=Path, default=DEFAULT_DROP)

    fit_flight = subparsers.add_parser("fit-flight", help="fit env-v1 flight coefficients")
    fit_flight.add_argument("--flight", type=Path, default=DEFAULT_FLIGHT)
    fit_flight.add_argument("--bootstrap", type=int, default=50)
    fit_flight.add_argument("--output", type=Path)

    fit_court = subparsers.add_parser("fit-court", help="summarize acrylic-court targets")
    fit_court.add_argument("--court", type=Path, default=DEFAULT_COURT)
    fit_court.add_argument("--output", type=Path)

    audit = subparsers.add_parser("audit-close", help="audit every Phase 1B close gate")
    audit.add_argument("--root", type=Path, default=ROOT)
    audit.add_argument("--output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "validate":
            _write_json(None, validate_all(args.flight, args.court, args.drop))
        elif args.command == "fit-flight":
            if args.bootstrap < 0:
                raise CalibrationInputError("--bootstrap must be non-negative")
            traces = validate_flight_dataset(args.flight)
            _write_json(args.output, fit_report(traces, args.bootstrap))
        elif args.command == "fit-court":
            impacts = validate_court_dataset(args.court)
            _write_json(args.output, court_report(impacts))
        elif args.command == "audit-close":
            report = close_audit(args.root.resolve())
            _write_json(args.output, report)
            return 0 if report["passed"] else 1
        else:
            raise AssertionError(args.command)
    except CalibrationInputError as exc:
        print(f"phase1b empirical gate failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

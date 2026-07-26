from __future__ import annotations

import importlib.util
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "phase1b_empirical.py"
SPEC = importlib.util.spec_from_file_location("phase1b_empirical", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
phase1b = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = phase1b
SPEC.loader.exec_module(phase1b)


class Phase1BEmpiricalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.flight_path = self.root / "traces.jsonl"
        self.court_path = self.root / "impacts.jsonl"
        self.drop_path = self.root / "procedure.json"
        self.parameters = phase1b.FitParameters(0.30, 0.195, 0.25, 0.05)
        self.traces = self._flight_records()
        self._write_jsonl(self.flight_path, self.traces)
        self._write_jsonl(self.court_path, self._court_records())
        self.drop_path.write_text(
            json.dumps(self._drop_procedure()),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def _vector(value: tuple[float, float, float]) -> dict[str, float]:
        return {"x": value[0], "y": value[1], "z": value[2]}

    @staticmethod
    def _approval() -> dict[str, str]:
        return {
            "authority": "USA Pickleball",
            "sourceUrl": "https://equipment.usapickleball.org/ball-list/entry/test/",
            "verifiedAt": "2026-07-27T00:00:00Z",
        }

    @classmethod
    def _ball(cls, sample_id: str = "synthetic-01") -> dict[str, object]:
        return {
            "model": "Synthetic Approved Outdoor 40",
            "sampleId": sample_id,
            "holeCount": 40,
            "massKg": 0.024,
            "diameterM": 0.074,
            "approval": cls._approval(),
        }

    @staticmethod
    def _provenance(position: bool = True) -> dict[str, object]:
        value: dict[str, object] = {
            "kind": "project-physical-capture",
            "source": "synthetic unit-test fixture; never valid closing data",
            "capturedAt": "2026-07-27T00:00:00Z",
            "method": "deterministic unit test",
            "rawArtifactSha256": "a" * 64,
            "coordinateArtifactSha256": "b" * 64,
        }
        value[
            "positionUncertaintyMeters" if position else "velocityUncertaintyMps"
        ] = 0.000001
        return value

    def _flight_records(self) -> list[dict[str, object]]:
        definitions = [
            ("zero", "low", 5.0, 0.10, 0.0),
            ("zero", "medium", 7.0, 0.22, 0.0),
            ("zero", "high", 9.0, 0.36, 0.0),
            ("zero", "low", 11.0, 0.12, 0.0),
            ("zero", "medium", 13.0, 0.24, 0.0),
            ("zero", "high", 15.0, 0.34, 0.0),
            ("topspin", "low", 8.0, 0.14, math.pi * 10.0),
            ("topspin", "medium", 10.0, 0.24, math.pi * 20.0),
            ("topspin", "high", 12.0, 0.34, math.pi * 10.0),
            ("backspin", "low", 8.5, 0.14, -math.pi * 10.0),
            ("backspin", "medium", 10.5, 0.24, -math.pi * 20.0),
            ("backspin", "high", 12.5, 0.34, -math.pi * 20.0),
        ]
        result: list[dict[str, object]] = []
        for index, (spin_class, arc, speed, vertical_fraction, spin) in enumerate(
            definitions
        ):
            vertical = speed * vertical_fraction
            forward = math.sqrt(speed * speed - vertical * vertical)
            trace: dict[str, object] = {
                "traceId": f"synthetic-{index:02d}",
                "spinClass": spin_class,
                "arcClass": arc,
                "coordinateFrame": "picklebot-world-v1",
                "provenance": self._provenance(),
                "ball": self._ball(),
                "environment": {
                    "temperatureC": 20.0,
                    "airDensityKgM3": 1.204,
                    "windVelocityMps": self._vector((0.0, 0.0, 0.0)),
                },
                "initialState": {
                    "positionM": self._vector((0.0, 0.8, -5.8)),
                    "velocityMps": self._vector((0.0, vertical, forward)),
                    "angularVelocityRadS": self._vector((spin, 0.0, 0.0)),
                },
                "samples": [],
                "terminal": {},
            }
            landing_time, landing_position = phase1b._simulate_landing(
                trace,
                self.parameters,
            )
            state = phase1b._initial_state(trace)
            elapsed = 0.0
            samples: list[dict[str, object]] = []
            for fraction in (0.0, 0.2, 0.4, 0.6, 0.8):
                sample_time = landing_time * fraction
                state = phase1b._integrate(
                    state,
                    sample_time - elapsed,
                    trace,
                    self.parameters,
                )
                samples.append(
                    {
                        "timeS": sample_time,
                        "positionM": self._vector(state[0]),
                    }
                )
                elapsed = sample_time
            trace["samples"] = samples
            trace["terminal"] = {
                "classification": phase1b._classify_landing(landing_position),
                "flightTimeS": landing_time,
                "landingPositionM": self._vector(landing_position),
            }
            result.append(trace)
        return result

    def _court_records(self) -> list[dict[str, object]]:
        result: list[dict[str, object]] = []
        for case_type in ("vertical", "shallow", "spun"):
            for trial in range(5):
                tangential = 0.0 if case_type == "vertical" else 3.0 + trial * 0.1
                spin = 0.0 if case_type != "spun" else 31.4159265359
                result.append(
                    {
                        "trialId": f"{case_type}-{trial}",
                        "caseType": case_type,
                        "coordinateFrame": "picklebot-world-v1",
                        "provenance": self._provenance(position=False),
                        "surface": {
                            "system": "Synthetic Acrylic",
                            "base": "concrete",
                            "location": "unit-test",
                            "condition": "synthetic",
                        },
                        "ball": self._ball(),
                        "conditions": {
                            "temperatureC": 20.0,
                            "relativeHumidityPercent": 50.0,
                        },
                        "incoming": {
                            "velocityMps": self._vector((0.0, -5.0, tangential)),
                            "angularVelocityRadS": self._vector((spin, 0.0, 0.0)),
                        },
                        "outgoing": {
                            "velocityMps": self._vector((0.0, 3.2, tangential * 0.8)),
                            "angularVelocityRadS": self._vector((spin * 0.9, 0.0, 0.0)),
                        },
                        "samples": [
                            {"timeS": -0.01, "ballCenterM": self._vector((0.0, 0.08, -0.03))},
                            {"timeS": 0.0, "ballCenterM": self._vector((0.0, 0.037, 0.0))},
                            {"timeS": 0.01, "ballCenterM": self._vector((0.0, 0.07, 0.03))},
                        ],
                    }
                )
        return result

    @staticmethod
    def _drop_procedure() -> dict[str, object]:
        diameter = 0.074
        return {
            "procedureId": "synthetic-unit-test",
            "authority": "USA Pickleball",
            "source": "https://equipment.usapickleball.org/docs/test.pdf",
            "publishedAt": "2026-07-27T00:00:00Z",
            "retrievedAt": "2026-07-27T00:00:00Z",
            "documentSha256": "c" * 64,
            "releaseDatum": "ball-top",
            "releaseReferenceHeightM": 1.9812,
            "ballDiameterM": diameter,
            "initialBallCenterHeightM": 1.9812 - diameter / 2.0,
            "reboundMeasurementDatum": "ball-top",
            "minimumReboundTopHeightM": 0.762,
            "maximumReboundTopHeightM": 0.8636,
            "minimumTemperatureC": 18.3333333333,
            "maximumTemperatureC": 23.8888888889,
            "datumEvidence": "synthetic unit-test evidence",
        }

    @staticmethod
    def _write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
        path.write_text(
            "".join(json.dumps(record) + "\n" for record in records),
            encoding="utf-8",
        )

    def test_complete_reference_bundle_validates(self) -> None:
        report = phase1b.validate_all(
            self.flight_path,
            self.court_path,
            self.drop_path,
        )
        self.assertTrue(report["passed"])
        self.assertEqual(report["flightTraceCount"], 12)
        self.assertEqual(report["courtImpactCount"], 15)

    def test_flight_fit_recovers_synthetic_coefficients_and_passes(self) -> None:
        traces = phase1b.validate_flight_dataset(self.flight_path)
        report = phase1b.fit_report(traces, bootstrap_samples=0)
        self.assertAlmostEqual(report["parameters"]["dragCoefficient"], 0.30, places=3)
        self.assertAlmostEqual(
            report["parameters"]["liftCoefficientSlope"],
            0.195,
            places=2,
        )
        self.assertTrue(report["allTraceThresholdsPass"])
        self.assertTrue(report["aerodynamicImprovement"])
        self.assertFalse(report["qualifiesForFlightClose"])

    def test_simulator_provenance_is_rejected(self) -> None:
        self.traces[0]["provenance"]["kind"] = "simulator-generated"
        self._write_jsonl(self.flight_path, self.traces)
        with self.assertRaisesRegex(
            phase1b.CalibrationInputError,
            "project-physical-capture",
        ):
            phase1b.validate_flight_dataset(self.flight_path)

    def test_missing_high_speed_coverage_is_rejected(self) -> None:
        for trace in self.traces:
            velocity = trace["initialState"]["velocityMps"]
            speed = math.sqrt(sum(float(velocity[key]) ** 2 for key in ("x", "y", "z")))
            if speed > 14.0:
                scale = 13.0 / speed
                for key in ("x", "y", "z"):
                    velocity[key] *= scale
        self._write_jsonl(self.flight_path, self.traces)
        with self.assertRaisesRegex(
            phase1b.CalibrationInputError,
            "15 m/s",
        ):
            phase1b.validate_flight_dataset(self.flight_path)

    def test_fewer_than_five_court_trials_is_rejected(self) -> None:
        impacts = [
            record
            for record in self._court_records()
            if not (record["caseType"] == "spun" and record["trialId"] == "spun-4")
        ]
        self._write_jsonl(self.court_path, impacts)
        with self.assertRaisesRegex(
            phase1b.CalibrationInputError,
            "five trials per case",
        ):
            phase1b.validate_court_dataset(self.court_path)


if __name__ == "__main__":
    unittest.main()

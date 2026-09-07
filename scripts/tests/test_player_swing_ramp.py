import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from player_swing_ramp import summarize, validate_trace
import test_player_contact_fit


class SwingRampTests(unittest.TestCase):
    def fixture(self):
        report = test_player_contact_fit.ContactFitTests().fixture()
        rows = []
        for fixture in range(24):
            original = report["rows"][fixture*2]
            for mode in range(3):
                row = dict(original, index=len(rows), mode=mode, ticks=1,
                           tracePath=f"case-{len(rows)}", traceHash="control" if mode < 2 else "ramp")
                row.pop("fitted")
                rows.append(row)
        return dict(report, version="player-swing-ramp-probe-v1", expectedCases=72,
                    modes=["runtime", "local-control", "ramp-120ms"], rows=rows)

    def test_complete_control_and_motor_checks(self):
        result = summarize(self.fixture())
        self.assertEqual(result["exactControlCases"], 24)
        self.assertTrue(result["motorChecksPassed"])
        self.assertEqual(result["changedRampFixtures"], list(range(24)))

    def test_partial_or_reordered_schedule_rejected(self):
        for mutation in (lambda r: r["rows"].pop(), lambda r: r["rows"].reverse(),
                         lambda r: r.update(status="running"), lambda r: r["rows"][0].update(mode=False)):
            report = self.fixture(); mutation(report)
            with self.assertRaises(ValueError): summarize(report)

    def test_control_trace_and_contacts_must_match(self):
        for mutation in (lambda r: r.update(traceHash="changed"),
                         lambda r: r.update(contacts=[]), lambda r: r.update(maxSpeed=7)):
            report = self.fixture(); mutation(report["rows"][1])
            with self.assertRaises(ValueError): summarize(report)

    def test_motor_failure_keeps_original_case_index(self):
        report = self.fixture(); report["rows"][20]["maxSpeed"] = 13
        result = summarize(report)
        self.assertFalse(result["motorChecksPassed"])
        self.assertEqual(result["unsafeCases"], [dict(index=20, violations=["maxSpeed"])])

    def test_missed_landing_keeps_original_case_index(self):
        report = self.fixture()
        report["rows"][20].update(hit=False, landed=False, legalLanding=False, targetError=None)
        result = summarize(report)
        failures = [f for group in result["groups"] for f in group["failures"]]
        self.assertEqual([f["index"] for f in failures], [20])

    def test_trace_rejects_count_vector_and_timing_changes(self):
        keys = ("ball", "velocity", "spin", "feet", "bodyVelocity", "shoulder", "hand", "paddle",
                "paddleVelocity", "angularVelocity", "leftFoot", "rightFoot", "impact", "normal")
        sample = dict(ticks=1, time=0., rotation=[0, 0, 0, 1], **{k: [0, 0, 0] for k in keys})
        samples = [sample, dict(sample, ticks=2, time=1/240)]
        self.assertEqual(validate_trace(samples, dict(ticks=2))["violations"], [])
        unsafe = copy.deepcopy(samples)
        unsafe[1]["paddleVelocity"] = [13, 0, 0]
        fields = {v["field"] for v in validate_trace(unsafe, dict(ticks=2))["violations"]}
        self.assertEqual(fields, {"speed", "acceleration"})
        with self.assertRaises(ValueError): validate_trace(samples, dict(ticks=1))
        for mutation in (lambda s: s.update(time=.2), lambda s: s.update(time=float("nan")),
                         lambda s: s.update(ticks=1),
                         lambda s: s.update(ball=[float("nan"), 0, 0]),
                         lambda s: s.update(ball=[True, 0, 0])):
            changed = copy.deepcopy(samples); mutation(changed[1])
            with self.assertRaises(ValueError): validate_trace(changed, dict(ticks=2))


if __name__ == "__main__": unittest.main()

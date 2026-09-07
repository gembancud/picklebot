from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from player_contact_geometry import analyze, distribution


class ContactGeometryTests(unittest.TestCase):
    def fixture(self, end=0):
        sign = 1 if end == 0 else -1
        point = [0, .0635, .008*sign]
        shot = dict(eventIndex=0, player=end*2, time=1., planned=True, target=[0, 0, sign*4],
                    lowContact=False, selectedShot=4, paddlePosition=[0, 0, 0], hand=[0, -.1397, 0],
                    paddleVelocity=[0, 0, sign*4], paddleAngularVelocity=[0, 0, 0],
                    plannedNormal=[0, 0, sign], plannedSwing=5., plannedImpactAt=.98,
                    contacts=[dict(surface="RoundedHittingFace", point=point, normal=[0, 0, sign])])
        events = [dict(kind="hit", player=end*2, time=1., position=point),
                  dict(kind="bounce", position=[0, 0, sign*4])]
        return dict(rallies=[dict(gameSeed=1198000, rally=1, shots=[shot], events=events)])

    def test_centered_contact_and_both_ends(self):
        for end in (0, 1):
            result = analyze(self.fixture(end))
            row = result["rows"][0]
            self.assertAlmostEqual(row["delayMs"], 20.)
            self.assertEqual(row["postStepFaceCenterLongitudinalOffset"], 0)
            self.assertEqual(row["normalSpeedError"], -1)
            self.assertEqual(row["plannedToMeasuredNormalDegrees"], 0)

    def test_rolled_grip_recovers_local_axis_without_assuming_upright(self):
        report = self.fixture(); shot = report["rallies"][0]["shots"][0]
        shot["hand"] = [.1397, 0, 0]
        shot["contacts"][0]["point"] = [-.0635, 0, .008]
        self.assertEqual(analyze(report)["rows"][0]["postStepFaceCenterLongitudinalOffset"], 0)

    def test_angular_velocity_is_not_silently_omitted(self):
        report = self.fixture(); shot = report["rallies"][0]["shots"][0]
        shot["paddleAngularVelocity"] = [2, 0, 0]
        row = analyze(report)["rows"][0]
        self.assertAlmostEqual(row["angularNormalSpeed"], .127)
        self.assertAlmostEqual(row["pointNormalSpeed"], 4.127)

    def test_handle_and_opposed_normal_are_retained(self):
        report = self.fixture(); contact = report["rallies"][0]["shots"][0]["contacts"][0]
        contact.update(surface="NonContactHandle", normal=[0, 0, -1])
        result = analyze(report)
        self.assertEqual(result["rows"][0]["plannedToMeasuredNormalDegrees"], 180)
        self.assertEqual(result["groups"][0]["surfaces"], {"NonContactHandle": 1})

    def test_unplanned_and_multiple_contacts_are_explicit(self):
        report = self.fixture(); shot = report["rallies"][0]["shots"][0]
        shot["planned"] = False
        self.assertEqual(analyze(report)["skipped"], {"unplanned": 1})
        shot["planned"] = True; shot["contacts"] *= 2
        self.assertEqual(analyze(report)["skipped"], {"not exactly one contact": 1})

    def test_invalid_pose_time_and_event_are_rejected(self):
        for change in (dict(hand=[0, 0, 0]), dict(plannedNormal=[0, 0, 0]),
                       dict(hand=[True, 0, 0]), dict(plannedSwing=float("inf")),
                       dict(plannedImpactAt=float("nan")), dict(time=.9)):
            report = self.fixture(); report["rallies"][0]["shots"][0].update(change)
            with self.assertRaises(ValueError): analyze(report)

    def test_percentiles_keep_empty_and_single_samples_clear(self):
        self.assertIsNone(distribution([]))
        self.assertEqual(distribution([3])["median"], 3)
        self.assertEqual(distribution([1, 3])["median"], 2)
        self.assertAlmostEqual(distribution([1, 3])["p90"], 2.8)


if __name__ == "__main__": unittest.main()

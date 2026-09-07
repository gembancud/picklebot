import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from player_contact_fit import summarize


class ContactFitTests(unittest.TestCase):
    def fixture(self):
        rows = []
        for index in range(48):
            fixture = index // 2
            rows.append(dict(index=index, fixture=fixture, player=fixture//12*2, shot=[4, 6, 8][fixture%3],
                depth=[3.5, 4.5, 5.5, 6.5][fixture//3%4], fitted=index%2 == 0,
                infeasible=0, maxSpeed=8, maxAcceleration=100, maxReach=.6, maxAngularSpeed=12,
                movement=0, hit=True, landed=True, legalLanding=True, targetError=1,
                contacts=[dict(surface="RoundedHittingFace")], fault="None"))
        return dict(version="player-contact-fit-probe-v1", status="complete", error=None,
                    split="diagnostic", expectedCases=48, rows=rows, depths=[3.5, 4.5, 5.5, 6.5], shots=[4, 6, 8])

    def test_exact_paired_schedule(self):
        result = summarize(self.fixture())
        self.assertTrue(result["motorChecksPassed"])
        self.assertEqual(len(result["groups"]), 6)
        self.assertTrue(all(g["cases"] == g["hits"] == g["legalLandings"] == 8 for g in result["groups"]))

    def test_reordered_or_partial_schedule_fails(self):
        for mutation in (lambda r: r["rows"].pop(), lambda r: r["rows"].reverse(),
                         lambda r: r["rows"][0].update(fitted=False)):
            report = self.fixture(); mutation(report)
            with self.assertRaises(ValueError): summarize(report)

    def test_all_physical_failures_are_retained(self):
        for field, value in (("maxSpeed", 13), ("maxAcceleration", 101), ("maxReach", .7),
                             ("maxAngularSpeed", 13), ("movement", .01), ("infeasible", 1),
                             ("maxSpeed", float("nan"))):
            report = self.fixture(); report["rows"][17][field] = value
            result = summarize(report)
            self.assertFalse(result["motorChecksPassed"])
            self.assertEqual(result["unsafeCases"], [dict(index=17, violations=[field])])

    def test_missing_landing_is_not_a_zero_error(self):
        report = self.fixture()
        report["rows"][0].update(landed=False, legalLanding=False, targetError=None)
        result = summarize(report)
        self.assertEqual(result["groups"][0]["legalLandings"], 7)
        self.assertEqual(result["groups"][0]["meanLegalLandingError"], 1)
        report["rows"][0]["targetError"] = 0
        with self.assertRaises(ValueError): summarize(report)

    def test_landing_requires_legal_hit(self):
        report = self.fixture(); report["rows"][0]["hit"] = False
        with self.assertRaises(ValueError): summarize(report)


if __name__ == "__main__": unittest.main()

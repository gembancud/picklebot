from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from player_partner import partner_schedule, audit_partner_games


class PartnerTests(unittest.TestCase):
    def fixture(self):
        protocol = dict(seedBase=1140000, seedsPerCourtEndAndSeat=1)
        schedule = partner_schedule(1140000, 1)
        report = dict(candidateHash="new", olderHash="old", games=[], rallies=[])
        for entry in schedule:
            team, seat = entry["candidateTeam"], entry["candidateSeat"]
            report["games"].append(entry | dict(gameSeed=entry["seed"], complete=True, winner=team,
                score=[11, 0] if team == 0 else [0, 11], rallies=1,
                policyHashBySeat=["old" if i//2 != team or (entry["mixedPartner"] and i != seat) else "new" for i in range(4)],
                decisionCounts=[1]*4, ownershipFailures=[0]*4, angularViolations=[0]*4,
                firstDecisions=[dict(player=i, observationPlayer=i, observationTick=12, applyTick=18) for i in range(4)],
                metrics=dict(legalHits=[1]*4, infeasiblePaddleSteps=0, playerMaxSpeed=[3.8]*4,
                    playerMaxAcceleration=[14.01]*4, playerMaxPaddleSpeed=[12]*4,
                    playerMaxPaddleAcceleration=[100.03]*4, playerMaxReach=[.62]*4)))
            report["rallies"].append(dict(index=entry["index"]))
        return report, dict(schedule=schedule), protocol

    def test_pairing_covers_each_seat_and_end_with_equal_seeds(self):
        report, plan, protocol = self.fixture()
        for a, b in zip(plan["schedule"][::2], plan["schedule"][1::2]):
            self.assertEqual(a["seed"], b["seed"])
            self.assertEqual(a["candidateSeat"], b["candidateSeat"])
        result = audit_partner_games(report, plan, protocol)
        self.assertEqual(result["olderPolicyPartner"]["games"], 4)
        self.assertEqual(result["motorFailures"], [])

    def test_schedule_and_policy_seat_changes_are_rejected(self):
        for field, value in (("gameSeed", 1140999), ("candidateSeat", 3), ("policyHashBySeat", ["new"]*4)):
            report, plan, protocol = self.fixture(); report["games"][0][field] = value
            with self.assertRaises(ValueError): audit_partner_games(report, plan, protocol)

    def test_court_end_and_seat_splits_do_not_hide_one_sided_wins(self):
        report, plan, protocol = self.fixture()
        for game in report["games"]:
            game.update(winner=1, score=[0, 11])
        result = audit_partner_games(report, plan, protocol)
        self.assertEqual(result["samePolicyPartner"]["wins"], 2)
        for row in result["byCourtEnd"]:
            self.assertEqual(row["games"], 2)
            self.assertEqual(row["wins"], 0 if row["candidateTeam"] == 0 else 2)
        for row in result["byPlayerSeat"]:
            self.assertEqual(row["games"], 1)
            self.assertEqual(row["wins"], int(row["candidateSeat"] >= 2))

    def test_missing_decisions_and_rallies_are_rejected(self):
        report, plan, protocol = self.fixture(); report["games"][0]["firstDecisions"][1]["observationPlayer"] = 0
        with self.assertRaises(ValueError): audit_partner_games(report, plan, protocol)
        report, plan, protocol = self.fixture(); report["rallies"].pop()
        with self.assertRaises(ValueError): audit_partner_games(report, plan, protocol)

    def test_opponent_motor_failures_and_incomplete_games_remain_visible(self):
        report, plan, protocol = self.fixture()
        report["games"][0]["metrics"]["playerMaxPaddleAcceleration"][3] = 200
        report["games"][0].update(complete=False, winner=-1)
        result = audit_partner_games(report, plan, protocol)
        self.assertFalse(result["allGamesComplete"])
        self.assertTrue(result["motorFailures"])
        self.assertEqual(result["samePolicyPartner"]["games"], 4)


if __name__ == "__main__": unittest.main()

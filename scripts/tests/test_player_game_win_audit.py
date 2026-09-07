import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from player_game_win_audit import game_outcomes


class GameWinAuditTests(unittest.TestCase):
    def report(self):
        return dict(status="complete", rewardMode="game_win", games=[dict(gameSeed=1085000,
            candidateTeam=0, winner=0, score=[11, 7], complete=True, rallies=1, metrics=dict(legalHits=[1, 2, 3, 4]))],
            rallies=[dict(gameSeed=1085000, candidateTeam=0, winner=0, score=[11, 7],
                          fault="Out", seconds=5, legalHits=[1, 2, 3, 4])])

    def test_complete_game_outcome(self):
        result = game_outcomes(self.report())[0]
        self.assertTrue(result["won"])
        self.assertEqual(result["legalReturns"], 3)

    def test_incomplete_game_rejected(self):
        report = self.report(); report["games"][0]["complete"] = False
        with self.assertRaises(ValueError): game_outcomes(report)

    def test_win_by_two_required(self):
        report = self.report(); report["games"][0]["score"] = [11, 10]
        with self.assertRaises(ValueError): game_outcomes(report)

    def test_duplicate_game_rejected(self):
        report = self.report(); report["games"].append(copy.deepcopy(report["games"][0]))
        with self.assertRaises(ValueError): game_outcomes(report)

    def test_rally_reward_cannot_replace_game_reward(self):
        report = self.report(); report["rewardMode"] = "rally_win"
        with self.assertRaises(ValueError): game_outcomes(report)

    def test_hit_ledger_must_match(self):
        report = self.report(); report["rallies"][0]["legalHits"][0] += 1
        with self.assertRaises(ValueError): game_outcomes(report)

    def test_truncation_is_retained_without_a_point(self):
        report = self.report(); report["games"][0]["rallies"] += 1
        report["rallies"].insert(0, dict(gameSeed=1085000, candidateTeam=0, winner=-1, score=[0, 0],
                                      fault="None", seconds=31, legalHits=[0]*4))
        self.assertEqual(game_outcomes(report)[0]["truncatedRallies"], 1)
        report["rallies"][0]["score"] = [1, 0]
        with self.assertRaises(ValueError): game_outcomes(report)

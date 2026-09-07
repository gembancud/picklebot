import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from player_skill_gate_games import validate_trace, validate_game_outcome


class SkillGateGameTests(unittest.TestCase):
    def fixture(self):
        records = [dict(player=p, candidateTeam=0, gameSeed=1141000, observationPlayer=p, identity=p,
                        observationTick=t, applyTick=t+6, rally=0, selectedExpert=int(t>0),
                        action=dict(moveX=0., moveZ=0., attempt=False, shot=0)) for t in (0, 12) for p in (0, 1)]
        game = dict(candidateTeam=0, gameSeed=1141000, rallies=1, identityBySeat=[0, 1, 2, 3],
                    decisionCounts=[2, 2, 0, 0], expertSelections=[2, 2], expertSwitches=[1, 1, 0, 0],
                    firstDecisions=[records[0], records[1], None, None])
        return records, game

    def test_owned_pairs_and_switches(self):
        self.assertEqual(validate_trace(*self.fixture())["decisions"], 4)

    def test_changed_owner_identity_time_or_pair_fail(self):
        for mutate in (lambda r: r[0].update(player=2), lambda r: r[0].update(identity=1),
                       lambda r: r[0].update(applyTick=12), lambda r: r[0].update(gameSeed=1200000),
                       lambda r: r.pop(), lambda r: r.reverse()):
            rows, game = self.fixture(); mutate(rows)
            with self.assertRaises(ValueError): validate_trace(rows, game)

    def test_missing_pair_counts_and_false_first_action_fail(self):
        for mutate in (lambda g: g.update(expertSelections=[4, 0]), lambda g: g.update(expertSwitches=[0]*4),
                       lambda g: g["firstDecisions"][0]["action"].update(attempt=True)):
            rows, game = self.fixture(); game = copy.deepcopy(game); mutate(game)
            with self.assertRaises(ValueError): validate_trace(rows, game)

    def outcome(self):
        return dict(games=[dict(complete=True, winner=1, score=[2,11], rallies=1, gameSeed=1141000,
                               candidateTeam=0, metrics=dict(legalHits=[1,2,3,4]),
                               motorViolations={"frozen baseline/Rally/paddleAcceleration":3})],
                    rallies=[dict(score=[2,11], winner=1, gameSeed=1141000, candidateTeam=0, legalHits=[1,2,3,4])])

    def test_complete_scores_and_baseline_disclosure(self):
        validate_game_outcome(self.outcome())

    def test_no_point_time_limit_is_retained_not_a_win(self):
        report = self.outcome(); report["games"][0]["rallies"] = 2
        limit = dict(gameSeed=1141000, candidateTeam=0, winner=-1, fault="None",
                     score=[0,0], seconds=31.003, legalHits=[0]*4)
        report["rallies"].insert(0, limit)
        self.assertEqual(validate_game_outcome(report)["truncatedRallies"], 1)
        for field, value in (("score", [1,0]), ("seconds", 10), ("fault", "Out")):
            changed = copy.deepcopy(report); changed["rallies"][0][field] = value
            with self.assertRaises(ValueError): validate_game_outcome(changed)

    def test_incomplete_score_hits_or_candidate_motor_fail(self):
        for mutate in (lambda r: r["games"][0].update(complete=False),
                       lambda r: r["games"][0].update(score=[2,10]),
                       lambda r: r["rallies"][0].update(legalHits=[0]*4),
                       lambda r: r["games"][0]["motorViolations"].update({"candidate guarded/Rally/paddleAcceleration":1})):
            report = self.outcome(); mutate(report)
            with self.assertRaises(ValueError): validate_game_outcome(report)


if __name__ == "__main__": unittest.main()

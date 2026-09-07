from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from player_actor import validate_four_player_curriculum


class FourPlayerCurriculumTests(unittest.TestCase):
    def fixture(self):
        rows = [dict(gameSeed=1026000, rally=0, tick=12, player=i, candidateTeam=-1) for i in range(4)]
        report = dict(seed=1026000, teacherDecisions=4, actorDecisions=0,
                      gameResults=[dict(gameSeed=1026000, candidateTeam=-1)])
        return rows, report

    def test_four_owned_simultaneous_decisions_are_accepted(self):
        rows, report = self.fixture(); validate_four_player_curriculum(rows, report)

    def test_missing_or_duplicate_player_is_rejected(self):
        rows, report = self.fixture(); rows[3] = rows[2].copy()
        with self.assertRaises(ValueError): validate_four_player_curriculum(rows, report)
        rows, report = self.fixture(); rows.pop(); report["teacherDecisions"] = 3
        with self.assertRaises(ValueError): validate_four_player_curriculum(rows, report)

    def test_wrong_game_team_tick_and_counts_are_rejected(self):
        for field, value in (("gameSeed", 1026001), ("candidateTeam", 0), ("tick", 13)):
            rows, report = self.fixture(); rows[0][field] = value
            with self.assertRaises(ValueError): validate_four_player_curriculum(rows, report)
        rows, report = self.fixture(); report["teacherDecisions"] = 3
        with self.assertRaises(ValueError): validate_four_player_curriculum(rows, report)


if __name__ == "__main__": unittest.main()

from pathlib import Path
import sys
import unittest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from player_self_play_audit import complete_game_signal


class SelfPlaySignalTests(unittest.TestCase):
    def test_carried_critic_changes_advantage_not_team_return(self):
        rows = [dict(gameSeed=1000000, criticObservation=[.3]),
                dict(gameSeed=1000001, criticObservation=[-.6])]
        games = [dict(seed=1000000, won=True), dict(seed=1000001, won=False)]
        result = complete_game_signal(rows, games, lambda x: x[:, 0])
        self.assertTrue(torch.allclose(result, torch.tensor([.7, -.4])))

    def test_same_team_outcome_can_have_different_player_advantages(self):
        rows = [dict(gameSeed=1000000, criticObservation=[-.7]),
                dict(gameSeed=1000000, criticObservation=[-.2])]
        result = complete_game_signal(rows, [dict(seed=1000000, won=False)], lambda x: x[:, 0])
        self.assertTrue(torch.allclose(result, torch.tensor([-.3, -.8])))

    def test_zero_residual_signal_is_rejected(self):
        rows = [dict(gameSeed=1000000, criticObservation=[-1.])]
        with self.assertRaisesRegex(ValueError, "policy-gradient signal"):
            complete_game_signal(rows, [dict(seed=1000000, won=False)], lambda x: x[:, 0])

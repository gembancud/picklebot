from pathlib import Path
import sys
import unittest

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from player_shot_audit import compare_outputs, nearby_expected_ball


class ShotAuditTests(unittest.TestCase):
    def test_nearby_filter_uses_current_ground_position_and_expected_team(self):
        observation = [0.] * 54
        observation[42] = observation[46] = 1
        observation[5] = 10  # This is not a contact-height test.
        self.assertTrue(nearby_expected_ball(observation))
        observation[4] = 1.5 / 8.4
        self.assertFalse(nearby_expected_ball(observation))
        observation[4] = 0; observation[46] = 0
        self.assertFalse(nearby_expected_ball(observation))

    def test_serve_setup_and_dead_states_are_excluded(self):
        observation = [0.] * 54; observation[46] = 1
        for phase in (39, 43):
            observation[phase] = 1
            self.assertFalse(nearby_expected_ball(observation))
            observation[phase] = 0
        with self.assertRaises(ValueError): nearby_expected_ball([0] * 53)

    def test_changed_shot_is_separate_from_nonshot_drift(self):
        reference = torch.zeros(2, 12); candidate = reference.clone()
        candidate[0, 7] = 2
        result = compare_outputs(reference, candidate)
        self.assertEqual(result["changedShotChoices"], 1)
        self.assertEqual(result["argmaxShots"], {0: 1, 4: 1})
        self.assertEqual(result["maximumNonshotOutputChange"], 0)
        candidate[1, 0] = .25
        self.assertEqual(compare_outputs(reference, candidate)["maximumNonshotOutputChange"], .25)

    def test_unchanged_argmax_does_not_hide_probability_changes(self):
        reference = torch.zeros(1, 12); reference[0, 3] = 1
        candidate = reference.clone(); candidate[0, 3] = 3
        before = compare_outputs(reference, reference); after = compare_outputs(reference, candidate)
        self.assertEqual(after["changedShotChoices"], 0)
        self.assertGreater(after["meanProbabilities"][0], before["meanProbabilities"][0])
        self.assertLess(after["meanShotEntropy"], before["meanShotEntropy"])

    def test_rejects_empty_mismatched_or_nonfinite_outputs(self):
        for candidate in (torch.zeros(0, 12), torch.zeros(1, 11), torch.full((1, 12), float("nan"))):
            with self.assertRaises(ValueError): compare_outputs(torch.zeros(1, 12), candidate)


if __name__ == "__main__": unittest.main()

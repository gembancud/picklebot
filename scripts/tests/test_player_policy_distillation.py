import sys
import unittest
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from player_policy_distillation import distillation_loss, neutral_paddle, source_weights


class PolicyDistillationTests(unittest.TestCase):
    def test_equal_outputs_have_zero_loss(self):
        torch.manual_seed(2); values = torch.randn(7, 12)
        self.assertAlmostEqual(float(distillation_loss(values, values)), 0, places=6)

    def test_target_does_not_receive_gradient(self):
        student = torch.zeros(3, 12, requires_grad=True)
        target = torch.ones(3, 12, requires_grad=True)
        distillation_loss(student, target).backward()
        self.assertIsNotNone(student.grad)
        self.assertIsNone(target.grad)

    def test_changed_movement_has_cost(self):
        target = torch.zeros(1, 12); student = target.clone(); student[0, 0] = 1
        self.assertGreater(float(distillation_loss(student, target)), 1)

    def test_changed_hit_has_cost(self):
        target = torch.zeros(1, 12); student = target.clone(); student[0, 2] = 2
        self.assertGreater(float(distillation_loss(student, target)), 0)

    def test_changed_shot_has_cost(self):
        target = torch.zeros(1, 12); student = target.clone(); student[0, 3] = 3
        self.assertGreater(float(distillation_loss(student, target)), 0)

    def test_invalid_shapes_and_nonfinite_fail(self):
        for values in (torch.zeros(1, 13), torch.zeros(0, 12), torch.full((1, 12), float("nan"))):
            with self.assertRaises(ValueError):
                distillation_loss(values, values)

    def test_neutralization_preserves_original_and_nonpaddle_inputs(self):
        original = torch.randn(8, 54); saved = original.clone()
        changed = neutral_paddle(original)
        self.assertTrue(torch.equal(original, saved))
        self.assertTrue(torch.equal(changed[:, :25], original[:, :25]))
        self.assertTrue(torch.equal(changed[:, 37:], original[:, 37:]))

    def test_equal_expected_mass_for_sources(self):
        weights = source_weights([2, 5])
        self.assertAlmostEqual(float(weights[:2].sum()), float(weights[2:].sum()))
        for invalid in ([], [0], [-1], [True]):
            with self.assertRaises(ValueError):
                source_weights(invalid)

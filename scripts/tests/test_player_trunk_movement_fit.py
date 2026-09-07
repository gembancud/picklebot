import copy
import importlib.util
from pathlib import Path
import sys
import unittest
import torch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from player_actor import Actor
spec = importlib.util.spec_from_file_location("trunk_fit", Path(__file__).resolve().parents[1] / "player-agents-fit-trunk-movement.py")
fit = importlib.util.module_from_spec(spec); spec.loader.exec_module(fit)


class TrunkMovementTests(unittest.TestCase):
    def test_retention_ignores_movement_logits_and_detaches_reference(self):
        current = torch.zeros(3, 12, requires_grad=True)
        reference = torch.zeros(3, 12, requires_grad=True)
        labels = torch.zeros(3, 5); labels[:, 4] = 1
        changed = current + torch.tensor([1., 1.] + [0.] * 10)
        total, movement, retention = fit.objective(changed, labels, reference)
        self.assertEqual(float(retention), 0)
        self.assertGreater(float(movement), 0)
        total.backward(); self.assertIsNone(reference.grad)

    def test_non_movement_logits_have_a_soft_penalty(self):
        current = torch.zeros(2, 12); current[:, 2:] = 2
        labels = torch.zeros(2, 5); labels[:, 4] = 1
        total, movement, retention = fit.objective(current, labels, torch.zeros_like(current))
        self.assertEqual(float(movement), 0); self.assertEqual(float(retention), 4)
        self.assertEqual(float(total), 4)

    def test_optimizer_changes_hidden_and_movement_only(self):
        torch.manual_seed(1000000)
        parent = Actor(16); candidate = copy.deepcopy(parent)
        fit.configure_training(candidate)
        optimizer = torch.optim.Adam([p for p in candidate.parameters() if p.requires_grad], lr=.001)
        x = torch.randn(32, 54); labels = torch.zeros(32, 5); labels[:, 4] = 1
        with torch.no_grad(): reference = parent(x)
        for _ in range(3):
            optimizer.zero_grad(set_to_none=True)
            fit.objective(candidate(x), labels, reference)[0].backward(); optimizer.step()
        fit.validate_frozen_parameters(parent, candidate)
        self.assertFalse(torch.equal(parent.layers[0].weight, candidate.layers[0].weight))
        self.assertFalse(torch.equal(parent.layers[-1].weight[:2], candidate.layers[-1].weight[:2]))
        self.assertFalse(torch.equal(parent(x)[:, 2:], candidate(x)[:, 2:]))

    def test_changed_hit_shot_or_exploration_parameters_fail(self):
        parent = Actor(16)
        for kind in ("hit", "shot", "exploration"):
            candidate = copy.deepcopy(parent)
            with torch.no_grad():
                if kind == "hit": candidate.layers[-1].bias[2] += .01
                elif kind == "shot": candidate.layers[-1].weight[3, 0] += .01
                else: candidate.log_std[0] += .01
            with self.assertRaises(ValueError): fit.validate_frozen_parameters(parent, candidate)

    def test_invalid_tensors_fail(self):
        labels = torch.zeros(2, 5); output = torch.zeros(2, 12)
        for bad in (torch.zeros(2, 11), torch.full((2, 12), float("nan"))):
            with self.assertRaises(ValueError): fit.objective(bad, labels, output)
        with self.assertRaises(ValueError): fit.objective(output, labels[:, :4], output)


if __name__ == "__main__": unittest.main()

"""Post-step trust-region rollback must preserve networks and Adam moments."""
import copy
from pathlib import Path
import sys
import unittest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from player_actor import Actor
from player_ppo import Critic, bounded_optimizer_step


class PPORollbackTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(7)
        self.actor, self.critic = Actor(hidden=4), Critic()
        self.aopt = torch.optim.Adam(self.actor.parameters(), lr=.01)
        self.copt = torch.optim.Adam(self.critic.parameters(), lr=.01)
        self.states = (self.actor, self.critic, self.aopt, self.copt)

    def loss(self):
        return sum(p.square().mean() for m in (self.actor, self.critic) for p in m.parameters())

    def step(self, measure):
        return bounded_optimizer_step(*self.states, self.loss(), measure, .01)

    def assert_state_equal(self, left, right):
        if isinstance(left, torch.Tensor): self.assertTrue(torch.equal(left, right))
        elif isinstance(left, dict):
            self.assertEqual(left.keys(), right.keys())
            for key in left: self.assert_state_equal(left[key], right[key])
        elif isinstance(left, (list, tuple)):
            self.assertEqual(len(left), len(right))
            for a, b in zip(left, right): self.assert_state_equal(a, b)
        else: self.assertEqual(left, right)

    def snapshot(self):
        return tuple(copy.deepcopy(item.state_dict()) for item in self.states)

    def test_accepted_step_changes_parameters_and_initializes_adam(self):
        before = self.actor.layers[0].weight.detach().clone()
        self.assertEqual(self.step(lambda: .002), (True, .002))
        self.assertFalse(torch.equal(before, self.actor.layers[0].weight))
        self.assertTrue(self.aopt.state); self.assertTrue(self.copt.state)

    def test_first_rejected_step_restores_empty_adam_state(self):
        before = self.snapshot()
        self.assertEqual(self.step(lambda: .02), (False, .02))
        self.assert_state_equal(before, self.snapshot())

    def test_rejection_restores_existing_adam_moments_and_step_counters(self):
        self.step(lambda: .002)
        for value in (.011, float("nan"), float("inf"), -.001):
            with self.subTest(value=value):
                before = self.snapshot()
                accepted, _ = self.step(lambda: value)
                self.assertFalse(accepted)
                self.assert_state_equal(before, self.snapshot())

    def test_failed_measurement_restores_all_four_states(self):
        self.step(lambda: .002); before = self.snapshot()
        def fail(): raise RuntimeError("measurement failed")
        with self.assertRaisesRegex(RuntimeError, "measurement failed"): self.step(fail)
        self.assert_state_equal(before, self.snapshot())

    def test_accepted_bound_is_inclusive(self):
        self.assertEqual(self.step(lambda: .01), (True, .01))

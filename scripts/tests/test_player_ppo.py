from pathlib import Path
import sys
import unittest
import math
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from player_actor import Actor
from player_ppo import Critic, advantages, clipped_loss, log_probability, validate_episodes, validate_motor_metrics, freeze_nonshot_heads, nonshot_parameters, return_parameters, prepare_advantages


class PPOTests(unittest.TestCase):
    def test_constant_normalized_returns_cannot_silently_train_entropy_only(self):
        for reward in (-1., 0., 1.):
            with self.assertRaisesRegex(ValueError, "policy-gradient signal"):
                prepare_advantages(torch.full((8,), reward))

    def test_raw_complete_game_losses_keep_their_sign(self):
        original = -torch.ones(8)
        actual = prepare_advantages(original, "none")
        self.assertTrue(torch.equal(actual, original))
        actual[0] = 0
        self.assertEqual(original[0], -1)

    def test_mixed_normalization_preserves_existing_formula(self):
        original = torch.tensor([-1., -1., 1., .2])
        expected = (original-original.mean())/original.std(unbiased=False)
        self.assertTrue(torch.equal(prepare_advantages(original), expected))

    def test_invalid_advantages_are_rejected(self):
        for value in (torch.zeros(0), torch.zeros(2, 2), torch.tensor([float("nan")])):
            with self.assertRaises(ValueError): prepare_advantages(value, "none")
        with self.assertRaises(ValueError): prepare_advantages(torch.ones(2), "unknown")

    def test_raw_negative_advantage_has_a_policy_gradient_without_entropy(self):
        logp = torch.zeros(4, requires_grad=True)
        loss, _ = clipped_loss(logp, logp.detach(), prepare_advantages(-torch.ones(4), "none"))
        loss.backward()
        self.assertTrue(torch.all(logp.grad > 0))

    def test_default_returns_preserve_existing_objectives(self):
        self.assertEqual(return_parameters("rally_win"), (.995, .95))
        for mode in ("default", "full_episode"):
            self.assertEqual(return_parameters("game_win", mode), (1., 1.))

    def test_full_episode_credit_reaches_early_rally_decisions(self):
        reward = torch.zeros(100); reward[-1] = 1
        values = torch.linspace(-.7, .8, 100)
        terminal = torch.zeros(100, dtype=torch.bool); terminal[-1] = True
        gamma, lam = return_parameters("rally_win", "full_episode")
        advantage, target = advantages(reward, values, terminal, gamma=gamma, gae_lambda=lam)
        self.assertTrue(torch.allclose(target, torch.ones(100), atol=1e-6))
        self.assertTrue(torch.allclose(advantage, 1-values, atol=1e-6))
        reward[-1] = -1
        _, target = advantages(reward, values, terminal, gamma=gamma, gae_lambda=lam)
        self.assertTrue(torch.allclose(target, -torch.ones(100), atol=1e-6))

    def test_unknown_credit_assignment_is_rejected(self):
        for reward, mode in (("rally_win", "unknown"), ("shaped", "default")):
            with self.assertRaises(ValueError): return_parameters(reward, mode)

    @staticmethod
    def motor_report(team=0):
        metrics = dict(infeasiblePaddleSteps=0, playerMaxSpeed=[3.8]*4,
                       playerMaxAcceleration=[14.01]*4, playerMaxPaddleSpeed=[12.0]*4,
                       playerMaxPaddleAcceleration=[100.03]*4, playerMaxReach=[.62]*4)
        return dict(games=[dict(candidateTeam=team, metrics=metrics)])

    def test_motor_gate_checks_both_candidate_seats_and_court_ends(self):
        for team in (0, 1):
            validate_motor_metrics(self.motor_report(team))
            for player in range(team * 2, team * 2 + 2):
                for field, value in (("playerMaxSpeed", 4), ("playerMaxAcceleration", 15),
                                     ("playerMaxPaddleSpeed", 13), ("playerMaxPaddleAcceleration", 101),
                                     ("playerMaxReach", .63)):
                    report = self.motor_report(team)
                    report["games"][0]["metrics"][field][player] = value
                    with self.assertRaises(ValueError): validate_motor_metrics(report)

    def test_motor_gate_keeps_frozen_opponent_measurements_separate(self):
        for team in (0, 1):
            report = self.motor_report(team)
            report["games"][0]["metrics"]["playerMaxPaddleAcceleration"][(1-team)*2] = 900
            validate_motor_metrics(report)

    def test_motor_gate_checks_saved_actor_opponents_on_both_ends(self):
        for team in (0, 1):
            report = self.motor_report(team)
            report["opponentMode"] = "older actor / sampled"
            validate_motor_metrics(report)
            for player in range((1 - team) * 2, (1 - team) * 2 + 2):
                for field, value in (("playerMaxSpeed", 4), ("playerMaxAcceleration", 15),
                                     ("playerMaxPaddleSpeed", 13), ("playerMaxPaddleAcceleration", 101),
                                     ("playerMaxReach", .63)):
                    with self.subTest(team=team, player=player, field=field):
                        unsafe = self.motor_report(team)
                        unsafe["opponentMode"] = "older actor / sampled"
                        unsafe["games"][0]["metrics"][field][player] = value
                        with self.assertRaises(ValueError): validate_motor_metrics(unsafe)

    def test_motor_gate_explicit_baseline_modes_keep_the_original_motor(self):
        for mode in ("baseline / sampled", "baseline / maximum probability"):
            for team in (0, 1):
                report = self.motor_report(team)
                report["opponentMode"] = mode
                report["games"][0]["metrics"]["playerMaxPaddleAcceleration"][(1 - team) * 2] = 900
                validate_motor_metrics(report)

    def test_motor_gate_rejects_missing_nonfinite_and_infeasible_measurements(self):
        for invalid in (float("nan"), float("inf"), -1, None, True):
            report = self.motor_report()
            report["games"][0]["metrics"]["playerMaxReach"][0] = invalid
            with self.assertRaises(ValueError): validate_motor_metrics(report)
        report = self.motor_report(); report["games"][0]["metrics"]["infeasiblePaddleSteps"] = 1
        with self.assertRaises(ValueError): validate_motor_metrics(report)
        report = self.motor_report(); del report["games"][0]["metrics"]["playerMaxSpeed"]
        with self.assertRaises(ValueError): validate_motor_metrics(report)
        with self.assertRaises(ValueError): validate_motor_metrics({"games": []})

    def test_shot_training_preserves_movement_and_hit_outputs_exactly(self):
        torch.manual_seed(1)
        actor = Actor(8); observation = torch.randn(16, 54)
        original = actor(observation).detach().clone(); protected = nonshot_parameters(actor)
        freeze_nonshot_heads(actor)
        optimizer = torch.optim.Adam((p for p in actor.parameters() if p.requires_grad), lr=.01, weight_decay=0)
        for _ in range(5):
            optimizer.zero_grad(); actor(observation).square().sum().backward(); optimizer.step()
        after = actor(observation).detach()
        self.assertTrue(torch.equal(original[:, :3], after[:, :3]))
        self.assertFalse(torch.equal(original[:, 3:], after[:, 3:]))
        self.assertTrue(all(torch.equal(a, b) for a, b in zip(protected, nonshot_parameters(actor))))

    @staticmethod
    def episode():
        rows = [dict(episode="1000600/0", player=i, candidateTeam=0, gameSeed=1000600, rally=0, tick=12,
                     observation=[float(i)] * 54, criticObservation=([float(i)] * 54 + [float(i ^ 1)] * 54), reward=1, terminal=True) for i in range(2)]
        report = dict(rewardMode="rally_win", games=[dict(gameSeed=1000600, winner=0)], rallies=[dict(gameSeed=1000600, winner=0)])
        return rows, report

    def test_teammates_receive_the_same_recorded_team_reward(self):
        rows, report = self.episode()
        self.assertEqual(len(validate_episodes(rows, report)), 2)
        rows[1]["reward"] = -1
        with self.assertRaises(ValueError): validate_episodes(rows, report)

    def test_critic_does_not_receive_a_different_tick_or_players_observation(self):
        rows, report = self.episode(); rows[0]["criticObservation"][60] = 999
        with self.assertRaises(ValueError): validate_episodes(rows, report)
        rows, report = self.episode(); rows[1]["tick"] = 24
        with self.assertRaises(ValueError): validate_episodes(rows, report)

    def test_game_objective_uses_game_winner_not_rally_winner(self):
        rows, report = self.episode(); report["rewardMode"] = "game_win"; report["games"][0]["winner"] = 1
        for row in rows: row["reward"] = -1
        validate_episodes(rows, report)
        rows[0]["reward"] = 1
        with self.assertRaises(ValueError): validate_episodes(rows, report)

    def test_log_probability_matches_manual_independent_heads(self):
        actor = Actor(8)
        with torch.no_grad():
            for layer in actor.layers: layer.weight.zero_(); layer.bias.zero_()
            actor.log_std.zero_()
        logp, entropy = log_probability(actor, torch.zeros(1, 54), torch.zeros(1, 2), torch.ones(1), torch.zeros(1, dtype=torch.long))
        self.assertAlmostEqual(logp.item(), -math.log(2 * math.pi) - math.log(2) - math.log(9), places=5)
        self.assertTrue(torch.isfinite(entropy).all())

    def test_advantages_stop_at_terminal(self):
        reward = torch.tensor([0., 1., 0., -1.]); value = torch.zeros(4); done = torch.tensor([False, True, False, True])
        advantage, target = advantages(reward, value, done, gamma=1, gae_lambda=1)
        self.assertTrue(torch.equal(target, torch.tensor([1., 1., -1., -1.])))
        self.assertTrue(torch.equal(target, advantage))

    def test_incomplete_trajectory_is_not_silently_zero_bootstrapped(self):
        with self.assertRaises(ValueError): advantages(torch.zeros(2), torch.zeros(2), torch.tensor([False, False]))

    def test_clipping_preserves_positive_and_negative_advantage_signs(self):
        logp = torch.tensor([math.log(2), math.log(.5)], requires_grad=True)
        loss, kl = clipped_loss(logp, torch.zeros(2), torch.tensor([1., -1.]))
        self.assertAlmostEqual(loss.item(), -.2, places=6)
        loss.backward(); self.assertTrue(torch.equal(logp.grad, torch.zeros(2))); self.assertGreater(kl.item(), 0)

    def test_critic_has_no_actor_parameter_or_output_dependency(self):
        actor = Actor(8); critic = Critic(); observation = torch.randn(4, 54)
        expected = actor(observation).detach().clone()
        critic(torch.randn(4, 108)).sum().backward()
        self.assertTrue(all(p.grad is None for p in actor.parameters()))
        self.assertTrue(torch.equal(actor(observation).detach(), expected))


if __name__ == "__main__": unittest.main()

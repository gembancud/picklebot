"""Transport/lifecycle tests plus a real pinned-PPO update parity test."""
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import numpy as np
from mlagents.torch_utils import torch
from mlagents_envs.base_env import (ActionSpec, ActionTuple, BehaviorSpec,
    DecisionSteps, TerminalSteps, ObservationSpec, DimensionProperty, ObservationType)
from mlagents_envs.side_channel.stats_side_channel import StatsAggregationMethod
from mlagents.trainers.agent_processor import AgentManager
from mlagents.trainers.action_info import ActionInfo
from mlagents.trainers.env_manager import EnvManager, EnvironmentStep
from mlagents.trainers.stats import StatsReporter
from mlagents.trainers.torch_entities.action_log_probs import LogProbsTuple
from mlagents.trainers.trajectory import Trajectory, AgentExperience
from mlagents.trainers.ppo.trainer import PPOTrainer
from mlagents.trainers.ppo.optimizer_torch import PPOSettings
from mlagents.trainers.settings import TrainerSettings, NetworkSettings, ScheduleType
from mlagents.trainers.behavior_id_utils import BehaviorIdentifiers

from stability_diagnostics import (UpdateDiagnostics, DiagnosticError, Label,
    classify_index, install_diagnostics, PREFIX)

BEHAVIOR = "PicklebotArticulated?team=0"


def observation_spec(size=124):
    return ObservationSpec((size,), (DimensionProperty.NONE,), ObservationType.DEFAULT, "VectorSensor_size124")


SPEC = BehaviorSpec([observation_spec()], ActionSpec(16, (2,)))


def decision(agent=4):
    return DecisionSteps([np.zeros((1, 124), np.float32)], np.ones(1, np.float32),
        np.array([agent], np.int32), [np.array([[False, True]])],
        np.zeros(1, np.int32), np.zeros(1, np.float32))


def terminal(agent=4):
    return TerminalSteps([np.ones((1, 124), np.float32)], np.ones(1, np.float32),
        np.zeros(1, bool), np.array([agent], np.int32),
        np.zeros(1, np.int32), np.zeros(1, np.float32))


def action(agent=4):
    actions = ActionTuple(np.zeros((1, 16), np.float32), np.zeros((1, 1), np.int32))
    return ActionInfo(actions, actions,
        {"action": actions, "log_probs": LogProbsTuple(np.zeros((1, 16), np.float32), np.zeros((1, 1), np.float32))}, [agent])


def raw(index):
    return [(float(index), StatsAggregationMethod.AVERAGE)]


def fake_env_processor():
    policy = Mock()
    policy.use_recurrent = False
    policy.retrieve_previous_action.return_value = np.zeros((1, 17), np.float32)
    manager = AgentManager(policy, BEHAVIOR, StatsReporter("diagnostic-test"),
                           max_trajectory_length=2, threaded=False)
    env = SimpleNamespace(agent_managers={BEHAVIOR: manager})
    return env, manager


def send(env, worker=0, d=None, t=None, previous=None, stats=None):
    info = EnvironmentStep({BEHAVIOR: (d if d is not None else DecisionSteps.empty(SPEC),
        t if t is not None else TerminalSteps.empty(SPEC))}, worker,
        {BEHAVIOR: previous or ActionInfo.empty()}, stats or {})
    return EnvManager._process_step_infos(env, [info])


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.path = Path(self.temp.name) / "diagnostics.jsonl"
        self.diag = None

    def tearDown(self):
        if self.diag is not None:
            self.diag.close()
        self.temp.cleanup()

    def install(self):
        self.diag = install_diagnostics(self.path)
        return self.diag

    def test_full_cycle_classifier(self):
        groups = {"familiar": 0, "prior": 0, "focus": 0}
        focus = {}
        for i in range(256):
            row = classify_index(i)
            groups[row["group"]] += 1
            if row["group"] == "focus":
                key = (row["mode"], row["side"])
                focus[key] = focus.get(key, 0) + 1
        self.assertEqual(groups, {"familiar": 64, "prior": 64, "focus": 128})
        self.assertEqual(focus, {("air", "left"): 32, ("air", "right"): 32,
                                ("bounce", "left"): 48, ("bounce", "right"): 16})

    def test_transport_preserves_raw_values_and_strips_keys(self):
        original = {PREFIX + "4/D": raw(0) + raw(4), PREFIX + "4/T": raw(0),
                    "Picklebot/LegalReturn": raw(1)}
        labels, clean = UpdateDiagnostics.extract_metadata(original)
        self.assertEqual(labels, {(4, "D"): 4, (4, "T"): 0})
        self.assertEqual(clean, {"Picklebot/LegalReturn": raw(1)})
        self.assertEqual(len(original), 3)

    def test_bad_transport_is_rejected(self):
        for data in ({PREFIX + "4/D": raw(.5)}, {PREFIX + "4/D": raw(2**24)},
                     {PREFIX + "4/D": raw(1) + raw(2)},
                     {PREFIX + "4/T": raw(1) + raw(2)},
                     {PREFIX + "4/X": raw(1)}):
            with self.subTest(data=data), self.assertRaises(DiagnosticError):
                UpdateDiagnostics.extract_metadata(data)

    def test_initial_reset_and_horizon_segment(self):
        diag = self.install()
        env, manager = fake_env_processor()
        send(env, d=decision())  # RESET response has no stats yet.
        send(env, d=decision(), previous=action(), stats={PREFIX + "4/D": raw(64) + raw(64)})
        send(env, d=decision(), previous=action(), stats={PREFIX + "4/D": raw(64)})
        trajectory = manager.trajectory_queue.get_nowait()
        self.assertEqual(len(trajectory.steps), 2)
        self.assertEqual(diag.queued[id(trajectory)][1], Label(0, 4, 64, BEHAVIOR))

    def test_terminal_and_new_decision_same_id_keep_immutable_label(self):
        diag = self.install()
        env, manager = fake_env_processor()
        send(env, d=decision())
        send(env, d=decision(), t=terminal(), previous=action(),
             stats={PREFIX + "4/D": raw(64) + raw(128), PREFIX + "4/T": raw(64)})
        old = manager.trajectory_queue.get_nowait()
        send(env, d=decision(), previous=action(), stats={PREFIX + "4/D": raw(128)})
        send(env, t=terminal(), previous=action(), stats={PREFIX + "4/T": raw(128)})
        new = manager.trajectory_queue.get_nowait()
        self.assertEqual(diag.queued[id(old)][1].index, 64)
        self.assertEqual(diag.queued[id(new)][1].index, 128)
        self.assertEqual(len(old.steps), 1)
        self.assertEqual(len(new.steps), 2)

    def test_worker_ids_and_diagnostic_stats_do_not_leak(self):
        diag = self.install()
        env, manager = fake_env_processor()
        manager.record_environment_stats = Mock(wraps=manager.record_environment_stats)
        for worker, index in ((0, 64), (1, 128)):
            send(env, worker=worker, d=decision())
            send(env, worker=worker, t=terminal(), previous=action(),
                 stats={PREFIX + "4/T": raw(index), "Picklebot/Test": raw(1)})
        labels = [diag.queued[id(manager.trajectory_queue.get_nowait())][1] for _ in range(2)]
        self.assertEqual({(l.worker, l.index) for l in labels}, {(0, 64), (1, 128)})
        for call in manager.record_environment_stats.call_args_list:
            self.assertFalse(any(k.startswith(PREFIX) for k in call.args[0]))

    def test_missing_experience_metadata_fails(self):
        self.install()
        env, manager = fake_env_processor()
        send(env, d=decision())
        with self.assertRaisesRegex(DiagnosticError, "Missing metadata"):
            send(env, d=decision(), previous=action())

    def test_unterminated_episode_change_fails(self):
        self.install()
        env, manager = fake_env_processor()
        send(env, d=decision(), stats={PREFIX + "4/D": raw(64)})
        with self.assertRaisesRegex(DiagnosticError, "crossed an episode boundary"):
            send(env, d=decision(), previous=action(), stats={PREFIX + "4/D": raw(128)})

    def test_inactive_shutdown_terminal_does_not_create_experience(self):
        diag = self.install()
        env, manager = fake_env_processor()
        send(env, t=terminal(), stats={PREFIX + "4/T": raw(128)})
        self.assertTrue(manager.trajectory_queue.empty())
        self.assertFalse(diag.queued)
        self.assertFalse(diag.active_episode)

    def test_forced_reset_clears_only_episode_context(self):
        diag = self.install()
        env, manager = fake_env_processor()
        send(env, d=decision(), stats={PREFIX + "4/D": raw(64)})
        send(env, d=decision(), previous=action(), stats={PREFIX + "4/D": raw(64)})
        manager.end_episode()  # Same method called by EnvManager.reset().
        self.assertFalse(diag.active_episode)
        send(env, d=decision())
        send(env, t=terminal(), previous=action(), stats={PREFIX + "4/T": raw(128)})
        trajectory = manager.trajectory_queue.get_nowait()
        self.assertEqual(len(trajectory.steps), 1)
        self.assertEqual(diag.queued[id(trajectory)][1].index, 128)

    def test_actual_ppo_update_is_bitwise_identical(self):
        def run(instrumented):
            np.random.seed(7123)
            torch.manual_seed(7123)
            settings = TrainerSettings(
                hyperparameters=PPOSettings(batch_size=4, buffer_size=8, num_epoch=3,
                    learning_rate=1e-4, learning_rate_schedule=ScheduleType.CONSTANT,
                    beta_schedule=ScheduleType.CONSTANT, epsilon_schedule=ScheduleType.CONSTANT),
                network_settings=NetworkSettings(normalize=True, hidden_units=128, num_layers=2),
                max_steps=10000, summary_freq=10000, checkpoint_interval=10000)
            trainer = PPOTrainer("PicklebotArticulated", 10, settings, True, False, 7123,
                                 str(Path(self.temp.name) / ("instrumented" if instrumented else "plain")))
            parsed = BehaviorIdentifiers.from_name_behavior_id(BEHAVIOR)
            policy = trainer.create_policy(parsed, SPEC)
            trainer.add_policy(parsed, policy)
            if instrumented:
                self.install()
            rng = np.random.RandomState(9981)
            for episode_index, length in ((0, 7), (64, 8), (128, 6), (192, 6)):
                exps = []
                for step in range(length):
                    exps.append(AgentExperience(
                        obs=[rng.normal(size=124).astype(np.float32)],
                        reward=float(rng.uniform(-1, 1)), done=step == length - 1,
                        action=ActionTuple(np.zeros(16, np.float32), np.zeros(1, np.int32)),
                        action_probs=LogProbsTuple(np.zeros(16, np.float32), np.zeros(1, np.float32)),
                        action_mask=[np.array([False, True])], prev_action=np.zeros(17, np.float32),
                        interrupted=False, memory=None, group_status=[], group_reward=0.0))
                traj = Trajectory(exps, [np.zeros(124, np.float32)], [], "agent_0-4", BEHAVIOR)
                if instrumented:
                    self.diag.queued[id(traj)] = (traj, Label(0, 4, episode_index, BEHAVIOR))
                trainer._process_trajectory(traj)
            buffer_keys = set(trainer.update_buffer.keys())
            before_np = copy.deepcopy(np.random.get_state())
            trainer._update_policy()
            # Inference/drain trajectories after training stops are still
            # processed by the vendor but must not enter either update buffer.
            trainer.is_training = False
            if instrumented:
                self.diag.queued[id(traj)] = (traj, Label(0, 4, 192, BEHAVIOR))
            trainer._process_trajectory(traj)
            self.assertEqual(trainer.update_buffer.num_experiences, 0)
            if instrumented:
                self.assertFalse(self.diag.shadows[id(trainer)])
                self.assertFalse(self.diag.queued)
            result = (copy.deepcopy(policy.actor.state_dict()),
                      copy.deepcopy(trainer.optimizer.critic.state_dict()),
                      copy.deepcopy(trainer.optimizer.optimizer.state_dict()),
                      copy.deepcopy(np.random.get_state()), torch.get_rng_state().clone(),
                      buffer_keys, before_np,
                      [x.clone() for x in torch.cuda.get_rng_state_all()] if torch.cuda.is_available() else [])
            return result

        plain, logged = run(False), run(True)

        def equal(a, b):
            if isinstance(a, torch.Tensor):
                self.assertTrue(torch.equal(a, b))
            elif isinstance(a, np.ndarray):
                np.testing.assert_array_equal(a, b)
            elif isinstance(a, dict):
                self.assertEqual(a.keys(), b.keys())
                for key in a:
                    equal(a[key], b[key])
            elif isinstance(a, (tuple, list)):
                self.assertEqual(len(a), len(b))
                for x, y in zip(a, b):
                    equal(x, y)
            else:
                self.assertEqual(a, b)
        equal(plain, logged)
        rows = [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines()]
        record = next(r for r in rows if r["event"] == "update_prepared")
        self.assertEqual(record["bufferExperiences"], 27)
        self.assertEqual({k: v["count"] for k, v in record["groups"].items()},
                         {"familiar": 7, "prior": 8, "focus": 12})
        self.assertEqual(record["remainderNotUsedInEachEpoch"], 3)
        self.assertEqual(record["optimizerMinibatchesPerEpoch"], 6)
        self.assertTrue(any(r["event"] == "update_completed" for r in rows))
        critic_rows=[json.loads(x) for x in self.path.with_name('critic-episodes.jsonl').read_text().splitlines()]
        self.assertEqual(len(critic_rows), 4)
        self.assertTrue(all(x['predictionSource'].startswith('captured ') for x in critic_rows))
        learning=[json.loads(x) for x in self.path.with_name('learning-updates.jsonl').read_text().splitlines() if json.loads(x)['event']=='learning_update'][0]
        self.assertTrue(any(x['storedCritic']['rmse']>1e-5 for x in learning['groups'].values()))


if __name__ == "__main__":
    unittest.main(verbosity=2)

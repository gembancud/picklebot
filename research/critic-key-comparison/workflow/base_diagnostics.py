"""Read-only PPO update telemetry for the pinned Picklebot solo trainer.

Unity sends __picklebot_diag/<Agent.m_EpisodeId>/<D|T> with the ORIGINAL
recovery-schedule episode index as a float. This is transport metadata, never
an observation/reward/buffer field. Vendor methods still own every RL operation.
"""
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping
import json
import math
import os
import threading

import numpy as np

PREFIX = "__picklebot_diag/"


def classify_index(index: int) -> dict:
    """Mirror PlayerRecoveryScheduleV3; index is BEFORE any order permutation."""
    if not isinstance(index, int) or index < 0:
        raise ValueError("Expected a nonnegative original episode index")
    block = index // 4 % 64
    result = {"seat": index % 4, "block": block}
    if block < 16:
        basic = block % 8
        task = ("stationary-serve" if basic < 2 else "receive-feed" if basic < 4
                else "rally-air-feed" if basic < 6 else "rally-bounce-feed")
        result.update(group="familiar", task=task, pattern="court",
                      mode="serve" if basic < 2 else "receive" if basic < 4
                      else "air" if basic < 6 else "bounce", side="na", range=0.0)
    else:
        prior = block < 32
        air = block < 24 if prior else block < 48
        left = block < 40 or 48 <= block < 60
        fraction = (1 + block % 4) * .25
        result.update(group="prior" if prior else "focus",
                      task="rally-air-feed" if air else "rally-bounce-feed",
                      mode="air" if air else "bounce",
                      pattern="court" if prior else "lateral-left" if left else "lateral-right",
                      side="na" if prior else "left" if left else "right",
                      range=(.1 if prior else .025) * fraction)
    return result


@dataclass(frozen=True)
class Label:
    worker: int
    agent: int
    index: int
    behavior: str


class DiagnosticError(RuntimeError):
    pass


class UpdateDiagnostics:
    def __init__(self, output_path, classifier: Callable[[int], Mapping] = classify_index):
        self.path = Path(output_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.output = self.path.open("x", encoding="utf-8", buffering=1)
        self.classifier = classifier
        self.owner_thread = threading.get_ident()
        self.step_context = None
        self.batch_labels = None
        self.queued = {}  # id(Trajectory) -> (same object, immutable label)
        self.shadows = defaultdict(list)
        self.active_episode = {}  # (behavior,worker,agent) -> original index
        self.patches = []
        self.update_number = 0
        self._write({"event": "installed", "schema": 1,
                     "semantics": "fresh update-buffer experiences, before shuffle and advantage normalization",
                     "metadataInObservations": False, "metadataInBuffer": False})

    def _check_thread(self):
        if threading.get_ident() != self.owner_thread:
            raise DiagnosticError("Diagnostics require the pinned non-threaded trainer")

    def _write(self, record):
        self.output.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")

    @staticmethod
    def extract_metadata(stats):
        labels, clean = {}, {}
        for key, entries in stats.items():
            if not key.startswith(PREFIX):
                clean[key] = entries
                continue
            suffix = key[len(PREFIX):].split("/")
            if len(suffix) != 2 or suffix[1] not in ("D", "T"):
                raise DiagnosticError("Malformed diagnostic metadata key: " + key)
            try:
                agent = int(suffix[0])
            except ValueError as exc:
                raise DiagnosticError("Invalid diagnostic agent id") from exc
            values = []
            for value, _aggregation in entries:
                if not math.isfinite(value) or value < 0 or value >= 2 ** 24 or int(value) != value:
                    raise DiagnosticError("Episode index must be an exact nonnegative float32 integer")
                values.append(int(value))
            if not values:
                raise DiagnosticError("Empty diagnostic metadata")
            labels[(agent, suffix[1])] = values
        # A reset's first D message can remain in StatsSideChannel until its
        # first STEP. If old terminal and new decision coexist, D may carry both.
        for (agent, phase), values in labels.items():
            distinct = set(values)
            if phase == "T" and len(distinct) != 1:
                raise DiagnosticError("Multiple terminal episodes for one agent in one response")
            if phase == "D" and len(distinct) > 1:
                terminal = labels.get((agent, "T"), [])
                if not terminal or distinct != {terminal[-1], values[-1]}:
                    raise DiagnosticError("Unexplained decision-episode transition in one response")
        return {key: values[-1] for key, values in labels.items()}, clean

    def _patch(self, cls, name, wrapper):
        original = getattr(cls, name)
        replacement = wrapper(original)
        setattr(cls, name, replacement)
        self.patches.append((cls, name, original, replacement))

    def install(self):
        from mlagents.trainers.env_manager import EnvManager
        from mlagents.trainers.agent_processor import AgentProcessor, AgentManagerQueue
        from mlagents.trainers.trajectory import Trajectory
        from mlagents.trainers.ppo.trainer import PPOTrainer
        from mlagents.trainers.trainer.on_policy_trainer import OnPolicyTrainer
        from mlagents.trainers.trainer.rl_trainer import RLTrainer
        from mlagents.trainers.behavior_id_utils import get_global_agent_id
        from mlagents_envs.base_env import TerminalStep

        def env_wrapper(original):
            def wrapped(manager, step_infos):
                self._check_thread()
                total = 0
                for info in step_infos:
                    labels, clean = self.extract_metadata(info.environment_stats)
                    if self.batch_labels is not None:
                        raise DiagnosticError("Nested environment-step processing")
                    self.batch_labels = (info.worker_id, labels)
                    try:
                        total += original(manager, [info._replace(environment_stats=clean)])
                    finally:
                        self.batch_labels = None
                return total
            return wrapped

        def process_step_wrapper(original):
            def wrapped(processor, step, worker_id, index):
                self._check_thread()
                if self.batch_labels is None or self.batch_labels[0] != worker_id:
                    raise DiagnosticError("Agent processing outside its diagnostic environment response")
                phase = "T" if isinstance(step, TerminalStep) else "D"
                seed_index = self.batch_labels[1].get((int(step.agent_id), phase))
                gid = get_global_agent_id(worker_id, step.agent_id)
                identity = (processor._behavior_id, worker_id, int(step.agent_id))
                previous_step = processor._last_step_result.get(gid, (None, None))[0]
                previous_action = processor._last_take_action_outputs.get(gid)
                creates_experience = previous_step is not None and previous_action is not None
                # The first RESET response contains no environment_stats. Permit
                # it only when there is no action-derived experience to label.
                if seed_index is None and creates_experience:
                    raise DiagnosticError("Missing metadata for an actual training experience")
                if seed_index is not None:
                    previous_index = self.active_episode.get(identity)
                    if creates_experience and previous_index is not None and previous_index != seed_index:
                        raise DiagnosticError("Trajectory crossed an episode boundary without terminal cleanup")
                    self.active_episode[identity] = seed_index
                label = None if seed_index is None else Label(worker_id, int(step.agent_id), seed_index, processor._behavior_id)
                old_context = self.step_context
                self.step_context = label
                try:
                    return original(processor, step, worker_id, index)
                finally:
                    self.step_context = old_context
                    if phase == "T":
                        self.active_episode.pop(identity, None)
            return wrapped

        def queue_wrapper(original):
            def wrapped(queue, item):
                if isinstance(item, Trajectory):
                    self._check_thread()
                    label = self.step_context
                    if label is None or item.agent_id != get_global_agent_id(label.worker, label.agent) or item.behavior_id != label.behavior:
                        raise DiagnosticError("Queued trajectory identity does not match diagnostic context")
                    if id(item) in self.queued:
                        raise DiagnosticError("Trajectory published more than once; solo PPO expected")
                    self.queued[id(item)] = (item, label)
                return original(queue, item)
            return wrapped

        def trajectory_wrapper(original):
            def wrapped(trainer, trajectory):
                self._check_thread()
                if trainer.policy.sequence_length != 1:
                    raise DiagnosticError("Telemetry is validated for the current feed-forward policy only")
                record = self.queued.pop(id(trajectory), None)
                if record is None or record[0] is not trajectory:
                    raise DiagnosticError("Trajectory has no immutable diagnostic label")
                before = trainer.update_buffer.num_experiences
                result = original(trainer, trajectory)
                after = trainer.update_buffer.num_experiences
                added = after - before
                if added not in (0, len(trajectory.steps)):
                    raise DiagnosticError("Unexpected trajectory resequencing or buffer mutation")
                self.shadows[id(trainer)].extend([record[1]] * added)
                if len(self.shadows[id(trainer)]) != after:
                    raise DiagnosticError("Shadow labels and actual PPO buffer diverged")
                return result
            return wrapped

        def update_wrapper(original):
            def wrapped(trainer):
                self._check_thread()
                self.update_number += 1
                snapshot = self.snapshot(trainer)
                snapshot.update(event="update_prepared", update=self.update_number)
                self._write(snapshot)
                result = original(trainer)
                if self.shadows[id(trainer)] or trainer.update_buffer.num_experiences:
                    raise DiagnosticError("PPO update did not clear its fresh buffer and shadow labels")
                self._write({"event": "update_completed", "update": self.update_number,
                             "policyStep": int(trainer.policy.get_current_step())})
                return result
            return wrapped

        def clear_wrapper(original):
            def wrapped(trainer):
                result = original(trainer)
                self.shadows[id(trainer)].clear()
                return result
            return wrapped

        def end_episode_wrapper(original):
            def wrapped(processor):
                # EnvManager.reset() cleans AgentProcessor state without a
                # terminal _process_step for every agent. Mirror only that
                # diagnostic context cleanup; queued trajectories remain valid.
                result = original(processor)
                for identity in list(self.active_episode):
                    if identity[0] == processor._behavior_id:
                        self.active_episode.pop(identity)
                return result
            return wrapped

        self._patch(EnvManager, "_process_step_infos", env_wrapper)
        self._patch(AgentProcessor, "_process_step", process_step_wrapper)
        self._patch(AgentProcessor, "end_episode", end_episode_wrapper)
        self._patch(AgentManagerQueue, "put", queue_wrapper)
        self._patch(PPOTrainer, "_process_trajectory", trajectory_wrapper)
        self._patch(OnPolicyTrainer, "_update_policy", update_wrapper)
        self._patch(RLTrainer, "_clear_update_buffer", clear_wrapper)
        return self

    def snapshot(self, trainer):
        from mlagents.trainers.buffer import BufferKey
        labels = self.shadows[id(trainer)]
        n = trainer.update_buffer.num_experiences
        if n != len(labels) or not n:
            raise DiagnosticError("Missing or misaligned update-buffer labels")
        advantages = np.asarray(trainer.update_buffer[BufferKey.ADVANTAGES].get_batch(), dtype=np.float64)
        if advantages.shape != (n,) or not np.isfinite(advantages).all():
            raise DiagnosticError("Invalid raw advantages for buffer diagnostic")
        groups = defaultdict(list)
        scenarios = Counter()
        workers = Counter()
        for position, label in enumerate(labels):
            description = self.classifier(label.index)
            groups[str(description["group"])].append(position)
            key = "/".join(str(description.get(k, "na")) for k in ("group", "mode", "pattern", "side", "range"))
            scenarios[key] += 1
            workers[str(label.worker)] += 1
        mean, std = float(advantages.mean()), float(advantages.std())
        group_data = {}
        for group, positions in groups.items():
            vals = advantages[positions]
            group_data[group] = {"count": len(positions), "fraction": len(positions) / n,
                                 "rawAdvantageMean": float(vals.mean()), "rawAdvantageStd": float(vals.std()),
                                 "rawAdvantagePositiveFraction": float(np.mean(vals > 0)),
                                 "globallyNormalizedAdvantageMean": float(((vals - mean) / (std + 1e-10)).mean())}
        batch_size = int(trainer.hyperparameters.batch_size)
        optimizer = trainer.optimizer
        step = int(trainer.policy.get_current_step())
        return {"policyStep": step, "bufferExperiences": n, "groups": group_data,
                "scenarios": dict(scenarios), "workers": dict(workers),
                "uniqueEpisodes": len({(l.worker, l.agent, l.index) for l in labels}),
                "rawAdvantageMean": mean, "rawAdvantageStd": std,
                "optimizerMinibatchesPerEpoch": n // batch_size,
                "remainderNotUsedInEachEpoch": n % batch_size,
                "epochs": int(trainer.hyperparameters.num_epoch),
                "learningRate": float(optimizer.decay_learning_rate.get_value(step)),
                "beta": float(optimizer.decay_beta.get_value(step)),
                "epsilon": float(optimizer.decay_epsilon.get_value(step))}

    def close(self):
        for cls, name, original, replacement in reversed(self.patches):
            if getattr(cls, name) is replacement:
                setattr(cls, name, original)
            else:
                raise DiagnosticError("Another component replaced a diagnostic hook before cleanup")
        self.patches.clear()
        self._write({"event": "closed", "preparedUpdates": self.update_number,
                     "pendingQueuedTrajectories": len(self.queued),
                     "pendingBufferExperiences": sum(map(len, self.shadows.values()))})
        self.output.close()


def install_diagnostics(output_path, classify_index=classify_index):
    return UpdateDiagnostics(output_path, classify_index).install()


def main():
    output_path = os.environ.get("PICKLEBOT_DIAGNOSTIC_OUTPUT")
    if not output_path:
        raise DiagnosticError("PICKLEBOT_DIAGNOSTIC_OUTPUT must name a fresh JSONL artifact")
    telemetry = install_diagnostics(output_path)
    try:
        from mlagents.trainers.learn import main as learn_main
        learn_main()
    finally:
        telemetry.close()


if __name__ == "__main__":
    main()

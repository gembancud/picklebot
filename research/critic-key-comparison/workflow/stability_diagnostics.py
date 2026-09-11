"""Observational probes around pinned PPO; vendor owns all updates and RNG.

Use training data only. No diagnostic keys are added to AgentBuffer. The base
transport/shadow label implementation is unchanged from the stability audit.
"""
import json
import os
import time
from collections import defaultdict

import numpy as np
from mlagents.torch_utils import torch
from mlagents.trainers.buffer import BufferKey, RewardSignalUtil
from mlagents.trainers.trajectory import ObsUtil
from mlagents.trainers.torch_entities.agent_action import AgentAction
from mlagents.trainers.torch_entities.action_log_probs import ActionLogProbs
from mlagents.trainers.torch_entities.utils import ModelUtils

from base_diagnostics import (UpdateDiagnostics, DiagnosticError, Label,
                              classify_index, PREFIX)


def task_key(index):
    c = classify_index(index)
    return '/'.join([c['group'], c['mode']] + ([c['side']] if c['group'] == 'focus' else []))


def array(t):
    return t.detach().cpu().numpy().astype(np.float64)


def describe(x):
    x = np.asarray(x, dtype=np.float64).reshape(-1)
    if not len(x):
        return None
    if not np.isfinite(x).all():
        raise DiagnosticError('Nonfinite diagnostic measurement')
    return dict(n=len(x), mean=float(x.mean()), std=float(x.std()),
                p50=float(np.median(x)), p90=float(np.quantile(x, .9)), max=float(x.max()))


def fit_stats(prediction, target):
    p, y = np.asarray(prediction, np.float64), np.asarray(target, np.float64)
    e = p - y
    variance = float(y.var())
    return dict(n=len(y), predictionMean=float(p.mean()), targetMean=float(y.mean()),
                targetStd=float(y.std()), bias=float(e.mean()), rmse=float(np.sqrt(np.mean(e**2))),
                explainedVariance=None if variance < 1e-12 else float(1-e.var()/variance),
                sums=dict(p=float(p.sum()), y=float(y.sum()), p2=float((p*p).sum()),
                          y2=float((y*y).sum()), e=float(e.sum()), e2=float((e*e).sum())))


def cosine(a, b):
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return None if denom < 1e-14 else float(np.clip(np.dot(a, b)/denom, -1, 1))


def discounted(rewards, gamma):
    returns = np.zeros(len(rewards), dtype=np.float64)
    future = 0.0
    for i in range(len(rewards)-1, -1, -1):
        future = float(rewards[i]) + gamma * future
        returns[i] = future
    return returns


def distribution(actor, observations, action_masks):
    encoding, _ = actor.network_body(observations, memories=None, sequence_length=1)
    d = actor.action_model._get_dists(encoding, action_masks)
    assert not actor.action_model._continuous_distribution.tanh_squash
    return dict(mean=array(d.continuous.mean), std=array(d.continuous.std),
                probs=[array(x.probs) for x in d.discrete])


def exact_kl(before, after):
    # KL(old || new), summed over independent Gaussian coordinates and branches.
    m0, m1, s0, s1 = before['mean'], after['mean'], before['std'], after['std']
    cont = np.log(s1/s0) + (s0*s0 + (m0-m1)**2)/(2*s1*s1) - .5
    disc = np.zeros(len(m0))
    for p, q in zip(before['probs'], after['probs']):
        disc += (p * (np.log(np.maximum(p, 1e-300))-np.log(np.maximum(q, 1e-300)))).sum(axis=1)
    return cont.sum(axis=1)+disc, cont, disc


def gradient(loss, params, retain_graph=True):
    values = torch.autograd.grad(loss, params, retain_graph=retain_graph, allow_unused=True)
    return np.concatenate([array(v if v is not None else torch.zeros_like(p)).reshape(-1)
                           for p, v in zip(params, values)])


class LearningDiagnostics(UpdateDiagnostics):
    def __init__(self, output_path, classifier=classify_index):
        super().__init__(output_path, classifier)
        self.learning_output = self.path.with_name('learning-updates.jsonl').open('x', encoding='utf-8', buffering=1)
        self.episode_output = self.path.with_name('critic-episodes.jsonl').open('x', encoding='utf-8', buffering=1)
        self.episode_parts = defaultdict(list)
        self.active_update = None
        self.minibatch_rows = []
        self.extra_seconds = 0.0
        self.critic_capture = None
        self.critic_shadows = defaultdict(list)

    def emit(self, record):
        self.learning_output.write(json.dumps(record, allow_nan=False, sort_keys=True)+'\n')

    def install(self):
        super().install()
        from mlagents.trainers.ppo.trainer import PPOTrainer
        from mlagents.trainers.ppo.optimizer_torch import TorchPPOOptimizer
        from mlagents.trainers.trainer.on_policy_trainer import OnPolicyTrainer
        from mlagents.trainers.optimizer.torch_optimizer import TorchOptimizer
        from mlagents.trainers.trainer.rl_trainer import RLTrainer

        def value_wrapper(original):
            def wrapped(optimizer, *args, **kwargs):
                result = original(optimizer, *args, **kwargs)
                if self.critic_capture is not None:
                    assert not self.critic_capture, 'Nested value estimate capture'
                    self.critic_capture.update({k:np.array(v, dtype=np.float64, copy=True) for k,v in result[0].items()})
                return result
            return wrapped

        def clear_wrapper(original):
            def wrapped(trainer):
                result = original(trainer)
                self.critic_shadows[id(trainer)].clear()
                return result
            return wrapped

        def trajectory_wrapper(original):
            def wrapped(trainer, trajectory):
                labeled = self.queued.get(id(trajectory))
                before = trainer.update_buffer.num_experiences
                assert self.critic_capture is None
                capture = {}
                self.critic_capture = capture
                try:
                    result = original(trainer, trajectory)
                finally:
                    self.critic_capture = None
                after = trainer.update_buffer.num_experiences
                if after == before:
                    return result
                assert labeled is not None and after-before == len(trajectory.steps)
                label = labeled[1]
                b = trainer.update_buffer
                assert list(trainer.optimizer.reward_signals) == ['extrinsic']
                # The pinned framework aliases value_estimates_key with returns_key.
                # Capture the real value prediction before its field is overwritten.
                values = capture['extrinsic']
                assert len(values)==after-before
                self.critic_shadows[id(trainer)].extend(values)
                assert len(self.critic_shadows[id(trainer)])==after
                rewards = np.asarray(b[RewardSignalUtil.rewards_key('extrinsic')][before:after], np.float64)
                key = (id(trainer), label.worker, label.agent, label.index)
                self.episode_parts[key].append((values, rewards))
                if trajectory.done_reached:
                    parts = self.episode_parts.pop(key)
                    if not trajectory.interrupted:
                        v, r = [np.concatenate([part[j] for part in parts]) for j in (0, 1)]
                        gamma = trainer.optimizer.reward_signals['extrinsic'].gamma
                        y = discounted(r, gamma)
                        row = dict(task=task_key(label.index), worker=label.worker, index=label.index,
                                   policyStep=int(trainer.policy.get_current_step()),
                                   segments=len(parts), fit=fit_stats(v, y),
                                   initialPrediction=float(v[0]), initialReturn=float(y[0]),
                                   totalReward=float(r.sum()), interrupted=False,
                                   predictionSource='captured get_trajectory_value_estimates before buffer overwrite')
                        self.episode_output.write(json.dumps(row, allow_nan=False)+'\n')
                return result
            return wrapped

        def update_wrapper(original):
            def wrapped(trainer):
                started = time.perf_counter()
                snapshot = self.before_update(trainer)
                self.extra_seconds += time.perf_counter()-started
                self.active_update = trainer
                self.minibatch_rows = []
                try:
                    result = original(trainer)
                finally:
                    self.active_update = None
                started = time.perf_counter()
                self.after_update(trainer, snapshot)
                self.extra_seconds += time.perf_counter()-started
                return result
            return wrapped

        def minibatch_wrapper(original):
            def wrapped(optimizer, batch, num_sequences):
                if self.active_update is not None:
                    started = time.perf_counter()
                    with torch.no_grad():
                        n = len(batch[BufferKey.ADVANTAGES])
                        obs = [ModelUtils.list_to_tensor(x) for x in ObsUtil.from_buffer(batch, 1)]
                        masks = ModelUtils.list_to_tensor(batch[BufferKey.ACTION_MASK])
                        logs = optimizer.policy.actor.get_stats(obs, AgentAction.from_buffer(batch), masks=masks)['log_probs'].flatten()
                        old = ActionLogProbs.from_buffer(batch).flatten().to(logs.device)
                        delta = array(logs-old)
                        epsilon = optimizer.decay_epsilon.get_value(optimizer.policy.get_current_step())
                        ratio = np.exp(delta)
                        valid = np.asarray(batch[BufferKey.MASKS], dtype=bool)
                        current_values, _ = optimizer.critic.critic_pass(obs)
                        value = array(current_values['extrinsic'])
                        old_value = np.asarray(batch[RewardSignalUtil.value_estimates_key('extrinsic')], np.float64)
                        target_value = np.asarray(batch[RewardSignalUtil.returns_key('extrinsic')], np.float64)
                        clipped_value = old_value+np.clip(value-old_value,-epsilon,epsilon)
                        self.minibatch_rows.append(dict(n=n,
                            coordinateClipFraction=float((np.abs(ratio[valid]-1)>epsilon).mean()),
                            continuousClipFraction=float((np.abs(ratio[valid, :16]-1)>epsilon).mean()),
                            approximateJointKL=float(((ratio[valid]-1)-delta[valid]).sum(axis=1).mean()),
                            valueClipDominatesFraction=float((((target_value-clipped_value)**2 > (target_value-value)**2+1e-10)[valid]).mean()),
                            storedValueTargetMeanGap=float(np.abs(old_value-target_value)[valid].mean())))
                    self.extra_seconds += time.perf_counter()-started
                return original(optimizer, batch, num_sequences)
            return wrapped

        self._patch(PPOTrainer, '_process_trajectory', trajectory_wrapper)
        self._patch(OnPolicyTrainer, '_update_policy', update_wrapper)
        self._patch(TorchPPOOptimizer, 'update', minibatch_wrapper)
        self._patch(TorchOptimizer, 'get_trajectory_value_estimates', value_wrapper)
        self._patch(RLTrainer, '_clear_update_buffer', clear_wrapper)
        return self

    def before_update(self, trainer):
        assert trainer.policy.sequence_length == 1 and not trainer.hyperparameters.shared_critic
        b = trainer.update_buffer
        labels = list(self.shadows[id(trainer)])
        n = b.num_experiences
        assert n == len(labels)
        # Match the vendor's float32 global advantage normalization exactly.
        raw = np.array(b[BufferKey.ADVANTAGES].get_batch(), dtype=np.float32)
        adv = (raw-raw.mean())/(raw.std()+1e-10)
        observations = [ModelUtils.list_to_tensor(x) for x in ObsUtil.from_buffer(b, 1)]
        masks = ModelUtils.list_to_tensor(b[BufferKey.ACTION_MASK])
        actions = AgentAction.from_buffer(b)
        old_logs = ActionLogProbs.from_buffer(b).flatten()
        loss_mask = ModelUtils.list_to_tensor(b[BufferKey.MASKS], dtype=torch.bool)
        advantages = ModelUtils.list_to_tensor(adv)
        actor = trainer.policy.actor
        params = [p for p in actor.parameters() if p.requires_grad]
        theta = np.concatenate([array(p).reshape(-1) for p in params])
        stats = actor.get_stats(observations, actions, masks=masks)
        logs, entropy = stats['log_probs'].flatten(), stats['entropy']
        epsilon = trainer.optimizer.decay_epsilon.get_value(trainer.policy.get_current_step())
        beta = trainer.optimizer.decay_beta.get_value(trainer.policy.get_current_step())
        group_positions = defaultdict(list)
        for i, label in enumerate(labels):
            group_positions[task_key(label.index)].append(i)
        grads, group_rows, halves = {}, {}, {}
        with torch.no_grad():
            values, _ = trainer.optimizer.critic.critic_pass(observations)
            predictions = array(values['extrinsic'])
            dists = distribution(actor, observations, masks)
        targets = np.asarray(b[RewardSignalUtil.returns_key('extrinsic')], np.float64)
        stored_values = np.asarray(self.critic_shadows[id(trainer)], np.float64)
        assert stored_values.shape == targets.shape
        valid = array(loss_mask).astype(bool)
        total_valid = int(valid.sum())
        for key, positions in sorted(group_positions.items()):
            selection = torch.zeros_like(loss_mask)
            selection[positions] = True
            selection &= loss_mask
            positions = np.asarray(positions, dtype=np.int64)
            positions = positions[valid[positions]]
            if not len(positions):
                continue
            loss = ModelUtils.trust_region_policy_loss(advantages, logs, old_logs, selection, epsilon)
            g = gradient(loss, params)
            grads[key] = g
            episode_ids = list(dict.fromkeys((labels[i].worker, labels[i].agent, labels[i].index) for i in positions))
            assignment = {x:j % 2 for j,x in enumerate(episode_ids)}
            split_grads = []
            for half in range(2):
                selected = [i for i in positions if assignment[(labels[i].worker, labels[i].agent, labels[i].index)] == half]
                half_mask = torch.zeros_like(loss_mask)
                half_mask[selected] = True
                half_loss = ModelUtils.trust_region_policy_loss(advantages, logs, old_logs, half_mask, epsilon)
                split_grads.append(gradient(half_loss, params))
            halves[key] = split_grads
            group_rows[key] = dict(n=len(positions), episodes=len(episode_ids),
                fraction=len(positions)/total_valid, policyLoss=float(loss.detach().cpu()),
                gradientNorm=float(np.linalg.norm(g)),
                weightedGradientNorm=float(np.linalg.norm(g))*len(positions)/total_valid,
                splitHalfCosine=cosine(*split_grads),
                rawAdvantage=describe(raw[positions]), normalizedAdvantage=describe(adv[positions]),
                critic=fit_stats(predictions[positions], targets[positions]),
                storedCritic=fit_stats(stored_values[positions], targets[positions]))
        policy_loss = ModelUtils.trust_region_policy_loss(advantages, logs, old_logs, loss_mask, epsilon)
        full_gradient = gradient(policy_loss, params)
        combined = sum(group_rows[k]['fraction']*g for k,g in grads.items())
        reconstruction = np.linalg.norm(full_gradient-combined)/max(np.linalg.norm(full_gradient), 1e-12)
        if reconstruction > 2e-4:
            raise DiagnosticError('Task gradients failed to reconstruct the actual full-buffer policy gradient')
        entropy_gradient = gradient(-beta*ModelUtils.masked_mean(entropy, loss_mask), params, retain_graph=False)
        pairs = []
        keys = sorted(grads)
        for i,k in enumerate(keys):
            for j in keys[i+1:]:
                pairs.append(dict(a=k, b=j, cosine=cosine(grads[k], grads[j]),
                                  split0=cosine(halves[k][0], halves[j][0]),
                                  split1=cosine(halves[k][1], halves[j][1])))
        return dict(observations=observations, masks=masks, actions=actions, oldLogs=old_logs,
                    lossMask=loss_mask, advantages=advantages, groups=group_positions,
                    groupRows=group_rows, grads=grads, theta=theta, params=params,
                    dists=dists, targets=targets, predictions=predictions, epsilon=epsilon,
                    beforeLogs=array(logs), pairs=pairs, reconstruction=float(reconstruction),
                    fullGradient=full_gradient, entropyGradient=entropy_gradient,
                    bufferExperiences=n, policyStep=int(trainer.policy.get_current_step()))

    def after_update(self, trainer, s):
        actor = trainer.policy.actor
        with torch.no_grad():
            after_dist = distribution(actor, s['observations'], s['masks'])
            out = actor.get_stats(s['observations'], s['actions'], masks=s['masks'])
            after_logs = out['log_probs'].flatten()
            values, _ = trainer.optimizer.critic.critic_pass(s['observations'])
            prediction = array(values['extrinsic'])
        delta_theta = np.concatenate([array(p).reshape(-1) for p in s['params']])-s['theta']
        kl, cont, disc = exact_kl(s['dists'], after_dist)
        command_change = np.abs(np.clip(after_dist['mean'], -3, 3)/3-np.clip(s['dists']['mean'], -3, 3)/3)
        behavior_delta_before = s['beforeLogs']-array(s['oldLogs'])
        behavior_delta_after = array(after_logs)-array(s['oldLogs'])
        ratio_after = np.exp(behavior_delta_after)
        for key, row in s['groupRows'].items():
            positions = np.asarray(s['groups'][key], np.int64)
            selection = torch.zeros_like(s['lossMask'])
            selection[positions] = True
            selection &= s['lossMask']
            positions = positions[array(s['lossMask'])[positions].astype(bool)]
            after_loss = ModelUtils.trust_region_policy_loss(s['advantages'], after_logs, s['oldLogs'], selection, s['epsilon'])
            row.update(kl=describe(kl[positions]), latentContinuousKL=describe(cont[positions].sum(axis=1)),
                discreteKL=describe(disc[positions]), commandChange=describe(command_change[positions]),
                coordinateClipFraction=float((np.abs(ratio_after[positions]-1)>s['epsilon']).mean()),
                continuousClipFraction=float((np.abs(ratio_after[positions,:16]-1)>s['epsilon']).mean()),
                preUpdateApproximateBehaviorKL=float(((np.exp(behavior_delta_before[positions])-1)-behavior_delta_before[positions]).sum(axis=1).mean()),
                afterCritic=fit_stats(prediction[positions], s['targets'][positions]),
                afterPolicyLoss=float(after_loss.detach().cpu()),
                actualLossChange=float(after_loss.detach().cpu())-row['policyLoss'],
                predictedLossChange=float(np.dot(s['grads'][key], delta_theta)),
                gradientVsUpdateCosine=cosine(s['grads'][key], delta_theta))
        record = dict(event='learning_update', update=self.update_number, policyStep=s['policyStep'],
            bufferExperiences=s['bufferExperiences'], groups=s['groupRows'], pairs=s['pairs'],
            fullPolicyGradientNorm=float(np.linalg.norm(s['fullGradient'])),
            entropyGradientNorm=float(np.linalg.norm(s['entropyGradient'])),
            gradientReconstructionRelativeError=s['reconstruction'],
            actualParameterChangeNorm=float(np.linalg.norm(delta_theta)),
            policyGradientVsUpdateCosine=cosine(s['fullGradient'], delta_theta),
            actorObjectiveVsUpdateCosine=cosine(s['fullGradient']+s['entropyGradient'], delta_theta),
            allKL=describe(kl), minibatches=self.minibatch_rows,
            extraDiagnosticSecondsSoFar=self.extra_seconds)
        self.emit(record)
        reporter = trainer._stats_reporter
        for key, row in s['groupRows'].items():
            prefix = 'PicklebotDiagnostic/'+key+'/'
            for name, value in [('CriticRMSE', row['critic']['rmse']),
                                ('UpdateKL', row['kl']['mean']),
                                ('PolicyLossChange', row['actualLossChange']),
                                ('GradientNorm', row['gradientNorm'])]:
                reporter.add_stat(prefix+name, value)

    def close(self):
        self.emit(dict(event='closed', updates=self.update_number,
                       incompleteEpisodesExcluded=len(self.episode_parts), extraDiagnosticSeconds=self.extra_seconds))
        super().close()
        self.learning_output.close()
        self.episode_output.close()


def install_diagnostics(output_path, classify_index=classify_index):
    return LearningDiagnostics(output_path, classify_index).install()


def main():
    # Select and verify the installed package before any training starts.
    from runtime_identity import verify_runtime
    verify_runtime()
    telemetry = install_diagnostics(os.environ['PICKLEBOT_DIAGNOSTIC_OUTPUT'])
    try:
        from mlagents.trainers.learn import main as learn_main
        learn_main()
    finally:
        telemetry.close()


if __name__ == '__main__':
    main()

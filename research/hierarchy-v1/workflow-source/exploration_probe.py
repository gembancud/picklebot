"""Read-only CPU replay of saved first states; diagnostic used on 2026-09-12.

This is the script already executed through stdin, saved afterward for audit.
It does not step Unity, sample actions, optimize, write checkpoints or update statistics.
"""
import json
import hashlib
from pathlib import Path
import numpy as np
from mlagents.torch_utils import torch
from mlagents.trainers.torch_entities.networks import SimpleActor
from mlagents.trainers.settings import NetworkSettings
from mlagents_envs.base_env import ObservationSpec, DimensionProperty, ObservationType, ActionSpec

torch.set_num_threads(1)
torch.set_default_device('cpu')
root = Path('F:/dev/picklebot')
base = root / 'artifacts/hierarchy-v1/two-regions-01/evaluation/ExecutionV1Initial'
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
first = {c: read(base / c / 'first-decisions.json') for c in ['A', 'B']}
seeds = sorted(map(int, first['A']))
x = torch.tensor(np.array([first[c][str(s)]['observation'] for c in ['A', 'B'] for s in seeds]), dtype=torch.float32, device='cpu')
names = ['move.x', 'move.z', 'turn.rate', 'crouch', 'sprint', 'torso.turn', 'torso.forwardLean', 'torso.lateralLean', 'shoulder.yaw', 'shoulder.flexion', 'shoulder.abduction', 'elbow.flexion', 'forearm.rotation', 'wrist.flexion', 'wrist.deviation', 'offHand.lift']
paths = {
    'initial': root / 'training/snapshots/execution-v1-initial.pt',
    'placement262147': root / 'artifacts/mlagents/execution-placement-01/PicklebotExecutionV1/checkpoint.pt',
}
results = {}
for label, path in paths.items():
    checkpoint = torch.load(path, map_location='cpu', weights_only=False)
    actor = SimpleActor(
        [ObservationSpec((136,), (DimensionProperty.NONE,), ObservationType.DEFAULT, 'VectorSensor_size136')],
        NetworkSettings(normalize=True, hidden_units=128, num_layers=2), ActionSpec(16, (2,)),
        conditional_sigma=False, tanh_squash=False,
    ).to('cpu')
    actor.load_state_dict(checkpoint['Policy'], strict=True)
    actor.eval()
    with torch.no_grad():
        encoded, _ = actor.network_body([x])
        dist = actor.action_model._continuous_distribution(encoded)
        mu, sd = dist.mean.cpu(), dist.std.cpu()
        mapped = mu.clamp(-3, 3) / 3
        normal = torch.distributions.Normal(mu, sd)
        clip_probability = normal.cdf(torch.full_like(mu, -3)) + 1 - normal.cdf(torch.full_like(mu, 3))
        log_sigma = actor.action_model._continuous_distribution.log_sigma.detach().cpu().flatten()
        per_channel = [{
            'channel': name, 'logSigma': float(log_sigma[i]), 'rawStd': float(sd[0, i]),
            'mappedStdBeforeClip': float(sd[0, i] / 3),
            'deterministicMin': float(mapped[:, i].min()), 'deterministicMax': float(mapped[:, i].max()),
            'fractionFirstStateMeansClipped': float((mu[:, i].abs() >= 3).float().mean()),
            'meanSampleClipProbability': float(clip_probability[:, i].mean()),
        } for i, name in enumerate(names)]
        results[label] = {
            'checkpointSha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'states': len(x), 'uniqueInitialStates': len(np.unique(x.numpy()[:256, :124], axis=0)),
            'rawStdMinMedianMax': [float(sd[0].min()), float(sd[0].median()), float(sd[0].max())],
            'mappedStdMinMedianMaxBeforeClip': [float(sd[0].min() / 3), float(sd[0].median() / 3), float(sd[0].max() / 3)],
            'rawMeanMinMax': [float(mu.min()), float(mu.max())],
            'firstStateMeanClippedFraction': float((mu.abs() >= 3).float().mean()),
            'fractionFirstStateMappedMeansAtAbsPoint95': float((mapped.abs() >= .95).float().mean()),
            'meanSampleClipProbability': float(clip_probability.mean()),
            'pairedTargetFirstActionMaxDelta': float((mapped[:256] - mapped[256:]).abs().max()),
            'pairedTargetFirstActionMedianMaxDelta': float((mapped[:256] - mapped[256:]).abs().max(dim=1).values.median()),
            'perChannel': per_channel,
        }
print(json.dumps(results, indent=2))

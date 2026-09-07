"""Train a small paddle policy by imitation of ballistic stroke examples.

The analytical teacher exists only in this training script. Unity executes the
exported neural weights and resolves every collision with its physics engine.
Training and tuning seeds are disjoint from the Unity rally validation seeds.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import torch
from torch import nn

ROOT = Path(__file__).resolve().parents[1]


def examples(count, seed):
    rng = np.random.default_rng(seed)
    # States just after the ball has bounced on the receiver's half.
    x = rng.uniform(-0.55, 0.55, count)
    y = rng.uniform(0.037, 0.11, count)
    z = rng.uniform(-0.94, -0.25, count)
    vx = rng.uniform(-0.9, 0.9, count)
    vy = rng.uniform(1.4, 3.7, count)
    vz = rng.uniform(-5.0, -2.3, count)
    t = (-1.25 - z) / vz
    hit_x = x + vx * t
    hit_y = y + vy * t - 4.905 * t * t
    hit_vy = vy - 9.81 * t
    # Elastic paddle reflection. Select a direction with the same speed that
    # lands at the centre of the opposite half, at z=0.65.
    speed2 = vx * vx + hit_vy * hit_vy + vz * vz
    dx, dz, dy = -hit_x, np.full(count, 1.90), 0.035 - hit_y
    b = 9.81 * dy - speed2
    c = dx * dx + dz * dz + dy * dy
    discriminant = b * b - 9.81**2 * c
    valid = (discriminant > 0) & (hit_y > 0.13) & (hit_y < 0.95) & (abs(hit_x) < 0.68)
    # Low ballistic arc; root written to avoid cancellation.
    flight2 = 2 * c / (-b + np.sqrt(np.maximum(discriminant, 0)))
    flight = np.sqrt(flight2)
    outgoing = np.stack([dx / flight, dy / flight + 4.905 * flight, dz / flight], axis=1)
    incoming = np.stack([vx, hit_vy, vz], axis=1)
    normal = outgoing - incoming
    slopes = normal[:, :2] / normal[:, 2:3]
    inputs = np.stack([x, y, z, vx, vy, vz], axis=1)[valid].astype(np.float32)
    targets = np.column_stack([hit_x, hit_y, slopes])[valid].astype(np.float32)
    return inputs, targets


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--steps', type=int, default=12000)
    parser.add_argument('--seed', type=int, default=810001)
    args = parser.parse_args()
    torch.set_num_threads(4)
    torch.manual_seed(args.seed)
    x, y = examples(180000, args.seed)
    tx, ty = examples(12000, args.seed + 1)
    mean, scale = x.mean(0), x.std(0)
    net = nn.Sequential(nn.Linear(6, 64), nn.Tanh(), nn.Linear(64, 64), nn.Tanh(), nn.Linear(64, 4))
    x = torch.from_numpy((x - mean) / scale)
    y = torch.from_numpy(y)
    tx, ty = torch.from_numpy((tx - mean) / scale), torch.from_numpy(ty)
    opt = torch.optim.Adam(net.parameters(), lr=0.001)
    start = time.time()
    for step in range(args.steps):
        if step == args.steps * 2 // 3:
            for group in opt.param_groups: group['lr'] = 0.0002
        ids = torch.randint(len(x), (1024,))
        loss = ((net(x[ids]) - y[ids])**2).mean()
        opt.zero_grad()
        loss.backward()
        opt.step()
        if (step + 1) % 2000 == 0:
            with torch.no_grad(): error = (net(tx) - ty).abs().mean(0).tolist()
            print(json.dumps({'step': step+1, 'loss': loss.item(), 'tuning_mae': error, 'seconds': time.time()-start}), flush=True)
    output = ROOT / 'Assets/Picklebot/Rally/Models'
    artifacts = ROOT / 'artifacts/rally/training'
    output.mkdir(parents=True, exist_ok=True)
    artifacts.mkdir(parents=True, exist_ok=True)
    torch.save(net.state_dict(), artifacts / 'rally-policy.pt')
    layers = []
    for layer in net:
        if isinstance(layer, nn.Linear):
            layers.append(dict(inputs=layer.in_features, outputs=layer.out_features,
                weights=layer.weight.detach().flatten().tolist(), bias=layer.bias.detach().tolist()))
    weights = dict(version='rally-policy-v1', seed=args.seed, mean=mean.tolist(), scale=scale.tolist(), layers=layers)
    path = output / 'rally-policy.json'
    path.write_text(json.dumps(weights, separators=(',', ':')))
    with torch.no_grad():
        reference = dict(cases=[dict(input=(row.numpy() * scale + mean).tolist(),
            output=net(row).tolist()) for row in tx[:32]])
    (output / 'rally-policy.reference.json').write_text(json.dumps(reference, indent=2))
    torch.onnx.export(net, torch.zeros(1, 6), str(artifacts / 'rally-policy.onnx'),
        input_names=['normalized_state'], output_names=['paddle_command'], opset_version=13)
    with torch.no_grad(): error = (net(tx) - ty).abs().mean(0).tolist()
    manifest = dict(version='rally-policy-v1', method='behavioral-cloning',
        teacher='ballistic interception and elastic reflection; training only', seed=args.seed,
        training_examples=len(x), tuning_examples=len(tx), steps=args.steps,
        tuning_mae=error, elapsed_seconds=time.time()-start, torch_version=torch.__version__,
        weights_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        trainer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        provisional=True, notes='Tuning error is not Unity rally success. Validate separately in Unity.')
    (output / 'rally-policy.manifest.json').write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest), flush=True)


if __name__ == '__main__': main()

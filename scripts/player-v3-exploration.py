#!/usr/bin/env python3
"""Create a provenance-recorded exploration variant without changing policy means."""
import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from player_actor import file_hash
from player_v3_actor import ACTION_VERSION, OBS_VERSION, ActorV3, source_hash


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parent', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--channels', required=True, type=int, nargs='+')
    parser.add_argument('--standard-deviation', required=True, type=float)
    parser.add_argument('--reason', required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Preserve existing checkpoint evidence')
    sigma = args.standard_deviation
    if not math.isfinite(sigma) or not math.exp(-5) <= sigma <= math.e:
        raise ValueError('Standard deviation must respect the actor schema')
    channels = sorted(set(args.channels))
    if len(channels) != len(args.channels) or any(i < 0 or i >= 18 for i in channels):
        raise ValueError('Use distinct current-schema channel indices')
    if not args.reason.strip():
        raise ValueError('Record the evidence motivating this exploration change')

    _, parent = ActorV3.load(args.parent)
    if (parent['observationVersion'], parent['actionVersion']) != (OBS_VERSION, ACTION_VERSION):
        raise ValueError('Migrate the policy schema explicitly first')
    if parent['sourceHash'] != source_hash():
        raise ValueError('Record any environment transition separately')
    parent_hash = file_hash(args.parent)
    data = dict(parent)
    data['logStd'] = list(parent['logStd'])
    for channel in channels:
        data['logStd'][channel] = math.log(sigma)
    if data['logStd'] == parent['logStd']:
        raise ValueError('Requested exploration already matches the parent')
    data.update(
        parentModelHash=parent_hash,
        method='Exploration variant; learned mean-network tensors retained',
        explorationInitialization=dict(
            previousLogStd=parent['logStd'],
            channels=channels,
            newStandardDeviation=sigma,
            reason=args.reason,
            scriptHash=file_hash(Path(__file__)),
            createdUtc=datetime.now(timezone.utc).isoformat(),
            note='No prescribed joint pose, action sequence, release time or stroke target. No optimization on this new sampling distribution yet.'
        )
    )
    if data['layers'] != parent['layers'] or any(
        data['logStd'][i] != parent['logStd'][i] for i in range(18) if i not in channels
    ):
        raise AssertionError('Unselected policy tensors changed')
    if file_hash(args.parent) != parent_hash or source_hash() != parent['sourceHash']:
        raise ValueError('Input changed during variant creation')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as target:
        json.dump(data, target, indent=2)
    print(json.dumps(dict(actor=str(args.output), sha256=file_hash(args.output),
                          sourceHash=data['sourceHash'], learnedLayersUnchanged=True)))


if __name__ == '__main__':
    main()

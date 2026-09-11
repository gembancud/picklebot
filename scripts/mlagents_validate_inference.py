"""Validate recorded Unity actions against their pinned framework checkpoint."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import numpy as np
import torch
from mlagents.torch_utils import set_torch_config
from mlagents.trainers.settings import TorchSettings, NetworkSettings
from mlagents.trainers.torch_entities.networks import SimpleActor
from mlagents_envs.base_env import ObservationSpec, ObservationType, DimensionProperty, ActionSpec

ROOT = Path(__file__).resolve().parents[1]

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def stationary_fractions(seed, attempt=0):
    assert isinstance(attempt, int) and 0 <= attempt < 64
    seed = (seed + 0x9e3779b9 * attempt) & 0xffffffff
    def mix(x):
        x ^= x >> 16; x = (x * 0x7feb352d) & 0xffffffff
        x ^= x >> 15; x = (x * 0x846ca68b) & 0xffffffff
        return x ^ (x >> 16)
    return tuple(np.float32((mix(seed ^ salt) >> 8) / 16777216) for salt in [0x91a73b21,0x4d38ac67])

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evaluation', type=Path)
    args = parser.parse_args()
    directory = args.evaluation.resolve()
    destination = directory/'verification.json'
    if destination.exists():
        raise RuntimeError('Refuse to overwrite existing verification evidence')
    report = json.loads((directory/'report.json').read_text())
    launch = json.loads((directory/'launch.json').read_text())
    assert report['status'] == 'seed_budget_complete' and not report['failure']
    assert report['split'] == 'development' and not report['trainerConnected']
    assert report['sourceIdentity'] == launch['sourceIdentity']
    source = json.loads((directory/'source-records.json').read_text())
    assert all(digest(ROOT/name) == value for name,value in source['files'].items())
    assert source['sourceIdentity'] == hashlib.sha256(json.dumps(source['files'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    model = ROOT/launch['model']
    checkpoint_path = model.with_suffix('.pt')
    assert digest(model) == launch['modelHash']
    assert digest(checkpoint_path) == launch['checkpointHash']
    first, count = launch['firstSeed'], launch['seedCount']
    assert 1100000 <= first < first+count <= 1200000
    assert report['firstSeed'] == first and report['seedCount'] == count
    assert report['task'] == launch['task']
    if 'feedLateralOffset' in launch:
        assert report['drillVersion'] == launch['drillVersion'] and launch['drillVersion'] in ['player-v3-grounded-drills-10-lateral-feeds','player-v3-grounded-drills-11-hold-reset','player-v3-grounded-drills-12-absolute-approach','player-v3-grounded-drills-13-stationary-contact','player-v3-grounded-drills-14-falling-contact','player-v3-grounded-drills-15-falling-miss-loss']
        if launch['drillVersion'] in ['player-v3-grounded-drills-11-hold-reset','player-v3-grounded-drills-12-absolute-approach','player-v3-grounded-drills-13-stationary-contact','player-v3-grounded-drills-14-falling-contact','player-v3-grounded-drills-15-falling-miss-loss']:
            assert np.float32(report['initialHoldLift'])==np.float32(launch['initialHoldLift']) and 0<=launch['initialHoldLift']<=140
        assert np.float32(report['feedLateralOffset']) == np.float32(launch['feedLateralOffset'])
        assert np.isfinite(launch['feedLateralOffset']) and abs(launch['feedLateralOffset']) <= .9
    if 'curriculumVersion' in launch:
        assert report['curriculumVersion'] == launch['curriculumVersion'] and launch['curriculumVersion'] in ['ml-drill-curriculum-v5-serve-practice','ml-drill-curriculum-v6-stationary-varied','ml-drill-curriculum-v7-stationary-resampling','ml-drill-curriculum-v8-stationary-return-mix','ml-drill-curriculum-v9-falling-return']
    if launch['task'] in ['varied-return','serve-return','contact-return','low-high-return','mixed-height-return','lateral-practice-return','focused-lateral-return','serve-practice-return']:
        assert report['maximumReturnDifficulty'] == launch['maximumReturnDifficulty']
    if launch['task'] in ['falling-contact','falling-return','stationary-return','stationary-practice','stationary-contact','low-return','low-high-return','mixed-height-return','lateral-practice-return','focused-lateral-return','serve-practice-return']:
        assert np.float32(report['feedLowering']) == np.float32(launch['feedLowering']) and 0 <= launch['feedLowering'] <= .9
    assert 1 <= launch['arenas'] == report['arenas'] <= 32
    episodes = [json.loads(line) for line in (directory/'episodes.jsonl').read_text().splitlines()]
    rows = [json.loads(line) for line in (directory/'decisions.jsonl').read_text().splitlines()]
    assert len(episodes) == report['completedEpisodes'] == count
    assert sorted(e['seed'] for e in episodes) == list(range(first,first+count))
    assert len(rows) == report['decisions']
    assert sum(e['physicsTicks'] for e in episodes) == report['physicsTicks']
    grouped = collections.defaultdict(list)
    for row in rows:
        assert len(row['observation']) == 124 and len(row['continuous']) == 16 and len(row['physical']) == 18
        assert row['player'] == (row['seed']-first)%4
        grouped[row['seed']].append(row)
    assert set(grouped) == set(range(first,first+count))
    for episode in episodes:
        traces = grouped[episode['seed']]
        if launch['task'] in ['stationary-contact','falling-contact']:
            assert episode['task']==launch['task']
        if launch['task'] in ['stationary-return','falling-return']:
            expected_task=('falling-contact' if launch['task']=='falling-return' else 'stationary-contact') if (episode['seed']-first)//4%2==0 else 'varied-return'
            assert episode['task']==expected_task and all(r['task']==expected_task for r in traces)
            if expected_task=='varied-return':
                assert 0 <= episode['feedDifficulty'] <= launch['maximumReturnDifficulty']
                assert not episode['resetRejections']
                assert episode['outcome'] in ['legal_return','body_or_handle','other_player','miss','rule_terminal','time_limit','bad_return']
        if launch.get('drillVersion') in ['player-v3-grounded-drills-11-hold-reset','player-v3-grounded-drills-12-absolute-approach','player-v3-grounded-drills-13-stationary-contact','player-v3-grounded-drills-14-falling-contact','player-v3-grounded-drills-15-falling-miss-loss']:
            expected_lift=launch['initialHoldLift'] if episode['task'] in ['drop-contact','drop-serve'] else 0
            assert np.float32(episode['initialHoldLift'])==np.float32(expected_lift)
            assert abs(traces[0]['observation'][121]*140-expected_lift)<1e-4
        if 'feedLateralOffset' in launch:
            expected_offset = launch['feedLateralOffset'] if episode['task'] in ['low-return','stationary-contact','falling-contact'] else 0
            if launch['task'] == 'lateral-practice-return' and episode['task'] == 'low-return':
                condition=(episode['seed']-first)//8%4
                expected_offset=np.float32(launch['feedLateralOffset'])*np.float32(condition*.5) if condition<3 else np.float32(0)
            if launch['task'] == 'focused-lateral-return' and episode['task'] == 'low-return':
                slot=(episode['seed']-first)//4%8
                expected_offset=np.float32(launch['feedLateralOffset'])*np.float32(1 if slot%2==0 else .5 if slot==3 else 0)
            if launch['task'] == 'serve-practice-return' and episode['task'] == 'low-return':
                slot=(episode['seed']-first)//4%8
                expected_offset=np.float32(launch['feedLateralOffset'])*np.float32(1 if slot in [1,5] else .5 if slot==7 else 0)
            if launch['task']=='stationary-practice' or (launch['task'] in ['stationary-return','falling-return'] and episode['task'] in ['stationary-contact','falling-contact']):
                if launch['curriculumVersion'] in ['ml-drill-curriculum-v7-stationary-resampling','ml-drill-curriculum-v8-stationary-return-mix','ml-drill-curriculum-v9-falling-return']:
                    assert isinstance(episode['resetRejections'], list)
                    assert all(isinstance(x,str) and x for x in episode['resetRejections'])
                else:
                    assert not episode.get('resetRejections')
                expected_offset=np.float32(launch['feedLateralOffset'])*stationary_fractions(episode['seed'], len(episode.get('resetRejections') or []))[1]
            assert np.float32(episode['feedLateralOffset']) == np.float32(expected_offset)
        if launch['task'] in ['serve-return','contact-return','low-high-return','mixed-height-return','lateral-practice-return','focused-lateral-return','serve-practice-return']:
            drop_task = {'serve-return':'drop-serve','contact-return':'drop-contact','low-high-return':'low-return','mixed-height-return':'low-return','lateral-practice-return':'low-return','focused-lateral-return':'low-return','serve-practice-return':'drop-contact'}[launch['task']]
            actual_task = drop_task if (episode['seed']-first)//4%2 == 0 else 'varied-return'
            if launch['task'] == 'focused-lateral-return':
                actual_task='varied-return' if (episode['seed']-first)//4%8 in [1,5] else 'low-return'
            if launch['task'] == 'serve-practice-return':
                slot=(episode['seed']-first)//4%8
                actual_task='drop-contact' if slot in [0,4] else 'varied-return' if slot in [2,6] else 'low-return'
            assert episode['task'] == actual_task and all(r['task'] == actual_task for r in traces)
            if actual_task == 'varied-return':
                assert 0 <= episode['feedDifficulty'] <= launch['maximumReturnDifficulty']
                assert not any(r['canRelease'] for r in traces)
        if launch['task'] == 'low-return':
            assert episode['task'] == 'low-return' and all(r['task'] == 'low-return' for r in traces)
        if launch['task'] in ['falling-contact','falling-return','stationary-return','stationary-practice','stationary-contact','low-return','low-high-return','mixed-height-return','lateral-practice-return','focused-lateral-return','serve-practice-return']:
            expected_lowering = np.float32(launch['feedLowering'] if episode['task'] in ['low-return','stationary-contact','falling-contact'] else 0)
            if launch['task'] == 'mixed-height-return' and episode['task'] == 'low-return':
                expected_lowering *= np.float32(((episode['seed']-first)//8%5)*.25)
            if launch['task'] == 'lateral-practice-return' and episode['task'] == 'low-return' and (episode['seed']-first)//8%4 == 3:
                expected_lowering += np.float32(.1)
            if launch['task'] == 'focused-lateral-return' and episode['task'] == 'low-return' and (episode['seed']-first)//4%8 == 7:
                expected_lowering += np.float32(.1)
            if launch['task'] == 'serve-practice-return' and episode['task'] == 'low-return' and (episode['seed']-first)//4%8 == 3:
                expected_lowering += np.float32(.1)
            if launch['task']=='stationary-practice' or (launch['task'] in ['stationary-return','falling-return'] and episode['task'] in ['stationary-contact','falling-contact']):
                expected_lowering=np.float32(launch['feedLowering'])*stationary_fractions(episode['seed'], len(episode.get('resetRejections') or []))[0]
            assert np.float32(episode['feedLowering']) == expected_lowering
            if episode['task'] != 'drop-contact':assert not any(r['canRelease'] for r in traces)
            assert np.isfinite(episode['faceContactBallHeight'])
            if not episode['faceContact']: assert episode['faceContactBallHeight'] == -1
        if launch['task'] in ['falling-contact','stationary-contact','stationary-practice'] or (launch['task'] in ['stationary-return','falling-return'] and episode['task'] in ['stationary-contact','falling-contact']):
            assert episode['task'] in ['stationary-contact','falling-contact'] and all(r['task']==episode['task'] for r in traces)
            assert not any(r['canRelease'] or r['release'] for r in traces)
            assert episode['outcome'] in ['face_contact','body_or_handle','other_player','miss','rule_terminal','time_limit']
            assert (episode['outcome']=='face_contact')==bool(episode['faceContact'])
            assert not episode['serveAccepted']
            assert traces[0]['observation'][120]<.5
        if episode.get('outcome') == 'serve_contact':
            assert episode['task'] == 'drop-contact'
            assert all(episode[k] for k in ['released','dropBounced','faceContact','serveAccepted'])
        assert len(traces) == episode['decisions']
        assert [row['observationTick'] for row in traces] == list(range(0,episode['physicsTicks'],12))
        assert episode['player'] == (episode['seed']-first)%4
        assert episode['outcome'] not in ['exception','infeasible']
        if launch['task'] == 'varied-return':
            assert episode['task'] == 'varied-return' and 0 <= episode['feedDifficulty'] <= launch['maximumReturnDifficulty']
    set_torch_config(TorchSettings(device='cpu'))
    torch.set_default_device('cpu'); torch.set_num_threads(2)
    actor = SimpleActor([ObservationSpec((124,),(DimensionProperty.NONE,),ObservationType.DEFAULT,'VectorSensor')],
        NetworkSettings(normalize=True,hidden_units=128,num_layers=2,deterministic=True),
        ActionSpec.create_hybrid(16,(2,)),conditional_sigma=False,tanh_squash=False)
    checkpoint = torch.load(checkpoint_path,map_location='cpu',weights_only=False)
    actor.load_state_dict(checkpoint['Policy'],strict=True); actor.eval()
    obs = torch.tensor([row['observation'] for row in rows],dtype=torch.float32)
    assert bool(torch.isfinite(obs).all())
    masks = torch.tensor([[1,1 if row['canRelease'] else 0] for row in rows],dtype=torch.float32)
    with torch.no_grad():
        _,out,_ = actor.get_action_and_stats([obs],masks=masks)
    expected = out['env_action'].continuous
    actual = np.asarray([row['continuous'] for row in rows],dtype=np.float32)
    error = float(np.max(np.abs(expected-actual)))
    assert np.isfinite(actual).all() and error <= .0001, f'Unity/PyTorch action error {error}'
    assert np.array_equal(out['env_action'].discrete[:,0],np.asarray([r['release'] for r in rows]))
    physical = np.zeros((len(rows),18),dtype=np.float32)
    mapping = [0,1,2,3,5,6,7,8,9,10,11,12,13,14,15,17]
    physical[:,mapping] = np.clip(actual,-1,1)
    physical[:,[3,5,17]] = (physical[:,[3,5,17]]+1)*.5
    physical[:,16] = np.asarray([r['release'] if r['canRelease'] else 0 for r in rows])
    mapping_error = float(np.max(np.abs(physical-np.asarray([r['physical'] for r in rows],dtype=np.float32))))
    assert mapping_error <= .000001
    result = dict(status='verified',arenas=report['arenas'],episodes=len(episodes),decisions=len(rows),physicsTicks=report['physicsTicks'],
        firstSeed=first,seedCount=count,outcomes=dict(collections.Counter(e['outcome'] for e in episodes)),
        meanReward=float(np.mean([e['reward'] for e in episodes])),maxActionError=error,
        maxPhysicalMappingError=mapping_error,checkpointStep=launch['checkpointStep'],
        sourceIdentity=launch['sourceIdentity'],modelHash=launch['modelHash'],checkpointHash=launch['checkpointHash'],
        validatorHash=digest(Path(__file__)),trainerConnected=False,deterministic=True)
    with destination.open('x') as handle:
        json.dump(result,handle,indent=2)
    print(json.dumps(result))

if __name__ == '__main__':
    main()

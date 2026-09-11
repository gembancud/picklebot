"""Convert measured physical traces with the pinned framework's demonstration writer/loader."""
from pathlib import Path
import json, hashlib
import numpy as np
from mlagents.trainers.demo_loader import write_demo, demo_to_buffer
from mlagents.trainers.buffer import BufferKey
from mlagents.trainers.trajectory import ObsUtil
from mlagents_envs.communicator_objects.brain_parameters_pb2 import BrainParametersProto
from mlagents_envs.communicator_objects.agent_info_action_pair_pb2 import AgentInfoActionPairProto
from mlagents_envs.communicator_objects.demonstration_meta_pb2 import DemonstrationMetaProto

ROOT=Path('F:/dev/picklebot')
RUN=ROOT/'artifacts/player-v3/movement-demonstrations-01'
CHANNELS=[0,1,2,3,5,6,7,8,9,10,11,12,13,14,15,17]
def main():
    report=json.loads((RUN/'report.json').read_text(encoding='utf-8'))
    assert report['status']=='complete' and not report['failure'] and len(report['episodes'])==32
    dest=RUN/'demos';dest.mkdir(exist_ok=False)
    all_rows=[];files=[]; seen={};conflicts=[]
    for episode in report['episodes']:
        seed=episode['seed'];path=RUN/f'{seed}.jsonl'
        rows=[json.loads(s) for s in path.read_text().splitlines()]
        assert len(rows)==episode['decisions']+1 and rows[-1]['terminal']
        assert rows[-1]['observationTick']==episode['ticks']
        assert all(not r['terminal'] and r['observationTick']==i*12 and r['applyTick']==i*12+6 for i,r in enumerate(rows[:-1]))
        assert episode['maxSpeed']<=12 and episode['maxAcceleration']<=100 and episode['maxAngularSpeed']<=11.99
        obs=np.asarray([r['observation'] for r in rows],dtype=np.float32)
        physical=np.asarray([r['physical'] for r in rows],dtype=np.float32)
        assert obs.shape==(len(rows),124) and np.isfinite(obs).all()
        controls=physical[:,CHANNELS].copy();controls[:,[3,4,15]]=controls[:,[3,4,15]]*2-1
        decoded=np.zeros_like(physical);decoded[:,CHANNELS]=controls;decoded[:,[3,5,17]]=(decoded[:,[3,5,17]]+1)/2
        assert np.max(abs(decoded-physical))<1e-6 and np.max(abs(controls))<=1
        for i,r in enumerate(rows[:-1]):
            key=tuple(obs[i].tolist()); previous=seen.get(key)
            if previous is not None and np.max(abs(previous[2]-controls[i]))>1e-5:
                conflicts.append(dict(firstSeed=previous[0],firstTick=previous[1],seed=seed,tick=r['observationTick'],maxActionDifference=float(np.max(abs(previous[2]-controls[i])))))
            seen[key]=(seed,r['observationTick'],controls[i])
        brain=BrainParametersProto(brain_name='PicklebotArticulated',is_training=True)
        brain.action_spec.num_continuous_actions=16;brain.action_spec.num_discrete_actions=1;brain.action_spec.discrete_branch_sizes.extend([2])
        pairs=[]
        for r,o,c in zip(rows,obs,controls):
            pair=AgentInfoActionPairProto();pair.agent_info.id=r['seat'];pair.agent_info.done=r['terminal'];pair.agent_info.reward=0
            observation=pair.agent_info.observations.add();observation.shape.extend([124]);observation.dimension_properties.extend([1]);observation.name='VectorSensor';observation.float_data.data.extend(o.tolist())
            pair.action_info.continuous_actions.extend(c.tolist());pair.action_info.discrete_actions.extend([0]);pairs.append(pair)
        meta=DemonstrationMetaProto(api_version=1,demonstration_name=str(seed),number_steps=len(pairs),number_episodes=1,mean_reward=0)
        demo=dest/f'{seed}.demo';write_demo(str(demo),meta,brain,pairs)
        spec,buffer=demo_to_buffer(str(demo),1)
        assert spec.action_spec.continuous_size==16 and tuple(spec.action_spec.discrete_branches)==(2,)
        assert buffer.num_experiences==episode['decisions']
        assert np.array_equal(np.asarray(buffer[ObsUtil.get_name_at(0)]),obs[:-1])
        assert np.array_equal(np.asarray(buffer[BufferKey.CONTINUOUS_ACTION]),controls[:-1])
        partition='train' if seed<1060776 else 'validation'
        files.append(dict(seed=seed,partition=partition,decisions=episode['decisions'],path=demo.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(demo.read_bytes()).hexdigest()))
        all_rows.extend(rows[:-1])
    result=dict(status='verified',episodes=len(files),decisions=len(all_rows),physicsTicks=report['physicsTicks'],files=files,exactObservationConflicts=conflicts,
        canonicalDemoActions='Environment continuous controls [-1,1]; release=0. Physical actions inverse-mapped and round-tripped exactly.',
        loaderRequirement='Load each .demo separately before merging training buffers: concatenating terminal frames across files otherwise creates cross-episode samples in this pinned loader.',
        bcRequirement='Pinned BC loss compares raw actor outputs. Convert continuous labels to raw coordinates by multiplying canonical environment controls by 3 in the project adapter, leaving .demo files unchanged.',
        limitations='Authored motion examples, not expert pickleball outcomes. Validation episodes are held out from cloning within the training-only seed allocation, not final or game-development evaluations.')
    (RUN/'demo-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='files'}))
if __name__=='__main__':main()

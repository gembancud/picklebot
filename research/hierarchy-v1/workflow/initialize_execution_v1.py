"""Initialize the 136-input executor from the pinned 124-input actor and critic.

This is a weight warm start with a fresh optimizer and experience counter,
not a resume. New goal weights are zero; original outputs are checked using
the installed ML-Agents actor/critic, including deterministic action outputs.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import numpy as np
from mlagents.torch_utils import torch
from mlagents.trainers.settings import TrainerSettings, NetworkSettings, ScheduleType
from mlagents.trainers.ppo.optimizer_torch import PPOSettings
from mlagents.trainers.ppo.trainer import PPOTrainer
from mlagents.trainers.behavior_id_utils import BehaviorIdentifiers
from mlagents_envs.base_env import BehaviorSpec, ObservationSpec, DimensionProperty, ObservationType, ActionSpec

OLD=124
NEW=136
BEHAVIOR='PicklebotExecutionV1'
FIRST='network_body._body_endoder.seq_layers.0.weight'

def make_trainer(size, directory):
    settings=TrainerSettings(hyperparameters=PPOSettings(batch_size=1024,buffer_size=8192,
        learning_rate=1e-4,learning_rate_schedule=ScheduleType.CONSTANT,
        beta_schedule=ScheduleType.CONSTANT,epsilon_schedule=ScheduleType.CONSTANT),
        network_settings=NetworkSettings(normalize=True,hidden_units=128,num_layers=2),
        max_steps=32768,summary_freq=2048,checkpoint_interval=32768)
    name=BEHAVIOR if size==NEW else 'PicklebotArticulated'
    trainer=PPOTrainer(name,10,settings,True,False,19001,str(directory))
    spec=BehaviorSpec([ObservationSpec((size,),(DimensionProperty.NONE,),ObservationType.DEFAULT,f'VectorSensor_size{size}')],ActionSpec(16,(2,)))
    parsed=BehaviorIdentifiers.from_name_behavior_id(name+'?team=0')
    policy=trainer.create_policy(parsed,spec)
    trainer.add_policy(parsed,policy)
    return trainer,policy

def expand(state):
    result=copy.deepcopy(state)
    if state[FIRST].shape!=(128,OLD): raise ValueError('Unexpected parent network')
    for key,value in state.items():
        if key==FIRST:
            result[key]=torch.cat([value,torch.zeros((128,NEW-OLD),dtype=value.dtype,device=value.device)],dim=1)
        elif key.endswith('normalizer.running_mean'):
            if value.shape!=(OLD,): raise ValueError('Unexpected normalizer shape')
            result[key]=torch.cat([value,torch.zeros(NEW-OLD,dtype=value.dtype,device=value.device)])
        elif key.endswith('normalizer.running_variance'):
            # Unit-variance prior for already-scaled goals. Preserve all old stats.
            steps=state[key.replace('running_variance','normalization_steps')]
            result[key]=torch.cat([value,torch.ones(NEW-OLD,dtype=value.dtype,device=value.device)*steps])
    return result

def verify(old_policy,new_policy,old_critic,new_critic):
    device=next(new_policy.actor.parameters()).device
    rng=np.random.RandomState(19007)
    mean=old_policy.actor.state_dict()['network_body.processors.0.normalizer.running_mean'].to(device)
    var=old_policy.actor.state_dict()['network_body.processors.0.normalizer.running_variance'].to(device)
    count=old_policy.actor.state_dict()['network_body.processors.0.normalizer.normalization_steps'].to(device)
    obs=mean+torch.tensor(rng.normal(size=(512,OLD)),dtype=torch.float32,device=device)*torch.sqrt(var/count)
    goals=torch.tensor(rng.uniform(-1,1,size=(512,NEW-OLD)),dtype=torch.float32,device=device)
    masks=torch.ones((512,2),device=device);masks[:,1]=0
    def outputs(policy,critic,x):
        encoded,_=policy.actor.network_body([x])
        exported=policy.actor([x],masks)
        value,_=critic([x])
        # Export indexes 4 and 7 are deterministic continuous/discrete actions.
        return encoded,exported[4],exported[7],value['extrinsic']
    with torch.no_grad():
        a=outputs(old_policy,old_critic,obs)
        b=outputs(new_policy,new_critic,torch.cat([obs,goals],dim=1))
        errors=[float((x-y).abs().max()) for x,y in zip(a,b)]
        for x,y in zip(a,b): torch.testing.assert_close(x,y,rtol=2e-5,atol=2e-5)
    # Goal input must have a live gradient path despite its zero initialization.
    new_policy.actor.zero_grad()
    encoded,_=new_policy.actor.network_body([torch.cat([obs,goals],dim=1)])
    encoded.square().mean().backward()
    grad=new_policy.actor.network_body._body_endoder.seq_layers[0].weight.grad[:,OLD:]
    if not bool(torch.isfinite(grad).all()) or not bool(grad.abs().sum()>0):
        raise AssertionError('Goal weights cannot learn')
    new_policy.actor.zero_grad()
    return dict(probes=512,maxErrors=dict(zip(['encoding','continuousAction','discreteAction','critic'],errors)),goalGradientNonzero=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists(): raise FileExistsError('Use a fresh initialization directory')
    parent=torch.load(args.parent,map_location='cpu',weights_only=False)
    args.output.mkdir(parents=True)
    with tempfile.TemporaryDirectory() as tmp:
        old,op=make_trainer(OLD,Path(tmp)/'parent')
        new,np_=make_trainer(NEW,args.output)
        op.actor.load_state_dict(parent['Policy'],strict=True)
        old.optimizer.critic.load_state_dict(parent['Optimizer:critic'],strict=True)
        np_.actor.load_state_dict(expand(parent['Policy']),strict=True)
        new.optimizer.critic.load_state_dict(expand(parent['Optimizer:critic']),strict=True)
        checks=verify(op,np_,old.optimizer.critic,new.optimizer.critic)
        if new.optimizer.optimizer.state_dict()['state']: raise AssertionError('Optimizer must start fresh')
        new.model_saver.save_checkpoint(BEHAVIOR,0)
        state=torch.load(args.output/'checkpoint.pt',map_location='cpu',weights_only=False)
        assert int(next(iter(state['global_step'].values())).item())==0
        assert not state['Optimizer:value_optimizer']['state']
        record=dict(status='warm_start_verified',parent=str(args.parent.resolve()),
            parentHash=hashlib.sha256(args.parent.read_bytes()).hexdigest(),
            parentStep=int(next(iter(parent['global_step'].values())).item()),
            behavior=BEHAVIOR,observationCount=NEW,continuousCount=16,discreteBranches=[2],
            optimizer='fresh',globalStep=0,goalNormalization='zero-mean unit-variance prior using inherited normalization count',
            checks=checks,files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in args.output.iterdir() if p.is_file()})
        (args.output/'initialization.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
        print(json.dumps(record))

if __name__=='__main__': main()

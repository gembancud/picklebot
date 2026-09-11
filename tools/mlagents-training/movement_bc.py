"""Offline warm start using the pinned ML-Agents BCModule, with explicit action-coordinate adaptation.

No project-owned RL or cloning optimizer is implemented here. Canonical Unity demos
remain [-1,1]; the adapter converts labels into the raw coordinates used by BCModule.
"""
import argparse, hashlib, inspect, json, time
from pathlib import Path
import numpy as np
import torch
from mlagents.torch_utils import set_torch_config
from mlagents.trainers.settings import TorchSettings, NetworkSettings, BehavioralCloningSettings
from mlagents.trainers.policy.torch_policy import TorchPolicy
from mlagents.trainers.torch_entities.networks import SimpleActor
from mlagents.trainers.torch_entities.components.bc.module import BCModule
from mlagents.trainers.torch_entities.model_serialization import ModelSerializer
from mlagents.trainers.torch_entities.agent_action import AgentAction
from mlagents.trainers.demo_loader import demo_to_buffer
from mlagents.trainers.buffer import AgentBuffer, BufferKey
from mlagents.trainers.trajectory import ObsUtil

ROOT=Path('F:/dev/picklebot')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load_partition(manifest,partition):
    result=AgentBuffer();spec=None
    for entry in manifest['files']:
        if entry['partition']!=partition:continue
        path=ROOT/entry['path'];assert sha(path)==entry['sha256']
        current_spec,buffer=demo_to_buffer(str(path),1,spec)
        spec=current_spec;assert buffer.num_experiences==entry['decisions']
        for key,field in buffer.items():result[key].extend(field)
    return spec,result

def metrics(policy,buffer):
    actor=SimpleActor(policy.behavior_spec.observation_specs,NetworkSettings(normalize=True,hidden_units=128,num_layers=2,deterministic=True),policy.behavior_spec.action_spec,conditional_sigma=False,tanh_squash=False).to('cuda')
    actor.load_state_dict(policy.actor.state_dict(),strict=True);actor.eval()
    obs=torch.as_tensor(np.asarray(buffer[ObsUtil.get_name_at(0)]),device='cuda')
    with torch.no_grad():_,out,_=actor.get_action_and_stats([obs],masks=torch.ones((len(obs),2),device='cuda'))
    wanted=np.asarray(buffer[BufferKey.CONTINUOUS_ACTION]);error=out['env_action'].continuous-wanted
    return dict(samples=len(obs),continuousRmse=float(np.sqrt(np.mean(error**2))),paddleAndTorsoRmse=float(np.sqrt(np.mean(error[:,5:15]**2))),maxAbsoluteError=float(np.max(abs(error))),releaseZeroRate=float(np.mean(out['env_action'].discrete==0)))

def main():
    p=argparse.ArgumentParser();p.add_argument('--updates',type=int,default=128);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    assert not args.output.exists();args.output.mkdir(parents=True)
    manifest_path=ROOT/'artifacts/player-v3/movement-demonstrations-01/demo-verification.json';manifest=json.loads(manifest_path.read_text())
    assert manifest['status']=='verified' and max(c['maxActionDifference'] for c in manifest['exactObservationConflicts'])<.01
    spec,train=load_partition(manifest,'train');_,validation=load_partition(manifest,'validation')
    set_torch_config(TorchSettings(device='cuda'));torch.set_num_threads(2);torch.manual_seed(4106);np.random.seed(4106)
    policy=TorchPolicy(4106,spec,NetworkSettings(normalize=True,hidden_units=128,num_layers=2),SimpleActor,dict(conditional_sigma=False,tanh_squash=False))
    parent=ROOT/'artifacts/mlagents/articulated-return-01/PicklebotArticulated/PicklebotArticulated-196622.pt'
    parent_hash=sha(parent);checkpoint=torch.load(parent,map_location='cuda',weights_only=False)
    policy.actor.load_state_dict(checkpoint['Policy'],strict=True)
    assert all(torch.equal(v,checkpoint['Policy'][k]) for k,v in policy.actor.state_dict().items())
    before=dict(train=metrics(policy,train),validation=metrics(policy,validation))
    settings=BehavioralCloningSettings(demo_path=str(ROOT/manifest['files'][0]['path']),strength=1,steps=0,batch_size=256,num_epoch=1,samples_per_update=2048)
    bc=BCModule(policy,settings,.0003,256,1)
    # Preserve observation and episode boundaries from each individually loaded demo.
    prepared=AgentBuffer()
    for key,field in train.items():prepared[key].extend(field)
    targets=np.asarray(prepared[BufferKey.CONTINUOUS_ACTION],dtype=np.float32)
    raw=targets*3
    converted=AgentAction(torch.as_tensor(raw,device='cuda'),None).to_action_tuple(clip=True).continuous
    assert np.max(abs(converted-targets))<=1e-7
    # Without conversion, even a perfect raw-space match executes at one-third amplitude.
    wrong=AgentAction(torch.as_tensor(targets,device='cuda'),None).to_action_tuple(clip=True).continuous
    assert np.max(abs(wrong-targets))>.6
    prepared[BufferKey.CONTINUOUS_ACTION].set(list(raw))
    bc.demonstration_buffer=prepared;bc.n_sequences=256
    launch=dict(parent=str(parent.relative_to(ROOT)),parentHash=parent_hash,parentEnvironmentSteps=196622,seed=4106,updates=args.updates,trainSamples=train.num_experiences,validationSamples=validation.num_experiences,frameworkBC=inspect.getfile(BCModule),frameworkBCHash=sha(inspect.getfile(BCModule)),scriptHash=sha(__file__),manifestHash=sha(manifest_path),normalizer='Copied unchanged; no normalizer updates during BC.',actionLabelTransform='raw=3*canonicalEnvironmentControl; checked through upstream AgentAction.to_action_tuple(clip=True)',algorithm='Unmodified pinned BCModule.update; fresh BC Adam, no new RL environment steps.',before=before)
    (args.output/'launch.json').write_text(json.dumps(launch,indent=2),encoding='utf-8')
    started=time.perf_counter();trace=[]
    for update in range(1,args.updates+1):
        result=bc.update();assert np.isfinite(result['Losses/Pretraining Loss'])
        if update%16==0 or update==args.updates:
            row=dict(update=update,loss=float(result['Losses/Pretraining Loss']),elapsedSeconds=time.perf_counter()-started,validation=metrics(policy,validation));trace.append(row);print(json.dumps(row),flush=True)
    after=dict(train=metrics(policy,train),validation=metrics(policy,validation))
    assert all(torch.isfinite(v).all() for v in policy.actor.state_dict().values())
    assert sha(parent)==parent_hash
    for k,v in policy.actor.state_dict().items():
        if 'normalizer' in k:assert torch.equal(v,checkpoint['Policy'][k])
    saved={name:module.state_dict() for name,module in policy.get_modules().items()};saved['BC:adam']=bc.optimizer.state_dict()
    torch.save(saved,args.output/'checkpoint.pt')
    ModelSerializer(policy).export_policy_model(str(args.output/'PicklebotMovement'))
    adam=sorted(set(float(v['step']) for v in bc.optimizer.state_dict()['state'].values()))
    summary=dict(status='offline_bc_completed_not_accepted',before=before,after=after,bcAdamSteps=adam,rlEnvironmentStepsAdded=0,elapsedSeconds=time.perf_counter()-started,trace=trace,checkpointHash=sha(args.output/'checkpoint.pt'),onnxHash=sha(args.output/'PicklebotMovement.onnx'),parentUnchanged=True,limitation='Offline action imitation only. Closed-loop movement and legal-return transfer remain unverified; no gameplay promotion.')
    (args.output/'verification.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary),flush=True)
if __name__=='__main__':main()

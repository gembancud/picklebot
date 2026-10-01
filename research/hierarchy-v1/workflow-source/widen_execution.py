"""Function-preserving two-layer Swish network widening; maintained PPO trainer."""
from pathlib import Path
import copy,json,hashlib
import torch,yaml
from mlagents import torch_utils
from mlagents.trainers.learn import parse_command_line
from mlagents.trainers.ppo.trainer import PPOTrainer
from mlagents.trainers.behavior_id_utils import BehaviorIdentifiers
from mlagents_envs.base_env import BehaviorSpec,ObservationSpec,DimensionProperty,ObservationType,ActionSpec
R=Path('F:/dev/picklebot'); A=R/'artifacts/hierarchy-v1/randomized-scale-01'
B='PicklebotExecutionV1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):
 with p.open('x',encoding='utf-8') as f:json.dump(x,f,indent=2)
def trainer(config,width):
 opts=parse_command_line([str(config),'--run-id',f'transfer-validation-{width}','--results-dir',str(A/'validation')])
 torch_utils.set_torch_config(opts.torch_settings)
 torch.set_default_device('cpu')
 t=PPOTrainer(B,10,opts.behaviors[B],True,False,19023,str(A/'validation'/str(width)))
 spec=BehaviorSpec([ObservationSpec((136,),(DimensionProperty.NONE,),ObservationType.DEFAULT,'VectorSensor_size136')],ActionSpec(16,(2,)))
 ident=BehaviorIdentifiers.from_name_behavior_id(B+'?team=0')
 p=t.create_policy(ident,spec);t.add_policy(ident,p)
 return t
def widened(old):
 out=copy.deepcopy(old);gen=torch.Generator().manual_seed(19023)
 first='network_body._body_endoder.seq_layers.0.'
 second='network_body._body_endoder.seq_layers.2.'
 heads=['action_model._continuous_distribution.mu.weight','action_model._discrete_distribution.branches.0.weight','value_heads.value_heads.extrinsic.weight']
 for k,v in old.items():
  if k in (first+'weight',first+'bias',second+'bias'):out[k]=torch.cat([v,v],0)
  elif k==second+'weight' or k in heads:
   w=torch.cat([v,v],0) if k==second+'weight' else v
   alpha=.35+.3*torch.rand(w.shape,generator=gen,device='cpu')
   out[k]=torch.cat([w*alpha,w*(1-alpha)],1)
 return out
def outputs(t,obs):
 actor=t.model_saver.modules['Policy'];critic=t.model_saver.modules['Optimizer:critic']
 actor.eval();critic.eval()
 with torch.no_grad():
  h,_=actor.network_body([obs]);a=actor.action_model
  return [a._continuous_distribution.mu(h),a._discrete_distribution.branches[0](h),critic([obs])[0]['extrinsic']]
def main():
 A.mkdir(exist_ok=True);assert not (A/'transfer-proof.json').exists()
 parent=R/'artifacts/mlagents/execution-right-retention-01'/B/'checkpoint.pt'
 assert sha(parent)=='e6e02e45d4d44a12db25dea8b88692db3887aad1ef17627ae6054d46bf6dadad'
 old=torch.load(parent,map_location='cpu',weights_only=False)
 config=yaml.safe_load((R/'config/mlagents/execution-v1-movement-progress.yaml').read_text(encoding='utf-8'))
 config['torch_settings']['device']='cpu'
 paths=[]
 for width in (128,256):
  config['behaviors'][B]['network_settings']['hidden_units']=width
  p=A/f'transfer-{width}.yaml'
  if p.exists():assert p.read_text(encoding='utf-8')==yaml.safe_dump(config)
  else:p.write_text(yaml.safe_dump(config),encoding='utf-8')
  paths.append(p)
 small=trainer(paths[0],128);large=trainer(paths[1],256)
 for t in (small,large):
  for m in t.model_saver.modules.values():
   if isinstance(m,torch.nn.Module):m.cpu()
 for key in ('Policy','Optimizer:critic'):
  small.model_saver.modules[key].load_state_dict(old[key],strict=True)
  large.model_saver.modules[key].load_state_dict(widened(old[key]),strict=True)
 rows=[]
 for p in (R/'artifacts/hierarchy-v1/right-retention-01/evaluation').rglob('first-decisions.json'):
  data=json.loads(p.read_text(encoding='utf-8-sig'))
  rows.extend(row['observation'] for row in data.values())
 assert len(rows)>=2000
 obs=torch.tensor(rows,dtype=torch.float32,device='cpu')
 torch.manual_seed(19023);probe=torch.cat([obs,torch.randn(4096,136,device='cpu')],0)
 errors=[]
 for a,b in zip(outputs(small,probe),outputs(large,probe)):
  assert torch.isfinite(b).all();torch.testing.assert_close(a,b,atol=2e-5,rtol=2e-5)
  errors.append(float((a-b).abs().max()))
 state={k:copy.deepcopy(m.state_dict()) for k,m in large.model_saver.modules.items()}
 assert not state['Optimizer:value_optimizer']['state']
 assert all(v.item()==0 for v in state['global_step'].values())
 dest=A/'initial-02';dest.mkdir();torch.save(state,dest/'checkpoint.pt')
 # Verify actual installed initialize loader, including critic and fresh optimizer.
 large.model_saver._load_model(str(dest/'checkpoint.pt'),reset_global_steps=True)
 for key,m in large.model_saver.modules.items():
  loaded=m.state_dict()
  if key in ('Policy','Optimizer:critic','global_step'):
   assert all(torch.equal(v,loaded[k]) for k,v in state[key].items())
 assert not large.model_saver.modules['Optimizer:value_optimizer'].state_dict()['state']
 large.model_saver.export(str(dest/B),B)
 write(A/'transfer-proof.json',dict(parent=str(parent),parentHash=sha(parent),parentStep=2097180,initialStep=0,hiddenUnits=256,layers=2,realObservations=len(rows),numericalProbes=4096,maxOutputErrors=errors,optimizer='fresh Adam; old moments intentionally not transferred',normalizersPreserved=True,checkpointHash=sha(dest/'checkpoint.pt'),onnxHash=sha(dest/(B+'.onnx')),strictActorCriticLoad=True,installedInitializeLoadVerified=True))
 print(json.dumps({'status':'widened_and_verified','maxErrors':errors,'realObservations':len(rows)}))
if __name__=='__main__':main()

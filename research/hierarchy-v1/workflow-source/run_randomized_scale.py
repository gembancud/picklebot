"""Validate a frozen worker probe then launch a bounded maintained PPO run."""
from pathlib import Path
import json,hashlib,subprocess,sys,time,socket,traceback
import torch,yaml
R=Path('F:/dev/picklebot');A=R/'artifacts/hierarchy-v1/randomized-scale-01';B='PicklebotExecutionV1'
NAME='execution-randomized-scale-01'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):
 with p.open('x',encoding='utf-8') as f:json.dump(x,f,indent=2)
def state_equal(a,b):
 if isinstance(a,torch.Tensor):return torch.equal(a.cpu(),b.cpu())
 if isinstance(a,dict):return a.keys()==b.keys() and all(state_equal(a[k],b[k]) for k in a)
 if isinstance(a,(list,tuple)):return len(a)==len(b) and all(state_equal(x,y) for x,y in zip(a,b))
 return a==b
def phase(label,inference,build,source):
 folder=A/label;folder.mkdir();name=NAME+('-probe' if inference else '')
 assert not (R/'artifacts/mlagents'/name).exists()
 config=yaml.safe_load((R/'config/mlagents/execution-v1-movement-progress.yaml').read_text(encoding='utf-8'))
 behavior=config['behaviors'][B];behavior['network_settings']['hidden_units']=256
 behavior.update(init_path=str(A/'initial-02/checkpoint.pt'),max_steps=8000000,checkpoint_interval=1000000,keep_checkpoints=10)
 (folder/'config.yaml').write_text(yaml.safe_dump(config,sort_keys=False),encoding='utf-8')
 manifest=read(R/'artifacts/hierarchy-v1/right-retention-01/training/manifest.json')
 manifest.update(evidenceRoot=str(folder),sourceIdentity=source['sourceIdentity'],buildIdentity=build['buildIdentity'],basePort=6155,workerCount=1 if inference else 8,firstSeed=2000000,seedsPerWorker=512 if inference else 122880,movementPattern='randomized',movementRange=.25,movementRehearsalRange=.1,maximumReturnDifficulty=.5,recordDecisions=inference)
 write(folder/'manifest.json',manifest)
 cmd=[str(Path(sys.executable).parent/'Scripts/mlagents-learn.exe'),str(folder/'config.yaml'),'--run-id',name,'--results-dir',str(R/'artifacts/mlagents'),'--seed','19023','--env',str(Path(build['directory'])/'Picklebot.exe'),'--num-envs',str(manifest['workerCount']),'--base-port','6155','--no-graphics','--timeout-wait','180','--max-lifetime-restarts','0']
 if inference:cmd+=['--inference','--deterministic']
 cmd+=['--env-args','--picklebot-manifest',str(folder/'manifest.json')]
 write(folder/'launch.json',dict(command=cmd,configHash=sha(folder/'config.yaml'),manifestHash=sha(folder/'manifest.json'),additionalSteps=0 if inference else 8000000,checkpointInterval=1000000,maximumWallSeconds=1800 if inference else 43200))
 with (folder/'trainer-console.log').open('x',encoding='utf-8') as log:
  p=subprocess.Popen(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  write(folder/'process.json',dict(pid=p.pid,started=time.time(),owned=True));print(label,p.pid,flush=True)
  try:code=p.wait(timeout=1800 if inference else 43200)
  except subprocess.TimeoutExpired:
   subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True);raise
 write(folder/'exit.json',dict(exitCode=code,finished=time.time()))
 return folder,R/'artifacts/mlagents'/name
def main():
 build=read(A/'build-verification.json');source=read(A/'source-records.json');proof=read(A/'transfer-proof.json')
 assert sha(A/'initial-02/checkpoint.pt')==proof['checkpointHash']
 assert all(sha(R/p)==v for p,v in source['files'].items())
 assert all(sha(Path(build['directory'])/p)==v for p,v in build['files'].items())
 for port in range(6155,6163):
  with socket.socket() as s:s.bind(('0.0.0.0',port))
 ledgerpath=R/'artifacts/player-v3/seed-ledger.json';ledger=read(ledgerpath);assert not ledger['finalSeedsConsumed']
 write(A/'seed-ledger-before.json',ledger)
 ledger.setdefault('expandedTrainingBlocks',[]).append(dict(firstSeed=2000000,count=983040,run=NAME,purpose='Randomized continuous reset recipe, 256x2, 8million additional steps; probe reuses first512 training seeds.'))
 ledger.setdefault('expandedDevelopmentBlocks',[]).append(dict(firstSeed=4000000,count=100000,run=NAME,purpose='Reserved randomized development; never training.'))
 ledgerpath.write_bytes(json.dumps(ledger,indent=2).encode('utf-8'))
 folder,result=phase('probe',True,build,source)
 report=read(folder/'worker-00/report.json');finish=read(folder/'worker-00/worker-finish.json')
 assert finish['status']=='seed_budget_complete' and report['completedEpisodes']==512 and not report['failure']
 initial=torch.load(A/'initial-02/checkpoint.pt',map_location='cpu',weights_only=False)
 # Inference need not emit a checkpoint. When it does, verify no parameter updates.
 cp=result/B/'checkpoint.pt'
 if cp.exists():
  frozen=torch.load(cp,map_location='cpu',weights_only=False)
  for key in initial:
   if key!='global_step':assert state_equal(initial[key],frozen[key]),key
 eps=[json.loads(x) for x in (folder/'worker-00/episodes.jsonl').read_text(encoding='utf-8').splitlines()]
 assert len(eps)==512 and all(not e['precontactAlignmentRewardEnabled'] and not e['movementForwardProgressRewardEnabled'] for e in eps)
 focus=[e for e in eps if (e['seed']-2000000)%256>=128]
 assert len(focus)==256 and len(set(e['movementRange'] for e in focus))>250
 write(A/'probe-proof.json',dict(episodes=512,focusEpisodes=256,distinctFocusDistances=len(set(e['movementRange'] for e in focus)),completed=True,finalSeedsConsumed=False,legal=sum(e['outcome']=='legal_return' for e in eps),inferenceOnly=True))
 folder,result=phase('training',False,build,source)
 assert read(folder/'exit.json')['exitCode']==0
 final=torch.load(result/B/'checkpoint.pt',map_location='cpu',weights_only=False)
 step=int(next(iter(final['global_step'].values())).item());assert 8000000<=step<8008192
 for key in ('Policy','Optimizer:critic'):
  assert final[key]['network_body._body_endoder.seq_layers.0.weight'].shape==(256,136)
  assert all(torch.isfinite(t).all() for t in final[key].values())
  assert not state_equal(initial[key],final[key])
 assert final['Optimizer:value_optimizer']['state']
 assert sha(A/'initial-02/checkpoint.pt')==proof['checkpointHash']
 assert not read(ledgerpath)['finalSeedsConsumed']
 write(A/'run-complete.json',dict(step=step,checkpointHash=sha(result/B/'checkpoint.pt'),modelHash=sha(result/(B+'.onnx')),promoted=False,evaluationPending=True))
 print('Eight million additional steps complete; frozen evaluation required.',flush=True)
if __name__=='__main__':
 try:main()
 except Exception:
  with (A/'runner-failure.txt').open('a',encoding='utf-8') as f:f.write(traceback.format_exc())
  raise

from pathlib import Path
import json,hashlib,shutil,subprocess,sys,time,importlib.util,traceback
import torch,yaml
R=Path('F:/dev/picklebot');A=R/'artifacts/hierarchy-v1/randomized-scale-24m';OLD=R/'artifacts/hierarchy-v1/randomized-scale-01';B='PicklebotExecutionV1';NAME='execution-randomized-scale-24m'
PARENT=R/'artifacts/mlagents/execution-randomized-scale-01';RESULT=R/'artifacts/mlagents'/NAME
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):
 with p.open('x',encoding='utf-8') as f:json.dump(x,f,indent=2)
def main():
 assert not A.exists() and not RESULT.exists();A.mkdir();T=A/'training';T.mkdir()
 parent=PARENT/B/'checkpoint.pt';assert sha(parent)=='a097fcbd1a44cd2431134565f00c9c04c2d6138a7a3d6443a94a8d86faa87ca4'
 spec=importlib.util.spec_from_file_location('resume_helper',R/'tools/mlagents-training/run_smooth_continuation.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
 h.START=8000058;h.RUN=NAME;h.TRAINING_SEED=19023
 source=read(OLD/'source-records.json');build=read(OLD/'build-verification.json')
 for p,digest in source['files'].items():assert sha(R/p)==digest,p
 for p,digest in build['files'].items():assert sha(Path(build['directory'])/p)==digest,p
 shutil.copyfile(OLD/'source-records.json',A/'source-records.json');shutil.copyfile(OLD/'build-verification.json',A/'build-verification.json')
 original=h.tree_hashes(PARENT);write(A/'parent-inputs.json',original)
 shutil.copytree(PARENT,RESULT);h.remap_status(PARENT,RESULT,T)
 config=yaml.safe_load((OLD/'training/config.yaml').read_text(encoding='utf-8'));behavior=config['behaviors'][B]
 behavior.pop('init_path');behavior.update(max_steps=24000000,checkpoint_interval=2000000,keep_checkpoints=24)
 path=T/'config.yaml';path.write_text(yaml.safe_dump(config,sort_keys=False),encoding='utf-8')
 manifest=read(OLD/'training/manifest.json');manifest.update(evidenceRoot=str(T),basePort=6255)
 write(T/'manifest.json',manifest)
 args=[str(path),'--run-id',NAME,'--results-dir',str(R/'artifacts/mlagents'),'--resume','--seed','19023','--env',str(Path(build['directory'])/'Picklebot.exe'),'--num-envs','8','--base-port','6255','--no-graphics','--timeout-wait','180','--max-lifetime-restarts','0','--env-args','--picklebot-manifest',str(T/'manifest.json')]
 state=torch.load(parent,map_location='cpu',weights_only=False)
 h.verify_resume_loader(path,['mlagents-learn']+args,RESULT,state,T)
 ledgerpath=R/'artifacts/player-v3/seed-ledger.json';ledger=read(ledgerpath);assert not ledger['finalSeedsConsumed'];write(A/'seed-ledger-before.json',ledger)
 ledger.setdefault('trainingReuses',[]).append(dict(firstSeed=2000000,count=983040,run=str(T.relative_to(R)),purpose='Same randomized distribution; resume8000058 to24000000 with preserved Adam/actor/critic/normalizers. Environment/RNG streams restart.'))
 ledgerpath.write_bytes(json.dumps(ledger,indent=2).encode('utf-8'))
 command=[str(Path(sys.executable).parent/'Scripts/mlagents-learn.exe')]+args
 write(T/'launch.json',dict(command=command,startStep=8000058,targetStep=24000000,additionalSteps=15999942,parentHash=sha(parent),curriculumUnchanged=True,optimizerPreserved=True,checkpointsEvery=2000000))
 with (T/'trainer-console.log').open('x',encoding='utf-8') as log:
  p=subprocess.Popen(command,cwd=R,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);write(T/'process.json',dict(pid=p.pid,started=time.time(),owned=True));print('Trainer',p.pid,flush=True)
  try:code=p.wait(timeout=86400)
  except subprocess.TimeoutExpired:
   subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True);raise
 write(T/'exit.json',dict(exitCode=code));assert code==0
 assert h.tree_hashes(PARENT)==original
 final=torch.load(RESULT/B/'checkpoint.pt',map_location='cpu',weights_only=False);step=h.step_of(final);assert 24000000<=step<24008192
 for key in ('Policy','Optimizer:critic'):
  assert all(torch.isfinite(v).all() for v in final[key].values())
  assert not torch.equal(state[key][h.FIRST_LAYER],final[key][h.FIRST_LAYER])
 assert final['Optimizer:value_optimizer']['state']
 write(A/'run-complete.json',dict(step=step,parentUnchanged=True,checkpointHash=sha(RESULT/B/'checkpoint.pt'),modelHash=sha(RESULT/(B+'.onnx')),promoted=False))
if __name__=='__main__':
 try:main()
 except Exception:
  A.mkdir(exist_ok=True);(A/'runner-failure.txt').write_text(traceback.format_exc(),encoding='utf-8');raise

"""One bounded trainer-delivery probe, never promoted or used as the long-run parent."""
from pathlib import Path
import json,hashlib,subprocess,sys,os,time,shutil,importlib.util,socket
import yaml,torch
R=Path("F:/dev/picklebot");H=Path(__file__).resolve().parent
NAME="execution-precontact-delivery-01";START=1048609;TARGET=START+8192
BASE=R/"artifacts/hierarchy-v1/precontact-alignment-01";A=BASE/"delivery-probe";RESULT=R/"artifacts/mlagents"/NAME
PARENT=R/"artifacts/mlagents/execution-smooth-continued-01";B="PicklebotExecutionV1"
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding="utf-8-sig"))
def write(p,x):
 with p.open("x",encoding="utf-8") as f:json.dump(x,f,indent=2)
def main():
 assert not A.exists() and not RESULT.exists()
 build=read(BASE/"build-verification.json");source=read(BASE/"source-records.json")
 for rel,digest in source["files"].items():assert sha(R/rel)==digest
 for rel,digest in build["files"].items():assert sha(Path(build["directory"])/rel)==digest
 checkpoint=PARENT/B/"checkpoint.pt";assert sha(checkpoint)=="c882329d7303f75703338738868a2ba53f553940e876b7962a7d410f20fa5a3d"
 helper_path=R/"tools/mlagents-training/run_smooth_continuation.py";assert sha(helper_path)=="c4454b1c7e69b50386ece91167edcc5d67def34886247079cb0c25fbe633d715"
 spec=importlib.util.spec_from_file_location("resume_helper",helper_path);helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper);helper.START=START;helper.RUN=NAME;helper.TRAINING_SEED=19023
 with socket.socket() as sock:sock.bind(("127.0.0.1",5855))
 A.mkdir();parent_hashes=helper.tree_hashes(PARENT);write(A/"parent-inputs.json",parent_hashes)
 shutil.copytree(PARENT,RESULT);assert helper.tree_hashes(RESULT)==parent_hashes;helper.remap_status(PARENT,RESULT,A)
 config=yaml.safe_load((R/"config/mlagents/execution-v1-movement-progress.yaml").read_text());behavior=config["behaviors"][B];assert behavior["reward_signals"]["extrinsic"]["gamma"]==.99
 behavior["max_steps"]=TARGET;behavior["checkpoint_interval"]=8192
 config_path=A/"config.yaml";config_path.write_text(yaml.safe_dump(config,sort_keys=False))
 manifest=read(R/"artifacts/hierarchy-v1/smooth-continued-01/training/manifest.json")
 manifest.update(evidenceRoot=str(A),sourceIdentity=source["sourceIdentity"],buildIdentity=build["buildIdentity"],basePort=5855,workerCount=1,movementPattern="axes",movementRange=.0625,movementForwardProgressReward=False,precontactAlignmentReward=True,precontactGamma=.99,optimizerDiagnostics=True)
 assert manifest["precontactGamma"]==behavior["reward_signals"]["extrinsic"]["gamma"]
 write(A/"manifest.json",manifest)
 args=[str(config_path),"--run-id",NAME,"--results-dir",str(R/"artifacts/mlagents"),"--resume","--seed","19023","--env",str(Path(build["directory"])/"Picklebot.exe"),"--num-envs","1","--base-port","5855","--no-graphics","--timeout-wait","180","--max-lifetime-restarts","0","--env-args","--picklebot-manifest",str(A/"manifest.json")]
 helper.verify_resume_loader(config_path,["mlagents-learn"]+args,RESULT,torch.load(checkpoint,map_location="cpu",weights_only=False),A)
 wrapper=H/"trainer_reward_delivery_wrapper.py";command=[sys.executable,str(wrapper)]+args
 write(A/"launch.json",dict(args=command,wrapperHash=sha(wrapper),runnerHash=sha(Path(__file__)),configHash=sha(config_path),manifestHash=sha(A/"manifest.json"),sourceIdentity=source["sourceIdentity"],budget=8192,maximumWallSeconds=900,promotion=False))
 ledger_path=R/"artifacts/player-v3/seed-ledger.json";ledger=read(ledger_path);assert not ledger["finalSeedsConsumed"]
 assert not any(x["run"]==str(A.relative_to(R)) for x in ledger.get("trainingReuses",[]))
 write(A/"seed-ledger-before.json",ledger);ledger.setdefault("trainingReuses",[]).append(dict(firstSeed=1000000,count=12288,run=str(A.relative_to(R)),purpose="One8192-experience trainer delivery probe from preserved parent; discarded as training parent; no final seeds."));ledger_path.write_text(json.dumps(ledger,indent=2))
 env=dict(os.environ,PICKLEBOT_DELIVERY_AUDIT=str(A/"received-rewards.jsonl"));start=time.monotonic()
 with (A/"trainer-console.log").open("x",encoding="utf-8") as log:
  process=subprocess.Popen(command,cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);write(A/"process.json",dict(pid=process.pid,started=time.time(),owned=True));print(f"Delivery probe trainer{process.pid}",flush=True)
  try:code=process.wait(timeout=900)
  except subprocess.TimeoutExpired:
   subprocess.run(["taskkill","/PID",str(process.pid),"/T","/F"],capture_output=True);raise
 write(A/"process-result.json",dict(exitCode=code,wallSeconds=time.monotonic()-start));assert code==0,"Probe failed; preserve logs"
 assert helper.tree_hashes(PARENT)==parent_hashes
 final=torch.load(RESULT/B/"checkpoint.pt",map_location="cpu",weights_only=False);step=helper.step_of(final);assert TARGET<=step<TARGET+8192
 write(A/"run-complete.json",dict(step=step,requiredRewardAuditPending=True,parentUnchanged=True,promotion=False));print(f"Probe completed at{step}; reward audit pending.")
if __name__=="__main__":main()

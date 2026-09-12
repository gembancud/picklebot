"""Fixed precontact reward arm from the preserved common parent; evaluation required."""
from pathlib import Path
import json,hashlib,subprocess,sys,os,time,shutil,importlib.util,socket
import yaml,torch
R=Path("F:/dev/picklebot");H=Path(__file__).resolve().parent
NAME="execution-precontact-alignment-01";START=1048609;TARGET=2097152
BASE=R/"artifacts/hierarchy-v1/precontact-alignment-01";A=BASE/"training";RESULT=R/"artifacts/mlagents"/NAME
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
 spec=importlib.util.spec_from_file_location("resume_helper",helper_path);helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper);helper.START=START;helper.RUN=NAME;helper.TRAINING_SEED=19017
 for port in range(5955,5963):
  with socket.socket() as sock:sock.bind(("0.0.0.0",port))
 proof=read(BASE/"delivery-probe-02/reward-delivery-verification.json")
 assert proof["status"]=="passed_transport_multiset_audit" and proof["episodes"]>=200
 for rel,digest in proof["inputs"].items():assert sha(BASE/"delivery-probe-02"/rel)==digest
 A.mkdir();parent_hashes=helper.tree_hashes(PARENT);write(A/"parent-inputs.json",parent_hashes)
 shutil.copytree(PARENT,RESULT);assert helper.tree_hashes(RESULT)==parent_hashes;helper.remap_status(PARENT,RESULT,A)
 config=yaml.safe_load((R/"config/mlagents/execution-v1-movement-progress.yaml").read_text());behavior=config["behaviors"][B];assert behavior["reward_signals"]["extrinsic"]["gamma"]==.99
 behavior["max_steps"]=TARGET;behavior["checkpoint_interval"]=524288
 config_path=A/"config.yaml";config_path.write_text(yaml.safe_dump(config,sort_keys=False))
 manifest=read(R/"artifacts/hierarchy-v1/smooth-continued-01/training/manifest.json")
 manifest.update(evidenceRoot=str(A),sourceIdentity=source["sourceIdentity"],buildIdentity=build["buildIdentity"],basePort=5955,workerCount=8,movementPattern="axes",movementRange=.0625,movementForwardProgressReward=False,precontactAlignmentReward=True,precontactGamma=.99,optimizerDiagnostics=False)
 assert manifest["precontactGamma"]==behavior["reward_signals"]["extrinsic"]["gamma"]
 write(A/"manifest.json",manifest)
 args=[str(config_path),"--run-id",NAME,"--results-dir",str(R/"artifacts/mlagents"),"--resume","--seed","19017","--env",str(Path(build["directory"])/"Picklebot.exe"),"--num-envs","8","--base-port","5955","--no-graphics","--timeout-wait","180","--max-lifetime-restarts","0","--env-args","--picklebot-manifest",str(A/"manifest.json")]
 helper.verify_resume_loader(config_path,["mlagents-learn"]+args,RESULT,torch.load(checkpoint,map_location="cpu",weights_only=False),A)
 command=[str(Path(sys.executable).parent/"Scripts/mlagents-learn.exe")]+args
 write(A/"launch.json",dict(args=command,runnerHash=sha(Path(__file__)),configHash=sha(config_path),manifestHash=sha(A/"manifest.json"),sourceIdentity=source["sourceIdentity"],budget=TARGET-START,maximumWallSeconds=3600,promotion=False))
 ledger_path=R/"artifacts/player-v3/seed-ledger.json";ledger=read(ledger_path);assert not ledger["finalSeedsConsumed"]
 assert not any(x["run"]==str(A.relative_to(R)) for x in ledger.get("trainingReuses",[]))
 write(A/"seed-ledger-before.json",ledger);ledger.setdefault("trainingReuses",[]).append(dict(firstSeed=1000000,count=98304,run=str(A.relative_to(R)),purpose="Fixed reward-only precontact arm from common parent1048609 to2097152; matched RNG19017, axes6.25-25cm25/25/50mix; no final seeds; all5 development batteries required before promotion."));ledger_path.write_text(json.dumps(ledger,indent=2))
 env=dict(os.environ);start=time.monotonic()
 with (A/"trainer-console.log").open("x",encoding="utf-8") as log:
  process=subprocess.Popen(command,cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);write(A/"process.json",dict(pid=process.pid,started=time.time(),owned=True));print(f"Precontact training trainer{process.pid}",flush=True)
  try:code=process.wait(timeout=3600)
  except subprocess.TimeoutExpired:
   subprocess.run(["taskkill","/PID",str(process.pid),"/T","/F"],capture_output=True);raise
 write(A/"process-result.json",dict(exitCode=code,wallSeconds=time.monotonic()-start));assert code==0,"Training failed; preserve logs"
 assert helper.tree_hashes(PARENT)==parent_hashes
 final=torch.load(RESULT/B/"checkpoint.pt",map_location="cpu",weights_only=False);step=helper.step_of(final);assert TARGET<=step<TARGET+8192
 enabled=0;episodes=0
 for worker in range(8):
  folder=A/f"worker-{worker:02}"
  startup=read(folder/"worker-startup.json");report=read(folder/"report.json")
  assert startup["precontactAlignmentReward"] and not startup["movementForwardProgressReward"]
  assert report["nextSeedIndex"]<12288
  for line in (folder/"episodes.jsonl").read_text().splitlines():
   row=json.loads(line);episodes+=1
   if row["precontactAlignmentRewardEnabled"]:
    enabled+=1
    assert row["precontactSettled"] and row["precontactTransitions"]==row["decisions"]
    assert abs(row["precontactDiscountedReward"]+row["precontactInitialPotential"])<1e-7
   else:assert row["precontactShapingReward"]==0 and row["precontactTransitions"]==0
 for rel,digest in source["files"].items():assert sha(R/rel)==digest
 assert not read(ledger_path)["finalSeedsConsumed"]
 assert enabled>0
 write(A/"run-complete.json",dict(step=step,episodes=episodes,shapedEpisodes=enabled,parentUnchanged=True,promotion=False,heldOutEvaluationPending=True,checkpointHash=sha(RESULT/B/"checkpoint.pt"),modelHash=sha(RESULT/f"{B}.onnx")))
 print(f"Training completed at{step}; all five development evaluations pending.")
if __name__=="__main__":main()

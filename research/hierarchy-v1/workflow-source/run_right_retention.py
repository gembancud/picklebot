"""Mixed right-return acquisition and retention from the preserved common parent; evaluation required."""
from pathlib import Path
import json,hashlib,subprocess,sys,os,time,shutil,importlib.util,socket
import yaml,torch
R=Path("F:/dev/picklebot");H=Path(__file__).resolve().parent
NAME="execution-right-retention-01";START=1048609;TARGET=2097152
BASE=R/"artifacts/hierarchy-v1/right-retention-01";A=BASE/"training";RESULT=R/"artifacts/mlagents"/NAME
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
 proof=read(BASE/"baseline-fixture/deterministic/verification.json")
 assert proof["resetContractVerified"] and proof["actorCriticNormalizationOptimizerUnchanged"] and proof["episodes"]==512
 plan=read(BASE/"plan.json");assert plan["runnerHash"]==sha(Path(__file__)) and plan["fixtureVerificationHash"]==sha(BASE/"baseline-fixture/deterministic/verification.json")
 A.mkdir();parent_hashes=helper.tree_hashes(PARENT);write(A/"parent-inputs.json",parent_hashes)
 shutil.copytree(PARENT,RESULT);assert helper.tree_hashes(RESULT)==parent_hashes;helper.remap_status(PARENT,RESULT,A)
 config=yaml.safe_load((R/"config/mlagents/execution-v1-movement-progress.yaml").read_text());behavior=config["behaviors"][B];assert behavior["reward_signals"]["extrinsic"]["gamma"]==.99
 behavior["max_steps"]=TARGET;behavior["checkpoint_interval"]=524288
 config_path=A/"config.yaml";config_path.write_text(yaml.safe_dump(config,sort_keys=False))
 manifest=read(R/"artifacts/hierarchy-v1/smooth-continued-01/training/manifest.json")
 manifest.update(evidenceRoot=str(A),sourceIdentity=source["sourceIdentity"],buildIdentity=build["buildIdentity"],basePort=5955,workerCount=8,task="movement-maintenance",movementPattern="lateral-right",movementRange=.0625,movementRecoveryMix=True,movementRehearsalRange=.1,interleavedRecovery=True,maximumReturnDifficulty=.25,movementForwardProgressReward=False,precontactAlignmentReward=False,precontactGamma=.99,optimizerDiagnostics=False)
 assert manifest["precontactGamma"]==behavior["reward_signals"]["extrinsic"]["gamma"]
 write(A/"manifest.json",manifest)
 args=[str(config_path),"--run-id",NAME,"--results-dir",str(R/"artifacts/mlagents"),"--resume","--seed","19017","--env",str(Path(build["directory"])/"Picklebot.exe"),"--num-envs","8","--base-port","5955","--no-graphics","--timeout-wait","180","--max-lifetime-restarts","0","--env-args","--picklebot-manifest",str(A/"manifest.json")]
 helper.verify_resume_loader(config_path,["mlagents-learn"]+args,RESULT,torch.load(checkpoint,map_location="cpu",weights_only=False),A)
 command=[str(Path(sys.executable).parent/"Scripts/mlagents-learn.exe")]+args
 write(A/"launch.json",dict(args=command,runnerHash=sha(Path(__file__)),configHash=sha(config_path),manifestHash=sha(A/"manifest.json"),sourceIdentity=source["sourceIdentity"],budget=TARGET-START,maximumWallSeconds=3600,promotion=False))
 ledger_path=R/"artifacts/player-v3/seed-ledger.json";ledger=read(ledger_path);assert not ledger["finalSeedsConsumed"]
 assert not any(x["run"]==str(A.relative_to(R)) for x in ledger.get("trainingReuses",[]))
 write(A/"seed-ledger-before.json",ledger);ledger.setdefault("trainingReuses",[]).append(dict(firstSeed=1000000,count=98304,run=str(A.relative_to(R)),purpose="Mixed fixed25cm right acquisition plus familiar/prior maintenance from common parent1048609 to2097152;50/25/25 episode-start allocation, unchanged rewards; acquisition and all5 retention batteries required; no final seeds."));ledger_path.write_text(json.dumps(ledger,indent=2))
 env=dict(os.environ);start=time.monotonic()
 with (A/"trainer-console.log").open("x",encoding="utf-8") as log:
  process=subprocess.Popen(command,cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);write(A/"process.json",dict(pid=process.pid,started=time.time(),owned=True));print(f"Right-return retention trainer{process.pid}",flush=True)
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
  assert not startup["precontactAlignmentReward"] and not startup["movementForwardProgressReward"]
  assert report["nextSeedIndex"]<12288
  for line in (folder/"episodes.jsonl").read_text().splitlines():
   row=json.loads(line);episodes+=1
   index=(row["seed"]-(1000000+worker*12288))%256;block=index//4
   if index>=128:
    assert row["movementPattern"]=="lateral-right" and row["movementRegion"]==5 and row["movementRange"]==.0625 and row["task"]==("rally-air-feed" if index<192 else "rally-bounce-feed")
   elif index>=64:
    assert row["movementPattern"]=="court" and abs(row["movementRange"]-.1*(1+block%4)*.25)<1e-7 and row["task"]==("rally-air-feed" if index<96 else "rally-bounce-feed")
   else:
    basic=block%8;expected="stationary-serve" if basic<2 else "receive-feed" if basic<4 else "rally-air-feed" if basic<6 else "rally-bounce-feed"
    assert row["task"]==expected and row["movementPattern"]=="court" and row["movementRange"]==(-1 if basic<4 else 0)
    if basic<2:assert row["serveFromLeft"]==(basic==1)
   assert not row["movementForwardProgressRewardEnabled"] and row["movementPositionReward"]==0
   if row["precontactAlignmentRewardEnabled"]:
    enabled+=1
    assert row["precontactSettled"] and row["precontactTransitions"]==row["decisions"]
    assert abs(row["precontactDiscountedReward"]+row["precontactInitialPotential"])<1e-7
   else:assert row["precontactShapingReward"]==0 and row["precontactTransitions"]==0
 for rel,digest in source["files"].items():assert sha(R/rel)==digest
 assert not read(ledger_path)["finalSeedsConsumed"]
 assert enabled==0
 helper.TARGET=TARGET;helper.BUFFER=8192
 verified_step,changes=helper.audit_final_states(torch.load(checkpoint,map_location="cpu",weights_only=False),final)
 workers,goals,inputs=helper.audit_workers(A,manifest,source,build)
 assert verified_step==step and len(goals)==episodes
 write(A/"extended-verification.json",dict(step=step,stateChanges=changes,workers=workers,episodes=episodes,inputHashes=inputs,parentUnchanged=True,finalSeedsConsumed=False,promoted=False))
 write(A/"run-complete.json",dict(step=step,episodes=episodes,shapedEpisodes=enabled,parentUnchanged=True,promotion=False,heldOutEvaluationPending=True,checkpointHash=sha(RESULT/B/"checkpoint.pt"),modelHash=sha(RESULT/f"{B}.onnx")))
 print(f"Training completed at{step}; all five development evaluations pending.")
if __name__=="__main__":main()

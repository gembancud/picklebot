"""Two no-update inference probes on already-used training seeds; never acceptance."""
from pathlib import Path
import json,hashlib,shutil,subprocess,sys,importlib.util,time
import torch
import prepare_movement_progress_evaluation as compare
R=Path('F:/dev/picklebot'); BASE=R/'artifacts/hierarchy-v1/precontact-frozen-training-01'
CAMPAIGN=R/'artifacts/hierarchy-v1/precontact-alignment-01'
PARENT=R/'artifacts/mlagents/execution-precontact-alignment-01';BEHAVIOR='PicklebotExecutionV1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,x):
    with p.open('x') as f:json.dump(x,f,indent=2)
def main():
    assert BASE.exists()
    src=read(CAMPAIGN/'source-records.json');build=read(CAMPAIGN/'build-verification.json')
    for rel,digest in src['files'].items():assert sha(R/rel)==digest
    for rel,digest in build['files'].items():assert sha(Path(build['directory'])/rel)==digest
    helper=R/'tools/mlagents-training/run_smooth_continuation.py'
    assert sha(helper)=='c4454b1c7e69b50386ece91167edcc5d67def34886247079cb0c25fbe633d715'
    spec=importlib.util.spec_from_file_location('helper',helper);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
    h.START=2097186
    original_hashes=h.tree_hashes(PARENT);state=torch.load(PARENT/BEHAVIOR/'checkpoint.pt',map_location='cpu',weights_only=False)
    assert sha(PARENT/BEHAVIOR/'checkpoint.pt')=='1251416299fbe20e01c4429b5290b075730bdc7b85e0cfd2a46953f715bb02f5'
    for condition in ['sampled']:
        audit=BASE/condition;audit.mkdir();name=f'execution-precontact-frozen-{condition}-01';result=R/'artifacts/mlagents'/name
        assert not result.exists();shutil.copytree(PARENT,result);h.remap_status(PARENT,result,audit)
        manifest=read(CAMPAIGN/'training/manifest.json')
        manifest.update(evidenceRoot=str(audit),basePort=6055,workerCount=1,seedsPerWorker=512,recordDecisions=True,precontactAlignmentReward=False)
        write(audit/'manifest.json',manifest)
        config=audit/'config.yaml';shutil.copyfile(CAMPAIGN/'training/config.yaml',config)
        command=[str(Path(sys.executable).parent/'Scripts/mlagents-learn.exe'),str(config),'--run-id',name,'--results-dir',str(R/'artifacts/mlagents'),'--resume','--inference','--seed','19031','--env',str(Path(build['directory'])/'Picklebot.exe'),'--num-envs','1','--base-port','6055','--no-graphics','--timeout-wait','180','--max-lifetime-restarts','0']
        if condition=='deterministic':command+=['--deterministic']
        command+=['--env-args','--picklebot-manifest',str(audit/'manifest.json')]
        write(audit/'launch.json',dict(args=command,manifestHash=sha(audit/'manifest.json'),configHash=sha(config),noUpdatesRequested=True))
        ledgerpath=R/'artifacts/player-v3/seed-ledger.json';ledger=read(ledgerpath);assert not ledger['finalSeedsConsumed']
        ledger.setdefault('trainingReuses',[]).append(dict(firstSeed=1000000,count=512,run=audit.relative_to(R).as_posix(),purpose='Frozen inference on used training seeds; no learning, no acceptance.'))
        ledgerpath.write_bytes(json.dumps(ledger,indent=2).encode())
        with (audit/'console.log').open('x') as log:
            process=subprocess.Popen(command,cwd=R,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            write(audit/'process.json',dict(pid=process.pid,started=time.time()));print(condition,process.pid,flush=True)
            try:code=process.wait(timeout=600)
            except subprocess.TimeoutExpired:
                subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True);raise
        write(audit/'exit.json',dict(code=code))
        finish=read(audit/'worker-00/worker-finish.json');report=read(audit/'worker-00/report.json')
        assert finish['status']=='seed_budget_complete' and report['completedEpisodes']==512 and not report['failure']
        assert 'Worker 0 exceeded the allowed number of restarts.' in (audit/'console.log').read_text()
        after=torch.load(result/BEHAVIOR/'checkpoint.pt',map_location='cpu',weights_only=False)
        for key in state:
            if key!='global_step':assert compare.same_state(state[key],after[key]),'Unexpected state update: '+key
        assert h.tree_hashes(PARENT)==original_hashes
        write(audit/'verification.json',dict(episodes=512,actorCriticNormalizationOptimizerUnchanged=True,parentUnchanged=True,nonzeroExitIsExpectedBoundedWorkerShutdown=True,heldOut=False,promotion=False))
        print(condition,'verified512 frozen episodes',flush=True)
if __name__=='__main__':main()

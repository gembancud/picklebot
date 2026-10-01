"""Run one bounded, audited execution-goal integration experiment."""
from pathlib import Path
import hashlib, json, os, subprocess, sys, time
import torch

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'artifacts/hierarchy-v1'
NAME='execution-placement-01'
AUDIT=BASE/NAME
RESULT=ROOT/'artifacts/mlagents'/NAME
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,obj):
    with p.open('x',encoding='utf-8') as f:json.dump(obj,f,indent=2)
def rows(p):return [json.loads(s) for s in p.read_text().splitlines() if s.strip()]

def main():
    assert not AUDIT.exists() and not RESULT.exists(),'Use a new experiment, never overwrite one'
    source=read(BASE/'source-records.json');build=read(BASE/'build-verification.json')
    assert source['sourceIdentity']==build['sourceIdentity']
    assert all(sha(ROOT/n)==h for n,h in source['files'].items()),'Source changed since build'
    binary=Path(build['directory'])
    assert all(sha(binary/n)==h for n,h in build['files'].items()),'Build changed'
    init=BASE/'execution-init-01';provenance=read(init/'initialization.json')
    assert sha(init/'checkpoint.pt')==provenance['files']['checkpoint.pt']
    AUDIT.mkdir()
    manifest=read(ROOT/'config/mlagents/execution-v1-workers.json')
    manifest.update(sourceIdentity=source['sourceIdentity'],buildIdentity=build['buildIdentity'],
        modelHash=provenance['files']['PicklebotExecutionV1-0.onnx'],evidenceRoot=str(AUDIT),basePort=5415,
        executionContract=source['contract'],sampleShotTargets=True,targetRadius=1.5,legalTargetReward=.25,
        optimizerDiagnostics=False)
    write(AUDIT/'manifest.json',manifest)
    config=ROOT/'config/mlagents/execution-v1-placement.yaml'
    args=[str(Path(sys.executable).parent/'Scripts/mlagents-learn.exe'),str(config),
        '--run-id',NAME,'--results-dir',str(ROOT/'artifacts/mlagents'),'--seed','19013',
        '--env',str(binary/'Picklebot.exe'),'--num-envs','8','--base-port','5415',
        '--no-graphics','--timeout-wait','180','--max-lifetime-restarts','0',
        '--env-args','--picklebot-manifest',str(AUDIT/'manifest.json')]
    write(AUDIT/'launch.json',dict(args=args,configHash=sha(config),manifestHash=sha(AUDIT/'manifest.json'),
        sourceIdentity=source['sourceIdentity'],initialization=provenance,
        budget=262144,purpose='Longer placement learning with fixed development retention and target-response evaluation; no automatic promotion'))
    ledgerpath=ROOT/'artifacts/player-v3/seed-ledger.json';ledger=read(ledgerpath)
    assert not ledger['finalSeedsConsumed']
    ledger['trainingReuses'].append(dict(firstSeed=1000000,count=98304,run=str(AUDIT.relative_to(ROOT)),purpose='Goal-conditioned execution warm start, 262144 experiences; same physical curriculum, independently sampled targets.'))
    ledgerpath.write_text(json.dumps(ledger,indent=2),encoding='utf-8')
    start=time.monotonic()
    with (AUDIT/'trainer-console.log').open('x',encoding='utf-8') as log:
        process=subprocess.Popen(args,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        write(AUDIT/'process.json',dict(pid=process.pid,started=time.time()))
        print(f'{NAME}: trainer {process.pid}, 8 workers x 16 courts, 262144 experiences',flush=True)
        try:code=process.wait(timeout=900)
        except subprocess.TimeoutExpired:
            subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],check=False,capture_output=True)
            write(AUDIT/'process-result.json',dict(exitCode=124,timeout=True,wallSeconds=time.monotonic()-start))
            raise
    write(AUDIT/'process-result.json',dict(exitCode=code,wallSeconds=time.monotonic()-start))
    assert code==0,'Trainer failed: see trainer-console.log'
    text=(AUDIT/'trainer-console.log').read_text()
    assert not any(s in text for s in ['Traceback (most recent call last)','[ERROR]','Failed to load for module'])
    state=torch.load(RESULT/'PicklebotExecutionV1/checkpoint.pt',map_location='cpu',weights_only=False)
    first='network_body._body_endoder.seq_layers.0.weight'
    step=int(next(iter(state['global_step'].values())).item())
    assert 262144<=step<270336
    assert state['Policy'][first].shape==(128,136)
    assert state['Policy'][first][:,133:135].abs().sum()>0,'Shot target coordinates did not learn'
    assert all(torch.isfinite(v).all() for v in state['Policy'].values() if isinstance(v,torch.Tensor))
    assert min(float(s['step']) for s in state['Optimizer:value_optimizer']['state'].values())>0
    workers=[];goals=[]
    for i in range(8):
        w=AUDIT/f'worker-{i:02}';startup=read(w/'worker-startup.json');report=read(w/'report.json')
        assert startup['sourceIdentity']==source['sourceIdentity'] and startup['manifestHash']==sha(AUDIT/'manifest.json')
        assert report['trainerConnected'] and report['contract']==source['contract'] and not report['failure']
        episodes=rows(w/'episodes.jsonl');g=rows(w/'execution-goals.jsonl')
        assert len(g)==len(episodes)>0
        assert all(e['decisions']==sum(e['decisionsByPlayer']) and all((n>0)==(j==e['player']) for j,n in enumerate(e['decisionsByPlayer'])) for e in episodes)
        assert all(x['assigned'] and 0<=x['bonus']<=.25 and (x['legalLanding'] or x['bonus']==0) for x in g)
        goals.extend(g);workers.append(dict(worker=i,episodes=len(episodes),contract=report['contract']))
    summary=dict(status='completed_learning_check',experiences=step,workers=workers,
        goalCoordinateWeightsChanged=True,episodes=len(goals),legalLandings=sum(x['legalLanding'] for x in goals),
        targetsHit=sum(x['targetHit'] for x in goals),
        model=str((RESULT/'PicklebotExecutionV1.onnx').relative_to(ROOT)),modelHash=sha(RESULT/'PicklebotExecutionV1.onnx'),
        checkpointHash=sha(RESULT/'PicklebotExecutionV1/checkpoint.pt'),
        heldOutPerformanceEvaluated=False,promoted=False)
    write(AUDIT/'verification.json',summary);print(json.dumps(summary),flush=True)

if __name__=='__main__':main()


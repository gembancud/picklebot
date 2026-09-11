from pathlib import Path
import argparse, collections, copy, hashlib, json, shutil, sys

ROOT=Path('F:/dev/picklebot'); BASE=ROOT/'artifacts/player-v3'; WORK=Path(__file__).resolve().parent
def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,obj):
    with Path(p).open('x',encoding='utf-8') as f: json.dump(obj,f,indent=2)
def rows(p): return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
def source_check():
    s=read(BASE/'stability-source-01/source-records.json')
    assert all(sha(ROOT/n)==h for n,h in s['files'].items())
    assert not read(BASE/'seed-ledger.json')['finalSeedsConsumed']
    return s
def equal(a,b):
    import torch
    if isinstance(a,torch.Tensor): assert isinstance(b,torch.Tensor) and a.dtype==b.dtype and torch.equal(a,b)
    elif isinstance(a,dict):
        assert a.keys()==b.keys()
        for k in a: equal(a[k],b[k])
    elif isinstance(a,(list,tuple)):
        assert type(a)==type(b) and len(a)==len(b)
        for x,y in zip(a,b): equal(x,y)
    else: assert a==b
def finalize(name):
    import torch
    a=BASE/name; l=read(a/'launch.json'); run=ROOT/'artifacts/mlagents'/l['trainerRunId']; s=source_check()
    assert read(a/'trainer-process-result.json')['exitCode']==0
    assert sha(ROOT/l['config'])==l['configHash'] and sha(a/'manifest.json')==l['manifestHash']
    assert all(sha(ROOT/l['parentTrainer']/n)==h for n,h in l['sourceFiles'].items())
    cp=run/'PicklebotArticulated/checkpoint.pt'; state=torch.load(cp,map_location='cpu',weights_only=False)
    step=int(next(iter(state['global_step'].values())).item()); assert l['targetDecisionSteps']<=step<l['targetDecisionSteps']+16384
    pt=run/f'PicklebotArticulated/PicklebotArticulated-{step}.pt'; model=pt.with_suffix('.onnx')
    equal(state,torch.load(pt,map_location='cpu',weights_only=False)); assert sha(model)==sha(run/'PicklebotArticulated.onnx')
    old=torch.load(a/'input-checkpoint.pt',map_location='cpu',weights_only=False)
    adam=sorted({float(x['step']) for x in state['Optimizer:value_optimizer']['state'].values()})
    assert min(adam)>l['initialAdamStep']
    changed=[k for k,v in state['Policy'].items() if k.endswith('.weight') and not torch.equal(v,old['Policy'][k])]; assert changed
    assert all(torch.isfinite(v).all() for v in state['Policy'].values() if isinstance(v,torch.Tensor) and v.is_floating_point())
    episodes=[]; worker_states=[]
    for i in range(l['workers']):
        w=a/f'worker-{i:02}'; start=read(w/'worker-startup.json'); rep=read(w/'report.json')
        assert start['sourceIdentity']==s['sourceIdentity'] and start['manifestHash']==l['manifestHash']
        assert rep['trainerConnected'] and not rep['failure'] and not rep['cooperativePairs'] and not list(w.glob('*failure.json'))
        rr=rows(w/'episodes.jsonl')
        assert all(e['backgroundDecisions']==0 and e['decisions']==sum(e['decisionsByPlayer']) and all((n>0)==(j==e['player']) for j,n in enumerate(e['decisionsByPlayer'])) for e in rr)
        episodes.extend(rr); worker_states.append(dict(worker=i,status=rep['status'],completed=len(rr),episodesHash=sha(w/'episodes.jsonl')))
    log=(a/'trainer-console.log').read_text(encoding='utf-8-sig')
    assert not any(x in log for x in ['Traceback (most recent call last)','[ERROR]','Failed to load for module'])
    asset=f"Assets/Picklebot/PlayerLearning/Models/LocalMovement_{l['trainerRunId']}_{step}.onnx"
    out=dict(status='completed_training_verified',run=l['trainerRunId'],step=step,additionalExperiences=step-l['initialGlobalStep'],checkpoint=pt.relative_to(ROOT).as_posix(),checkpointHash=sha(pt),mutableHash=sha(cp),modelFile=model.relative_to(ROOT).as_posix(),model=asset,modelHash=sha(model),sourceIdentity=s['sourceIdentity'],adamSteps=adam,changedWeightTensors=changed,workers=worker_states,episodes=len(episodes),finalSeedsConsumed=False,performanceEvaluated=False)
    if (a/'completion-verification.json').exists(): assert read(a/'completion-verification.json')==out
    else: write(a/'completion-verification.json',out)
    print(json.dumps({k:v for k,v in out.items() if k!='workers'}))
def prepare_eval(planpath):
    p=read(planpath); a=BASE/p['name']; s=source_check(); a.mkdir()
    lp=BASE/'seed-ledger.json'; ledger=read(lp); shutil.copyfile(lp,a/'seed-ledger-before.json')
    first=p.get('firstSeed',max(x['firstSeed']+x['count'] for key in ['developmentBlocks','developmentReuses'] for x in ledger[key])); count=p.get('seedCount',256)
    assert 1100000<=first and first+count<=1200000
    cases=[]
    for case in p['cases']:
        c=dict(case)
        if 'checkpointRecord' in c:
            record=Path(c.pop('checkpointRecord'))
            assert record.is_absolute() and record.is_file(), 'Explicit immutable checkpoint record required'
            model=read(record)
            assert sha(ROOT/model['checkpoint'])==model['checkpointHash']
            c.update(checkpointRecord=str(record),checkpointRecordHash=sha(record))
        elif 'audit' in c:
            model=read(BASE/c.pop('audit')/'completion-verification.json')
        else: model=read(BASE/'selected-paired-parent-01.json')
        c.update(model=model['model'],modelHash=model['modelHash'],checkpoint=model['step'])
        c.setdefault('recoveryMix',False);c.setdefault('rehearsalRange',0);c.setdefault('timing',0);c.setdefault('starts',0);c.setdefault('bonus',0);c.setdefault('pattern','court');c.setdefault('interleaved',False);c.setdefault('worker',0)
        cases.append(c)
    launch=dict(sourceIdentity=s['sourceIdentity'],firstSeed=first,seedCount=count,cases=cases,purpose=p['purpose'],inference='Unity InferenceEngine deterministic; no optimizer updates',finalSeedsConsumed=False)
    write(a/'launch.json',launch); shutil.copyfile(BASE/'stability-source-01/source-records.json',a/'source-records.json')
    code=(WORK/'movement_baseline01.cs.txt').read_text()
    code=code.replace('movement-parent-dev-01',p['name'])
    code=code.replace('var model=UnityEditor.AssetDatabase.LoadAssetAtPath<Unity.InferenceEngine.ModelAsset>((string)launch["model"]);if(model==null)throw new System.Exception("Missing model");','')
    code=code.replace('if(run==null){','''if(run==null){
  var path=(string)c["model"];var bytes=System.IO.File.ReadAllBytes(path);using(var hash=System.Security.Cryptography.SHA256.Create()){var actual=System.BitConverter.ToString(hash.ComputeHash(bytes)).Replace("-","").ToLowerInvariant();if(actual!=(string)c["modelHash"])throw new System.Exception("Model hash mismatch");}
  var model=UnityEditor.AssetDatabase.LoadAssetAtPath<Unity.InferenceEngine.ModelAsset>(path);if(model==null)throw new System.Exception("Missing model");''')
    code=code.replace('run.MovementRange=(float)c["range"];','run.MovementRecoveryMix=(bool)c["recoveryMix"];run.InterleavedRecovery=(bool)c["interleaved"];run.SchedulerWorkerId=(int)c["worker"];run.MovementRehearsalRange=(float)c["rehearsalRange"];run.MovementPattern=(string)c["pattern"];run.RecordDecisions=true;run.MovementPositionReward=(float)c["bonus"];run.MovementRange=(float)c["range"];')
    (a/'harness.cs.txt').write_text(code,encoding='utf-8')
    entry=dict(firstSeed=first,count=count,run=a.relative_to(ROOT).as_posix(),purpose=p['purpose'])
    ledger['developmentReuses' if 'firstSeed' in p else 'developmentBlocks'].append(entry)
    lp.write_text(json.dumps(ledger,indent=2),encoding='utf-8')
    print(json.dumps(launch))
def describe(rr):
    return dict(attempts=len(rr),contacts=sum(e['faceContact'] for e in rr),crossed=sum(e['netCrossed'] for e in rr),legal=sum(e['outcome'] in ['legal_return','legal_serve'] for e in rr),movingReturns=sum(e['outcome']=='legal_return' and e['contactDisplacement']>=.5 for e in rr),faults=dict(collections.Counter(e['terminalFault'] for e in rr)))
def verify_eval(name):
    a=BASE/name; l=read(a/'launch.json'); source_check(); assert not (a/'error.txt').exists()
    assert len(read(a/'complete.json'))==len(l['cases']); results={}
    for c in l['cases']:
        d=a/c['label']; rep=read(d/'report.json'); rr=rows(d/'episodes.jsonl')
        assert rep['status']=='seed_budget_complete' and not rep['failure'] and not rep['trainerConnected'] and rep['sourceIdentity']==l['sourceIdentity']
        assert len(rr)==l['seedCount'] and sorted(e['seed'] for e in rr)==list(range(l['firstSeed'],l['firstSeed']+l['seedCount']))
        assert sha(ROOT/c['model'])==c['modelHash']
        if 'checkpointRecord' in c:
            assert sha(c['checkpointRecord'])==c['checkpointRecordHash']
            record=read(c['checkpointRecord']);assert sha(ROOT/record['checkpoint'])==record['checkpointHash']
        assert all(e['backgroundDecisions']==0 and all((n>0)==(j==e['player']) for j,n in enumerate(e['decisionsByPlayer'])) for e in rr)
        challenge=[e for e in rr if e['movementRange']>0]
        retained=[e for e in rr if e['movementRange']<=0]
        results[c['label']]=dict(modelHash=c['modelHash'],checkpoint=c['checkpoint'],episodesHash=sha(d/'episodes.jsonl'),challenge=describe(challenge),air=describe([e for e in challenge if e['task']=='rally-air-feed']),bounce=describe([e for e in challenge if e['task']=='rally-bounce-feed']),retained={t:describe([e for e in retained if e['task']==t]) for t in sorted({e['task'] for e in retained})},byRange={str(v):describe([e for e in challenge if e['movementRange']==v]) for v in sorted({e['movementRange'] for e in challenge})},byRegion={str(v):describe([e for e in challenge if e['movementRegion']==v]) for v in sorted({e['movementRegion'] for e in challenge})})
    out=dict(status='verified_frozen_development_evaluation',sourceIdentity=l['sourceIdentity'],firstSeed=l['firstSeed'],seedCount=l['seedCount'],cases=results,finalSeedsConsumed=False)
    if (a/'verification.json').exists():assert read(a/'verification.json')==out
    else: write(a/'verification.json',out)
    print(json.dumps({k:dict(air=v['air'],bounce=v['bounce'],retained={t:x['legal'] for t,x in v['retained'].items()}) for k,v in results.items()}))

def training_config(parent_config, plan, parent_step):
    """Only budget/retention and the declared constant learning rate may differ."""
    import attr
    from mlagents.plugins.trainer_type import register_trainer_plugins
    from mlagents.trainers.settings import RunOptions, ScheduleType
    register_trainer_plugins()
    original=RunOptions.from_dict(copy.deepcopy(parent_config))
    behavior=original.behaviors['PicklebotArticulated']
    assert behavior.trainer_type=='ppo'
    assert all(getattr(behavior.hyperparameters,k)==ScheduleType.CONSTANT for k in ['learning_rate_schedule','beta_schedule','epsilon_schedule']), 'Parent effective schedules must all be constant'
    rate=plan['learningRate'];assert rate in (1e-4,3e-5), 'Unplanned learning rate'
    config=copy.deepcopy(parent_config)
    proposed=config['behaviors']['PicklebotArticulated']
    proposed.update(max_steps=parent_step+plan['budget'],keep_checkpoints=512)
    proposed['hyperparameters'].update(learning_rate=rate,learning_rate_schedule='constant',beta_schedule='constant',epsilon_schedule='constant')
    effective=RunOptions.from_dict(copy.deepcopy(config))
    before=attr.asdict(original);after=attr.asdict(effective)
    for value in [before,after]:
        b=value['behaviors']['PicklebotArticulated'];b.pop('max_steps');b.pop('keep_checkpoints');b['hyperparameters'].pop('learning_rate')
    assert before==after, 'Unexpected effective configuration change'
    assert effective.behaviors['PicklebotArticulated'].hyperparameters.learning_rate==rate
    return config,dict(parentLearningRate=behavior.hyperparameters.learning_rate,learningRate=rate,learningRateSchedule='constant',betaSchedule='constant',epsilonSchedule='constant',effectiveSettingsEqualExcept=['max_steps','keep_checkpoints','hyperparameters.learning_rate'])

def prepare_train(planpath):
    import yaml
    p=read(planpath); s=source_check(); parent=read(BASE/p['parentAudit']/'completion-verification.json')
    build=read(BASE/'stability-source-01/build-verification.json'); assert all(sha(BASE/'headless-build-53'/n)==h for n,h in build['files'].items())
    assert sha(ROOT/parent['checkpoint'])==parent['checkpointHash']
    parentRun=ROOT/'artifacts/mlagents'/parent['run']; cp=parentRun/'PicklebotArticulated/checkpoint.pt'; assert sha(cp)==parent['mutableHash']
    ev=BASE/p['evaluation']; assert read(ev/'verification.json')['status']=='verified_frozen_development_evaluation'
    name=p['run']; a=BASE/p['audit']; trainer=ROOT/'artifacts/mlagents'/name; config=ROOT/f'config/mlagents/{name}.yaml'
    assert not a.exists() and not trainer.exists() and not config.exists(); a.mkdir()
    lp=BASE/'seed-ledger.json'; ledger=read(lp); shutil.copyfile(lp,a/'seed-ledger-before.json')
    for n in ['source-records.json','source.zip']: shutil.copyfile(BASE/'stability-source-01'/n,a/n)
    shutil.copyfile(cp,a/'input-checkpoint.pt'); shutil.copyfile(ev/'verification.json',a/'baseline.json'); shutil.copyfile(BASE/p['parentAudit']/'completion-verification.json',a/'parent-state-verification.json')
    sys.path.insert(0,str(ROOT/'scripts')); from mlagents_clone_run import clone_run
    clone=clone_run(parentRun,trainer,ROOT/'artifacts/mlagents')
    target=parent['step']+p['budget']
    old_config=yaml.safe_load((ROOT/read(BASE/p['parentAudit']/'launch.json')['config']).read_text())
    c,effective_config=training_config(old_config,p,parent['step'])
    write(a/'effective-configuration-check.json',effective_config)
    with config.open('x',encoding='utf-8') as f: yaml.safe_dump(c,f,sort_keys=False)
    m=read(BASE/'movement-receive-train-01/manifest.json'); m.update(evidenceRoot=str(a),sourceIdentity=s['sourceIdentity'],buildIdentity=build['buildIdentity'],modelHash=parent['modelHash'],basePort=p['port'],workerCount=8,movementRange=p['range'],movementTiming=p.get('timing',0),movementStartVariation=p.get('starts',0),movementPositionReward=0,movementPattern=p['pattern'],movementRehearsalRange=p.get('rehearsalRange',0),movementRecoveryMix=p.get('recoveryMix',False),interleavedRecovery=p.get('interleaved',False),optimizerDiagnostics=True)
    write(a/'manifest.json',m)
    l=dict(trainerRunId=name,sourceIdentity=s['sourceIdentity'],buildIdentity=build['buildIdentity'],initialGlobalStep=parent['step'],additionalExperiences=p['budget'],targetDecisionSteps=target,initialAdamStep=min(parent['adamSteps']),trainingRngSeed=p['rng'],config=config.relative_to(ROOT).as_posix(),configHash=sha(config),manifestHash=sha(a/'manifest.json'),inputCheckpointHash=sha(cp),parentCheckpoint=cp.relative_to(ROOT).as_posix(),parentCheckpointHash=sha(cp),selectedNumberedCheckpoint=parent['checkpoint'],selectedNumberedHash=parent['checkpointHash'],parentTrainer=parentRun.relative_to(ROOT).as_posix(),workers=8,arenasPerWorker=16,activeLearners=128,firstSeed=m['firstSeed'],seedCount=m['seedsPerWorker']*8,sourceFiles=clone['sourceFiles'],cloneFiles=clone['cloneFiles'],cloneProvenanceHash=sha(trainer/'clone-provenance.json'),baselineHash=sha(a/'baseline.json'))
    write(a/'launch.json',l);write(a/'design.json',p)
    runner=(WORK/'run_local_movement_template.py').read_text().replace("name='movement-receive-01'",f"name='{name}'").replace("base/'movement-receive-train-01'",f"base/'{p['audit']}'").replace('__PICKLEBOT_DIAGNOSTICS_WRAPPER__',(WORK/'stability_diagnostics.py').as_posix())
    (a/'runner.py').write_text(runner,encoding='utf-8')
    ledger['trainingReuses'].append(dict(firstSeed=m['firstSeed'],count=l['seedCount'],run=a.relative_to(ROOT).as_posix(),task=m['task'],purpose=p['purpose'],allocationStatus=f"Reserved {p['budget']} additional experiences"))
    lp.write_text(json.dumps(ledger,indent=2),encoding='utf-8')
    print(json.dumps(dict(run=name,initialStep=parent['step'],targetStep=target,range=m['movementRange'],timing=m['movementTiming'],starts=m['movementStartVariation'])))

def link_tensorboard(name):
    run=ROOT/'artifacts/mlagents'/name; provenance=read(run/'clone-provenance.json'); inherited=set(provenance['cloneFiles'])
    import os
    new=[p for p in (run/'PicklebotArticulated').glob('events.out.tfevents.*') if p.relative_to(run).as_posix() not in inherited]
    assert new
    dst=ROOT/'artifacts/tensorboard-recent-distance-01'/name/'PicklebotArticulated';dst.mkdir(parents=True,exist_ok=True)
    for p in new:
        q=dst/p.name
        if not q.exists():os.link(p,q)
    print(json.dumps(dict(run=name,linked=[p.name for p in new])))

if __name__=='__main__':
    command,arg=sys.argv[1:]
    {'finalize':finalize,'prepare-eval':prepare_eval,'verify-eval':verify_eval,'prepare-train':prepare_train,'link-tensorboard':link_tensorboard}[command](arg)

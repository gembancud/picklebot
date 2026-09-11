"""Immutable four-run current-vs-corrected critic-key comparison and evaluation."""
from local_movement_sequence import *
from stability_review import cells, judge
from stability_mixture import verify_mixture
from worker_coverage import verify_worker_coverage
import datetime
import os
import socket
import subprocess
import time
import traceback

ORIGINAL=BASE/'critic-key-comparison-01'
CAMP=ORIGINAL/'recovery-01'
PACK=BASE/'critic-key-packages-01'
PY=ROOT/'tools/mlagents-training/.pixi/envs/default/python.exe'
CLI=Path(os.environ['LOCALAPPDATA'])/'Unity/bin/unity.exe'
PARENT='swing-recovery-parent-01'
PREFLIGHT='critic-key-preflight-01'
EVALUATION='critic-key-dev-01'
OUTPUT=Path('C:/Users/Admin/Documents/Codex/2026-09-07/https-unity-com-blog-meet-the-7/outputs/critic-key-comparison-results.md')
ARMS=[dict(label='control-s1',package='control',rng=15331),dict(label='fixed-s1',package='fixed',rng=15331),
      dict(label='fixed-s2',package='fixed',rng=15339),dict(label='control-s2',package='control',rng=15339)]
DISTS=[('legacy','court',.1),('focus','lateral',.025),('bridge','lateral',.05),('lateral','lateral',.1)]
GUARD='if(!UnityEditor.EditorApplication.isPlaying||UnityEngine.SceneManagement.SceneManager.GetActiveScene().path!=""||UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects().Length!=0)throw new System.Exception("Reserved empty evaluation scene required");'

def state(phase,**kw):
    data=dict(phase=phase,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),controllerPid=os.getpid(),**kw)
    p=CAMP/'status.next.json';p.write_text(json.dumps(data,indent=2),encoding='utf-8');p.replace(CAMP/'status.json')
    print(json.dumps(data),flush=True)

def check():
    source_check()
    assert all(sha(WORK/n)==h for n,h in read(WORK/'script-hashes.json').items()),'Frozen workflow changed'
    record=read(PACK/'verification.json')
    for p in record['packages'].values():
        target=Path(p['target'])/'mlagents'
        assert all(sha(target/n)==h for n,h in p['installedFiles'].items()),'Package changed'

def next_operation():
    check()
    assert not (CAMP/'STOP').exists(),'STOP requested; no next operation launched'
    assert not (ORIGINAL/'STOP').exists(),'Original campaign STOP requested'

def cli(code):
    p=subprocess.run([str(CLI),'command','eval',code,'--project-path',str(ROOT),'--format','json'],capture_output=True,text=True,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
    j=json.loads(p.stdout);inner=j.get('data',{}).get('result',{})
    if p.returncode or not j.get('success') or not inner.get('success'):raise RuntimeError(json.dumps(j)[-2400:])
    return inner.get('result')

def wait_file(path,timeout,errors=()):
    end=time.monotonic()+timeout
    while not path.exists():
        for error in errors:
            if error.exists():raise RuntimeError(error.read_text(encoding='utf-8')[-2500:])
        if time.monotonic()>end:raise TimeoutError(str(path))
        time.sleep(15)

def prepare():
    check()
    parent=read(BASE/PARENT/'completion-verification.json');assert parent['step']==8415374
    ledger=read(BASE/'seed-ledger.json')
    first=max(x['firstSeed']+x['count'] for key in ['developmentBlocks','developmentReuses'] for x in ledger[key])
    assert 1100000<=first and first+512<=1200000
    shutil.copyfile(BASE/'seed-ledger.json',CAMP/'seed-ledger-before-reservation.json')
    ledger['developmentBlocks'].append(dict(firstSeed=first,count=512,run=str(CAMP),purpose='Predeclared critic-key comparison:21 matched development conditions.'))
    (BASE/'seed-ledger.json').write_text(json.dumps(ledger,indent=2),encoding='utf-8')
    write(CAMP/'plan.json',dict(parent=PARENT,parentStep=parent['step'],parentCheckpointHash=parent['checkpointHash'],arms=ARMS,
        budgetEach=500000,totalBudget=2000000,firstEvaluationSeed=first,seedCount=512,evaluationConditions=21,
        workers=8,courtsPerWorker=16,finalSeedsConsumed=False,packageAuditHash=sha(PACK/'verification.json'),
        unchanged='Game source/build/body/rewards/observations/actions/interleaved mix/network/PPO settings. Only the installed trainer value-estimates key differs.',
        selection='Final checkpoint at fixed budget only; no selection by development outcome.',
        promising='Both corrected seeds pass historical retention plus focused air/bounce within6.25pp of parent; primary prior-air gain over paired control positive in both seeds and mean>=5pp. No automatic promotion.'))
    p=CAMP/'preflight-plan.json'
    write(p,dict(name=PREFLIGHT,firstSeed=1108473,seedCount=512,purpose='Verify background Editor matches historical parent legacy outcomes before the comparison.',cases=[dict(label='parent-legacy',audit=PARENT,pattern='court',range=.1)]))
    prepare_eval(p)

def preflight():
    next_operation();state('preflight')
    cli(GUARD+(BASE/PREFLIGHT/'harness.cs.txt').read_text(encoding='utf-8'))
    wait_file(BASE/PREFLIGHT/'complete.json',1800,[BASE/PREFLIGHT/'error.txt']);verify_eval(PREFLIGHT)
    old=rows(BASE/'stability-dev-01/parent-legacy/episodes.jsonl')
    new=rows(BASE/PREFLIGHT/'parent-legacy/episodes.jsonl')
    assert {x['seed']:x for x in old}=={x['seed']:x for x in new},'Background Editor outcomes changed'
    write(BASE/PREFLIGHT/'preflight-verification.json',dict(status='passed',historicalEpisodesExact=512))

def startup(a):
    import torch
    l=read(a/'launch.json');runtime=read(a/'trainer-runtime-verification.json')
    assert runtime['label']==read(a/'trainer-package.json')['label']
    mix=verify_mixture(a)
    updates=[x for x in rows(a/'learning-updates.jsonl') if x['event']=='learning_update']
    assert len(updates)>=2 and all(len(x['groups'])==10 for x in updates)
    run=ROOT/'artifacts/mlagents'/l['trainerRunId']
    pts=sorted((p for p in (run/'PicklebotArticulated').glob('PicklebotArticulated-*.pt') if p.with_suffix('.onnx').exists()),key=lambda p:int(p.stem.rsplit('-',1)[1]))
    pt=pts[-1];h=sha(pt);new=torch.load(pt,map_location='cpu',weights_only=False);assert sha(pt)==h
    old=torch.load(a/'input-checkpoint.pt',map_location='cpu',weights_only=False)
    step=int(next(iter(new['global_step'].values())).item());assert step>l['initialGlobalStep']
    adam=min(float(v['step']) for v in new['Optimizer:value_optimizer']['state'].values());assert adam>l['initialAdamStep']
    changed=[k for k,v in new['Policy'].items() if k.endswith('.weight') and not torch.equal(v,old['Policy'][k])];assert changed
    assert all(torch.isfinite(v).all() for v in new['Policy'].values() if isinstance(v,torch.Tensor) and v.is_floating_point())
    mb=[m for u in updates for m in u['minibatches']]
    if runtime['label']=='control':assert all(m['storedValueTargetMeanGap']==0 and m['valueClipDominatesFraction']==0 for m in mb)
    else:assert all(m['storedValueTargetMeanGap']>0 for m in mb)
    result=dict(status='actual_learning_and_assigned_trainer_verified',step=step,adamStep=adam,checkpointHash=h,
        changedWeightTensors=changed,measuredUpdates=len(updates),runtime=runtime,mixture=mix,
        maxValueClipDominatesFraction=max(m['valueClipDominatesFraction'] for m in mb))
    write(a/'startup-verification.json',result)
    return result

def train(arm):
    next_operation()
    for port in range(5005,5013):
        with socket.socket() as probe:
            probe.settimeout(.2);assert probe.connect_ex(('127.0.0.1',port))!=0,f'Port {port} occupied'
    name='critic-key-'+arm['label']+'-01';audit=name+'-train';p=CAMP/(arm['label']+'-plan.json')
    write(p,dict(run=name,audit=audit,parentAudit=PARENT,evaluation=PREFLIGHT,budget=500000,rng=arm['rng'],
        range=.025,pattern='lateral',rehearsalRange=.1,recoveryMix=True,interleaved=True,learningRate=1e-4,
        timing=0,starts=0,port=5005,purpose='Authorized controlled critic-key comparison; same full parent and interleaved practice.',package=arm['package']))
    prepare_train(p);a=BASE/audit
    record=read(PACK/'verification.json')['packages'][arm['package']]
    write(a/'trainer-package.json',dict(label=arm['package'],**record))
    with (a/'supervisor.log').open('x',encoding='utf-8') as out,(a/'supervisor-error.log').open('x',encoding='utf-8') as err:
        child=subprocess.Popen([str(PY),str(a/'runner.py')],cwd=ROOT,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
    write(a/'supervisor.json',dict(pid=child.pid,campaign=str(CAMP)))
    state('training',run=name,arm=arm['label'],supervisorPid=child.pid)
    deadline=time.monotonic()+2400;startup_deadline=time.monotonic()+600;linked=False;started=False;last=''
    while child.poll() is None:
        if not linked:
            try:link_tensorboard(name);linked=True
            except (AssertionError,FileNotFoundError):pass
        if not started:
            try:
                verified=startup(a);started=True
                state('training_verified',run=name,arm=arm['label'],step=verified['step'],runtime=arm['package'])
            except (AssertionError,FileNotFoundError,json.JSONDecodeError,EOFError,IndexError) as exc:
                last=str(exc)
                if time.monotonic()>startup_deadline:raise RuntimeError('Startup verification deadline: '+last)
        if time.monotonic()>deadline:raise TimeoutError('Identified trainer exceeded40min; no next run launched')
        time.sleep(15)
    assert child.returncode==0,(a/'trainer-console.log').read_text(encoding='utf-8')[-3000:]
    if not started:startup(a)
    if not linked:link_tensorboard(name)
    finish_training(arm)

def finish_training(arm):
    name='critic-key-'+arm['label']+'-01';audit=name+'-train';a=BASE/audit
    check();finalize(audit)
    update_rows=rows(a/'learning-updates.jsonl');updates=[x for x in update_rows if x['event']=='learning_update']
    base=rows(a/'optimizer-buffers.jsonl')
    prepared=[x for x in base if x['event']=='update_prepared'];completed=[x for x in base if x['event']=='update_completed']
    assert len(updates)==len(prepared)==len(completed) and len(updates)>=55
    assert all(len(x['groups'])==10 and x['gradientReconstructionRelativeError']<2e-4 for x in updates)
    coverage=verify_worker_coverage(prepared,read(a/'launch.json')['workers'])
    assert all(len(x['minibatches'])==3*y['optimizerMinibatchesPerEpoch'] for x,y in zip(updates,prepared))
    mb=[m for x in updates for m in x['minibatches']]
    write(a/'diagnostic-verification.json',dict(status='complete',updates=len(updates),
        maxValueClipDominatesFraction=max(m['valueClipDominatesFraction'] for m in mb),
        meanValueClipDominatesFraction=sum(m['valueClipDominatesFraction'] for m in mb)/len(mb),
        validCapturedCriticEpisodes=len(rows(a/'critic-episodes.jsonl')),mixture=verify_mixture(a),workerCoverage=coverage))
    model=read(a/'completion-verification.json')
    cli(GUARD+'var p="'+model['model']+'";if(!System.IO.File.Exists(p))System.IO.File.Copy("'+model['modelFile']+'",p);UnityEditor.AssetDatabase.ImportAsset(p,UnityEditor.ImportAssetOptions.ForceSynchronousImport);return true;')
    assert sha(ROOT/model['model'])==model['modelHash']
    state('trained',arm=arm['label'],run=name,step=model['step'])

def evaluation():
    next_operation();cases=[dict(label='anchor-legacy',audit='movement-position-control-train-01',pattern='court',range=.1)]
    cases += [dict(label='parent-'+d,audit=PARENT,pattern=p,range=r) for d,p,r in DISTS]
    for arm in ARMS:
        cases += [dict(label=arm['label']+'-'+d,audit='critic-key-'+arm['label']+'-01-train',pattern=p,range=r) for d,p,r in DISTS]
    assert len(cases)==21
    p=CAMP/'evaluation-plan.json'
    write(p,dict(name=EVALUATION,firstSeed=read(CAMP/'plan.json')['firstEvaluationSeed'],seedCount=512,
        purpose='Matched current-vs-corrected critic-key development evaluation; final checkpoints only; final seeds unused.',cases=cases))
    prepare_eval(p);state('evaluating',conditions=21,evaluation=EVALUATION)
    cli(GUARD+(BASE/EVALUATION/'harness.cs.txt').read_text(encoding='utf-8'))
    wait_file(BASE/EVALUATION/'complete.json',7200,[BASE/EVALUATION/'error.txt']);check();verify_eval(EVALUATION)

def review():
    a=BASE/EVALUATION;v=read(a/'verification.json');c=v['cases'];breakdown={}
    for case in read(a/'launch.json')['cases']:
        if case['pattern']=='lateral':breakdown[case['label']]=cells(rows(a/case['label']/'episodes.jsonl'),v['firstSeed'])
    write(a/'direction-mode-breakdown.json',breakdown)
    results={};rate=lambda x:x['legal']/x['attempts']
    for arm in ARMS:
        label=arm['label'];mapped={'control-legacy':c['anchor-legacy']}
        mapped.update({'parent-'+d:c['parent-'+d] for d,p,r in DISTS})
        mapped.update({'candidate-'+d:c[label+'-'+d] for d,p,r in DISTS})
        bd={'parent-'+d:breakdown['parent-'+d] for d in ['focus','bridge','lateral']}
        bd.update({'candidate-'+d:breakdown[label+'-'+d] for d in ['focus','bridge','lateral']})
        gates=judge(dict(cases=mapped),bd)['retention']
        for mode in ['air','bounce']:gates['parent-focus/'+mode]=rate(c[label+'-focus'][mode])>=rate(c['parent-focus'][mode])-.0625
        results[label]=dict(retentionPassed=all(gates.values()),retention=gates)
    gains={str(seed):rate(c[f'fixed-s{seed}-legacy']['air'])-rate(c[f'control-s{seed}-legacy']['air']) for seed in [1,2]}
    mean=sum(gains.values())/2
    promising=all(results[f'fixed-s{s}']['retentionPassed'] for s in [1,2]) and all(x>0 for x in gains.values()) and mean>=.05
    result=dict(status='completed_for_review',arms=results,primaryPairedGains=gains,meanPrimaryGain=mean,
        promising=promising,promoted=False,trainingExtended=False,finalSeedsConsumed=False,
        interpretation='Two training seeds and one common development cohort. Screening evidence only; not full-game acceptance. Clipping may be unhelpful; retain failed outcomes.')
    write(a/'review.json',result)
    labels=['parent']+[x['label'] for x in ARMS]
    lines=['# Critic-key comparison results','',
        'Four independent 500,000-experience runs completed from the same full parent. Only the trainer value-estimates key changed between methods. Both seeds used the same interleaved practice and corrected diagnostics. No model was promoted.','',
        '| Test | '+' | '.join(labels)+' |','|---|'+'---:|'*len(labels)]
    for d,p,r in DISTS:
        for mode in ['air','bounce']:
            values=[c[label+'-'+d][mode] for label in labels]
            lines.append('| '+d+'/'+mode+' | '+' | '.join(f"{x['legal']}/{x['attempts']}" for x in values)+' |')
    lines+=['','| Run | All retention gates | Failed gates |','|---|---|---|']
    for label,x in results.items():lines.append('| '+label+' | '+str(x['retentionPassed'])+' | '+', '.join(k for k,t in x['retention'].items() if not t)+' |')
    lines+=['',f"Corrected-minus-control earlier-air gains: seed1 {gains['1']:+.1%}, seed2 {gains['2']:+.1%}; mean {mean:+.1%}.",
        f'Predeclared promising screen passed: {promising}.','',
        '| Run | PPO updates | Mean minibatch fraction where value clipping controls the loss |','|---|---:|---:|']
    for arm in ARMS:
        x=read(BASE/('critic-key-'+arm['label']+'-01-train')/'diagnostic-verification.json')
        lines.append(f"| {arm['label']} | {x['updates']} | {x['meanValueClipDominatesFraction']:.2%} |")
    lines+=['','Serving, opening receive and central rally retention are included in the gates. Repeated basic resets across distributions are not independent samples. The raw verification and direction-mode breakdown retain every denominator.',
        '',result['interpretation'],'',
        'Operational recovery: the first control finished normally, but an overly strict controller check demanded all eight asynchronous workers in every PPO buffer. The corrected validator checks positive, accounted-for worker counts per buffer and all workers across the run. Independent worker completion and per-update drill checks remain. The valid first run and preflight were reused; training, seeds, budgets and evaluation criteria were unchanged.',
        '',f'Evidence: {a.as_posix()}','']
    OUTPUT.write_text('\n'.join(lines),encoding='utf-8')
    return result

def restore():
    before=read(CAMP/'editor-before.json')
    try:
        x=cli('if(UnityEditor.EditorApplication.isPlaying&&UnityEngine.SceneManagement.SceneManager.GetActiveScene().path==""&&UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects().Length==0){UnityEditor.EditorApplication.isPlaying=false;return "exit";}return "user scene preserved";')
        if x=='exit':
            time.sleep(3)
            path=before['path'].replace('\\','/')
            restore_code='UnityEditor.SceneManagement.EditorSceneManager.OpenScene("'+path+'");' if path else 'UnityEditor.SceneManagement.EditorSceneManager.NewScene(UnityEditor.SceneManagement.NewSceneSetup.EmptyScene,UnityEditor.SceneManagement.NewSceneMode.Single);'
            x=cli('if(!UnityEditor.EditorApplication.isPlaying&&UnityEngine.SceneManagement.SceneManager.GetActiveScene().path==""&&!UnityEngine.SceneManagement.SceneManager.GetActiveScene().isDirty){'+restore_code+'return "original scene restored";}return "user scene preserved";')
        write(CAMP/'editor-restoration.json',dict(status=x,original=before['path']))
        if x=='original scene restored' and before.get('batchMode'):
            # This task opened the otherwise absent batch Editor. Exit only that instance.
            try:cli('if(UnityEngine.Application.isBatchMode&&System.Diagnostics.Process.GetCurrentProcess().Id=='+str(before['pid'])+'){UnityEditor.EditorApplication.delayCall+=()=>UnityEditor.EditorApplication.Exit(0);}return "background editor exit requested";')
            except Exception:pass
    except Exception as exc:write(CAMP/'editor-restoration.json',dict(status='left_as_is',reason=str(exc)))

def main():
    try:
        next_operation()
        amendment=read(CAMP/'recovery-verification.json')
        assert all(sha(Path(p))==h for p,h in amendment['preservedEvidence'].items()),'Original recovery evidence changed'
        assert read(BASE/PREFLIGHT/'preflight-verification.json')['historicalEpisodesExact']==512
        assert read(CAMP/'plan.json')==read(ORIGINAL/'plan.json'),'Scientific plan changed'
        state('recovering_completed_control')
        finish_training(ARMS[0])
        for arm in ARMS[1:]:train(arm)
        evaluation();result=review();state('completed_for_review',review=result)
    except Exception:
        (CAMP/'error.txt').write_text(traceback.format_exc(),encoding='utf-8');state('failed',error=traceback.format_exc()[-2200:]);raise
    finally:restore()

if __name__=='__main__':main()

from pathlib import Path
import json, hashlib, shutil, torch
import prepare_movement_progress_evaluation as old
R=Path('F:/dev/picklebot'); H=Path(__file__).resolve().parent
BASE='artifacts/hierarchy-v1/precontact-alignment-01'; B=R/BASE
MODEL='ExecutionV1PrecontactFinal01'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
    proof=read(B/'training/run-complete.json'); source=read(B/'source-records.json')
    assert proof['parentUnchanged'] and 2097152<=proof['step']<2105344 and not proof['promotion']
    assert read(B/'training/process-result.json')['exitCode']==0
    assert not read(R/'artifacts/player-v3/seed-ledger.json')['finalSeedsConsumed']
    for rel,digest in source['files'].items(): assert sha(R/rel)==digest
    result=R/'artifacts/mlagents/execution-precontact-alignment-01'
    checkpoint=result/'PicklebotExecutionV1/checkpoint.pt'; model=result/'PicklebotExecutionV1.onnx'
    assert sha(checkpoint)==proof['checkpointHash'] and sha(model)==proof['modelHash']
    numbered=result/f"PicklebotExecutionV1/PicklebotExecutionV1-{proof['step']}.pt"
    state=torch.load(checkpoint,map_location='cpu',weights_only=False)
    assert old.same_state(state,torch.load(numbered,map_location='cpu',weights_only=False))
    assert list(state['global_step'].values())[0].item()==proof['step']
    assert tuple(state['Policy']['network_body._body_endoder.seq_layers.0.weight'].shape)==(128,136)
    asset=R/f'Assets/Picklebot/PlayerLearning/Models/{MODEL}.onnx'
    snapshot=R/'training/snapshots/execution-v1-precontact-final-01.pt'
    assert not asset.exists() and not snapshot.exists() and not (B/'selected-models.json').exists()
    identity=dict(model=MODEL,step=proof['step'],modelHash=sha(model),checkpointHash=sha(numbered),assetPath=asset.relative_to(R).as_posix(),checkpoint=snapshot.relative_to(R).as_posix(),sourceIdentity=source['sourceIdentity'])
    generated={}
    for key,(rel,digest) in old.TEMPLATES.items():
        template=R/rel; assert sha(template)==digest
        battery,condition=key.split('/'); code=template.read_text(encoding='utf-8-sig')
        campaign='fresh-placement-01' if battery=='narrow' else 'wide-movement-fixture-01'
        prefix=f'artifacts/hierarchy-v1/{campaign}/evaluation/'; assert prefix in code
        code=code.replace(prefix,BASE+f'/evaluation/{battery}/').replace(old.PARENT,MODEL).replace(old.PARENT_MODEL_HASH,identity['modelHash']).replace(old.PARENT_SNAPSHOT_HASH,identity['checkpointHash']).replace(old.OLD_SOURCE,source['sourceIdentity']).replace('step=1048609,',f"step={proof['step']},")
        hook='    run.AutoRun=false;run.RequireTrainer=false;run.Task="movement-maintenance";'; assert code.count(hook)==1
        code=code.replace(hook,hook+'\n    run.PrecontactAlignmentReward=false;run.MovementForwardProgressReward=false;')
        creation='var root=new UnityEngine.GameObject("Two-region evaluation");root.SetActive(false);'; assert creation in code
        code=code.replace(creation,'if(System.IO.Directory.Exists(output))throw new System.InvalidOperationException("Preserve existing evaluation");\n'+creation)
        guard='''    if(run.PrecontactAlignmentReward||run.Report.precontactAlignmentReward||run.MovementForwardProgressReward||run.Report.movementForwardProgressReward)throw new System.InvalidOperationException("Shaping enabled during evaluation");
    foreach(var ep in run.Episodes)if(ep.precontactAlignmentRewardEnabled||ep.precontactShapingReward!=0f||ep.precontactTransitions!=0||ep.movementForwardProgressRewardEnabled)throw new System.InvalidOperationException("Evaluation received shaping");
'''
        hook='    System.IO.File.WriteAllText(output+"/first-decisions.json"'; assert code.count(hook)==1
        code=code.replace(hook,guard+hook)
        path=H/f'precontact-final-{battery}-{condition}.cs'; assert not path.exists()
        generated[key]=(path,code,rel,digest)
    shutil.copyfile(numbered,snapshot); shutil.copyfile(model,asset)
    scripts={}
    for key,(path,code,rel,digest) in generated.items():
        path.write_bytes(code.encode()); scripts[key]=dict(path=str(path),sha256=sha(path),template=rel,templateHash=digest)
    with (B/'selected-models.json').open('x') as f: json.dump(dict(final=identity,scripts=scripts,selection='Mandatory fixed final endpoint; no performance selection',trainingProofHash=sha(B/'training/run-complete.json'),planHash=sha(B/'plan.json')),f,indent=2)
    print(json.dumps(identity,indent=2))
if __name__=='__main__': main()

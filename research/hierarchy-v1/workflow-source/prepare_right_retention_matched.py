"""Generate prospective matched acquisition tests, without changing the full batteries."""
from pathlib import Path
import json,hashlib
import prepare_movement_progress_evaluation as old
R=Path('F:/dev/picklebot');H=Path(__file__).resolve().parent
BASE='artifacts/hierarchy-v1/right-retention-01';B=R/BASE
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def generate(model,identity):
    source=read(B/'source-records.json')
    for rel,digest in source['files'].items():assert sha(R/rel)==digest
    assert sha(R/identity['assetPath'])==identity['modelHash'] and sha(R/identity['checkpoint'])==identity['checkpointHash']
    scripts={}
    for condition in ['A','B']:
        rel,digest=old.TEMPLATES['narrow/'+condition];template=R/rel;assert sha(template)==digest
        s=template.read_text(encoding='utf-8-sig')
        replacements={
            'artifacts/hierarchy-v1/fresh-placement-01/evaluation/':BASE+'/evaluation/acquisition/',
            old.PARENT:model,old.PARENT_MODEL_HASH:identity['modelHash'],old.PARENT_SNAPSHOT_HASH:identity['checkpointHash'],
            old.OLD_SOURCE:source['sourceIdentity'],'step=1048609,':f"step={identity['step']},",
            'run.Task="movement-maintenance"':'run.Task="right-return-acquisition"',
            'run.FirstSeed=1109593;run.SeedCount=256;run.ArenaCount=8;run.MaximumReturnDifficulty=.25f;':'run.FirstSeed=1109849;run.SeedCount=512;run.ArenaCount=16;run.MaximumReturnDifficulty=0;',
            'run.FixedServeSides="both";run.MovementRange=.025f;run.MovementPattern="lateral";run.MovementRehearsalRange=.1f;':'run.FixedServeSides="both";run.MovementRange=.0625f;run.MovementPattern="lateral-right";run.MovementRehearsalRange=0;',
            'run.MovementRecoveryMix=true;run.InterleavedRecovery=true;run.AlignDrillDecisions=false;':'run.MovementRecoveryMix=false;run.InterleavedRecovery=false;run.AlignDrillDecisions=false;run.PrecontactAlignmentReward=false;run.MovementForwardProgressReward=false;',
            'goals.Completed!=256||first.Count!=256':'goals.Completed!=512||first.Count!=512',
        }
        for before,after in replacements.items():assert before in s,before;s=s.replace(before,after)
        creation='var root=new UnityEngine.GameObject("Two-region evaluation");root.SetActive(false);'
        s=s.replace(creation,'if(System.IO.Directory.Exists(output))throw new System.InvalidOperationException("Preserve existing acquisition evaluation");\n'+creation)
        guard='''    foreach(var ep in run.Episodes)if(ep.movementPattern!="lateral-right"||ep.movementRegion!=5||ep.movementRange!=.0625f||ep.precontactAlignmentRewardEnabled||ep.precontactShapingReward!=0||ep.movementForwardProgressRewardEnabled)throw new System.InvalidOperationException("Acquisition reset or reward contract mismatch");
'''
        needle='    System.IO.File.WriteAllText(output+"/first-decisions.json"';assert s.count(needle)==1;s=s.replace(needle,guard+needle)
        # SourceIdentity identifies this evaluation runtime. Keep training provenance separately.
        s=s.replace('step='+str(identity['step'])+',sourceIdentity=', 'step='+str(identity['step'])+',trainingSourceIdentity="'+identity['trainingSourceIdentity']+'",sourceIdentity=')
        p=H/f'acquisition-matched-{model}-{condition}.cs';assert not p.exists();p.write_bytes(s.encode())
        scripts[condition]=dict(path=str(p),sha256=sha(p),templateHash=digest)
    return scripts
def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--final',action='store_true');args=parser.parse_args()
    if args.final:
        identity=read(B/'selected-models.json')['final'];identity={**identity,'trainingSourceIdentity':identity['sourceIdentity']}
    else:
        identity=dict(model=old.PARENT,step=1048609,assetPath=f'Assets/Picklebot/PlayerLearning/Models/{old.PARENT}.onnx',checkpoint='training/snapshots/execution-v1-smooth-continued-final-01.pt',modelHash=old.PARENT_MODEL_HASH,checkpointHash=old.PARENT_SNAPSHOT_HASH,trainingSourceIdentity=old.OLD_SOURCE)
    scripts=generate(identity['model'],identity)
    with (B/('acquisition-final-evaluation.json' if args.final else 'acquisition-baseline-evaluation.json')).open('x') as f:
        json.dump(dict(model=identity,scripts=scripts,firstSeed=1109849,count=512,conditions=['A','B'],purpose='Matched acquisition diagnostic on reused development anchors, not full mastery',scriptHash=sha(Path(__file__)),runtimeSourceIdentity=read(B/'source-records.json')['sourceIdentity']),f,indent=2)
    print('Prepared acquisition scripts for',identity['model'])
if __name__=='__main__':main()

"""Prepare actual Unity frame capture after matched evaluations; no invented motion."""
from pathlib import Path
import argparse,json,hashlib,shutil
R=Path('F:/dev/picklebot');H=Path(__file__).resolve().parent
B=R/'artifacts/hierarchy-v1/right-acquisition-01'
W=H.parent.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--role',choices=['baseline','final'],required=True);args=parser.parse_args()
    spec=read(B/f'acquisition-{args.role}-evaluation.json');identity=spec['model']
    reference=B/'evaluation/acquisition'/identity['model']/'A'
    assert read(reference/'summary.json')['episodes']==512
    destination=W/'outputs/right-acquisition-review-01'/args.role;assert not destination.exists()
    source=read(B/'source-records.json')
    for rel,digest in source['files'].items():assert sha(R/rel)==digest
    template=W/'outputs/wide-movement-review-02/capture.cs';s=template.read_text()
    s=s.replace('C:/Users/Admin/Documents/Codex/2026-09-07/https-unity-com-blog-meet-the-7/outputs/wide-movement-review-02',destination.as_posix())
    s=s.replace('(int)manifest["checkpoint"]==1048609','(int)manifest["checkpoint"]=='+str(identity['step']))
    s=s.replace('5f8c4a10a777ea4c69c0a2ef01831163252a3614bddaaedfe2ab4024d04831c9',source['sourceIdentity'])
    s=s.replace('checkpoint=1048609','checkpoint='+str(identity['step'])).replace('step=1048609','step='+str(identity['step']))
    before='run.Task="movement-maintenance";run.FirstSeed=1109849;run.SeedCount=512;run.ArenaCount=8;run.MaximumReturnDifficulty=.25f;'
    assert before in s;s=s.replace(before,'run.Task="right-return-acquisition";run.FirstSeed=1109849;run.SeedCount=512;run.ArenaCount=16;run.MaximumReturnDifficulty=0;')
    before='run.MovementRange=.25f;run.MovementPattern="axes";';assert before in s
    s=s.replace(before,'run.MovementRange=.0625f;run.MovementPattern="lateral-right";run.PrecontactAlignmentReward=false;run.MovementForwardProgressReward=false;')
    destination.mkdir(parents=True)
    (destination/'capture.cs').write_bytes(s.encode());shutil.copyfile(B/'source-records.json',destination/'source-records.json')
    manifest=dict(modelName=identity['model'],model=identity['assetPath'],modelHash=identity['modelHash'],checkpoint=identity['step'],checkpointPath=identity['checkpoint'],checkpointHash=identity['checkpointHash'],sourceIdentity=source['sourceIdentity'],firstSeed=1109849,seedCount=512,fullReplayEpisodes=512,clipCount=8,stages=[dict(condition='A',referenceDirectory=str(reference),clipSeeds=list(range(1109849,1109857)))],referenceInputSha256={p.relative_to(R).as_posix():sha(p) for p in reference.iterdir() if p.is_file()},captureScriptSha256=sha(destination/'capture.cs'),ledgerHash=sha(R/'artifacts/player-v3/seed-ledger.json'),selection='First eight declared resets: one per feed/seat cell, chosen before final results; successes and failures retained.',templateHash=sha(template),role=args.role)
    with (destination/'manifest.json').open('x') as f:json.dump(manifest,f,indent=2)
    print(destination)
if __name__=='__main__':main()

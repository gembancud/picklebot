"""Verify exact D-036 historical intent bridge and preserve prior evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import zipfile
from player_actor import contact_source_hash, player_source_hash, team_source_hash, source_record_text

ROOT=Path(__file__).resolve().parents[1]
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def experimental_source_hash():
    records=[]
    for folder in ('PlayerControls','PlayerControlsIntegration'):
        for path in (ROOT/'Assets/Picklebot'/folder).rglob('*.cs'):
            name=path.relative_to(ROOT).as_posix()
            if '/Tests/' not in name:records.append((name,path.read_text(encoding='utf-8-sig')))
    return hashlib.sha256((player_source_hash(ROOT)+'\n'+source_record_text(records)).encode('utf-8')).hexdigest()
def verify(unity=None):
    record=json.loads((ROOT/'config/player-controls-v2-intent.json').read_text())
    if digest(ROOT/'config/player-controls-v2-game.json')!=record['priorGameSha256']:raise RuntimeError('D-035 evidence changed')
    if digest(ROOT/'scripts/player-game-verify.py')!=record['priorGameVerifierSha256']:raise RuntimeError('D-035 verifier changed')
    decisions_path=ROOT/'config/player-controls-v2-decisions.json'
    if digest(decisions_path)!=record['priorDecisionsSha256']:raise RuntimeError('D-034 evidence changed')
    decisions=json.loads(decisions_path.read_text())
    if digest(ROOT/'scripts/player-decisions-verify.py')!=decisions['verifierSha256']:raise RuntimeError('D-034 verifier changed')
    integration_path=ROOT/'config/player-controls-v2-integration.json' 
    if digest(integration_path)!=record['priorIntegrationSha256']:raise RuntimeError('D-033 evidence changed')
    integration=json.loads(integration_path.read_text())
    if digest(ROOT/'scripts/player-controls-verify.py')!=integration['verifierSha256']:raise RuntimeError('D-033 verifier changed')
    if record['priorAdapterSources']!={'Assets/Picklebot/Doubles/PlayerBodyExternal.cs':'artifacts/player-controls-v2/PlayerBodyExternal-d033.cs.txt'}:
        raise RuntimeError('Unexpected historical body archive scope')
    for name,value in integration['baselineAdapterFiles'].items():
        historical=ROOT/record['priorAdapterSources'].get(name,name)
        if digest(historical)!=value:raise RuntimeError('D-033 body adapter evidence changed: '+name)
    prior_path=ROOT/'config/windows-source-migration.json' 
    if digest(prior_path)!=record['priorMigrationSha256']:raise RuntimeError('D-031 evidence changed')
    prior=json.loads(prior_path.read_text())
    baseline_path=ROOT/'artifacts/player-agents/baseline-manifest.json'
    if digest(baseline_path)!=prior['originalBaselineSha256']:raise RuntimeError('Original baseline evidence changed')
    tooling_path=ROOT/'config/windows-tooling-migration.json'
    if digest(tooling_path)!=prior['toolingRecordSha256']:raise RuntimeError('Tooling evidence changed')
    before_path=ROOT/'config/player-controls-v2-pre-integration.json'
    if digest(before_path)!=record['preIntegrationSha256']:raise RuntimeError('Pre-integration record changed')
    before=json.loads(before_path.read_text());archive=ROOT/before['archive']
    if digest(archive)!=before['sha256']:raise RuntimeError('Pre-integration archive changed')
    expected=json.loads(baseline_path.read_text())['files']
    expected.update(json.loads(tooling_path.read_text())['packageFiles']);expected.update(prior['baselineSourceFiles'])
    with zipfile.ZipFile(archive) as z:
        for name,value in expected.items():
            if hashlib.sha256(z.read(name)).hexdigest()!=value:raise RuntimeError('Archived baseline differs: '+name)
    changes=record['baselineAdapterFiles']
    if set(changes)!={'Assets/Picklebot/Doubles/PlayerBody.cs','Assets/Picklebot/Doubles/PlayerBodyExternal.cs','Assets/Picklebot/Doubles/DoublesRules.cs'}:
        raise RuntimeError('Unexpected body-adapter migration scope')
    expected.update(changes)
    actual=runpy.run_path(str(ROOT/'scripts/player-agents-baseline.py'))['snapshot']()
    if actual!=expected:raise RuntimeError('Unrecorded baseline changes: '+str(sorted(k for k in set(actual)|set(expected) if actual.get(k)!=expected.get(k))))
    for section in ('implementationFiles','preservedArtifacts'):
        for name,value in prior[section].items():
            if digest(ROOT/name)!=value:raise RuntimeError('Historical '+section+' changed: '+name)
    inventory={p.relative_to(ROOT).as_posix():digest(p) for folder in ('PlayerControls','PlayerControlsIntegration')
        for p in (ROOT/'Assets/Picklebot'/folder).rglob('*') if p.is_file() and p.suffix in ('.cs','.asmdef')}
    if inventory!=record['experimentalFiles']:raise RuntimeError('Experimental implementation differs from recorded evidence')
    if digest(Path(__file__))!=record['verifierSha256']:raise RuntimeError('Integration verifier changed')
    hashes=dict(contact=contact_source_hash(ROOT),player=player_source_hash(ROOT),team=team_source_hash(ROOT),controls=experimental_source_hash())
    if hashes!=record['sourceHashes']:raise RuntimeError('Unrecorded source identity')
    if unity:
        code='return new {contact=Picklebot.Doubles.Editor.ContactTraining.SourceHash(),player=Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash(),team=Picklebot.DoublesTraining.Editor.TeamTraining.SourceHash(),controls=Picklebot.PlayerControlsIntegration.Editor.PlayerControlSource.SourceHash()};'
        result=subprocess.run([unity,'command','eval',code,'--project-path',str(ROOT),'--format','json'],capture_output=True,text=True,check=True,timeout=60)
        envelope=json.loads(result.stdout);data=envelope['data']
        if not envelope.get('success') or Path(data['target']['projectPath']).resolve()!=ROOT.resolve() or not data['result'].get('success') or data['result']['result']!=hashes:
            raise RuntimeError('Live Unity identity differs or selected the wrong project')
    return dict(passed=True,unityCompared=bool(unity),sourceHashes=hashes,preservedArtifacts=len(prior['preservedArtifacts']),
        adapterFiles=len(changes),status='Historical actor intent bridge source verified; physical performance and trained V2 acceptance are separate')
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--unity',nargs='?',const='unity');args=parser.parse_args()
    print(json.dumps(verify(args.unity),indent=2))

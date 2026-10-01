from pathlib import Path
import hashlib,json,subprocess,xml.etree.ElementTree as ET
ROOT=Path('F:/dev/picklebot');BASE=ROOT/'artifacts/hierarchy-v1/two-regions-01';BUILD=BASE/'execution-two-region-build-01'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
tests=ET.parse(ROOT/'artifacts/hierarchy-v1/two-regions-integration-tests-02.xml').getroot()
assert tests.attrib['result']=='Passed' and int(tests.attrib['total'])==19
BASE.mkdir(exist_ok=False)
paths=[p for p in (ROOT/'Assets/Picklebot').rglob('*') if p.is_file() and p.suffix in ['.cs','.asmdef']]
paths += [ROOT/p for p in ['Packages/manifest.json','Packages/packages-lock.json','ProjectSettings/ProjectVersion.txt','ProjectSettings/ProjectSettings.asset','ProjectSettings/TimeManager.asset','ProjectSettings/DynamicsManager.asset']]
files={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(paths)}
identity=hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()
source=dict(sourceIdentity=identity,files=files,baselineCommit='2120407',contract='execution-v1-136obs-16continuous-release')
(BASE/'source-records.json').write_text(json.dumps(source,indent=2),encoding='utf-8')
model='Assets/Picklebot/PlayerLearning/Models/ExecutionV1Initial.onnx'
args=[str(Path.home()/'AppData/Local/Unity/bin/unity.exe'),'run',str(ROOT),'--timeout','900','--format','json','--','-executeMethod','Picklebot.PlayerLearning.Editor.ExecutionBuildV1.FromCommandLine','--execution-output',str(BUILD),'--execution-source',identity,'--execution-model-hash',sha(ROOT/model),'--execution-model',model]
print('Building fresh two-region worker '+identity,flush=True)
with (BASE/'build-console.log').open('x',encoding='utf-8') as log:
    result=subprocess.run(args,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
assert result.returncode==0,(BASE/'build-console.log').read_text()
assert read(BUILD/'build-result.json')['status']=='Succeeded'
assert all(sha(ROOT/n)==h for n,h in files.items()),'Source changed during build'
buildfiles={p.relative_to(BUILD).as_posix():sha(p) for p in sorted(BUILD.rglob('*')) if p.is_file()}
record=dict(directory=str(BUILD),sourceIdentity=identity,buildIdentity=hashlib.sha256(json.dumps(buildfiles,sort_keys=True,separators=(',',':')).encode()).hexdigest(),files=buildfiles)
(BASE/'build-verification.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in record.items() if k!='files'}))


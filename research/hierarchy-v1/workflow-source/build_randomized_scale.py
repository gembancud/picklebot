from pathlib import Path
import json,hashlib,subprocess,xml.etree.ElementTree as ET
R=Path('F:/dev/picklebot');A=R/'artifacts/hierarchy-v1/randomized-scale-01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):
 with p.open('x',encoding='utf-8') as f:json.dump(x,f,indent=2)
def main():
 tests=R/'artifacts/hierarchy-v1/randomized-scale-tests-02.xml'
 cases=list(ET.parse(tests).getroot().iter('test-case'));assert len(cases)==17 and all(c.attrib['result']=='Passed' for c in cases)
 prior=json.loads((R/'artifacts/hierarchy-v1/right-retention-01/source-records.json').read_text(encoding='utf-8'))
 paths=list((R/'Assets/Picklebot').rglob('*.cs'))+list((R/'Assets/Picklebot').rglob('*.asmdef'))+[R/p for p in prior['files'] if not p.startswith('Assets/')]
 files={p.relative_to(R).as_posix():sha(p) for p in sorted(set(paths))}
 identity=hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 output=A/'randomized-scale-build-01';assert not output.exists()
 model='Assets/Picklebot/PlayerLearning/Models/ExecutionV1Initial.onnx'
 command=[str(Path.home()/'AppData/Local/Unity/bin/unity.exe'),'run',str(R),'--timeout','900','--format','json','--','-executeMethod','Picklebot.PlayerLearning.Editor.ExecutionBuildV1.FromCommandLine','--execution-output',str(output),'--execution-source',identity,'--execution-model-hash',sha(R/model),'--execution-model',model]
 write(A/'source-records.json',dict(sourceIdentity=identity,files=files,testsHash=sha(tests),passedTests=len(cases),workingTreeBuild=True))
 with (A/'build-console.log').open('x',encoding='utf-8') as log:r=subprocess.run(command,cwd=R,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 assert r.returncode==0
 result=json.loads((output/'build-result.json').read_text(encoding='utf-8-sig'));assert result['status']=='Succeeded' and result['errors']==0
 assert all(sha(R/p)==digest for p,digest in files.items())
 hashes={p.relative_to(output).as_posix():sha(p) for p in sorted(output.rglob('*')) if p.is_file()}
 write(A/'build-verification.json',dict(directory=str(output),sourceIdentity=identity,buildIdentity=hashlib.sha256(json.dumps(hashes,sort_keys=True,separators=(',',':')).encode()).hexdigest(),files=hashes))
 print('Randomized worker build verified.',flush=True)
if __name__=='__main__':main()

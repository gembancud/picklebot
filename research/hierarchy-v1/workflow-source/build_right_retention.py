"""Build the tested fixed-right retention experiment; no trainer launch or source rewrite."""
from pathlib import Path
import hashlib,json,subprocess,xml.etree.ElementTree as ET
ROOT=Path("F:/dev/picklebot")
BASE=ROOT/"artifacts/hierarchy-v1/right-retention-01"
MODEL="Assets/Picklebot/PlayerLearning/Models/ExecutionV1Initial.onnx"
MODEL_HASH="bc6f8be16b791a2cd253b150b3f4c4c2492cdc0e65f94fa305ab4addefe78d51"
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding="utf-8-sig"))
def write(p,v):
 with p.open("x",encoding="utf-8") as h:json.dump(v,h,indent=2)
def main():
 assert not BASE.exists(),"Preserve prior build attempts"
 validated=ROOT/"artifacts/hierarchy-v1/right-acquisition-01/source-records.json"
 prior=read(validated)
 for rel,digest in prior["files"].items():
  if rel not in ("Assets/Picklebot/PlayerLearning/PlayerRecoveryScheduleV3.cs",):assert sha(ROOT/rel)==digest,rel
 proof=read(ROOT/"research/hierarchy-v1/precontact-scheduler-validation-01/verification.json")
 assert proof["episodes"]==512 and proof["focusEpisodes"]==256 and proof["actionsAndGoalsByteIdentical"]
 tests=ROOT/"artifacts/hierarchy-v1/right-retention-tests-01.xml"
 cases=list(ET.parse(tests).getroot().iter("test-case"));assert len(cases)==18 and all(c.attrib["result"]=="Passed" for c in cases)
 record=read(Path(__file__).resolve().parent/"right-retention-tests-01-result.json")
 assert record["originalSettingsRestored"] and record["testResultHash"]==sha(tests) and record["exitCode"]==0
 assert sha(ROOT/MODEL)==MODEL_HASH
 git=["git","-c",f"safe.directory={ROOT.as_posix()}","-C",str(ROOT)]
 assert not subprocess.check_output(git+["status","--porcelain"]),"Commit reviewed work before build"
 paths=[p for p in (ROOT/"Assets/Picklebot").rglob("*") if p.is_file() and p.suffix in (".cs",".asmdef")]
 paths += [ROOT/p for p in prior["files"] if not p.startswith("Assets/")]
 files={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(paths))}
 identity=hashlib.sha256(json.dumps(files,sort_keys=True,separators=(",",":")).encode()).hexdigest()
 output=BASE/"execution-right-retention-build-01"
 cli=Path.home()/"AppData/Local/Unity/bin/unity.exe"
 command=[str(cli),"run",str(ROOT),"--timeout","900","--format","json","--","-executeMethod","Picklebot.PlayerLearning.Editor.ExecutionBuildV1.FromCommandLine","--execution-output",str(output),"--execution-source",identity,"--execution-model-hash",MODEL_HASH,"--execution-model",MODEL]
 BASE.mkdir()
 write(BASE/"source-records.json",dict(sourceIdentity=identity,files=files,baselineRuntimeIdentity=prior["sourceIdentity"],validationRecordHash=sha(validated),gitCommit=subprocess.check_output(git+["rev-parse","HEAD"],text=True).strip(),testsPath=str(tests),testsHash=sha(tests),totalPassedTestCases=18,contract="execution-v1-136obs-16continuous-release"))
 write(BASE/"build-launch.json",dict(args=command,scriptHash=sha(Path(__file__)),sourceIdentity=identity))
 with (BASE/"build-console.log").open("x",encoding="utf-8") as log:
  result=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 assert result.returncode==0,"Build failed; inspect preserved log"
 result=read(output/"build-result.json")
 assert result["status"]=="Succeeded" and result["errors"]==0 and result["sourceIdentity"]==identity and result["modelHash"]==MODEL_HASH
 for rel,digest in files.items():assert sha(ROOT/rel)==digest,rel
 build_files={p.relative_to(output).as_posix():sha(p) for p in sorted(output.rglob("*")) if p.is_file()}
 build=hashlib.sha256(json.dumps(build_files,sort_keys=True,separators=(",",":")).encode()).hexdigest()
 write(BASE/"build-verification.json",dict(directory=str(output),sourceIdentity=identity,buildIdentity=build,files=build_files))
 print(json.dumps(dict(sourceIdentity=identity,buildIdentity=build,trainingLaunched=False)))
if __name__=="__main__":main()

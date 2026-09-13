"""Frozen initial/1m checkpoint evaluations; writes evidence, never changes training."""
from pathlib import Path
import json,hashlib,subprocess,time,shutil,traceback
R=Path('F:/dev/picklebot');W=Path(__file__).resolve().parent
A=R/'artifacts/hierarchy-v1/randomized-scale-01';E=A/'evaluation-process'
CLI=Path.home()/'AppData/Local/Unity/bin/unity.exe'
B='PicklebotExecutionV1';RESULT=R/'artifacts/mlagents/execution-randomized-scale-01'/B
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,obj):
 with p.open('x',encoding='utf-8') as f:json.dump(obj,f,indent=2)
def command(args):
 p=subprocess.run([str(CLI),'command']+args+['--project-path',str(R),'--format','json'],capture_output=True,text=True,encoding='utf-8',creationflags=subprocess.CREATE_NO_WINDOW,timeout=660)
 if p.returncode:raise RuntimeError(p.stdout+p.stderr)
 data=json.loads(p.stdout);assert data['success'],data
 if 'eval_file' in args:assert data['data']['success'] and data['data']['result']['success'],data
 return data
def script(name,text):
 p=E/(name+'.cs');p.write_text(text,encoding='utf-8');return command(['eval_file',str(p),'540000','--timeout','600'])
def select(target):
 if target==0:return A/'initial-02'/B,A/'initial-02/checkpoint.pt',0
 deadline=time.time()+43200
 while time.time()<deadline:
  if (A/'runner-failure.txt').exists():raise RuntimeError('Training runner failed; preserve current evaluations')
  candidates=[]
  for p in RESULT.glob(B+'-*.pt'):
   step=int(p.stem.rsplit('-',1)[1]);onnx=p.with_suffix('.onnx')
   if target-8192<=step<=target+8192 and onnx.exists() and time.time()-max(p.stat().st_mtime,onnx.stat().st_mtime)>5:candidates.append((step,p))
  if candidates:
   step,p=min(candidates);return p.with_suffix(''),p,step
  time.sleep(60)
 raise TimeoutError('Checkpoint did not arrive')
def main():
 E.mkdir();write(E/'plan.json',dict(milestones=list(range(0,8000001,1000000)),batteries=['narrow-A','narrow-B','narrow-random','wide-A','wide-B','randomized-A','randomized-B'],randomizedDevelopmentSeeds='4000000..4000511',selection='First numbered checkpoint within8192 steps of each1m milestone, after completed export',promotion=False))
 source=json.loads((A/'source-records.json').read_text(encoding='utf-8'))['sourceIdentity']
 # Start an isolated task-owned Editor after the executable probe passed.
 deadline=time.time()+1800
 while not (A/'probe-proof.json').exists():
  if (A/'runner-failure.txt').exists() or time.time()>deadline:raise RuntimeError('Worker probe did not pass')
  time.sleep(15)
 editor=subprocess.Popen(['C:/Program Files/Unity/Hub/Editor/6000.5.5f1/Editor/Unity.exe','-batchmode','-projectPath',str(R),'-logFile',str(E/'editor.log')],creationflags=subprocess.CREATE_NO_WINDOW)
 write(E/'editor-process.json',dict(pid=editor.pid,owned=True))
 ready=False
 for attempt in range(24):
  time.sleep(10)
  try:
   script('prepare',f'''if(UnityEditor.EditorApplication.isPlaying)throw new System.InvalidOperationException("Expected idle editor");
for(int i=0;i<UnityEngine.SceneManagement.SceneManager.sceneCount;i++)if(UnityEngine.SceneManagement.SceneManager.GetSceneAt(i).isDirty)throw new System.InvalidOperationException("Unsaved scene");
System.IO.File.WriteAllText("{E.as_posix()}/scene-before.json",Newtonsoft.Json.JsonConvert.SerializeObject(UnityEditor.SceneManagement.EditorSceneManager.GetSceneManagerSetup()));
UnityEditor.SceneManagement.EditorSceneManager.NewScene(UnityEditor.SceneManagement.NewSceneSetup.EmptyScene,UnityEditor.SceneManagement.NewSceneMode.Single);
return "Ready";''');ready=True;break
  except Exception:
   if editor.poll() is not None:raise
 if not ready:raise RuntimeError('Evaluation Editor did not become ready')
 for milestone in range(0,8000001,1000000):
  prefix,checkpoint,step=select(milestone);model=f'ExecutionV1RandomizedScale{milestone:07}'
  modelpath=R/'Assets/Picklebot/PlayerLearning/Models'/(model+'.onnx');assert not modelpath.exists();shutil.copyfile(prefix.with_suffix('.onnx'),modelpath)
  modelhash,checkpointHash=sha(modelpath),sha(checkpoint)
  script(f'import-{milestone}',f'UnityEditor.AssetDatabase.ImportAsset("Assets/Picklebot/PlayerLearning/Models/{model}.onnx",UnityEditor.ImportAssetOptions.ForceSynchronousImport); return "Imported";')
  command(['editor_play'])
  for battery,condition in [('narrow','A'),('narrow','B'),('narrow','random'),('wide','A'),('wide','B'),('randomized','A'),('randomized','B')]:
   template='narrow' if battery=='randomized' else battery
   s=(W/f'right-retention-final-{template}-{condition}.cs').read_text(encoding='utf-8')
   s=s.replace('ExecutionV1RightRetentionFinal01',model).replace('a8af32d4adea142bbbaf3942d4c2927266fd798153dff5edfa155a867b4e6590',modelhash).replace('ebe469fce16e41c9963d50e4a6783fb49496b21d865c5ac6653057524411397e',checkpointHash).replace('de8bda54ce1aad9fcb545226c91a92a115f08b41e57dc036b6f9431e15b1ed4e',source).replace('step=2097180',f'step={step}')
   s=s.replace(f'right-retention-01/evaluation/{template}/',f'randomized-scale-01/evaluation/{battery}/')
   if battery=='randomized':
    s=s.replace('FirstSeed=1109593;run.SeedCount=256','FirstSeed=4000000;run.SeedCount=512').replace('MaximumReturnDifficulty=.25f','MaximumReturnDifficulty=.5f').replace('MovementRange=.025f;run.MovementPattern="lateral"','MovementRange=.25f;run.MovementPattern="randomized"').replace('goals.Completed!=256||first.Count!=256','goals.Completed!=512||first.Count!=512')
   result=script(f'{milestone}-{battery}-{condition}',s)
   write(E/f'{milestone}-{battery}-{condition}.json',result)
  command(['editor_stop'])
  write(E/f'{milestone}-complete.json',dict(step=step,model=model,modelHash=modelhash,checkpointHash=checkpointHash,batteries=7,promoted=False))
  print('Evaluated',milestone,'actual',step,flush=True)
 script('restore',f'''var previous=Newtonsoft.Json.JsonConvert.DeserializeObject<UnityEditor.SceneManagement.SceneSetup[]>(System.IO.File.ReadAllText("{E.as_posix()}/scene-before.json"));
if(previous.Length>0&&System.Array.TrueForAll(previous,s=>!s.isLoaded||!string.IsNullOrEmpty(s.path)))UnityEditor.SceneManagement.EditorSceneManager.RestoreSceneManagerSetup(previous);
UnityEditor.EditorApplication.delayCall+=()=>UnityEditor.EditorApplication.Exit(0);return "Evaluation complete";''')
 write(E/'complete.json',dict(milestones=9,batteriesPerMilestone=7,promoted=False))
if __name__=='__main__':
 try:main()
 except Exception:
  E.mkdir(exist_ok=True)
  (E/'failure.txt').write_text(traceback.format_exc(),encoding='utf-8');raise

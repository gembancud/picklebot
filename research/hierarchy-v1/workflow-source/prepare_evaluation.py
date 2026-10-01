from pathlib import Path
import json, shutil, subprocess, time
root=Path('F:/dev/picklebot');base=root/'artifacts/hierarchy-v1'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
verify=read(base/'execution-goals-smoke-01/verification.json')
assert verify['status']=='completed_learning_check'
target=root/'Assets/Picklebot/PlayerLearning/Models/ExecutionV1Smoke01.onnx'
assert not target.exists();shutil.copyfile(root/verify['model'],target)
path=root/'artifacts/player-v3/seed-ledger.json';ledger=read(path)
assert not ledger['finalSeedsConsumed']
assert max(x['firstSeed']+x['count'] for k in ['developmentBlocks','developmentReuses'] for x in ledger[k])==1109529
ledger['developmentBlocks'].append(dict(firstSeed=1109529,count=64,run='artifacts/hierarchy-v1/placement-dev-01',purpose='Initial vs trained execution model; 64 common reset/target seeds, movement-maintenance range 0.1, no promotion.'))
path.write_text(json.dumps(ledger,indent=2),encoding='utf-8')
plan=base/'placement-dev-01';plan.mkdir()
(plan/'plan.json').write_text(json.dumps(dict(firstSeed=1109529,seedCount=64,task='movement-maintenance',movementRange=.1,maximumReturnDifficulty=.25,fixedServeSides='both',targetRadius=1.5,models=['ExecutionV1Initial','ExecutionV1Smoke01'],promote=False),indent=2),encoding='utf-8')
args=['C:/Program Files/Unity/Hub/Editor/6000.5.5f1/Editor/Unity.exe','-batchmode','-projectPath',str(root),'-logFile',str(base/'evaluation-editor.log')]
p=subprocess.Popen(args,creationflags=subprocess.CREATE_NO_WINDOW)
(base/'evaluation-editor-process.json').write_text(json.dumps(dict(pid=p.pid,args=args,started=time.time()),indent=2),encoding='utf-8')
print(json.dumps(dict(editorPid=p.pid,firstSeed=1109529,episodesPerModel=64)))

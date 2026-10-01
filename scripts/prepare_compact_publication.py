"""Preserve selected trained states and compact evidence; leave bulk artifacts local."""
from pathlib import Path
import json,hashlib,shutil,gzip,csv,uuid
R=Path(__file__).resolve().parents[1];B='PicklebotExecutionV1'
DEST=R/'research/hierarchy-v1/randomized-scale-publication'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 DEST.mkdir(exist_ok=False);records=[]
 def copy(src,dst):
  dst.parent.mkdir(parents=True,exist_ok=True);assert not dst.exists();shutil.copyfile(src,dst)
  records.append(dict(source=str(src.relative_to(R)) if src.is_relative_to(R) else str(src),path=dst.relative_to(R).as_posix(),sha256=sha(dst),bytes=dst.stat().st_size))
 result=R/'artifacts/mlagents/execution-randomized-scale-24m'
 copy(result/B/'checkpoint.pt',R/'training/snapshots/execution-v1-randomized-scale-24m-final.pt')
 copy(result/B/f'{B}-23999987.pt',R/'training/snapshots/execution-v1-randomized-scale-24m-evaluated.pt')
 model=R/'Assets/Picklebot/PlayerLearning/Models/ExecutionV1RandomizedScale24mFinal.onnx'
 copy(result/f'{B}.onnx',model)
 template=Path(str(R/'Assets/Picklebot/PlayerLearning/Models/ExecutionV1RandomizedScale24m24000000.onnx')+'.meta').read_text(encoding='utf-8')
 import re
 Path(str(model)+'.meta').write_text(re.sub(r'guid: [0-9a-f]+','guid: '+uuid.uuid4().hex,template),encoding='utf-8')
 table=[]
 for campaign in ['randomized-scale-01','randomized-scale-24m']:
  root=R/'artifacts/hierarchy-v1'/campaign
  for rel in ['run-complete.json','source-records.json','training/config.yaml','training/manifest.json','training/launch.json','evaluation-process/complete.json','evaluation-process/plan.json']:
   if (root/rel).exists():copy(root/rel,DEST/campaign/rel)
  for summary in sorted((root/'evaluation').rglob('summary.json')):
   data=json.loads(summary.read_text(encoding='utf-8'));folder=summary.parent
   copy(summary,DEST/campaign/summary.relative_to(root))
   copy(folder/'model-identity.json',DEST/campaign/(folder/'model-identity.json').relative_to(root))
   eps=[json.loads(x) for x in (folder/'episodes.jsonl').read_text(encoding='utf-8').splitlines()]
   ident=json.loads((folder/'model-identity.json').read_text(encoding='utf-8'))
   for task in sorted({e['task'] for e in eps}):
    rows=[e for e in eps if e['task']==task]
    table.append(dict(campaign=campaign,step=ident['step'],battery=summary.relative_to(root/'evaluation').parts[0],condition=data['condition'],task=task,episodes=len(rows),legal=sum(e['outcome'] in ('legal_serve','legal_return') for e in rows)))
   if campaign=='randomized-scale-24m' and '24000000' in str(summary):
    for name in ['episodes.jsonl','execution-goals.jsonl']:
     src=folder/name;dst=DEST/campaign/src.relative_to(root);dst=Path(str(dst)+'.gz')
     with src.open('rb') as inp,gzip.open(dst,'wb') as out:shutil.copyfileobj(inp,out)
  for complete in (root/'evaluation-process').glob('*-complete.json'):copy(complete,DEST/campaign/'evaluation-process'/complete.name)
 with (DEST/'skill-history.csv').open('w',encoding='utf-8',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=list(table[0]));writer.writeheader();writer.writerows(table)
 old=Path('C:/Users/Admin/Documents/Codex/2026-09-07/https-unity-com-blog-meet-the-7/work/hierarchy-v1')
 for p in old.iterdir():
  if p.suffix in ('.py','.cs','.yaml','.patch'):copy(p,R/'research/hierarchy-v1/workflow-source'/p.name)
 (DEST/'publication-manifest.json').write_text(json.dumps(dict(finalStep=24000022,evaluatedStep=23999987,rawArtifactsRemainLocal=True,files=records),indent=2),encoding='utf-8')
 print(json.dumps(dict(files=len(records),bytes=sum(r['bytes'] for r in records),skillRows=len(table))))
if __name__=='__main__':main()

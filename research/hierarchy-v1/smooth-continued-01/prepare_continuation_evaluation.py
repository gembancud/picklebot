"""Select predetermined step checkpoints after completed continuation, then stage Unity evaluation."""
from pathlib import Path
import json,hashlib,shutil
import torch
root=Path('F:/dev/picklebot');here=Path(__file__).parent
base=root/'artifacts/hierarchy-v1/smooth-continued-01'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=read(base/'plan.json');verification=read(base/'training/verification.json')
assert verification['status']=='completed_continuation_check' and verification['resumeStateExact'] and verification['parentRunUnchanged']
assert verification['sourceIdentity']==plan['sourceIdentity'] and verification['initialStep']==plan['initialStep']
result=root/'artifacts/mlagents/execution-smooth-continued-01'
folder=result/'PicklebotExecutionV1'
def actual_step(p):
    s=torch.load(p,map_location='cpu',weights_only=False)
    return int(next(iter(s['global_step'].values())).item())
def equal_state(a,b):
    if isinstance(a,torch.Tensor):return isinstance(b,torch.Tensor) and a.dtype==b.dtype and torch.equal(a,b)
    if isinstance(a,dict):return isinstance(b,dict) and a.keys()==b.keys() and all(equal_state(a[k],b[k]) for k in a)
    if isinstance(a,(list,tuple)):return type(a)==type(b) and len(a)==len(b) and all(equal_state(x,y) for x,y in zip(a,b))
    return a==b
assert not (base/'selected-models.json').exists()
available=[]
for checkpoint in folder.glob('PicklebotExecutionV1-*.pt'):
    step=actual_step(checkpoint)
    assert int(checkpoint.stem.rsplit('-',1)[1])==step
    onnx=checkpoint.with_suffix('.onnx')
    available.append((step,checkpoint,onnx))
assert available,'Missing numbered checkpoint/export pairs'
mid=min(available,key=lambda r:(abs(r[0]-524288),r[0]))
assert abs(mid[0]-524288)<=8192
assert mid[2].is_file(),'The predetermined midpoint export is missing; do not substitute a different checkpoint'
final_step=actual_step(folder/'checkpoint.pt')
assert 1048576<=final_step<1056768
assert verification['experiences']==final_step
assert verification['checkpointHash']==sha(folder/'checkpoint.pt') and verification['modelHash']==sha(result/'PicklebotExecutionV1.onnx')
final=next(r for r in available if r[0]==final_step)
assert equal_state(torch.load(final[1],map_location='cpu',weights_only=False),torch.load(folder/'checkpoint.pt',map_location='cpu',weights_only=False))
assert sha(final[2])==sha(result/'PicklebotExecutionV1.onnx')
selection={}
for name,row,model in [('mid',mid,'ExecutionV1SmoothContinuedMid01'),('final',final,'ExecutionV1SmoothContinuedFinal01')]:
    step,checkpoint,onnx=row
    asset=root/f'Assets/Picklebot/PlayerLearning/Models/{model}.onnx'
    assert not asset.exists();shutil.copy2(onnx,asset)
    selection[name]=dict(model=model,step=step,modelHash=sha(onnx),checkpointHash=sha(checkpoint),checkpoint=str(checkpoint.relative_to(root)).replace('\\','/'),sourceIdentity=plan['sourceIdentity'])
    for condition in ['A','B','random']:
        code=(here/f'smooth-{condition}.cs').read_text(encoding='utf-8-sig')
        code=code.replace('ExecutionV1SmoothDistance01',model).replace('smooth-distance-01/evaluation','smooth-continued-01/evaluation')
        guard=f'''string expectedModelHash="{sha(onnx)}", expectedCheckpointHash="{sha(checkpoint)}";
string absoluteModelPath="F:/dev/picklebot/Assets/Picklebot/PlayerLearning/Models/{model}.onnx";
System.Func<string> actualModelHash=()=>{{using(var hash=System.Security.Cryptography.SHA256.Create())return System.BitConverter.ToString(hash.ComputeHash(System.IO.File.ReadAllBytes(absoluteModelPath))).Replace("-","").ToLowerInvariant();}};
if(actualModelHash()!=expectedModelHash)throw new System.InvalidOperationException("Selected model hash mismatch before evaluation");
'''
        code=code.replace('int region=',guard+'int region=',1)
        identity=f'''    if(actualModelHash()!=expectedModelHash)throw new System.InvalidOperationException("Selected model changed during evaluation");
    System.IO.File.WriteAllText(output+"/model-identity.json",Newtonsoft.Json.JsonConvert.SerializeObject(new{{model,modelHash=expectedModelHash,checkpointHash=expectedCheckpointHash,step={step},sourceIdentity="{plan['sourceIdentity']}"}}));
'''
        code=code.replace('    result=Newtonsoft.Json.JsonConvert.SerializeObject',identity+'    result=Newtonsoft.Json.JsonConvert.SerializeObject',1)
        (here/f'continued-{name}-{condition}.cs').write_text(code,encoding='utf-8',newline='\n')
for mode in ['prepare_scene','restore_editor']:
    code=(here/f'smooth-{mode}.cs').read_text(encoding='utf-8-sig').replace('smooth-distance-01/','smooth-continued-01/')
    (here/f'continued-{mode}.cs').write_text(code,encoding='utf-8',newline='\n')
with (base/'selected-models.json').open('x',encoding='utf-8') as f:json.dump(selection,f,indent=2)
print(json.dumps(selection,indent=2))

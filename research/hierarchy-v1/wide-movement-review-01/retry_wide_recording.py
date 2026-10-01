"""Preserve failed capture 01 and retry identical selection with terminal writer closure."""
from pathlib import Path
import hashlib,json,shutil

workspace=Path(__file__).resolve().parents[2]
old=workspace/'outputs/wide-movement-review-01'
out=workspace/'outputs/wide-movement-review-02'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
error=read(old/'error.json')
assert 'Sharing violation' in error['error'] and error['completedEpisodes']==512
assert not out.exists() and not (old/'complete.json').exists()
manifest=read(old/'manifest.json')
assert sha(old/'capture.cs')==manifest['captureScriptSha256']
code=(old/'capture.cs').read_text(encoding='utf-8-sig')
code=code.replace(old.as_posix(),out.as_posix())
needle='    string folder=System.IO.Path.Combine(destination,"evaluations","A");\n    WriteNew(System.IO.Path.Combine(folder,"first-decisions.json"),first);'
assert code.count(needle)==1
replacement='''    // The seed budget is complete: close only terminal evidence writers before
    // reading them. No more actions, physics ticks, rewards or runner steps occur.
    foreach(var holder in new object[]{run,goals})
    foreach(string name in new[]{"evidence","decisionEvidence"})
    {
        var writerField=holder.GetType().GetField(name,System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance);
        if(writerField?.GetValue(holder) is System.IO.StreamWriter writer)
        {writer.Dispose();writerField.SetValue(holder,null);}
    }
'''+needle
code=code.replace(needle,replacement)
out.mkdir()
for name in ['source-records.json','plan.json','fixture-summary.json','evaluation-analysis.json']:
    shutil.copy2(old/name,out/name)
(out/'capture.cs').write_text(code,encoding='utf-8',newline='\n')
manifest['captureScriptSha256']=sha(out/'capture.cs')
manifest['retryOf']=str(old)
manifest['retryReason']='Terminal exporter read before evidence writer disposal; simulation completed512, original failure preserved. Identical selected seeds, recipe, source, model and frame sampling.'
manifest['originalManifestSha256']=sha(old/'manifest.json')
manifest['originalErrorSha256']=sha(old/'error.json')
with (out/'manifest.json').open('x',encoding='utf-8') as h:json.dump(manifest,h,indent=2)
with (out/'revision.json').open('x',encoding='utf-8') as h:json.dump(dict(
    reason=manifest['retryReason'],script=Path(__file__).name,scriptSha256=sha(Path(__file__)),
    oldCaptureSha256=sha(old/'capture.cs'),newCaptureSha256=sha(out/'capture.cs'),
    selectionUnchanged=True,sourceChanged=False,newSeedsAllocated=False),h,indent=2)
print(json.dumps({'output':str(out),'clips':manifest['clipCount'],'captureSha256':sha(out/'capture.cs')}))

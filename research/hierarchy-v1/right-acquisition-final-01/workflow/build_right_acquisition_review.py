"""Build an offline before/after viewer only from verified actual Unity recordings."""
from pathlib import Path
import json,hashlib
W=Path(__file__).resolve().parent.parent.parent
B=W/'outputs/right-acquisition-review-01'
def read(p):return json.loads(p.read_text())
def main():
    assert not (B/'index.html').exists()
    data={};hashes={}
    for role in ['baseline','final']:
        root=B/role;complete=read(root/'complete.json');manifest=read(root/'manifest.json')
        assert complete['status']=='complete_verified_replay' and complete['matchesReference']==512 and complete['clips']==8
        clips=[]
        for seed in range(1109849,1109857):
            p=root/f'clips/A-{seed}/recording.json';record=read(p)
            assert record['matchesReference'] and record['episode']['seed']==seed
            frames=[{k:f[k] for k in ['tick','faceContact','netCrossed']} for f in record['frames']]
            for i in range(len(frames)):
                for view in [0,1]:assert (root/f'clips/A-{seed}/frame-{i:04d}-{view}.jpg').is_file()
            hashes[p.relative_to(B).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
            clips.append(dict(seed=seed,episode=record['episode'],frames=frames))
        first=read(root/'evaluations/A/first-decisions.json')
        distinct=len({tuple(v['observation'][:124]) for v in first.values()})
        assert len(first)==512 and distinct==8
        for clip in clips:
            assert [f['tick'] for f in clip['frames']]==list(range(0,12*len(clip['frames']),12)), 'Replay timing must be uniform from tick zero'
        data[role]=dict(clips=clips,checkpoint=manifest['checkpoint'],model=manifest['modelName'],summary=read(root/'evaluations/A/summary.json'),distinctStartingSituations=distinct)
    analysis_path=Path('F:/dev/picklebot/artifacts/hierarchy-v1/right-acquisition-01/results/analysis.json')
    analysis=read(analysis_path)
    retention={battery:{model:{c:dict(legal=x['legal'],attempts=x['attempts']) for c,x in v['counts'].items()} for model,v in result['groups']['all']['models'].items() if model in ('ExecutionV1SmoothContinuedFinal01','ExecutionV1RightAcquisitionFinal01')} for battery,result in analysis['batteries'].items()}
    hashes['fullRetentionAnalysis']=hashlib.sha256(analysis_path.read_bytes()).hexdigest()
    (B/'data.js').write_bytes(('window.REPLAY='+json.dumps(data,separators=(',',':'))+';window.RETENTION='+json.dumps(retention,separators=(',',':'))+';').encode())
    html='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Picklebot · Right-return comparison</title>
<style>body{margin:0;background:#101d25;color:#edf4f7;font:16px system-ui}main{max-width:1300px;margin:auto;padding:30px}h1{font-size:34px;margin-bottom:8px}p{color:#bacbd5;line-height:1.5}label{display:block;margin:22px 0 8px}select,button{padding:10px;background:#203744;color:white;border:1px solid #69828e;border-radius:6px}section{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:20px}article{background:#182c36;padding:15px;border-radius:12px}img{display:block;width:100%;background:#091015;margin-top:10px}h2{font-size:22px;margin:0}small{color:#b9ccd4}input{width:100%;margin-top:18px}#status{min-height:24px}.controls{display:flex;gap:12px;align-items:center;margin-top:16px}@media(max-width:700px){section{grid-template-columns:1fr}main{padding:15px}}</style>
<main><small>PICKLEBOT · ACTUAL UNITY RECORDINGS</small><h1>Learning the rightward return</h1><p>The same 25 cm feed and target, before and after concentrated practice. Eight cases cover both rally feed types and all four player positions. They were selected before final results. These clips demonstrate this drill; they do not establish full-game readiness or retention.</p>
<label for="case">Recorded case</label><select id="case"></select><div class="controls"><button id="play">Play</button><button id="restart">Restart</button><span id="time"></span></div><input id="seek" type="range" min="0" value="0" step="1" aria-label="Replay position"><p id="status"></p>
<section><article><h2>Preserved baseline</h2><p id="baseline-score"></p><small id="baseline-model"></small><img id="baseline-court" alt="Baseline full court recording"><img id="baseline-close" alt="Baseline paddle and body recording"></article><article><h2>Acquisition checkpoint</h2><p id="final-score"></p><small id="final-model"></small><img id="final-court" alt="Acquisition full court recording"><img id="final-close" alt="Acquisition paddle and body recording"></article></section><p>Each score covers all 512 target-A test attempts, not just the displayed examples. Playback is synchronized by simulation time; a finished attempt holds its last recorded frame.</p></main><script src="data.js"></script><script src="review.js"></script></html>'''
    html=html.replace('Each score covers all 512 target-A test attempts, not just the displayed examples.', 'Each score covers all 512 target-A test attempts: eight distinct starting situations repeated 64 times each, not 512 different challenges. The clips show each of those eight situations once.')
    html=html.replace('<label for="case">','<aside style="border-left:4px solid #e6b366;padding:12px 18px;background:#29302c"><strong>Acquired this drill; earlier skills regressed.</strong><p id="retention"></p><p>This checkpoint is preserved for diagnosis and is not promoted as the shared player policy. Target-following and broader movement remain unresolved.</p></aside><label for="case">')
    (B/'index.html').write_bytes(html.encode())
    js='''const $=id=>document.getElementById(id),roles=['baseline','final'];let choice=0,frame=0,playing=false,last=0;
for(let i=0;i<8;i++){let c=REPLAY.baseline.clips[i],o=document.createElement('option');o.value=i;o.textContent=`${c.episode.task==='rally-air-feed'?'Air feed':'Bounce feed'} · Player ${c.episode.player+1} · Seed ${c.seed}`;$('case').append(o)}
for(const r of roles){let d=REPLAY[r];$(r+'-score').textContent=`${d.summary.legal}/512 legal returns · ${d.summary.targets}/512 target hits`;$(r+'-model').textContent=`Checkpoint ${d.checkpoint.toLocaleString()}`}
function draw(){let texts=[];for(const r of roles){let c=REPLAY[r].clips[choice],i=Math.min(frame,c.frames.length-1),f=c.frames[i],base=`${r}/clips/A-${c.seed}/frame-${String(i).padStart(4,'0')}`;$(r+'-court').src=base+'-0.jpg';$(r+'-close').src=base+'-1.jpg';texts.push(`${r==='baseline'?'Before':'After'}: ${i===c.frames.length-1?c.episode.outcome.replaceAll('_',' '):f.netCrossed?'crossed net':f.faceContact?'paddle contact':'tracking / swinging'}`)}$('status').textContent=texts.join(' · ');$('time').textContent=(frame/20).toFixed(2)+' s';$('seek').value=frame}
function reset(){playing=false;$('play').textContent='Play';frame=0;$('seek').max=Math.max(...roles.map(r=>REPLAY[r].clips[choice].frames.length))-1;draw()}
$('case').onchange=()=>{choice=+$('case').value;reset()};$('restart').onclick=reset;$('seek').oninput=()=>{playing=false;$('play').textContent='Play';frame=+$('seek').value;draw()};$('play').onclick=()=>{playing=!playing;last=0;$('play').textContent=playing?'Pause':'Play'};
function animate(t){if(playing&&(!last||t-last>=50)){last=t;frame=Math.min(frame+1,+$('seek').max);draw();if(frame>=+$('seek').max){playing=false;$('play').textContent='Play'}}requestAnimationFrame(animate)}reset();requestAnimationFrame(animate);'''
    js+='\n$("retention").textContent=Object.entries(RETENTION).map(([battery,models])=>Object.keys(models.ExecutionV1SmoothContinuedFinal01).map(c=>{let a=models.ExecutionV1SmoothContinuedFinal01[c],b=models.ExecutionV1RightAcquisitionFinal01[c];return `${battery} ${c}: ${a.legal}/${a.attempts} before → ${b.legal}/${b.attempts} after`}).join("; ")).join(". ");\n'
    (B/'review.js').write_bytes(js.encode())
    (B/'viewer-provenance.json').write_bytes(json.dumps(dict(recordingHashes=hashes,actualUnityFrames=True,visualInspectionPending=True,masteryAccepted=False),indent=2).encode())
    print(B/'index.html')
if __name__=='__main__':main()

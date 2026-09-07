"""Verify retained competition evidence against the current models and source."""
import hashlib
import json
from pathlib import Path
import statistics

ROOT=Path(__file__).resolve().parents[1]
runtime=ROOT/'Assets/Picklebot/Competition'
files=list(runtime.glob('*.cs'))+[ROOT/'Assets/Picklebot/Rally/RallyRules.cs',ROOT/'Assets/Picklebot/Rally/RallyNeuralPolicy.cs']
source='\n'.join(str(p.relative_to(ROOT))+'\n'+p.read_text() for p in sorted(files))
source_hash=hashlib.sha256(source.encode()).hexdigest()
hashes={name:hashlib.sha256((runtime/'Models'/f'{name}.json').read_bytes()).hexdigest() for name in ['stroke','strategy']}
for name,trainer in [('stroke','competition-skill-train.py'),('strategy','competition-train.py')]:
    manifest=json.loads((runtime/'Models'/f'{name}.manifest.json').read_text())
    assert manifest['model_sha256']==hashes[name],f'Stale {name} model manifest'
    assert manifest['trainer_sha256']==hashlib.sha256((ROOT/'scripts'/trainer).read_bytes()).hexdigest(),f'Stale {name} trainer manifest'
assert manifest['stroke_sha256']==hashes['stroke']
assert manifest['training_seed_end']<840000
reports={}
for label,count in [('self-final',100),('near-final',100),('far-final',100),('centre-final',20)]:
    r=json.loads((ROOT/'artifacts/competition'/f'{label}.json').read_text())
    assert r['runtimeSha256']==source_hash,'Stale runtime evidence'
    assert r['strokeSha256']==hashes['stroke'],'Stale stroke evidence'
    assert r['strategySha256']==('none' if label=='centre-final' else hashes['strategy']),'Stale strategy evidence'
    points=r['points'];assert len(points)==count
    assert [p['seed'] for p in points]==list(range(840000,840000+count))
    for p in points:
        assert p['winner'] in [-1,0,1]
        assert (p['winner']==0)==p['result'].startswith('Time cap')
        events=p['events'];server=1 if p['seed']%2==0 else -1
        if p['returns']:
            assert [e.split()[1] for e in events[:2]]==['Table','Table']
            assert [1 if float(e.split()[2].split(',')[2])>0 else -1 for e in events[:2]]==[server,-server]
        for i in range(p['returns']):
            paddle,landing=events[2+2*i:4+2*i]
            expected='PaddleNear' if -server*(-1)**i<0 else 'PaddleFar'
            assert paddle.split()[1]==expected and landing.split()[1]=='Table'
            x,y,z=map(float,landing.split()[2].split(','))
            assert abs(x)<=.91 and (1 if z>0 else -1)==server*(-1)**i
        for d in p['decisions']:assert len(d['observation'])==8 and d['action'] in range(5)
    reports[label]=points
selfplay=reports['self-final'];centre=reports['centre-final']
near_wins=sum(p['winner']==-1 for p in reports['near-final'])
far_wins=sum(p['winner']==1 for p in reports['far-final'])
assert near_wins>=70 and far_wins>=70,'Policy does not beat the centre opponent on both sides'
assert sum(p['returns']>=1 for p in selfplay)>=90,'Too many points fail before a legal return'
assert sum(p['result']=='Miss or out' and p['returns']>0 for p in selfplay)>=80,'Points do not end through missed legal returns'
travel=statistics.mean(sum(p['travel']) for p in selfplay)
baseline_travel=statistics.mean(sum(p['travel']) for p in centre)
assert travel>baseline_travel*1.5,'No clear increase in paddle movement'
actions=[d['action'] for p in selfplay for d in p['decisions']]
assert len(set(actions))>=2,'Only one shot choice used'
for name,count in [('competition-tests',5),('physics-tests',2),('rally-tests',7)]:
    tests=json.loads((ROOT/'artifacts/competition'/f'{name}.json').read_text())
    assert tests['status']=='completed' and tests['summary']['passed']>=count and tests['summary']['failed']==0
repeat=json.loads((ROOT/'artifacts/competition/repeat-final.json').read_text())
assert repeat['runtimeSha256']==source_hash and repeat['strategySha256']==hashes['strategy']
assert repeat['points']==selfplay[:3],'Point replay changed'
summary=dict(verified=True,near_wins_out_of_100=near_wins,far_wins_out_of_100=far_wins,
    self_play_mean_returns=statistics.mean(p['returns'] for p in selfplay),
    self_play_mean_total_lateral_travel_m=travel,centre_mean_total_lateral_travel_m=baseline_travel,
    self_play_action_counts={str(a):actions.count(a) for a in range(5)},
    self_play_results={r:sum(p['result']==r for p in selfplay) for r in sorted({p['result'] for p in selfplay})},
    source_sha256=source_hash,model_sha256=hashes)
print(json.dumps(summary,indent=2))
(ROOT/'artifacts/competition/verification.json').write_text(json.dumps(summary,indent=2))

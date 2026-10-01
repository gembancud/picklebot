"""Descriptive within-run windows; not fixed-checkpoint evaluation or iid intervals."""
from pathlib import Path
import json,hashlib
R=Path('F:/dev/picklebot');B=R/'artifacts/hierarchy-v1/precontact-alignment-01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    inputs={};workers=[]
    for w in range(8):
        p=B/f'training/worker-{w:02}/episodes.jsonl';inputs[p.relative_to(R).as_posix()]=sha(p)
        workers.append([json.loads(s) for s in p.read_text().splitlines()])
    def count(rows):
        wins=sum(x['outcome']=='legal_return' for x in rows)
        return dict(legal=wins,attempts=len(rows),rate=wins/len(rows) if rows else None)
    windows=[]
    for j in range(min(map(len,workers))//512):
        rows=sum([w[j*512:(j+1)*512] for w in workers],[])
        focus=[x for x in rows if x['movementPattern']=='axes'];hard=[x for x in focus if x['movementRange']==.0625]
        windows.append(dict(ordinal=j,episodesPerWorker=[j*512,(j+1)*512],focus=count(focus),nominal25cm=count(hard),directions25cm={name:count([x for x in hard if x['movementRegion']==region]) for region,name in [(3,'left'),(5,'right'),(1,'shallow'),(7,'deep')]}))
    result=dict(windows=windows,inputs=inputs,excludedTailEpisodesByWorker=[len(w)-512*len(windows) for w in workers],scope='Changing policy and sampled actions during training; contiguous512 completed episodes per worker, approximate mixture balance. These are not equal optimizer-step windows or fixed-checkpoint held-out tests.',interpretation='25cm legal rates remain around37-41% without sustained improvement; right25cm roughly1-8%. Recipe-specific observed stall, not proof of model capacity exhaustion or futility of all longer training.',scriptHash=sha(Path(__file__)))
    with (B/'results/learning-windows.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(windows,indent=2))
if __name__=='__main__':main()

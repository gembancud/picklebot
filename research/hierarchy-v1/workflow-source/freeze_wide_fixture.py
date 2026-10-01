from pathlib import Path
import shutil, hashlib, json
here = Path(__file__).resolve().parent
base = Path('F:/dev/picklebot/artifacts/hierarchy-v1/wide-movement-fixture-01')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
files = [here / f'wide-fixture-{i:04}.json' for i in range(0,512,64)]
assert all(p.is_file() for p in files)
assert not (base/'fixture').exists() and not (base/'fixture-hashes.json').exists()
all_rows=[]
for path in files:
    result=json.loads(path.read_text(encoding='utf-8-sig'))
    assert result['policyActions']==result['physicsTicks']==result['rewardsCollected']==0
    assert len(result['rows'])==64 and result['seedCount']==512
    all_rows.extend(result['rows'])
assert len(all_rows)==512 and len({row['seed'] for row in all_rows})==512
(base/'fixture').mkdir()
hashes={}
for path in files:
    target=base/'fixture'/path.name
    shutil.copy2(path,target)
    assert sha(target)==sha(path)
    hashes[path.name]=sha(path)
with (base/'fixture-hashes.json').open('x',encoding='utf-8') as handle: json.dump(hashes,handle,indent=2)
print(json.dumps(dict(resets=len(all_rows),overlapRows=sum(bool(row['overlaps']) for row in all_rows),
    challengeRows=sum(row['challenge'] for row in all_rows),sourceUnchanged=True,policyOutcomesObserved=False)))

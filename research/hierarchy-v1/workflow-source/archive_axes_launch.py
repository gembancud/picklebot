from pathlib import Path
import hashlib,json,shutil
root=Path('F:/dev/picklebot');src=root/'artifacts/hierarchy-v1/axes-recovery-01/training'
dest=root/'docs/research/execution-v1-evidence/axes-recovery-01/launch'
assert not dest.exists();dest.mkdir()
records={}
for name in ['launch.json','manifest.json','process.json','resume-load-proof.json','status-remap.json']:
    a=src/name;b=dest/name;shutil.copy2(a,b)
    ha=hashlib.sha256(a.read_bytes()).hexdigest();assert hashlib.sha256(b.read_bytes()).hexdigest()==ha
    records[name]=ha
with (dest/'archive-manifest.json').open('x',encoding='utf-8') as h:
    json.dump({'status':'launched_with_verified_resume','files':records,'performanceEvaluated':False,'masteryAccepted':False},h,indent=2)
print('Verified resume and launch metadata preserved.')

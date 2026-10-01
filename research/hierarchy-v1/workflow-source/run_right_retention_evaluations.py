from pathlib import Path
import subprocess,json,time,hashlib,os
W=Path(__file__).resolve().parent
B=Path('F:/dev/picklebot/artifacts/hierarchy-v1/right-retention-01')
out=B/'evaluation-process';assert not out.exists();out.mkdir()
def write(name,obj):
    with (out/name).open('x') as f:json.dump(obj,f,indent=2)
write('started.json',dict(pid=os.getpid(),started=time.time()))
cli='C:/Users/Admin/AppData/Local/Unity/bin/unity.exe'
scripts=[f'acquisition-matched-ExecutionV1RightRetentionFinal01-{c}.cs' for c in ['A','B']]+[f'right-retention-final-{b}-{c}.cs' for b,c in [('narrow','A'),('narrow','B'),('narrow','random'),('wide','A'),('wide','B')]]
write('plan.json',dict(scripts={s:hashlib.sha256((W/s).read_bytes()).hexdigest() for s in scripts}))
for i,s in enumerate(scripts):
    start=time.time();p=subprocess.run([cli,'command','eval_file',str(W/s),'180000','--timeout','240','--project-path','F:/dev/picklebot','--format','json'],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
    write(f'{i:02}-result.json',dict(script=s,exitCode=p.returncode,seconds=time.time()-start,stdout=p.stdout,stderr=p.stderr))
    assert p.returncode==0,(s,p.stdout,p.stderr)
    result=json.loads(p.stdout)
    assert result['success'] and result['data']['success'] and result['data']['result']['success'],result
    print(s,result['data']['result']['result'],flush=True)
write('complete.json',dict(completed=len(scripts),finished=time.time(),promoted=False))

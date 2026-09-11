from pathlib import Path
import json,hashlib,os,subprocess,time,sys
root=Path('F:/dev/picklebot');base=root/'artifacts/player-v3'
name='movement-receive-01'
run=base/'movement-receive-train-01';read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
launch=read(run/'launch.json');manifest=read(run/'manifest.json');source=read(run/'source-records.json')
assert all(sha(root/n)==h for n,h in source['files'].items())
assert sha(root/launch['config'])==launch['configHash'] and sha(run/'manifest.json')==launch['manifestHash']
assert not (run/'trainer-process.json').exists()
assert all(not (run/f'worker-{i:02}/worker-startup.json').exists() for i in range(launch['workers']))
build=read(base/'stability-source-01/build-verification.json')
assert all(sha(base/'headless-build-53'/n)==h for n,h in build['files'].items())
trainer=root/'artifacts/mlagents'/name
assert all(sha(trainer/n)==h for n,h in launch['cloneFiles'].items())
assert sha(trainer/'clone-provenance.json')==launch['cloneProvenanceHash']
assert all(sha(root/launch['parentTrainer']/n)==h for n,h in launch['sourceFiles'].items())
wrapper=Path('__PICKLEBOT_DIAGNOSTICS_WRAPPER__')
assert wrapper.is_absolute() and wrapper.is_file(), 'Frozen diagnostic wrapper missing'
assert sha(wrapper)==read(wrapper.parent/'script-hashes.json')[wrapper.name]
args=[str(root/'tools/mlagents-training/.pixi/envs/default/python.exe'),str(wrapper),str(root/launch['config']),'--resume','--run-id',name,'--results-dir',str(root/'artifacts/mlagents'),'--seed',str(launch['trainingRngSeed']),'--env',str(base/'headless-build-53/Picklebot.exe'),'--num-envs',str(launch['workers']),'--base-port',str(manifest['basePort']),'--no-graphics','--timeout-wait','180','--max-lifetime-restarts','0','--env-args','--picklebot-manifest',str(run/'manifest.json')]
child_env=os.environ.copy();child_env['PICKLEBOT_DIAGNOSTIC_OUTPUT']=str(run/'optimizer-buffers.jsonl')
package=read(run/'trainer-package.json')
target=Path(package['target'])
assert target.is_dir()
child_env['PYTHONPATH']=str(target)+(os.pathsep+child_env['PYTHONPATH'] if child_env.get('PYTHONPATH') else '')
child_env['PICKLEBOT_PACKAGE_RECORD']=str(run/'trainer-package.json')
startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
started=time.perf_counter();utc=time.time()
with (run/'trainer-console.log').open('x',encoding='utf-8') as log:
    p=subprocess.Popen(args,cwd=root,stdout=log,stderr=subprocess.STDOUT,startupinfo=startup,creationflags=subprocess.CREATE_NO_WINDOW,env=child_env)
    with (run/'trainer-process.json').open('x') as f:json.dump(dict(pid=p.pid,args=args,startUnixSeconds=utc),f,indent=2)
    print(f'{name} trainer PID {p.pid}',flush=True)
    code=p.wait()
with (run/'trainer-process-result.json').open('x') as f:json.dump(dict(pid=p.pid,exitCode=code,wallSeconds=time.perf_counter()-started,endUnixSeconds=time.time()),f,indent=2)
print(f'{name} exit {code}',flush=True)
sys.exit(code)

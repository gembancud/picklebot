from pathlib import Path
import subprocess,hashlib
root=Path('F:/dev/picklebot')
state=root/'docs/CURRENT_STATE.md'
old=subprocess.check_output(['git','-c','safe.directory=F:/dev/picklebot','-C',str(root),'show','HEAD:docs/CURRENT_STATE.md'])
current=state.read_text(encoding='utf-8-sig')
marker='# Active drill-mastery goal — two-region screen complete'
assert current.count(marker)==1 and old.decode('utf-8-sig').startswith(marker)
state.write_bytes(current.split(marker)[0].encode('utf-8')+old)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name,canonical in [('goal_path_diagnostic.json','goal-path-diagnostic.json'),('training-target-coverage.json','training-target-coverage.json')]:
    duplicate=root/'research/hierarchy-v1/smooth-distance-01'/name
    retained=root/'docs/research/execution-v1-evidence/smooth-distance-01'/canonical
    assert duplicate.resolve().is_relative_to(root.resolve()) and sha(duplicate)==sha(retained)
    subprocess.run(['git','-c','safe.directory=F:/dev/picklebot','-C',str(root),'restore','--staged','--',str(duplicate.relative_to(root))],check=True)
    duplicate.unlink()
print('Preserved historical document bytes and retained one canonical copy of each raw diagnostic.')

from pathlib import Path
import json,hashlib,subprocess,ast,shutil
R=Path('F:/dev/picklebot');W=Path(__file__).resolve().parent;A=R/'research/hierarchy-v1/right-acquisition-final-01'
fix=A/'encoding-amendment';assert not fix.exists();fix.mkdir()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
report=R/'docs/research/execution-v1-right-acquisition-final.md';state=R/'docs/CURRENT_STATE.md';goal=R/'docs/DRILL_MASTERY_GOAL.md'
for p in [report,state,goal]:shutil.copyfile(p,fix/(p.name+'.before'))
# Only undo the accidental cp1252 decoding introduced by these two new archive
# helpers. Restore historical CURRENT_STATE bytes from the pre-helper commit.
s=report.read_text(encoding='utf-8');repaired=s.encode('cp1252').decode('utf-8');assert '128×2' in repaired and ' → ' in repaired;report.write_bytes(repaired.encode())
old=subprocess.check_output(['git','-c','safe.directory=F:/dev/picklebot','-C',str(R),'show','12be95b:docs/CURRENT_STATE.md'])
prefix,sep,_=state.read_bytes().partition(b'---\n\n');assert sep and b'rightward acquisition finished' in prefix
tree=ast.parse((W/'archive_right_acquisition_final.py').read_text(encoding='utf-8'))
head=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='head' for t in n.targets))
state.write_bytes(head.encode()+prefix+sep+old)
s=goal.read_text(encoding='utf-8');start=s.index('Current work:');end=s.index('\n\nApp status:',start)
s=s[:start]+'Current work: Rightward acquisition completed at 2,097,175 with all seven evaluations. It learned the eight canonical rightward 25 cm cases but lost earlier skills, including serving. The checkpoint is preserved without promotion. Next prepare a maintenance-plus-concentrated-rightward experiment from the common parent, validating reset coverage before launch. Broader mastery, useful target following and acceptance thresholds remain unproven; final seeds are unused. [Completed comparison](research/execution-v1-right-acquisition-final.md).'+s[end:];goal.write_bytes(s.encode())
shutil.copyfile(W/'archive_right_acquisition_final.py',fix/'archive_right_acquisition_final-fixed.py')
shutil.copyfile(Path(__file__),fix/Path(__file__).name)
(fix/'amendment.json').write_bytes(json.dumps(dict(reason='Platform-default cp1252 decoding failed while finalizing CURRENT_STATE and mangled the new report. Raw archive copied before failure; no simulations or models changed. Explicit UTF-8 correction, with original failed helper and before bytes retained.',restoredHistoricalStateCommit='12be95b',afterHashes={p.relative_to(R).as_posix():sha(p) for p in [report,state,goal]}),indent=2).encode())
print('Archive finalized; raw evidence unchanged')

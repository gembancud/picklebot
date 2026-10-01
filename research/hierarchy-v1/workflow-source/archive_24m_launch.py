from pathlib import Path
import shutil,json
R=Path('F:/dev/picklebot');W=Path(__file__).parent;A=R/'artifacts/hierarchy-v1/randomized-scale-24m'
D=R/'research/hierarchy-v1/randomized-scale-24m';D.mkdir()
for name in ['run_randomized_24m.py','evaluate_randomized_24m.py']:shutil.copyfile(W/name,D/name)
for rel in ['training/config.yaml','training/manifest.json','training/resume-load-proof.json','training/launch.json','training/process.json','evaluation-process/plan.json']:
 dest=D/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(A/rel,dest)
state=R/'docs/CURRENT_STATE.md';old=state.read_bytes();(D/'current-state-before.md').write_bytes(old)
state.write_bytes(b'# Active update:24-million-step continuation launched\n\nRun `execution-randomized-scale-24m` resumes the completed randomized256x2 run at8000058, targeting24000000 with unchanged curriculum/rewards and exact restored actor/critic/normalizers/Adam.8workers x16courts; frozen development evaluation every2million. Original8m run and7m retention reference preserved. Training resets and RNG streams restart on reused training-only seeds; this is not a bitwise rollout continuation. See artifacts/hierarchy-v1/randomized-scale-24m for current processes, logs, checkpoint and evaluation completion. No promotion or final-test use. Older status entries below are historical.\n\n'+old)
print('24m continuation launch and exact resume proof archived.')

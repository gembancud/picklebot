from pathlib import Path
import json,shutil,hashlib
root=Path('F:/dev/picklebot');here=Path(__file__).parent
base=root/'artifacts/hierarchy-v1/smooth-continued-01'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
proof=read(base/'training/resume-load-proof.json')
assert proof['globalStep']==262179 and proof['actorCriticNormalizersAndAdamExact']
log=(base/'training/trainer-console.log').read_text(encoding='utf-8-sig')
assert 'Resuming training from step 262179.' in log
workflow=root/'research/hierarchy-v1/smooth-continued-01';workflow.mkdir(exist_ok=False)
for name in ['prepare_smooth_continuation.py','prepare_continuation_evaluation.py','analyze_smooth_continuation.py']:
    shutil.copy2(here/name,workflow/name)
shutil.copy2(root/'tools/mlagents-training/run_smooth_continuation.py',workflow/'run_smooth_continuation.py')
for name in ['plan.json']:shutil.copy2(base/name,workflow/name)
for name in ['launch.json','resume-load-proof.json','status-remap.json','parent-result-inputs.json']:
    shutil.copy2(base/'training'/name,workflow/name)
(workflow/'README.md').write_text('''# Bounded smooth-placement continuation

The completed 262,179-experience smooth policy retained legal returns but failed useful target following. First-decision diagnostics found correct target encodings, normalization and learned goal sensitivity. This run tests more experience with the same physical curriculum and reward recipe.

The maintained ML-Agents trainer resumes actor, critic, normalizers, Adam and global step from an isolated copy. `init_path` is removed so it cannot override resume. Checkpoint-manager paths are remapped to protect the completed parent. The actual trainer confirmed step 262,179; a separate installed-loader preflight matched all registered state exactly. Live simulation, unfinished rollouts and process RNG progression restart.

Target: 1,048,576 total experiences, eight workers × sixteen courts. The nearest retained checkpoint to 524,288 (within 8,192, lower step on a tie) and the final checkpoint are selected by step before observing their performance. All are evaluated on the same A/B/random development anchor. The midpoint describes learning progress; it does not replace the fixed final candidate. No automatic promotion or mastery acceptance.

The plan, launcher and resume proof are saved here. Runtime results remain under `artifacts/hierarchy-v1/smooth-continued-01`. Source/build identity is unchanged from the smooth-distance experiment. No final seeds are consumed. Wider positioning and varied rule-context coverage remain open requirements.
''',encoding='utf-8',newline='\n')
state=root/'docs/CURRENT_STATE.md'
text=state.read_text(encoding='utf-8-sig')
text=text.replace('The task-owned evaluation Editor is closed and no training is running. Next: inspect normalization and motor-command sensitivity to the goal before deciding between longer unchanged training and a targeted integration change.',
'The input diagnostic passed for recorded first decisions. A bounded unchanged continuation, `execution-smooth-continued-01`, is now running toward 1,048,576 total experiences on 128 courts. The installed loader matched the complete saved state and the trainer confirmed resume at step 262,179. Midpoint and final checkpoint selection are fixed before evaluation. The task-owned evaluation Editor is closed.')
state.write_text(text,encoding='utf-8',newline='\n')
goal=root/'docs/DRILL_MASTERY_GOAL.md'
text=goal.read_text(encoding='utf-8-sig').replace('Diagnose the goal-to-command path before the next training decision.',
'The first-decision goal-path diagnostic passed; a bounded unchanged continuation to roughly 1M experiences tests whether more training develops useful target following.')
goal.write_text(text,encoding='utf-8',newline='\n')
print('Saved plan, resume proof, scripts and active run status.')

from pathlib import Path
import json, shutil

root=Path('F:/dev/picklebot');here=Path(__file__).parent
state=root/'docs/CURRENT_STATE.md'
header='''# Active drill-mastery goal — smooth placement screen complete

The smooth-distance experiment completed at **262,179 experiences**, with 20 Unity checks passing and 768 frozen-policy attempts. It preserved legal returns but failed the predeclared aiming screen. On the same 256 resets, initializer → candidate target hits were A **117 → 109**, B **4 → 18**, and random **75 → 65**. Legal landings were **228 → 228/229/229** respectively.

Changing the requested region produced a negative assignment gain of **−0.04883** (paired 95% interval **[−0.078125, −0.021484]**). This is one short training run on reused development cases; no model was promoted and mastery is not accepted. Both target instructions appeared in all 440 recorded training reset-descriptor cells, so gross assignment imbalance does not explain the result.

The task-owned evaluation Editor is closed and no training is running. Next: inspect normalization and motor-command sensitivity to the goal before deciding between longer unchanged training and a targeted integration change. Wide/deep/shallow positioning, varied mandatory-bounce receiving and kitchen-boundary behavior remain separate coverage gaps.

[Experiment and evidence](research/execution-v1-smooth-distance.md) · [Coverage audit](research/drill-mastery-coverage.md) · [Active goal](DRILL_MASTERY_GOAL.md)

---
'''
old=state.read_text(encoding='utf-8-sig')
assert not old.startswith('# Active drill-mastery goal — smooth')
state.write_text(header+'\n'+old,encoding='utf-8')

goal=root/'docs/DRILL_MASTERY_GOAL.md'
text=goal.read_text(encoding='utf-8-sig')
text=text.replace('Immediate work: verify the two-region placement implementation, establish its baseline, run a bounded learning experiment with familiar-skill rehearsal, then evaluate placement and retention together. Movement-goal and strategy training remain later stages.',
'Current work: two-region and smooth-distance placement experiments retained legality but did not establish target following. Diagnose the goal-to-command path before the next training decision. Keep the existing recovery screen as an anchor and expand development coverage for varied required-bounce receiving, explicit kitchen behavior and measured lateral/deep/shallow positioning. [Coverage audit](research/drill-mastery-coverage.md). Movement-goal and strategy training remain later stages.')
goal.write_text(text,encoding='utf-8')

design=root/'docs/HIERARCHICAL_CONTROL.md'
text=design.read_text(encoding='utf-8-sig')
text=text.replace('Maximum bonus is 0.25; it decreases linearly to zero at the target radius. Existing legal-hit rewards remain. Misses, illegal hits and illegal serves receive no placement bonus. Target circles near boundaries are effectively clipped by court legality.',
'Maximum bonus is 0.25. The default `linear-radius` mode decreases linearly to zero at the target radius. An opt-in `smooth-distance-2m` experiment pays `0.25 × exp(−distance / 2 m)` for legal landings, including legal target misses. Both modes keep the same target-hit radius and existing legal-hit rewards. Attempts without a legal landing receive no placement bonus. Target circles near boundaries are effectively clipped by court legality.')
text=text.replace('`TargetHitGivenLegal`, and `LandingDistanceGivenLegal`.', '`TargetHitGivenLegal`, `LandingDistanceGivenLegal`, and `PlacementBonus`.')
text+='\n[Smooth-distance experiment](research/execution-v1-smooth-distance.md): denser feedback preserved legality but failed paired target following after 262,179 experiences. Nonzero placement bonus is not target success. No executor promotion.\n'
design.write_text(text,encoding='utf-8')

coverage=(here/'mastery-coverage.md').read_text(encoding='utf-8-sig')
coverage=coverage.replace('Smooth-placement experiment is still a separate pending test at audit time.', 'The later smooth-distance screen also failed target following; see the smooth-distance report. Neither result establishes physical infeasibility.')
(root/'docs/research/drill-mastery-coverage.md').write_text(coverage,encoding='utf-8')
for name in ['training_target_coverage.py','training-target-coverage.json']:
    shutil.copy2(here/name,root/'research/hierarchy-v1/smooth-distance-01'/name)
shutil.copy2(here/'training-target-coverage.json',root/'docs/research/execution-v1-evidence/smooth-distance-01/training-target-coverage.json')
report=root/'docs/research/execution-v1-smooth-distance.md'
text=report.read_text(encoding='utf-8')
text+='\nTraining coverage audit: all 440 recorded reset-descriptor cells saw both instructions (3,722 A and 3,747 B attempts). 157 cells produced at least one legal landing in each region across the changing stochastic policies. Descriptor cells do not establish exact physical-state identity, and this is not frozen-policy competence. [Coverage data and input hashes](execution-v1-evidence/smooth-distance-01/training-target-coverage.json).\n'
report.write_text(text,encoding='utf-8')
print('Updated current state, design, active goal, coverage and training audit.')

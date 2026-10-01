from pathlib import Path
import json

root = Path('F:/dev/picklebot')
result = json.loads((root / 'artifacts/hierarchy-v1/fresh-placement-01/audit/analysis.json').read_text(encoding='utf-8-sig'))
assert result['status'] == 'complete_fresh_development_screen'
assert result['screen']['promising'] is False
assert result['novelty']['exactNovelResets'] == 62
assert result['promoted'] is False and result['masteryAccepted'] is False
assert (root / 'docs/research/execution-v1-fresh-placement.md').exists()

path = root / 'docs/CURRENT_STATE.md'
old = path.read_text(encoding='utf-8-sig')
assert old.startswith('# Active drill-mastery goal — longer training produces partial target response')
new = '''# Active drill-mastery goal — fresh placement comparison complete

The frozen **1,048,609-experience executor** and initializer each completed 768 attempts on a newly reserved development cohort. Initializer → candidate target hits were **A 115 → 96**, **B 3 → 33**, and **random 65 → 77**, out of 256 per condition. Legal landings were **235 → 234/235/235** respectively.

Changing the requested region produced positive assignment gain: **0.06055**, paired 95% interval **[0.02734, 0.09180]**. Giving equal weight to each distinct initial physical observation also gave a positive interval. However, 194 resets repeated earlier observations; the 62 that differed did not show a clear response. These are differences from the earlier evaluation anchor, not proof of unseen training situations.

The full predeclared screen **failed**. A-target accuracy stayed below the initializer, and required-bounce receiving under A fell from **14/16 to 13/16**, exceeding the five-percentage-point point-estimate tolerance. That one extra miss has wide uncertainty; it does not by itself establish a reliable regression. B-target hits remain **0/112 for airborne feeds** and **0/16 for required-bounce receiving**. Serves remained legal **16/16**, but A-target serves fell **16/16 → 0/16**. No model promotion or mastery acceptance.

No training or task-owned Editor remains active. Next, broaden the frozen comparison to left/right/shallow/deep feeds with measured root travel, then use the per-skill results to choose the next bounded training stage. A reset-only axes fixture is prepared but has not been executed or allocated seeds. Varied rule contexts, paired teamwork and learned strategy remain unfinished. Final acceptance seeds remain untouched.

[Latest result](research/execution-v1-fresh-placement.md) · [Remaining coverage](research/drill-mastery-coverage.md) · [Active goal](DRILL_MASTERY_GOAL.md)

---
'''
path.write_text(new + old, encoding='utf-8')

path = root / 'docs/DRILL_MASTERY_GOAL.md'
old = path.read_text(encoding='utf-8-sig')
start = old.index('Current work:')
end = old.index('\n\nApp status:', start)
new = ('Current work: the frozen 1,048,609-experience executor completed the fresh placement comparison. '
       'Positive aggregate target responsiveness persisted, but the predeclared screen failed: A-target accuracy remained below the initializer and A-required-bounce receiving had one additional miss in 16 attempts. '
       'The 62 resets with observations different from the earlier anchor did not establish a clear target response. '
       'Broaden the frozen comparison to explicit lateral/deep/shallow movement with measured root travel before choosing the next bounded training stage; keep the current anchor for retention. '
       'Varied mandatory-bounce receiving and deliberate kitchen behavior remain coverage gaps. '
       '[Latest result](research/execution-v1-fresh-placement.md) · [Coverage audit](research/drill-mastery-coverage.md). '
       'Movement-goal and strategy training remain later stages.')
path.write_text(old[:start] + new + old[end:], encoding='utf-8')

path = root / 'docs/HIERARCHICAL_CONTROL.md'
old = path.read_text(encoding='utf-8-sig')
assert 'execution-v1-fresh-placement.md' not in old
path.write_text(old.rstrip() + '\n\n[Fresh frozen comparison](research/execution-v1-fresh-placement.md): target responsiveness persisted mainly on repeated physical setups. Balanced aiming and broader movement remain unproven; the predeclared screen failed, including one extra required-bounce receiving miss in a small sample. No executor promotion.\n', encoding='utf-8')

path = root / 'docs/research/drill-mastery-coverage.md'
old = path.read_text(encoding='utf-8-sig')
assert '## Fresh placement follow-up' not in old
path.write_text(old.rstrip() + '''

## Fresh placement follow-up

The [fresh comparison](execution-v1-fresh-placement.md) completed both frozen models on a newly reserved 256-reset cohort under the same recipe. It contained 150 unique initial physical observations; 194 resets (90 unique observations) matched the earlier anchor and 62 resets (60 unique observations) differed. Nearest-prior feature differences and both reset-weighted and equal-unique-observation estimates are preserved in the analysis. This does not establish unseen-training generalization.

The candidate's overall assignment gain was positive, but the exact-novel subset interval included zero. The full screen failed: A accuracy remained lower and required-bounce receiving A changed 14/16 to 13/16. All broader coverage gaps above remain open. The next prepared fixture uses existing standalone axes movement at nominal 25/50/75/100 cm, with recovery interleaving disabled; it is a proposal, not completed evaluation evidence or proof that footwork is required.
''', encoding='utf-8')
print('Updated current state, active goal, hierarchy status and coverage audit; mastery remains unaccepted.')

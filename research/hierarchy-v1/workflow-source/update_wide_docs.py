"""Update current pointers while preserving earlier report bytes."""
from pathlib import Path
import json

root = Path('F:/dev/picklebot')
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
archive = root/'docs/research/execution-v1-evidence/wide-movement-01'
assert read(archive/'archive-manifest.json')['status']=='complete_byte_preserved_archive'
assert read(archive/'audit/analysis.json')['status']=='complete_wide_movement_diagnostic'

intro = '''# Active drill-mastery goal — wider movement assessed

The frozen **1,048,609-experience executor** completed a 512-reset diagnostic under each of two target instructions. In the 256 explicit directional challenges, it made **38 legal returns under A and 40 under B**. A results by nominal feed displacement were **31/64 at 25 cm, 7/64 at 50 cm, and 0/64 at both 75 and 100 cm**. By direction: left 3/66, right 0/64, shallow 19/62 and deep 16/64.

The body moves: accepted contacts followed an average 44 cm of root travel. Misses averaged 98 cm through episode termination, a longer measurement window. Movement alone is therefore insufficient; useful positioning and contact remain weak. Nominal feed displacement is not required player travel, and reset geometry checks do not establish every trajectory's reachability.

The previous narrow focus practised only 2.5–10 cm of lateral feed displacement. The next bounded experiment will introduce four-direction focus at **6.25–25 cm**, retaining the **25% familiar / 25% prior court / 50% focus** mixture, interleaved ordering, current body and PPO settings. It will resume the complete saved trainer state to approximately 2.1 million total experiences and compare the frozen endpoint against both narrow and wider tests. The curriculum change and training are not yet launched in this snapshot.

The current checkpoint still serves legally on both sides, but balanced aiming and broader receiving remain unfinished. No model promotion or mastery acceptance. Final evaluation seeds remain unused.

[Diagnostic and recordings](research/execution-v1-wide-movement.md) · [Coverage](research/drill-mastery-coverage.md) · [Active goal](DRILL_MASTERY_GOAL.md)

---
'''
path = root/'docs/CURRENT_STATE.md'
old = path.read_bytes()
assert old.startswith(b'# Active drill-mastery goal') and b'wider movement assessed' not in old
path.write_bytes(intro.replace('\n','\r\n').encode('utf-8')+old)

path = root/'docs/DRILL_MASTERY_GOAL.md'
old = path.read_bytes()
start = old.index(b'Current work:')
end = old.index(b'App status:',start)
current = '''Current work: the wider 512-reset diagnostic is complete. The selected executor returned 31/64 of the 25 cm directional challenges, 7/64 at 50 cm, and none at 75–100 cm under target A. Recorded root movement confirms the body moves, but useful positioning and contact are unreliable. Next: a bounded full-state continuation with four-direction focus at 6.25–25 cm and the existing 25/25/50 familiar/prior/focus rehearsal mix, followed by narrow retention and wider movement evaluation of the same endpoint. The change is not yet launched in this snapshot. Balanced target following, varied mandatory-bounce receiving, deliberate kitchen behavior, and mastery thresholds remain open. [Latest result](research/execution-v1-wide-movement.md) · [Coverage audit](research/drill-mastery-coverage.md). Movement-goal and strategy training remain later stages.

'''
path.write_bytes(old[:start]+current.replace('\n','\r\n').encode('utf-8')+old[end:])

for filename, addition in {
    'docs/HIERARCHICAL_CONTROL.md': '''

[Wider movement diagnostic](research/execution-v1-wide-movement.md): the current executor makes some 25 cm returns, few 50 cm returns, and no 75–100 cm returns. Recorded body movement is present; timely positioning and contact remain weak. Next is graded four-direction execution practice with familiar-skill rehearsal, before learned strategy.
''',
    'docs/research/drill-mastery-coverage.md': '''

## Wider movement follow-up

The [512-reset diagnostic](execution-v1-wide-movement.md) completed paired A/B evaluations for both the initializer and current executor. Reset-only inspection covered all 32 direction/distance/feed cells, with 174 distinct initial physical observations. Two of 128 cells including player seat were absent. These are development probes, not final acceptance tests.

The 256 directional challenges use nominal 25/50/75/100 cm feeds in all four directions. Current A legality is 38/256: left 3/66, right 0/64, shallow 19/62 and deep 16/64. Distance results are 31/64, 7/64, 0/64 and 0/64. Only 69/256 attempts made accepted contact. Actual contacts distinguish volleys from bounced returns; the remaining 187 attempts had no accepted contact. Root travel exists but does not establish useful positioning or natural movement.

Wide target assignment gain was -0.00586, interval [-0.015625, 0.001953125]; aggregate target responsiveness came from familiar cases. No wide target-following claim is supported. The next proposed focus spans 6.25–25 cm left/right/shallow/deep while keeping familiar and prior-court rehearsal. Wider probes remain for transfer measurement; mandatory-bounce variations and deliberate kitchen behavior still require separate coverage.
'''
}.items():
    path=root/filename
    old=path.read_bytes()
    assert b'execution-v1-wide-movement.md' not in old
    path.write_bytes(old+addition.replace('\n','\r\n').encode('utf-8'))
print('Updated four current-state/goal documents; older report bytes preserved.')

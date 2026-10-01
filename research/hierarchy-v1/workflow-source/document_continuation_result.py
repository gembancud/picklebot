from pathlib import Path
import json,math
root=Path('F:/dev/picklebot');base=root/'artifacts/hierarchy-v1/smooth-continued-01'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
model='ExecutionV1SmoothContinuedFinal01'
def rows(name,condition):return {r['seed']:r for r in (json.loads(l) for l in (base/f'evaluation/{model}/{condition}/{name}').read_text().splitlines())}
a,b=rows('execution-goals.jsonl','A'),rows('execution-goals.jsonl','B');ep=rows('episodes.jsonl','A')
matrix={}
for task in sorted({r['task'] for r in ep.values()}):
    seeds=[s for s in a if ep[s]['task']==task]
    def hit(landing,goal):return landing['legalLanding'] and math.hypot(landing['landingX']-goal['targetX'],landing['landingZ']-goal['targetZ'])<=goal['radius']
    matrix[task]=dict(attemptsPerInstruction=len(seeds),AInstructionHitsA=sum(hit(a[s],a[s]) for s in seeds),AInstructionHitsB=sum(hit(a[s],b[s]) for s in seeds),BInstructionHitsA=sum(hit(b[s],a[s]) for s in seeds),BInstructionHitsB=sum(hit(b[s],b[s]) for s in seeds),bothRequestedRegionsReached=sum(hit(a[s],a[s]) and hit(b[s],b[s]) for s in seeds))
with (root/'docs/research/execution-v1-evidence/smooth-continued-01/target-matrix.json').open('x',encoding='utf-8') as f:json.dump(matrix,f,indent=2)
report=root/'docs/research/execution-v1-smooth-continued.md'
text=report.read_text(encoding='utf-8')
text+='''
The positive paired response is uneven. Airborne B has 0/112 target hits and mandatory-bounce receiving B has 0/16. Bounced-rally landings hit B 27 times under either instruction. A-goal serves reach A 0/16 while B-goal serves reach B 8/16, despite legal serving remaining intact. No paired reset reaches both requested regions. The model responds to instructions in some situations; it is not a balanced two-region controller. [Instruction-versus-landing matrix](execution-v1-evidence/smooth-continued-01/target-matrix.json).

Next: freeze this checkpoint and compare it with the initializer on separately declared unused development seeds under the same physical mixture and A/B/random instructions. Measure novel physical reset coverage explicitly; new seed IDs alone do not prove novel scenarios. This diagnostic confirmation is justified by the positive target-response component, while the full predeclared screening gate remains failed. No further training, architecture change, or promotion is implied by this result.
'''
report.write_text(text,encoding='utf-8',newline='\n')
state=root/'docs/CURRENT_STATE.md'
old=state.read_bytes()
header='''# Active drill-mastery goal — longer training produces partial target response

The unchanged continuation completed at **1,048,609 total experiences**. The predeclared midpoint and final models each completed 768 frozen evaluation attempts. Compared with the 262,179-experience parent, final A/B/random target hits changed **109/18/65 → 103/35/71** out of 256 per condition. Final legal counts were **229/231/229**; the per-drill legal-retention screen passed against both the initializer and immediate parent.

The requested-versus-opposite-region assignment gain improved from **−0.04883 to +0.0625**, final paired 95% interval **[0.03125, 0.09570]**. This is early target responsiveness on a reused development anchor. The full screen still failed because A accuracy did not exceed the initializer. B-air remains 0/112 and B-required-bounce receiving 0/16; no reset succeeds at both requested regions. No promotion or mastery acceptance.

No training or task-owned Editor is active. The next action is a fresh, predeclared frozen-model development comparison, including a count of genuinely new physical resets and separate drill/region results. More training or architecture changes depend on that evidence. Wide/deep/shallow positioning, varied rule contexts, paired teamwork and learned strategy remain unfinished.

[Latest result](research/execution-v1-smooth-continued.md) · [Remaining coverage](research/drill-mastery-coverage.md) · [Active goal](DRILL_MASTERY_GOAL.md)

---
'''
assert not old.startswith(b'# Active drill-mastery goal \xe2\x80\x94 longer')
state.write_bytes(header.encode('utf-8')+old)
goal=root/'docs/DRILL_MASTERY_GOAL.md'
text=goal.read_text(encoding='utf-8-sig')
start=text.index('Current work:');end=text.index('\n\nApp status:',start)
text=text[:start]+'''Current work: the longer unchanged continuation produced positive paired target responsiveness while retaining legal returns, but failed balanced placement screening. Confirm the frozen final checkpoint on separately declared unused development cases, reporting actual physical novelty and per-drill/region failures. Keep the existing recovery screen as an anchor and expand coverage for varied required-bounce receiving, explicit kitchen behavior and measured lateral/deep/shallow positioning. [Latest result](research/execution-v1-smooth-continued.md) · [Coverage audit](research/drill-mastery-coverage.md). Movement-goal and strategy training remain later stages.'''+text[end:]
goal.write_text(text,encoding='utf-8',newline='\n')
design=root/'docs/HIERARCHICAL_CONTROL.md'
with design.open('a',encoding='utf-8',newline='\n') as f:f.write('\n[Longer unchanged continuation](research/execution-v1-smooth-continued.md): at 1,048,609 experiences the final model shows positive paired target response while preserving legality, but balanced placement remains unproven. The full screen failed and no model was promoted.\n')
print(json.dumps(matrix,indent=2))

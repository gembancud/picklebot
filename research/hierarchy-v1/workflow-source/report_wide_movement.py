from pathlib import Path
import json
root=Path('F:/dev/picklebot')
base=root/'artifacts/hierarchy-v1/wide-movement-fixture-01'
a=json.loads((base/'audit/analysis.json').read_text(encoding='utf-8-sig'))
assert a['status']=='complete_wide_movement_diagnostic' and a['masteryAccepted'] is False
initial,candidate=a['models']
path=root/'docs/research/execution-v1-wide-movement.md'
assert not path.exists()
def count(group,model,condition):
    m=a['summaries'][group][model][condition]
    return f"{m['legal']}/{m['attempts']}"
def interval(value):
    return f"{value['mean']:.5f} [{value['ci95'][0]:.5f}, {value['ci95'][1]:.5f}]"
lines=['# Wider movement diagnostic', '',
 'The frozen 1,048,609-experience executor can return some wider feeds, but the progression remains incomplete. All four model/target conditions completed 512 attempts. The same 512 base resets were reused under A/B instructions; they are not 2,048 independent situations. No training or simulation changes occurred.', '',
 '| Cases | Initializer A | Current A | Current B |', '|---|---:|---:|---:|']
for group,label in [('all','All cases'),('schedule/familiar','Familiar and retained skills'),('schedule/axis-challenge','Movement challenges')]:
    lines.append(f'| {label} | {count(group,initial,"A")} | {count(group,candidate,"A")} | {count(group,candidate,"B")} |')
lines+=['','The initializer ignores target inputs, so its A/B physical outcomes match exactly. Both conditions remain archived. The movement subset retains all 256 attempts, including contact failures.','',
 '| Nominal feed shift | Initializer A | Current A | Current B |','|---|---:|---:|---:|']
for cm in (25,50,75,100):
    group=f'nominal-shift/{cm}cm'
    lines.append(f'| {cm} cm | {count(group,initial,"A")} | {count(group,candidate,"A")} | {count(group,candidate,"B")} |')
lines+=['','| Direction | Initializer A | Current A | Current B |','|---|---:|---:|---:|']
for direction in ('left','right','shallow','deep'):
    group=f'axis/{direction}'
    lines.append(f'| {direction.title()} | {count(group,initial,"A")} | {count(group,candidate,"A")} | {count(group,candidate,"B")} |')
lines+=['','Directions and distances are marginal counts. Full drill/direction/distance/player cells are preserved; two player-specific cells are empty. No cases were substituted based on outcomes.','',
 '## Retained skills and actual movement','', '| Drill | Initializer A | Current A | Current B |','|---|---:|---:|---:|']
for task in ('stationary-serve','receive-feed','rally-air-feed','rally-bounce-feed'):
    group=f'drill/{task}'
    lines.append(f'| {task} | {count(group,initial,"A")} | {count(group,candidate,"A")} | {count(group,candidate,"B")} |')
t=a['actualContactAndMovementTelemetry']['schedule/axis-challenge'][candidate]['A']
contact=t['rootPathBeforeAcceptedContactMetres']
net=t['netRootDisplacementConditionalOnAcceptedContactMetres']
miss=t['rootPathThroughNoContactTerminationMetres']
lines+=['', f"Under A, the current executor made accepted paddle contact on **{t['acceptedFaceContacts']}/256** movement attempts. Its mean root path before those contacts was **{contact['mean']:.3f} m**, with mean net displacement **{net['mean']:.3f} m**. In the **{miss['measuredAttempts']}** attempts without accepted contact, mean root path through termination was **{miss['mean']:.3f} m**.", '',
 'This is movement, but distance travelled does not prove useful positioning. Misses can last longer and accumulate more travel. A nominal feed shift is measured from the initial paddle face, not a required footwork distance. These results do not establish a physical control limit or prove every feed is reachable within its contact window.', '',
 '## Target instructions','', '| Cases | Paired assignment gain [pointwise 95% interval] |','|---|---:|']
for group,label in [('all','All cases'),('schedule/familiar','Familiar and retained'),('schedule/axis-challenge','Movement challenges')]:
    lines.append(f'| {label} | {interval(a["causalResetWeighted"][group][candidate]["assignmentGain"])} |')
lines+=['', 'The aggregate target response comes from familiar cases. A useful directional target response is not established on the movement challenges. Actual legal landing coordinates determine success; nonzero distance reward does not count as a target hit.', '',
 '## What this supports next','',
 'The next candidate curriculum is graded axes practice: 6.25/12.5/18.75/25 cm focus shifts while retaining the existing interleaved 25% familiar, 25% prior-court and 50% focus schedule. Keep the body, PPO, full checkpoint state, A/B goals and smooth reward unchanged. The opt-in scheduler needs a small implementation change; it is not yet applied or trained.', '',
 'Inspect representative recorded misses before deciding whether flight timing also needs adjustment. A bounded continuation can then reuse the narrow and wide frozen batteries; 50–100cm remain transfer probes. Do not keep extending the unchanged narrow recipe merely because its familiar scores remain high.', '',
 '## Evidence limits','',
 'The reset-only fixture inspected all 512 cases with zero policy actions, zero physics ticks and no initial overlaps. It found 174 distinct initial physical observations and covered all 32 direction/distance/feed cells. Sparse repetitions, one training lineage, zero start/timing variation and this reset recipe do not establish full-court generalization. A passed geometry inspection does not prove contact feasibility.', '',
 'No new mastery threshold, model promotion, or final-seed use occurred. Varied mandatory-bounce receiving, kitchen-boundary decisions, broader movement and reliable targeting remain requirements of the active goal.', '',
 '[Full analysis](execution-v1-evidence/wide-movement-01/audit/analysis.json) · [Reset fixture](execution-v1-evidence/wide-movement-01/fixture-summary.json) · [Frozen plan](execution-v1-evidence/wide-movement-01/plan.json) · [Archive manifest](execution-v1-evidence/wide-movement-01/archive-manifest.json)', '']
with path.open('x',encoding='utf-8') as handle: handle.write('\n'.join(lines))
print(path)

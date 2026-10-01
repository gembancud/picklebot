from pathlib import Path
import json
R=Path('F:/dev/picklebot');B=R/'artifacts/hierarchy-v1/right-acquisition-01'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
a=read(B/'results/analysis.json');match=read(B/'results/acquisition-analysis.json');proof=read(B/'training/run-complete.json')
P='ExecutionV1SmoothContinuedFinal01';F='ExecutionV1RightAcquisitionFinal01'
assert read(B/'evaluation-process/complete.json')['completed']==7
assert not a['promoted'] and not a['finalSeedsConsumed']
rows=[]
for battery,entry in a['batteries'].items():
    vals=entry['groups']['all']['models']
    for condition,old in vals[P]['counts'].items():
        new=vals[F]['counts'][condition]
        rows.append(f"| {battery} {condition} | {old['legal']}/{old['attempts']} | {new['legal']}/{new['attempts']} | {old['targets']} → {new['targets']} |")
details=[]
for battery,groups in [(k,v['groups']) for k,v in a['batteries'].items()]:
    for group,row in groups.items():
        if group.startswith('drill/') or group in ('axis/left','axis/right','axis/shallow','axis/deep','shift/25cm','shift/50cm','shift/75cm','shift/100cm'):
            old,new=row['models'][P]['counts'],row['models'][F]['counts']
            details.append(f"| {battery}: {group} | {old['A']['legal']} → {new['A']['legal']} / {new['A']['attempts']} | {old['B']['legal']} → {new['B']['legal']} / {new['B']['attempts']} |")
m=match['groups']['all']['models'][F];ci=m['uniqueClusterAssignmentGain'];causal=m['causal']
text='''# Right-return acquisition: learned locally, lost retention

The fixed endpoint learned the concentrated rightward 25 cm drill, but it is not a usable replacement for the shared executor. All eight canonical feed/seat situations produce legal returns for both target requests. Earlier skills regress severely, and reliable target-conditioned placement is unproven. Preserve this checkpoint as diagnostic evidence; do not promote it or simply extend its right-only curriculum.

## Fixed experiment

Resumed common parent 1,048,609 with full ML-Agents PPO state, unchanged 128×2 network, controls, physics and placement reward. Eight workers ×16 courts practiced only rightward 25 cm rally returns (both airborne and bounced feeds, all seats), without movement shaping or maintenance. This isolates concentrated acquisition; it does not distinguish increased hard-task exposure from removal of competing tasks. No scripted movement or stroke was added.

'''+f"Endpoint: **{proof['step']:,}** experiences; **{proof['episodes']:,}** completed training attempts. Actor/critic/normalizer/Adam and worker reward checks passed. Parent unchanged. Model `{F}`, ONNX `{a['model']['modelHash']}`; snapshot `{a['model']['checkpointHash']}`.\n\n"
text+='''## Matched acquisition

Parent legal returns: A 0/512, B 0/512. Final: A 512/512, B 512/512. These are **eight distinct starting observations repeated 64 times**, not 512 independent challenges. First full observations and target conditions matched across models. The result establishes acquisition of these canonical cases, not generalization or network capacity limits.

'''+f"Final target hits: A {m['conditions']['A']['targetHits']}/512; B {m['conditions']['B']['targetHits']}/512. Assignment gain {ci['mean']:.4f}, equal-unique-observation cluster interval [{ci['ci95'][0]:.4f}, {ci['ci95'][1]:.4f}]. Both requested targets were hit in **zero** matched pairs. Mean landing displacement toward B was {causal['landingShiftTowardBMetresGivenBothLegal']['mean']:.3f} m; repeated-seed intervals in raw output must not be interpreted as 512 independent cases.\n\n"
text+='''## Retention and transfer

These are the original unchanged development batteries, with evaluation shaping off and exact initial observation/target pairing verified. Scores include failures.

| Battery | Parent legal | Final legal | Target hits, parent → final |
|---|---:|---:|---:|
'''+ '\n'.join(rows)+'\n\n| Variation | A legal | B legal |\n|---|---:|---:|\n'+'\n'.join(details)+'\n\n'
text+='''## Next experiment and remaining goal

Test simultaneous maintenance and concentrated acquisition from the preserved common parent: keep the earlier familiar and prior-court practice, and replace the dispersed focus block with the now-learnable fixed rightward 25 cm cases. Keep PPO, controls and reward unchanged. Check the same endpoint for both acquisition and retention before widening the new skill. This tests whether the demonstrated skill can coexist with earlier skills; it does not assume the mix will work and does not rule out a later preservation objective or architecture change.

Before launching, validate the reset-only schedule and its per-seat/feed/serve-side coverage, preserve old schedule behavior, verify the worker build and full-state resume. No new run is launched by this report. The same shared execution policy must still learn broader movement, varied mandatory-bounce receiving, deliberate kitchen legality and causal placement. Explicit attainable acceptance thresholds and repeated final acceptance remain open. Final seeds are unused.

Evidence: `artifacts/hierarchy-v1/right-acquisition-01/results`, full raw evaluation directories, `training/extended-verification.json`, and the frozen evaluation plan. Actual eight-case before/after recordings are being assembled separately; they must show the retention regression alongside the narrow success.
'''
path=R/'docs/research/execution-v1-right-acquisition-final.md';assert not path.exists();path.write_bytes(text.encode())
print(path)

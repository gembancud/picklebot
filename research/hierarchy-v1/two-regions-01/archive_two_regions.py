from pathlib import Path
import json,shutil,hashlib
root=Path('F:/dev/picklebot');base=root/'artifacts/hierarchy-v1/two-regions-01';here=Path(__file__).parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
analysis=read(base/'audit/analysis.json');training=read(base/'execution-two-regions-02/verification.json')
assert analysis['status']=='complete_development_screen' and not analysis['promoted']
source=read(base/'source-records.json')
assert all(sha(root/n)==h for n,h in source['files'].items())
model=root/'Assets/Picklebot/PlayerLearning/Models/ExecutionV1TwoRegions01.onnx'
assert sha(model)==training['modelHash']
parent=root/'Assets/Picklebot/PlayerLearning/Models/ExecutionV1Initial.onnx'
assert sha(parent)=='bc6f8be16b791a2cd253b150b3f4c4c2492cdc0e65f94fa305ab4addefe78d51'
dest=root/'docs/research/execution-v1-evidence/two-regions-01';dest.mkdir(exist_ok=False)
for name in ['plan.json','source-records.json','retry.json']:
    shutil.copy2(base/name,dest/name)
shutil.copy2(base/'audit/analysis.json',dest/'analysis.json')
shutil.copy2(root/'artifacts/hierarchy-v1/two-regions-integration-tests-02.xml',dest/'integration-tests.xml')
for name in ['verification.json','launch.json','manifest.json','process-result.json']:
    shutil.copy2(base/'execution-two-regions-02'/name,dest/('training-'+name))
for m in ['ExecutionV1Initial','ExecutionV1TwoRegions01']:
    for condition in ['A','B','random']:
        out=dest/m/condition;out.mkdir(parents=True)
        for name in ['episodes.jsonl','execution-goals.jsonl','first-decisions.json','report.json','summary.json']:
            shutil.copy2(base/'evaluation'/m/condition/name,out/name)
checkpoint=root/'artifacts/mlagents/execution-two-regions-02/PicklebotExecutionV1/checkpoint.pt'
assert sha(checkpoint)==training['checkpointHash']
shutil.copy2(checkpoint,root/'training/snapshots/execution-v1-two-regions-01.pt')
identity=dict(checkpointHash=sha(checkpoint),modelHash=sha(model),parentHash=sha(parent),sourceIdentity=source['sourceIdentity'],promoted=False,masteryAccepted=False)
(root/'training/snapshots/execution-v1-two-regions-01.json').write_text(json.dumps(identity,indent=2),encoding='utf-8')
workflow=root/'research/hierarchy-v1/two-regions-01';workflow.mkdir(exist_ok=False)
for name in ['install_two_regions.py','add_two_region_integration.py','build_two_regions.py','build_two_regions_02.py','prepare_two_region_campaign.py','two_regions_evaluate_template.cs','analyze_two_regions.py','archive_two_regions.py']:
    shutil.copy2(here/name,workflow/name)
counts=analysis['summaries']['all'];causal=analysis['causal']['all']['ExecutionV1TwoRegions01']
lines=['# Two-region placement experiment','',
'The drill-mastery goal is active. This is a development experiment; no model has been promoted and mastery has not been established.','',
'Two separated target choices were added while keeping the existing body, feed schedule and PPO settings. Target radius is 1 m, versus 1.5 m in the unchanged random-target retention test. Serve targets differ in depth inside the correct service box; rally targets differ laterally. The targets are geometrically legal, with feasibility still to be measured per feed.','',
'19 Unity integration checks passed, including worker configuration, sampling and canonical landing evidence. A test initially read evidence before its writer closed; its lifecycle was corrected. The first build audit detected Unity changing an analytics define; a fresh build passed. The first training launch failed before learning because Windows reserved port5426. The unchanged retry used ports5605–5612. All failed records are retained locally.','',
f'Training completed at **{training["experiences"]:,} experiences**, using 8 workers × 16 courts and the original initializer with fresh optimizer state. The final checkpoint was selected in advance.','',
'Each condition uses the same 256 development resets, spanning one complete recovery cycle. A and B are paired target requests; random retains the previous target distribution. No final evaluation seeds were used.','',
'| Condition | Initial legal / target hits | Trained legal / target hits |','|---|---:|---:|']
for c in ['A','B','random']:
    a=counts['ExecutionV1Initial'][c];b=counts['ExecutionV1TwoRegions01'][c]
    lines.append(f'| {c} | {a["legal"]} / {a["targets"]} | {b["legal"]} / {b["targets"]} |')
g=causal['assignmentGain'];shift=causal['landingShiftTowardBMetresGivenBothLegal']
lines += ['',f'The requested-versus-opposite-region assignment gain was **{g["mean"]:.4f}**, with paired-bootstrap 95% interval **[{g["ci95"][0]:.4f}, {g["ci95"][1]:.4f}]**. Identical target-blind landings cancel in this measure; illegal attempts contribute zero.',
f'Both requests landed legally in {causal["bothLegalPairs"]}/256 pairs. Their mean projected landing shift toward B was {shift["mean"]:.4f} m. This conditional shift excludes pairs with an illegal attempt and must be read beside unconditional outcomes.','',
f'Predeclared promising-screen result: **{analysis["screen"]["promising"]}**. Checks: `{json.dumps(analysis["screen"]["tests"])}`. This is not final acceptance.','',
'Per-drill, region, service-side, movement and player counts and uncertainty are included in the analysis. These are reused development resets from one training lineage; repeated geometries and small subgroups limit inference. Current movement ranges do not demonstrate wide/deep/shallow mastery.','',
'[Analysis and per-skill counts](execution-v1-evidence/two-regions-01/analysis.json) · [Frozen plan](execution-v1-evidence/two-regions-01/plan.json) · [Training verification](execution-v1-evidence/two-regions-01/training-verification.json)']
(root/'docs/research/execution-v1-two-regions.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(dict(report='docs/research/execution-v1-two-regions.md',screen=analysis['screen']['tests'],promising=analysis['screen']['promising'],identity=identity),indent=2))

from pathlib import Path
import shutil,json,hashlib
R=Path('F:/dev/picklebot');W=Path(__file__).resolve().parent;A=R/'research/hierarchy-v1/right-retention-setup-01';assert not A.exists();A.mkdir()
names=['prepare_right_retention.py','PlayerRightReturnRetentionV1Tests.cs','prepare_right_retention_workflow.py','build_right_retention.py','probe_right_retention_baseline.py','prepare_right_retention_runner.py','run_right_retention.py','test_right_retention.py','right-retention-tests-metadata.json','right-retention-tests-01-result.json','right-retention-tests-01-console.log','right-retention-tests-01-settings-before.asset','right-retention-tests-01-settings-after.asset']
for name in names:shutil.copyfile(W/name,A/name)
shutil.copyfile(R/'artifacts/hierarchy-v1/right-retention-tests-01.xml',A/'tests.xml')
(A/'experiment.md').write_bytes('''# Fixed-right acquisition with maintenance

The right-only endpoint acquired eight canonical rightward25cm situations but lost earlier skills. This experiment resumes preserved common parent1048609, not the regressed specialist. One shared execution policy, maintained ML-Agents PPO128x2, same optimizer/config/reward and fixed endpoint2097152 (one buffer overshoot allowed).8 workers x16 courts. Maximum3600seconds. No scripted strokes or movement, release timing, new reward shaping or strategy policy.

Only curriculum changes:256-reset cycles contain128 fixed25cm rightward focus starts (64air/64bounce),64 familiar starts and64 prior-court starts. Existing familiar/prior recipes remain exact, including both service sides and required-bounce receiving. The existing permutation interleaves8focus/4familiar/4prior in each16 starts. These are episode allocations, not promised transition or PPO-gradient proportions; actual decisions per group must be reported. Half the experience budget in right-only training is not guaranteed to equal rightward exposure here.

The opt-in recovery pattern lateral-right uses a fixed focus range; old lateral/axes recovery and pure right-acquisition contracts retain their behavior.18 Unity tests passed, covering new physical reset parity and worker configuration alongside original lifecycle/interleaving tests. Build and frozen512-case worker fixture must pass before launch; verify no learned-state changes during that fixture.

Mandatory endpoint selection, no peak selection or automatic extension. Evaluate the same paired acquisitionA/B512 development anchors and original narrowA/B/random256 and wideA/B512 batteries, with shaping off and actual landing coordinates. Preserve raw outcome and observation pairing. Development advance gate: all eight canonical rightward situations legal under both targets; every legacy narrow drill/condition within5 percentage points of parent legality (so no lost canonical serves or receiving successes in16-case cohorts). This is a progression screen, not mastery or a statistical noninferiority guarantee. Report all movement-direction losses and target causal estimates even if that screen passes. A different source/worker execution can change wall time and asynchronous sample ordering.

Neither the best mixture nor sufficient network capacity is assumed. If acquisition or retention fails, compare per-task learning and actual sample exposure before changing architecture or extending. Goal remains broader movement, varied mandatory-bounce reception, deliberate kitchen behavior, reliable target-following, evidence-based final thresholds and repeated acceptance by one checkpoint. All current probes reuse development/training seeds; final acceptance seeds remain unused.
'''.encode())
doc=R/'docs/CURRENT_STATE.md'
head='''# Active drill-mastery goal: mixed rightward retention setup tested

The next reset-only curriculum uses50% fixed rightward25cm,25% familiar drills and25% prior-court episode starts, interleaved within16 starts.18 Unity tests passed, including physical reset parity and original recovery behavior. Build and frozen-worker fixture are next; no training launch yet. Planned common parent1048609 to fixed2097152 with unchanged PPO, controls and rewards. Mandatory acquisition plus all5 retention evaluations; no automatic promotion or extension. Final acceptance seeds remain unused.

Plan and tests: `research/hierarchy-v1/right-retention-setup-01`. The previous right-only result is preserved and unpromoted: [report](research/execution-v1-right-acquisition-final.md).

---

'''
doc.write_bytes(head.encode()+doc.read_bytes());print(A)

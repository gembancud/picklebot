from pathlib import Path
import json
root=Path('F:/dev/picklebot')
base=root/'artifacts/hierarchy-v1/axes-recovery-01'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
plan=read(base/'plan.json');proof=read(base/'training/resume-load-proof.json')
assert proof['status']=='exact_registered_state_restored' and proof['globalStep']==1048609
assert 'Resuming training from step 1048609.' in (base/'training/trainer-console.log').read_text()
report='''# Graded four-direction recovery

The wide diagnostic found little transfer beyond 25 cm. The next experiment changes focus feeds from 2.5–10 cm lateral offsets to **6.25 / 12.5 / 18.75 / 25 cm** offsets left, right, shallow and deep. Existing **25% familiar / 25% prior-court / 50% focus** practice and interleaving remain intact.

`execution-axes-recovery-01` resumed the full actor, critic, normalization, Adam and step state at **1,048,609 experiences**, on **8 workers × 16 courts**. Its fixed endpoint is approximately **2,097,152 total experiences**. PPO settings, body controls, goal inputs and smooth landing reward are unchanged. Process RNG and live episodes restart; this is not bitwise trajectory continuation.

All **14 Unity checks passed**, including the complete recorded default curriculum and new four-direction reset construction. Two test compilation issues were corrected before execution: an unnecessary JSON-library dependency and the installed Unity SceneHandle type. The test runner's sole analytics-define edit was restored to the prior exact bytes before building. A new standalone worker was built and source/build identities verified.

Training is running in this snapshot; improvement has not been evaluated. The mandatory frozen endpoint will replay the narrow 256-reset A/B/random battery and wide 512-reset A/B battery. Compare actual legal returns, target outcomes, root movement and contact by skill, direction and distance against the initializer and immediate parent. The 50–100 cm feeds remain transfer probes. No automatic extension, model promotion or mastery acceptance.

[Frozen plan](execution-v1-evidence/axes-recovery-01/setup/plan.json) · [Tests](execution-v1-evidence/axes-recovery-01/setup/integration-tests.xml) · [Setup evidence](execution-v1-evidence/axes-recovery-01/setup/archive-manifest.json) · [Previous movement results](execution-v1-wide-movement.md) · [Recordings](execution-v1-wide-movement-review.md)
'''
p=root/'docs/research/execution-v1-axes-recovery.md'
assert not p.exists();p.write_text(report,encoding='utf-8')
p=root/'docs/CURRENT_STATE.md';old=p.read_bytes()
header='''# Active drill-mastery goal — graded movement training running

**execution-axes-recovery-01** is running on **128 practice courts**, resumed at **1,048,609 experiences** toward a fixed endpoint near **2.1 million**. The full policy, critic, normalization and optimizer state loaded exactly. Only focus practice changes: smaller **6.25–25 cm left/right/shallow/deep offsets**, retaining the **25/25/50 familiar/prior/focus** mixture and existing PPO, body, target and reward settings.

All **14 curriculum checks passed**, followed by a verified new worker build. The previous frozen model's seven movement recordings match the full 512-attempt diagnostic; browser playback remains unverified because local-file automation was blocked. The new training has no assessed performance result yet. Its endpoint must pass narrow retention and wider movement comparisons before further decisions. Final acceptance seeds remain unused; mastery is not accepted.

[Current experiment](research/execution-v1-axes-recovery.md) · [Movement recordings](research/execution-v1-wide-movement-review.md) · [Active goal](DRILL_MASTERY_GOAL.md)

---
'''
p.write_bytes(header.encode()+old)
p=root/'docs/DRILL_MASTERY_GOAL.md';old=p.read_bytes();start=old.index(b'Current work:');end=old.index(b'App status:',start)
current='''Current work: graded four-direction training is running as `execution-axes-recovery-01`, resumed with full trainer state at 1,048,609 experiences toward about 2.1 million. Focus offsets span 6.25–25 cm, retaining familiar and prior-court practice. Fourteen Unity curriculum checks and the new worker build passed. The mandatory endpoint will undergo narrow skill-retention and wide movement comparisons before any further training decision. Balanced target following, varied mandatory-bounce receiving, deliberate kitchen behavior, mastery thresholds and repeated acceptance remain open. [Current experiment](research/execution-v1-axes-recovery.md) · [Movement evidence](research/execution-v1-wide-movement.md). Movement-goal and strategy training remain later stages.

'''
p.write_bytes(old[:start]+current.encode()+old[end:])
p=root/'docs/HIERARCHICAL_CONTROL.md';old=p.read_bytes()
p.write_bytes(old+b'\n\n[Graded movement continuation](research/execution-v1-axes-recovery.md) is running after14 passing curriculum checks. Recovery now accepts opt-in axes focus while preserving default lateral behavior. No additional actor or strategy policy is introduced.\n')
print('Current training status documented; performance pending.')

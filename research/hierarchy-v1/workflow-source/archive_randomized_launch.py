from pathlib import Path
import json,shutil,hashlib,time
R=Path('F:/dev/picklebot');W=Path(__file__).resolve().parent;A=R/'artifacts/hierarchy-v1/randomized-scale-01'
archive=R/'research/hierarchy-v1/randomized-scale-01';archive.mkdir(exist_ok=False)
for name in ['prepare_randomized_scale.py','expand_randomized_seeds.py','widen_execution.py','test_randomized_scale.py','build_randomized_scale.py','run_randomized_scale.py','evaluate_randomized_scale.py','normalize_scale_endings.py','randomized-scale-tests-metadata.json','randomized-scale-tests-01-result.json','randomized-scale-tests-02-result.json']:
 shutil.copyfile(W/name,archive/name)
for name in ['transfer-proof.json','source-records.json','build-verification.json','probe-proof.json','training/config.yaml','training/manifest.json','training/launch.json','training/process.json']:
 dest=archive/name;dest.parent.mkdir(exist_ok=True,parents=True);shutil.copyfile(A/name,dest)
for n in [1,2]:shutil.copyfile(R/f'artifacts/hierarchy-v1/randomized-scale-tests-{n:02}.xml',archive/f'tests-{n:02}.xml')
doc='''# Randomized execution scaling experiment

Run: `execution-randomized-scale-01`. Started 13 September 2026.

- Maintained ML-Agents PPO; one execution policy, two hidden layers of256.
- Parent: right-retention endpoint2097180. Actor and critic widened by duplicate hidden units with complementary outgoing weights. Preserved normalizers and action distribution parameters; fresh Adam, new phase counter0. On2816 recorded observations plus4096 numerical probes, maximum action-mean/value error was below0.000009. Installed initialization loader verified. Earlier128 checkpoint remains intact.
- Budget:8million additional experiences; checkpoints every1million, keep10. Eight executable workers,16 courts each.12-hour failure timeout, no automatic extension or promotion.
- Same reward definitions and motor constraints.50% episode starts: random axes movement, nominal reset displacement2.5cm–1m, varied feed difficulty up to.5, flight-timing fraction0–.25, start-position fraction0–.15.25%: prior court movement, continuous range.005–.1 plus feed variation.25%: familiar serves/required-bounce receives/rally feeds; serves preserved, half non-serve familiar cycles retain anchor settings. Episode shares differ from decision/gradient shares.
- Fixed-ball serving stays fixed. No scripted actions, added shaping, changed collider or physics timestep. Air-feed labels are not proof of volley contact; assess actual contact mode.
- Training seeds2000000–2983039; development4000000–4099999 reserved separately. First512 training seeds used by the frozen probe and then training. Existing final-test seeds remain forbidden and unconsumed.
-17/17 Unity tests passed, including768 distinct non-familiar physical reset observations across separate training/development samples, reproducibility and old curriculum checks. This validates reset construction, not universal biomechanical reachability.
- Frozen executable probe completed512 episodes, including256 distinct focus distances, with no shaping. Its bounded seed exhaustion is expected; it is not a training failure.
- Automatic frozen evaluations: initial model and approximately each1m checkpoint, original narrowA/B/random and wideA/B plus randomized512-seedA/B. Actual snapshot steps/hashes and all raw failures retained. Repeated development evaluation is not final acceptance. Evaluation process failure must be inspected separately from training.

This pilot changes capacity, reset distribution, duration and optimizer initialization together. Improvement would support this combined recipe; it would not isolate network size as the cause. The prior mixed run learned rightward returns but regressed narrow legality from234/235 to164/167 out of256; it was not promoted.

Live artifacts: `artifacts/hierarchy-v1/randomized-scale-01/`. TensorBoard: http://127.0.0.1:6009/ (select the training run, not its `-probe` companion).
'''
(R/'docs/research/execution-v1-randomized-scale.md').write_text(doc,encoding='utf-8')
state=R/'CURRENT_STATE.md'
if not state.exists():state=R/'docs/CURRENT_STATE.md'
if state.exists():
 old=state.read_bytes();(archive/'current-state-before.md').write_bytes(old)
 prefix=b'# Active update: randomized scaling launched (2026-09-13)\n\n`execution-randomized-scale-01` is training:256x2,8million additional steps,8workers x16courts. Prior right-retention training and all7 evaluations finished; no promotion. See docs/research/execution-v1-randomized-scale.md and artifacts/hierarchy-v1/randomized-scale-01 for current process/checkpoint/evaluation status. Historical sections below may describe earlier running processes.\n\n'
 state.write_bytes(prefix+old)
print('Launch protocol and validation evidence archived.')

from pathlib import Path
import json,shutil,hashlib
R=Path('F:/dev/picklebot');W=Path(__file__).resolve().parent;B=R/'artifacts/hierarchy-v1/right-acquisition-01'
out=R/'research/hierarchy-v1/right-acquisition-checkpoint-01';assert not out.exists();out.mkdir()
files=['training/run-complete.json','training/process-result.json','training/extended-verification.json','selected-models.json','acquisition-baseline-evaluation.json','acquisition-final-evaluation.json','evaluation-process/started.json','evaluation-process/plan.json']
hashes={}
for rel in files:
    dst=out/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(B/rel,dst);hashes[rel]=hashlib.sha256(dst.read_bytes()).hexdigest()
for name in ['audit_right_acquisition_training.py','run_right_acquisition_evaluations.py','right-acquisition-import-final.cs']:
    shutil.copyfile(W/name,out/name)
for c in ['A','B']:
    src=B/'evaluation/acquisition/ExecutionV1SmoothContinuedFinal01'/c
    for name in ['summary.json','model-identity.json']:
        dst=out/'baseline'/c/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src/name,dst)
for name in ['manifest.json','complete.json','parity.json']:
    dst=out/'baseline-recording'/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(W.parents[1]/'outputs/right-acquisition-review-01/baseline'/name,dst)
(out/'inputs.json').write_bytes(json.dumps(hashes,indent=2).encode())
doc=R/'docs/CURRENT_STATE.md'
head='''# Active drill-mastery goal: rightward acquisition finished; evaluation running

Training `execution-right-acquisition-01` finished at 2,097,175 steps after 31,195 completed practice episodes (1,007 seconds). Final selection is the declared endpoint, not a peak chosen by reward. `ExecutionV1RightAcquisitionFinal01` is preserved with its numbered checkpoint. Actor/critic and normalizer updates, Adam state, worker identity and reward formula checks passed; the common parent is unchanged.

Matched baseline evaluation on 512 reused development feeds achieved 0 legal returns for both target A and target B. Eight cases selected before final results were recorded from actual Unity frames; replay matched all 512 baseline attempts. This diagnostic is rightward 25 cm only. It cannot establish retained skills, other directions, or mastery.

Sequential final evaluation is running: matched acquisition A/B, then the original narrow A/B/random and wide A/B batteries. Runner PID39720 (historical launch identity; check live state), task-owned Editor PID31548. Training has stopped. Logs and progress: `artifacts/hierarchy-v1/right-acquisition-01/evaluation-process`. Do not restart because a tool observation expires. Final acceptance seeds remain unused. No model promotion and no claim of mastery.

Evidence: `research/hierarchy-v1/right-acquisition-checkpoint-01`; prospective tests and fixed demo cases: `research/hierarchy-v1/right-acquisition-evaluation-plan-01`. Next: verify all seven outcomes, measure retention and matched target-following, then record the same eight final-model cases and assemble the comparison.

---

'''
doc.write_bytes((head+doc.read_text()).encode())
print(out)

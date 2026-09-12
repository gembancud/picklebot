from pathlib import Path
import hashlib,json,shutil
R=Path('F:/dev/picklebot'); W=Path(__file__).resolve().parent
out=R/'research/hierarchy-v1/right-acquisition-evaluation-plan-01'
assert not out.exists()
names=['prepare_right_acquisition_evaluation.py','analyze_right_acquisition_final.py','prepare_right_acquisition_matched.py','analyze_right_acquisition_matched.py','prepare_right_acquisition_recording.py','build_right_acquisition_review.py','right-acquisition-eval-prepare.cs','right-acquisition-eval-restore.cs']
out.mkdir(parents=True)
hashes={}
for name in names:
    src=W/name; dst=out/name; shutil.copyfile(src,dst)
    hashes[name]=hashlib.sha256(dst.read_bytes()).hexdigest()
plan=dict(scripts=hashes,endpoint=2097152,checkpointSelection='Fixed final endpoint, no selection by performance',acquisition=dict(firstSeed=1109849,count=512,conditions=['A','B'],models=['ExecutionV1SmoothContinuedFinal01','ExecutionV1RightAcquisitionFinal01']),retention=['narrow-A','narrow-B','narrow-random','wide-A','wide-B'],demo=dict(seeds=list(range(1109849,1109857)),selection='First eight resets, fixed before final evaluation; retain successes and misses',replayParityEpisodes=512),developmentReuse=True,acceptanceSeedsUsed=False,promotion=False,concurrency='Baseline editor evaluations overlap independent training. Wall time and asynchronous worker ordering need not reproduce a previous isolated run.')
(out/'plan.json').write_bytes(json.dumps(plan,indent=2).encode())
print(out)

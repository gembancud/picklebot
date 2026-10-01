from pathlib import Path
W=Path(__file__).resolve().parent
pairs=[('prepare_right_acquisition_evaluation.py','prepare_right_retention_evaluation.py'),('prepare_right_acquisition_matched.py','prepare_right_retention_matched.py'),('run_right_acquisition_evaluations.py','run_right_retention_evaluations.py'),('right-acquisition-eval-prepare.cs','right-retention-eval-prepare.cs'),('right-acquisition-eval-restore.cs','right-retention-eval-restore.cs'),('right-acquisition-import-final.cs','right-retention-import-final.cs')]
for old,new in pairs:
    dst=W/new;assert not dst.exists()
    s=(W/old).read_text(encoding='utf-8').replace('right-acquisition','right-retention').replace('ExecutionV1RightAcquisitionFinal01','ExecutionV1RightRetentionFinal01')
    if new.endswith('eval-prepare.cs'):s=s.replace('acquisition-baseline-evaluation.json','selected-models.json')
    dst.write_bytes(s.encode())
print('Prepared fixed-endpoint seven-test workflow')

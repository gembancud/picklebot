from pathlib import Path
import json, shutil
root=Path('F:/dev/picklebot')
audit=root/'artifacts/hierarchy-v1/target-response-01'
dest=root/'docs/research/execution-v1-evidence/target-response-01'
dest.mkdir(exist_ok=False)
for name in ['plan.json','verification.json','summary.json','evaluate.cs']:
    shutil.copy2(audit/name,dest/name)
shutil.copy2(Path(__file__).with_name('analyze_response.py'),dest/'analyze.py')
for folder in audit.iterdir():
    if folder.is_dir():
        (dest/folder.name).mkdir()
        for name in ['episodes.jsonl','execution-goals.jsonl','report.json']:
            shutil.copy2(folder/name,dest/folder.name/name)
ledgerpath=root/'artifacts/player-v3/seed-ledger.json'
ledger=json.loads(ledgerpath.read_text(encoding='utf-8-sig'))
assert not ledger['finalSeedsConsumed']
ledger.setdefault('developmentReuses',[]).append(dict(firstSeed=1109529,count=64,
    run='artifacts/hierarchy-v1/target-response-01',purpose='Matched fixed target sensitivity, initializer negative control and smoke model'))
ledgerpath.write_text(json.dumps(ledger,indent=2),encoding='utf-8')
print('Counterfactual evidence archived; development reuse recorded')

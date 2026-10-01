"""Read preserved paired evaluations; report rightward failure stages without reruns."""
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path('F:/dev/picklebot')
BASE = ROOT/'artifacts/hierarchy-v1/movement-progress-01'
inputs = {}

def read(path, lines=False):
    raw = path.read_bytes()
    inputs[str(path.relative_to(ROOT))] = hashlib.sha256(raw).hexdigest()
    text = raw.decode('utf-8-sig')
    return [json.loads(line) for line in text.splitlines()] if lines else json.loads(text)

plan = read(BASE/'plan.json')
analysis = read(BASE/'audit/analysis.json')
wide = plan['evaluation']['batteries']['wide']
fixture = read(ROOT/wide['baselineCampaign']/'fixture/wide-fixture-0000.json')
descriptors = {row['seed']: row for row in fixture['planned']}
assert len(descriptors) == 512
paths = dict(wide['baselineEvaluationRoots'])
paths['ExecutionV1MovementProgressFinal01'] = str((BASE/'evaluation/wide/ExecutionV1MovementProgressFinal01').relative_to(ROOT))
rows = []
for model, relative in paths.items():
    for condition in ('A', 'B'):
        folder = ROOT/relative/condition
        episodes = read(folder/'episodes.jsonl', True)
        goals = {g['seed']: g for g in read(folder/'execution-goals.jsonl', True)}
        assert len(episodes) == len(goals) == 512
        for cm in (25, 50, 75, 100):
            selected = [e for e in episodes if descriptors[e['seed']]['direction'] == 'right' and descriptors[e['seed']]['centimetres'] == cm]
            stages = collections.Counter()
            for e in selected:
                if goals[e['seed']]['legalLanding']: stage = 'legal'
                elif not e['faceContact']: stage = 'no_accepted_face_contact'
                elif not e['netCrossed']: stage = 'contact_without_net_crossing'
                else: stage = 'crossed_without_legal_return'
                stages[stage] += 1
            rows.append(dict(model=model, condition=condition, nominalShiftCm=cm,
                attempts=len(selected), stages=dict(stages),
                faults=dict(collections.Counter(e['terminalFault'] for e in selected)),
                seeds=[e['seed'] for e in selected]))
for path, expected in inputs.items():
    if path in analysis['inputSha256']:
        assert expected == analysis['inputSha256'][path], path
result = dict(rows=rows, inputSha256=inputs,
    scriptSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    limitations=['Conditions reuse matched feeds; do not pool as independent cases.',
        'No accepted face contact does not identify timing, reach, or action cause.',
        'WrongSide is a landing on the wrong half after contact, not evidence of an illegal grip.',
        'Summary telemetry cannot establish outgoing velocity or a mechanically feasible alternative.',
        'No new seeds, simulation changes, training, promotion, or mastery claim.'])
destination = Path(__file__).with_name('rightward-progress-diagnosis.json')
with destination.open('x', encoding='utf-8') as handle:
    json.dump(result, handle, indent=2)
print(destination)

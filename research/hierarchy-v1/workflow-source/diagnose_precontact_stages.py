from pathlib import Path
import json,hashlib
from collections import Counter
R=Path('F:/dev/picklebot');B=R/'artifacts/hierarchy-v1/precontact-alignment-01'
def read(p):return json.loads(p.read_text())
def rows(p):return {r['seed']:r for r in map(json.loads,p.read_text().splitlines())}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def stage(e):
    return 'legal' if e['outcome'] in ('legal_serve','legal_return') else 'no_contact' if not e['faceContact'] else 'contact_without_crossing' if not e['netCrossed'] else 'crossed_not_legal'
def main():
    analysis=read(B/'results/analysis.json');inputs=analysis['inputSha256']
    for rel,digest in inputs.items():assert sha(R/rel)==digest
    desc={r['seed']:r for r in read(R/'artifacts/hierarchy-v1/wide-movement-fixture-01/fixture/wide-fixture-0000.json')['planned']}
    out={}
    for c in ['A','B']:
        p=rows(R/f'artifacts/hierarchy-v1/wide-movement-fixture-01/evaluation/ExecutionV1SmoothContinuedFinal01/{c}/episodes.jsonl')
        n=rows(B/f'evaluation/wide/ExecutionV1PrecontactFinal01/{c}/episodes.jsonl');assert set(p)==set(n)
        groups={d:[s for s in p if desc[s]['direction']==d] for d in ['left','right','shallow','deep']}
        for cm in [25,50,75,100]:groups[f'{cm}cm']=[s for s in p if desc[s]['centimetres']==cm]
        out[c]={}
        for g,seeds in groups.items():
            transitions=Counter(stage(p[s])+' -> '+stage(n[s]) for s in seeds)
            lost=[s for s in seeds if stage(p[s])=='legal' and stage(n[s])!='legal']
            gained=[s for s in seeds if stage(p[s])!='legal' and stage(n[s])=='legal']
            out[c][g]=dict(attempts=len(seeds),transitions=dict(transitions),lostLegalSeeds=sorted(lost),gainedLegalSeeds=sorted(gained),lostLegalFinalStages=dict(Counter(stage(n[s]) for s in lost)))
    target=B/'results/stage-diagnosis.json'
    with target.open('x') as f:json.dump(dict(pairedDevelopmentFeeds=True,analysisHash=sha(B/'results/analysis.json'),groups=out,scriptHash=sha(Path(__file__)),causalMechanismProven=False),f,indent=2)
    for c in out:print(c,'deep',out[c]['deep'],'right',out[c]['right'])
if __name__=='__main__':main()

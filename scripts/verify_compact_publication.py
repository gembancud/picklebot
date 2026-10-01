"""Check selected checkpoint identity, published file hashes, and compact results."""
from pathlib import Path
import json,gzip,hashlib,subprocess,re
import torch
R=Path(__file__).resolve().parents[1];D=R/'research/hierarchy-v1/randomized-scale-publication'
def main():
 manifest=json.loads((D/'publication-manifest.json').read_text(encoding='utf-8'))
 for row in manifest['files']:
  p=R/row['path'];assert p.stat().st_size==row['bytes'];assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'],p
 for label,step in [('final',24000022),('evaluated',23999987)]:
  p=R/f'training/snapshots/execution-v1-randomized-scale-24m-{label}.pt';state=torch.load(p,map_location='cpu',weights_only=False)
  assert int(next(iter(state['global_step'].values())).item())==step
  assert state['Optimizer:value_optimizer']['state']
  for key in ('Policy','Optimizer:critic'):
   assert state[key]['network_body._body_endoder.seq_layers.0.weight'].shape==(256,136)
   assert all(torch.isfinite(v).all().item() for v in state[key].values())
 files=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=R).decode().split('\0')
 flags=[];oversized=[]
 pattern=re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,}|AKIA[0-9A-Z]{16}|-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----)')
 for rel in files:
  p=R/rel
  if not rel or not p.is_file():continue
  if p.stat().st_size>=100000000:oversized.append(rel)
  if p.suffix in ('.py','.cs','.json','.md','.yaml','.yml','.toml','.log','.ps1') and pattern.search(p.read_bytes()):flags.append(rel)
 assert not flags,flags;assert not oversized,oversized
 raw=0
 for p in D.rglob('*.jsonl.gz'):
  with gzip.open(p,'rt',encoding='utf-8') as f:
   for line in f:json.loads(line);raw+=1
 report=dict(filesVerified=len(manifest['files']),checkpointSteps=[23999987,24000022],optimizerStatePresent=True,rawRowsParsed=raw,largeGitBlobs=False,credentialPatternMatches=0,bulkArtifactsIncluded=False)
 (D/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
if __name__=='__main__':main()

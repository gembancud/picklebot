"""Clone a completed ML-Agents run with checkpoint retention confined to the clone."""
from pathlib import Path
import argparse,hashlib,json,shutil

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def clone_run(source,destination,allowed_root):
    source=Path(source).resolve();destination=Path(destination).resolve();allowed_root=Path(allowed_root).resolve()
    if not source.is_relative_to(allowed_root) or not destination.is_relative_to(allowed_root):raise ValueError('Run paths must stay inside the supplied training root')
    if source==destination or source.is_relative_to(destination) or destination.is_relative_to(source):raise ValueError('Distinct non-nested runs required')
    if not source.is_dir() or destination.exists():raise ValueError('Existing completed source and new destination required')
    history={p.relative_to(source).as_posix():digest(p) for p in source.rglob('*') if p.is_file()}
    status=source/'run_logs/training_status.json';data=json.loads(status.read_text(encoding='utf-8-sig'));rewrites=[]
    def relocate(value,behavior):
        old=Path(value).resolve()
        if not old.is_relative_to(allowed_root):raise ValueError('Historical checkpoint outside training root')
        local=source/old.relative_to(source) if old.is_relative_to(source) else source/behavior/old.name
        if not old.is_file() or not local.is_file() or digest(old)!=digest(local):raise ValueError('Historical checkpoint has no identical local copy: '+str(old))
        new=(destination/local.relative_to(source)).resolve()
        if not new.is_relative_to(destination):raise ValueError('Checkpoint path escaped clone')
        rewrites.append(dict(original=str(old),cloned=str(new),sha256=digest(local)))
        return str(new)
    def visit(node,behavior):
        if isinstance(node,dict):
            for key,value in list(node.items()):
                if key=='file_path':node[key]=relocate(value,behavior)
                elif key=='auxillary_file_paths':node[key]=[relocate(p,behavior) for p in value]
                else:visit(value,behavior)
        elif isinstance(node,list):
            for item in node:visit(item,behavior)
    for behavior,record in data.items():
        if behavior!='metadata':visit(record,behavior)
    shutil.copytree(source,destination)
    if not all(digest(destination/n)==h for n,h in history.items()):raise RuntimeError('Clone bytes differ before metadata rewrite')
    (destination/'run_logs/training_status.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    if not all(digest(source/n)==h for n,h in history.items()):raise RuntimeError('Source changed during clone')
    # Preserve an inherited provenance document before replacing the clone's
    # canonical document. This makes cloning work across multiple generations.
    provenance=destination/'clone-provenance.json'
    inherited=None
    if provenance.exists():
        inherited=digest(provenance);lineage=destination/'clone-lineage';lineage.mkdir(exist_ok=True)
        archived=lineage/(inherited+'.json')
        if archived.exists():
            if digest(archived)!=inherited:raise RuntimeError('Conflicting inherited clone provenance')
        else:shutil.copyfile(provenance,archived)
    cloned={p.relative_to(destination).as_posix():digest(p) for p in destination.rglob('*') if p.is_file() and p!=provenance}
    result=dict(version='isolated-mlagents-clone-v2',source=str(source),destination=str(destination),sourceFiles=history,cloneFiles=cloned,rewrittenCheckpointPaths=rewrites,inheritedProvenanceHash=inherited)
    with provenance.open('w' if inherited else 'x') as f:json.dump(result,f,indent=2)
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source',type=Path);parser.add_argument('destination',type=Path);args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]/'artifacts/mlagents'
    print(json.dumps(clone_run(args.source,args.destination,root)))

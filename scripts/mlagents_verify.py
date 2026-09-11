"""Verify the isolated training runtime, source pin and GPU/autograd availability."""
import argparse
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import subprocess
import sys
import torch
import onnx

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError('Refuse to overwrite verification evidence')
    subprocess.run([sys.executable,str(ROOT/'scripts/setup_mlagents.py'),'--verify-source-only'],check=True)
    assert sys.version_info[:3] == (3,10,12)
    assert metadata.version('mlagents') == metadata.version('mlagents-envs') == '1.2.0.dev0'
    assert torch.__version__ == '2.8.0+cu126' and torch.cuda.is_available()
    torch.manual_seed(4100)
    layer = torch.nn.Linear(32,16,device='cuda')
    optimizer = torch.optim.Adam(layer.parameters(),lr=.001)
    x = torch.randn(64,32,device='cuda')
    before = layer.weight.detach().clone()
    loss = layer(x).square().mean()
    loss.backward(); optimizer.step()
    assert bool(torch.isfinite(layer.weight).all()) and not torch.equal(before,layer.weight)
    report = dict(python=sys.version,executable=sys.executable,torch=torch.__version__,cuda=torch.cuda.is_available(),
        gpu=torch.cuda.get_device_name(),gpuUpdateVerified=True,mlagents=metadata.version('mlagents'),
        envs=metadata.version('mlagents-envs'),numpy=metadata.version('numpy'),onnx=onnx.__version__,hashes={})
    for relative in ['Packages/manifest.json','Packages/packages-lock.json','tools/mlagents-training/pixi.toml',
                     'tools/mlagents-training/pixi.lock','tools/mlagents-training/source-pin.json']:
        report['hashes'][relative]=hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2))
    print(json.dumps(report))

if __name__ == '__main__':
    main()

"""Export PyTorch checkpoint reference outputs for Unity inference tests."""
import importlib.util
import json
from pathlib import Path
import numpy as np
import torch
from torch import nn

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('skill',ROOT/'scripts/competition-skill-train.py')
skill=importlib.util.module_from_spec(spec);spec.loader.exec_module(skill)
torch.set_num_threads(4)
for name,inputs,width,outputs in [('stroke',10,96,6),('strategy',8,32,5)]:
    path=ROOT/'Assets/Picklebot/Competition/Models'/name
    data=json.loads(path.with_suffix('.json').read_text())
    net=nn.Sequential(nn.Linear(inputs,width),nn.Tanh(),nn.Linear(width,width),nn.Tanh(),nn.Linear(width,outputs))
    net.load_state_dict(torch.load(ROOT/'artifacts/competition/training'/f'{name}.pt',map_location='cpu',weights_only=True))
    if name=='stroke': x=skill.examples(1000,839950)[0][:64]
    else:
        rng=np.random.default_rng(839950);x=rng.normal(size=(64,inputs)).astype(np.float32)*np.array(data['scale'],np.float32)+np.array(data['mean'],np.float32)
    with torch.no_grad(): y=net(torch.tensor((x-np.array(data['mean'],np.float32))/np.array(data['scale'],np.float32))).numpy()
    path.with_suffix('.reference.json').write_text(json.dumps(dict(samples=[dict(input=a.tolist(),output=b.tolist()) for a,b in zip(x,y)]),indent=2))

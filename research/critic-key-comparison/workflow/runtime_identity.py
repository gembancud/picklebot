from pathlib import Path
import hashlib
import importlib.metadata
import inspect
import json
import os
import sys

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def verify_runtime():
    from mlagents.trainers.buffer import RewardSignalUtil
    from mlagents.trainers.ppo.optimizer_torch import TorchPPOOptimizer
    from mlagents.trainers.ppo.trainer import PPOTrainer
    from mlagents.trainers.trainer.on_policy_trainer import OnPolicyTrainer
    from mlagents.torch_utils import torch
    p=Path(os.environ['PICKLEBOT_PACKAGE_RECORD'])
    j=json.loads(p.read_text(encoding='utf-8'))
    target=Path(j['target']).resolve()
    actual={x.relative_to(target/'mlagents').as_posix():sha(x) for x in (target/'mlagents').rglob('*.py') if '__pycache__' not in x.parts}
    assert actual==j['installedFiles'],'Package source changed'
    classes=[RewardSignalUtil,TorchPPOOptimizer,PPOTrainer,OnPolicyTrainer]
    modules={c.__name__:str(Path(inspect.getfile(c)).resolve()) for c in classes}
    assert all(Path(x).is_relative_to(target) for x in modules.values()),'Wrong installed trainer selected'
    distinct=RewardSignalUtil.value_estimates_key('extrinsic')!=RewardSignalUtil.returns_key('extrinsic')
    assert distinct==(j['label']=='fixed'),'Wrong critic-key mapping'
    assert torch.cuda.is_available(),'Expected original CUDA runtime'
    data=dict(status='assigned_installed_trainer_verified',label=j['label'],target=str(target),modules=modules,
              distinctCriticKey=distinct,python=sys.executable,pythonVersion=sys.version,
              mlagents=importlib.metadata.version('mlagents'),torch=torch.__version__,cuda=torch.version.cuda,
              device=torch.cuda.get_device_name(0),wheelHash=j['wheelHash'])
    with (p.parent/'trainer-runtime-verification.json').open('x',encoding='utf-8') as f:json.dump(data,f,indent=2)
    print(json.dumps(data),flush=True)
    return data

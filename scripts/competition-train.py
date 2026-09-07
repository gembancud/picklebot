"""CPU PPO shot selection. Rewards come from terminal Unity point winners.

The stroke network is frozen. The opponent alternates between the current
policy (self-play) and the same stroke network aiming at the centre.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import time
import numpy as np
import torch
from torch import nn

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('stroke_trainer', ROOT/'scripts/competition-skill-train.py')
stroke = importlib.util.module_from_spec(spec); spec.loader.exec_module(stroke)


def unity(code):
    proc = subprocess.run(['unity','command','eval',code,'--format','json'],cwd=ROOT,text=True,capture_output=True,timeout=30)
    data=json.loads(proc.stdout)
    if not data.get('success'): raise RuntimeError(data)
    result=data['data']['result']
    if isinstance(result,dict):
        if not result.get('success',True): raise RuntimeError(result)
        return result.get('result')
    return result


def collect(seed, episodes, label, path, mode):
    target=ROOT/'artifacts/competition'/f'{label}.json'
    unity(f'return Picklebot.Competition.Editor.CompetitionEditor.Collect({seed},{episodes},"{label}","{path}","{mode}");')
    start=time.time()
    while True:
        status=unity('return Picklebot.Competition.Editor.CompetitionEditor.Status;')
        if str(status).startswith('completed:'): break
        if str(status).startswith('failed:') or time.time()-start>180: raise RuntimeError(status)
        time.sleep(.3)
    return json.loads(target.read_text())


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--iterations',type=int,default=30);parser.add_argument('--episodes',type=int,default=96)
    args=parser.parse_args(); seed=830010
    torch.set_num_threads(4);torch.manual_seed(seed)
    net=nn.Sequential(nn.Linear(8,32),nn.Tanh(),nn.Linear(32,32),nn.Tanh(),nn.Linear(32,5))
    with torch.no_grad(): net[-1].weight.mul_(.05);net[-1].bias.zero_()
    mean=np.array([0,.35,0,0,0,-4.5,0,0],np.float32)
    scale=np.array([.5,.3,.8,2,2,1,.5,.5],np.float32)
    opt=torch.optim.Adam(net.parameters(),lr=.0015)
    output=ROOT/'artifacts/competition/training';output.mkdir(parents=True,exist_ok=True)
    model_path=output/'strategy-current.json'; rows=[]
    start=time.time()
    for iteration in range(args.iterations):
        stroke.export(net,mean,scale,model_path,'competitive-strategy-v1',seed)
        mode=['near','far','self'][iteration%3]
        report=collect(830500+iteration*args.episodes,args.episodes,f'train-{iteration:03}',model_path,mode)
        obs=[];actions=[];old_logp=[];rewards=[]
        for point in report['points']:
            for side in [-1,1]:
                if mode=='near' and side>0 or mode=='far' and side<0:continue
                selected=[d for d in point['decisions'] if d['side']==side]
                for i,d in enumerate(selected):
                    obs.append(d['observation']);actions.append(d['action']);old_logp.append(d['logProbability'])
                    rewards.append((0 if point['winner']==0 else 1 if point['winner']==side else -1)*(.97**(len(selected)-i-1)))
        if not obs: raise RuntimeError('No learned actions in point batch.')
        x=torch.tensor((np.asarray(obs,dtype=np.float32)-mean)/scale)
        action=torch.tensor(actions);old=torch.tensor(old_logp);advantage=torch.tensor(rewards)
        # Terminal zero-sum reward only; no reward for long rallies or matching
        # the opponent. A constant batch baseline reduces variance.
        advantage=(advantage-advantage.mean())/(advantage.std()+1e-6)
        for epoch in range(5):
            order=torch.randperm(len(x))
            for ids in order.split(256):
                dist=torch.distributions.Categorical(logits=net(x[ids]))
                ratio=(dist.log_prob(action[ids])-old[ids]).exp()
                loss=-torch.minimum(ratio*advantage[ids],ratio.clamp(.8,1.2)*advantage[ids]).mean()-.02*dist.entropy().mean()
                opt.zero_grad();loss.backward();nn.utils.clip_grad_norm_(net.parameters(),.5);opt.step()
        points=report['points'];learner_side=-1 if mode=='near' else 1
        row=dict(iteration=iteration,mode=mode,actions=len(obs),mean_returns=float(np.mean([p['returns'] for p in points])),
            learner_win_rate=None if mode=='self' else float(np.mean([p['winner']==learner_side for p in points])),
            action_counts=np.bincount(actions,minlength=5).tolist(),seconds=time.time()-start)
        rows.append(row); print(json.dumps(row),flush=True)
    path=ROOT/'Assets/Picklebot/Competition/Models/strategy.json'
    stroke.export(net,mean,scale,path,'competitive-strategy-v1',seed)
    torch.save(net.state_dict(),output/'strategy.pt')
    manifest=dict(method='PPO terminal point reward; alternating centre opponent and shared-policy self-play',seed=seed,
        iterations=args.iterations,episodes_per_iteration=args.episodes,training_seed_start=830500,
        training_seed_end=830500+args.iterations*args.episodes-1,validation_partition=[840000,850000],
        reward='winner +1; loser -1; 0.97 discount between own shots; entropy 0.02',
        physics='Unity local PhysicsScene at 240 Hz; frozen neural stroke control',
        model_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),stroke_sha256=hashlib.sha256((path.parent/'stroke.json').read_bytes()).hexdigest(),
        trainer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),history=rows)
    (path.parent/'strategy.manifest.json').write_text(json.dumps(manifest,indent=2))


if __name__=='__main__':main()

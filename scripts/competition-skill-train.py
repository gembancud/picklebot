"""Train goal-conditioned stroke control for dissipative Unity physics.

This is the low-level imitation bootstrap. Shot choice is trained separately
from actual Unity point rewards by competition-train.py.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np
import torch
from torch import nn

ROOT = Path(__file__).resolve().parents[1]
DT, G, DRAG, BOUNCE, RADIUS = 1/240, 9.81, .025, .86, .025


def advance(p, v):
    v = v + (np.array([0, -G, 0]) - DRAG * np.linalg.norm(v, axis=1)[:, None] * v) * DT
    return p + v * DT, v


def examples(n, seed):
    rng = np.random.default_rng(seed)
    p = np.column_stack([rng.uniform(-.65,.65,n),rng.uniform(.16,.7,n),rng.uniform(.85,1.3,n)])
    v = np.column_stack([rng.uniform(-1.8,1.8,n),rng.uniform(.5,2.5,n),rng.uniform(-6,-3.6,n)])
    state = np.zeros((n,7)); hit = np.zeros((n,3)); incoming = np.zeros((n,3)); remaining = np.zeros(n)
    bounced = np.zeros(n, bool); done = np.zeros(n, bool); recorded = np.zeros(n,bool)
    record_step = rng.integers(0,145,n)
    record_time = np.zeros(n)
    for step in range(250):
        select = (~done) & (~recorded) & (step >= record_step)
        state[select] = np.column_stack([p,v,bounced])[select]
        recorded[select] = True; record_time[select] = step * DT
        old = p.copy(); p,v = advance(p,v)
        floor = (p[:,1] <= RADIUS) & (v[:,1] < 0) & (~done)
        p[floor,1] = RADIUS
        v[floor,1] *= -BOUNCE
        bounced[floor] = True
        crossed = (p[:,2] <= -1.25) & (~done)
        ratio = np.clip((-1.25-old[:,2]) / (p[:,2]-old[:,2]), 0, 1)
        hit[crossed] = (old + (p-old)*ratio[:,None])[crossed]
        incoming[crossed] = v[crossed]
        remaining[crossed] = step*DT + ratio[crossed]*DT-record_time[crossed]
        done |= crossed
    gx = rng.uniform(-.64,.64,n); gz = rng.uniform(.4,.95,n)
    flight = rng.uniform(.43,.53,n)
    desired = np.column_stack([(gx-hit[:,0])/flight,
        (RADIUS-hit[:,1])/flight + .5*G*flight,(gz+1.25)/flight])
    # First-order drag compensation for the short outgoing flight.
    desired[:,[0,2]] *= 1 + .5*DRAG*np.linalg.norm(desired,axis=1)[:,None]*flight[:,None]
    delta = desired-incoming
    normal = delta/np.linalg.norm(delta,axis=1)[:,None]
    swing = (incoming*normal).sum(1) + np.linalg.norm(delta,axis=1)/1.90
    targets = np.column_stack([hit[:,:2],normal[:,:2]/normal[:,2:3],swing,remaining])
    # Include flight duration as an observation so the stroke network can express
    # different pace. Strategy currently chooses a fixed .48-second flight.
    inputs = np.column_stack([state,gx,gz,flight])
    valid = done & recorded & bounced & (remaining>.04) & (hit[:,1]>.10) & (hit[:,1]<.95) & (abs(hit[:,0])<.84) & (abs(swing)<2.5)
    return inputs[valid].astype(np.float32), targets[valid].astype(np.float32)


def export(net, mean, scale, path, version, seed):
    layers=[dict(inputs=m.in_features,outputs=m.out_features,weights=m.weight.detach().flatten().tolist(),bias=m.bias.detach().tolist()) for m in net if isinstance(m,nn.Linear)]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(version=version,seed=seed,mean=mean.tolist(),scale=scale.tolist(),layers=layers),separators=(',',':')))


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--steps',type=int,default=18000)
    args=parser.parse_args(); seed=830001
    torch.set_num_threads(4); torch.manual_seed(seed)
    x,y=examples(220000,seed); tx,ty=examples(20000,seed+1)
    mean,scale=x.mean(0),x.std(0); scale=np.maximum(scale,.05)
    x,y=torch.from_numpy((x-mean)/scale),torch.from_numpy(y)
    tx,ty=torch.from_numpy((tx-mean)/scale),torch.from_numpy(ty)
    net=nn.Sequential(nn.Linear(10,96),nn.Tanh(),nn.Linear(96,96),nn.Tanh(),nn.Linear(96,6))
    opt=torch.optim.Adam(net.parameters(),lr=.001); start=time.time()
    for step in range(args.steps):
        if step==args.steps*2//3:
            for group in opt.param_groups: group['lr']=.0002
        ids=torch.randint(len(x),(1024,)); loss=((net(x[ids])-y[ids])**2).mean()
        opt.zero_grad();loss.backward();opt.step()
        if (step+1)%3000==0:
            with torch.no_grad(): error=(net(tx)-ty).abs().mean(0).tolist()
            print(json.dumps(dict(step=step+1,mae=error,seconds=time.time()-start)),flush=True)
    path=ROOT/'Assets/Picklebot/Competition/Models/stroke.json'
    export(net,mean,scale,path,'competitive-stroke-v1',seed)
    artifacts=ROOT/'artifacts/competition/training';artifacts.mkdir(parents=True,exist_ok=True)
    torch.save(net.state_dict(),artifacts/'stroke.pt')
    manifest=dict(method='goal-conditioned behavioral cloning',seed=seed,steps=args.steps,examples=len(x),
        tuning_examples=len(tx),mae=error,physics=dict(dt=DT,gravity=G,quadratic_drag=DRAG,court_restitution=BOUNCE,paddle_restitution=.9,ball_radius=RADIUS),
        model_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),trainer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (path.parent/'stroke.manifest.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps(manifest),flush=True)


if __name__=='__main__':main()

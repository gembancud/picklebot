#!/usr/bin/env python3
"""One provenance-checked PPO update from complete, training-only V3 drill episodes."""
import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import torch
from torch import nn
from player_v3_actor import ActorV3, source_hash
from player_v3_rollouts import validate
from player_actor import ROOT, file_hash
from player_ppo import advantages, clipped_loss, prepare_advantages, bounded_optimizer_step

class CriticV3(nn.Module):
    def __init__(self,actor):
        super().__init__();h=actor.layers[0].out_features
        self.layers=nn.Sequential(nn.Linear(actor.layers[0].in_features,h),nn.Tanh(),nn.Linear(h,h),nn.Tanh(),nn.Linear(h,1))
        self.layers[0].load_state_dict(actor.layers[0].state_dict());self.layers[2].load_state_dict(actor.layers[1].state_dict())
        with torch.no_grad():self.layers[4].weight.zero_();self.layers[4].bias.zero_()
    def forward(self,x):return self.layers(x).squeeze(-1)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rollout',type=Path);parser.add_argument('actor',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--critic',type=Path);parser.add_argument('--epochs',type=int,default=4);parser.add_argument('--batch',type=int,default=128)
    parser.add_argument('--learning-rate',type=float,default=.0001);parser.add_argument('--target-kl',type=float,default=.01)
    args=parser.parse_args()
    if args.epochs<1 or args.batch<1 or not math.isfinite(args.learning_rate) or args.learning_rate<=0 or not math.isfinite(args.target_kl) or args.target_kl<=0:raise ValueError('Invalid PPO parameters')
    if args.output.exists():raise ValueError('Refuse to overwrite training evidence')
    torch.set_num_threads(2);torch.manual_seed(1000000)
    report,rows,summary=validate(args.rollout,args.actor)
    if report['split']!='training':raise ValueError('Only training-split rollouts may update the policy')
    if any(ep['outcome']=='exception' for ep in report['episodes']):raise ValueError('Fix software exceptions before training')
    if len(rows)<32:raise ValueError('Insufficient attempted decisions for a PPO update')
    actor,parent=ActorV3.load(args.actor);critic=CriticV3(actor)
    if args.critic:critic.load_state_dict(torch.load(args.critic,map_location='cpu',weights_only=True))
    inputs=[args.actor,args.rollout/'report.json',args.rollout/'rows.jsonl',ROOT/'config/player-agents/evaluation-v1.json']
    if args.critic:inputs.append(args.critic)
    frozen={str(p):file_hash(p) for p in inputs}
    trainers={name:file_hash(ROOT/'scripts'/name) for name in ('player-v3-ppo.py','player_v3_actor.py','player_v3_rollouts.py','player_actor.py','player_ppo.py')}
    obs=torch.tensor([r['observation'] for r in rows]);raw=torch.tensor([r['sample']['raw'] for r in rows]);mask=torch.tensor([r['sample']['mask'] for r in rows])
    old_logp=torch.tensor([r['sample']['logProbability'] for r in rows]);reward=torch.tensor([r['reward'] for r in rows]);terminal=torch.tensor([r['terminal'] for r in rows])
    with torch.no_grad():old_value=critic(obs)
    adv=torch.empty_like(reward);returns=torch.empty_like(reward)
    for episode in range(len(report['episodes'])):
        indices=[i for i,r in enumerate(rows) if r['episode']==episode]
        if not indices:continue
        gae,target=advantages(reward[indices],old_value[indices],terminal[indices],gamma=.99,gae_lambda=.95)
        adv[indices]=gae;returns[indices]=target
    adv=prepare_advantages(adv)
    actor_optimizer=torch.optim.Adam(actor.parameters(),lr=args.learning_rate);critic_optimizer=torch.optim.Adam(critic.parameters(),lr=args.learning_rate)
    updates=0;measurements=[];stopped=False
    def measure_kl():
        if not all(torch.isfinite(p).all() for p in list(actor.parameters())+list(critic.parameters())):return float('inf')
        return clipped_loss(actor.raw_logp(obs,raw,mask),old_logp,adv,clip=.1)[1]
    args.output.mkdir(parents=True)
    for epoch in range(args.epochs):
        for batch in torch.randperm(len(rows)).split(args.batch):
            logp=actor.raw_logp(obs[batch],raw[batch],mask[batch]);policy_loss,_=clipped_loss(logp,old_logp[batch],adv[batch],clip=.1)
            value_loss=.5*(critic(obs[batch])-returns[batch]).square().mean()
            entropy=((actor.log_std+.5*(1+math.log(2*math.pi)))*mask[batch]).sum(-1).mean()
            loss=policy_loss+value_loss-.001*entropy
            if not torch.isfinite(loss):raise ValueError('Nonfinite training loss')
            accepted,kl=bounded_optimizer_step(actor,critic,actor_optimizer,critic_optimizer,loss,measure_kl,args.target_kl)
            measurements.append(dict(epoch=epoch,accepted=accepted,kl=kl,policyLoss=float(policy_loss.detach()),valueLoss=float(value_loss.detach())))
            if not accepted:stopped=True;break
            updates+=1
        if stopped:break
    if any(file_hash(p)!=h for p,h in frozen.items()) or any(file_hash(ROOT/'scripts'/n)!=h for n,h in trainers.items()) or source_hash()!=report['sourceHash']:raise ValueError('Inputs changed during update')
    training=dict(status='complete' if updates else 'rejected',rollout=str(args.rollout),parentModelHash=frozen[str(args.actor)],
        sourceHash=report['sourceHash'],inputHashes=frozen,trainerHashes=trainers,seedList=[ep['seed'] for ep in report['episodes']],
        summary=summary,optimizerSteps=updates,measurements=measurements,hyperparameters=dict(epochs=args.epochs,batch=args.batch,learningRate=args.learning_rate,targetKL=args.target_kl),createdUtc=datetime.now(timezone.utc).isoformat())
    if updates:
        meta=dict(parent,sourceHash=report['sourceHash'],parentModelHash=frozen[str(args.actor)],method='PPO on '+report.get('task','contact')+' drill',
            trainingSteps=parent.get('trainingSteps',0)+summary['physicsSteps'],trainingDecisions=len(rows),optimizerSteps=updates,
            dataHash=frozen[str(args.rollout/'rows.jsonl')],trainerHashes=trainers,createdUtc=training['createdUtc'])
        export=actor.export(meta);(args.output/'actor.json').write_text(json.dumps(export,indent=2));torch.save(critic.state_dict(),args.output/'critic.pt')
        training['actorHash']=file_hash(args.output/'actor.json');training['criticHash']=file_hash(args.output/'critic.pt')
    (args.output/'training.json').write_text(json.dumps(training,indent=2))
    print(json.dumps(dict(status=training['status'],optimizerSteps=updates,output=str(args.output))))
    if not updates:raise ValueError('No bounded PPO update accepted')
if __name__=='__main__':main()

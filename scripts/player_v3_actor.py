"""Versioned articulated policy, with explicit trunk transfer and raw-Gaussian PPO traces."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import torch
from torch import nn
from player_actor import ROOT, Actor, file_hash, digest, source_record_text, source_records, player_source_hash

OBS_VERSION = "player-observation-v3-joints-124"
ACTION_VERSION = "player-action-v3-joints-18"

def source_hash():
    return digest(player_source_hash(ROOT) + "\n" + source_record_text(source_records(ROOT, ("PlayerControls", "PlayerControlsIntegration"))))

class ActorV3(nn.Module):
    def __init__(self, hidden=128, observations=124, actions=18):
        super().__init__()
        self.layers=nn.ModuleList([nn.Linear(observations,hidden), nn.Linear(hidden,hidden), nn.Linear(hidden,actions)])
        self.log_std=nn.Parameter(torch.full((actions,),-1.8))
    def forward(self,x):
        for i,layer in enumerate(self.layers):
            x=layer(x)
            if i<len(self.layers)-1: x=x.tanh()
        return x
    @staticmethod
    def actions(raw,mask):
        a=raw.tanh().clone()
        positive=[3,4,5,16]+([17] if a.shape[-1]==18 else [])
        a[...,positive]=(a[...,positive]+1)*.5
        return a*mask
    def raw_logp(self,obs,raw,mask):
        return ((-.5*((raw-self(obs))/self.log_std.exp()).square()-self.log_std-.9189385332046727)*mask).sum(-1)
    def export(self,metadata):
        return dict(metadata,version="player-actor-v3",observationVersion=OBS_VERSION if self.layers[0].in_features==124 else "player-observation-v3-joints-121",
            actionVersion=ACTION_VERSION if self.layers[-1].out_features==18 else "player-action-v3-joints-17",
            logStd=self.log_std.detach().tolist(),layers=[dict(inputs=l.in_features,outputs=l.out_features,
            weights=l.weight.detach().flatten().tolist(),bias=l.bias.detach().tolist()) for l in self.layers])
    @classmethod
    def load(cls,path):
        data=json.loads(Path(path).read_text())
        schemas={(OBS_VERSION,ACTION_VERSION):(124,18),('player-observation-v3-joints-121','player-action-v3-joints-17'):(121,17)}
        shape=schemas.get((data['observationVersion'],data['actionVersion']))
        if data['version']!='player-actor-v3' or shape is None:raise ValueError('Schema mismatch')
        model=cls(data['layers'][0]['outputs'],*shape)
        if len(data['layers'])!=3: raise ValueError('Layer count mismatch')
        with torch.no_grad():
            for layer,record in zip(model.layers,data['layers']):
                if (record['inputs'],record['outputs']) != (layer.in_features,layer.out_features): raise ValueError('Layer shape mismatch')
                layer.weight.copy_(torch.tensor(record['weights']).reshape_as(layer.weight));layer.bias.copy_(torch.tensor(record['bias']))
            model.log_std.copy_(torch.tensor(data['logStd']))
        if not all(torch.isfinite(p).all() for p in model.parameters()) or not ((model.log_std>=-5)&(model.log_std<=1)).all(): raise ValueError('Invalid tensors')
        return model,data

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path);parser.add_argument('--parent',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists(): raise ValueError('Refuse to overwrite actor evidence')
    torch.set_num_threads(2);torch.manual_seed(1300000)
    parent,metadata=Actor.load_export(args.parent);model=ActorV3(parent.layers[0].out_features)
    with torch.no_grad():
        model.layers[0].weight.zero_();model.layers[0].weight[:,:54].copy_(parent.layers[0].weight);model.layers[0].bias.copy_(parent.layers[0].bias)
        model.layers[1].load_state_dict(parent.layers[1].state_dict())
        nn.init.normal_(model.layers[2].weight,0,.005);model.layers[2].bias.zero_();model.layers[2].bias[[3,4,5,16]]=-2
    data=model.export(dict(sourceHash=source_hash(),parentModelHash=file_hash(args.parent),parentTrainingSourceHash=metadata['sourceHash'],
        trainingSteps=0,method='V1 trunk transfer; all 18 action heads freshly initialized',initializationSeed=1300000,
        createdUtc=datetime.now(timezone.utc).isoformat(),trainerHash=file_hash(Path(__file__)),
        protocolHash=file_hash(ROOT/'config/player-agents/evaluation-v1.json')))
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(data,indent=2))
    print(json.dumps(dict(actor=str(args.output),sha256=file_hash(args.output),sourceHash=data['sourceHash'],trainingSteps=0)))
if __name__=='__main__': main()

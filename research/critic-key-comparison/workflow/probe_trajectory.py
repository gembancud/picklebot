"""Collect identical synthetic trajectories under each installed package."""
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
import os
import sys
import numpy as np
from mlagents.torch_utils import torch
from test_stability_diagnostics import (PPOTrainer,PPOSettings,TrainerSettings,NetworkSettings,
    ScheduleType,BehaviorIdentifiers,BEHAVIOR,SPEC,AgentExperience,ActionTuple,LogProbsTuple,Trajectory,Label)
from mlagents.trainers.buffer import BufferKey,RewardSignalUtil
from stability_diagnostics import install_diagnostics

def digest(x):return hashlib.sha256(np.asarray(x).tobytes()).hexdigest()
np.random.seed(22271);torch.manual_seed(22271)
with TemporaryDirectory() as d:
    settings=TrainerSettings(hyperparameters=PPOSettings(batch_size=4,buffer_size=8,num_epoch=3,
        learning_rate=1e-4,learning_rate_schedule=ScheduleType.CONSTANT,beta_schedule=ScheduleType.CONSTANT,epsilon_schedule=ScheduleType.CONSTANT),
        network_settings=NetworkSettings(normalize=True,hidden_units=128,num_layers=2),max_steps=10000,summary_freq=10000,checkpoint_interval=10000)
    trainer=PPOTrainer('PicklebotArticulated',10,settings,True,False,22271,str(Path(d)/'trainer'))
    parsed=BehaviorIdentifiers.from_name_behavior_id(BEHAVIOR)
    policy=trainer.create_policy(parsed,SPEC);trainer.add_policy(parsed,policy)
    diag=install_diagnostics(Path(d)/'probe.jsonl')
    rng=np.random.RandomState(43371)
    try:
        for index,length in [(0,7),(64,8),(128,6),(192,6)]:
            steps=[AgentExperience(obs=[rng.normal(size=124).astype(np.float32)],reward=float(rng.uniform(-1,1)),done=i==length-1,
                action=ActionTuple(np.zeros(16,np.float32),np.zeros(1,np.int32)),
                action_probs=LogProbsTuple(np.zeros(16,np.float32),np.zeros(1,np.float32)),action_mask=[np.array([False,True])],
                prev_action=np.zeros(17,np.float32),interrupted=False,memory=None,group_status=[],group_reward=0.) for i in range(length)]
            t=Trajectory(steps,[np.zeros(124,np.float32)],[],'agent_0-4',BEHAVIOR)
            diag.queued[id(t)]=(t,Label(0,4,index,BEHAVIOR));trainer._process_trajectory(t)
        b=trainer.update_buffer
        captured=np.asarray(diag.critic_shadows[id(trainer)])
        stored=np.asarray(b[RewardSignalUtil.value_estimates_key('extrinsic')])
        targets=np.asarray(b[RewardSignalUtil.returns_key('extrinsic')])
        fixed=os.environ['PICKLEBOT_TEST_PACKAGE']=='fixed'
        assert np.array_equal(stored,captured) if fixed else np.array_equal(stored,targets)
        out=dict(label=os.environ['PICKLEBOT_TEST_PACKAGE'],advantages=digest(b[BufferKey.ADVANTAGES]),
            targets=digest(targets),trueCriticPredictions=digest(captured),storedMatchesPrediction=bool(np.array_equal(stored,captured)),
            storedMatchesTarget=bool(np.array_equal(stored,targets)),experiences=b.num_experiences)
        Path(sys.argv[1]).write_text(json.dumps(out,indent=2),encoding='utf-8')
    finally:diag.close()

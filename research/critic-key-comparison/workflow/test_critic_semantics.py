import os
import unittest
from mlagents.torch_utils import torch
from mlagents.trainers.buffer import AgentBuffer,RewardSignalUtil
from mlagents.trainers.torch_entities.utils import ModelUtils

class Semantics(unittest.TestCase):
    def test_selected_package_preserves_declared_value_behavior(self):
        fixed=os.environ['PICKLEBOT_TEST_PACKAGE']=='fixed'
        b=AgentBuffer()
        b[RewardSignalUtil.value_estimates_key('extrinsic')].extend([0.])
        b[RewardSignalUtil.returns_key('extrinsic')].set([1.])
        old=torch.tensor(b[RewardSignalUtil.value_estimates_key('extrinsic')])
        target=torch.tensor(b[RewardSignalUtil.returns_key('extrinsic')])
        self.assertEqual(float(old.item()),0 if fixed else 1)
        value=torch.tensor([.5],requires_grad=True)
        loss=ModelUtils.trust_region_value_loss({'extrinsic':value},{'extrinsic':old},{'extrinsic':target},.2,torch.tensor([True]))
        grad=torch.autograd.grad(loss,value)[0].item()
        self.assertAlmostEqual(loss.item(),.64 if fixed else .25,places=6)
        self.assertAlmostEqual(grad,0 if fixed else -1,places=6)

if __name__=='__main__':unittest.main(verbosity=2)

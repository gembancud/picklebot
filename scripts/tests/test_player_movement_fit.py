import copy
import importlib.util
from pathlib import Path
import sys
import unittest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from player_actor import Actor
spec=importlib.util.spec_from_file_location("movement_fit",Path(__file__).resolve().parents[1]/"player-agents-fit-movement.py")
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class MovementFitTests(unittest.TestCase):
    def test_cached_features_match_complete_actor(self):
        actor=Actor(16); x=torch.randn(10,54)
        self.assertTrue(torch.equal(actor(x),actor.layers[-1](module.features(actor,x))))

    def test_only_movement_rows_may_change(self):
        parent=Actor(16); changed=copy.deepcopy(parent)
        with torch.no_grad(): changed.layers[-1].weight[:2].add_(.1)
        module.validate_frozen_parameters(parent,changed)
        for parameter in ("hidden","shot","hit","exploration"):
            bad=copy.deepcopy(changed)
            with torch.no_grad():
                if parameter=="hidden": bad.layers[0].bias[0]+=1
                elif parameter=="shot": bad.layers[-1].weight[3,0]+=1
                elif parameter=="hit": bad.layers[-1].bias[2]+=1
                else: bad.log_std[0]+=1
            with self.assertRaises(ValueError): module.validate_frozen_parameters(parent,bad)

    def test_exact_movement_has_zero_loss(self):
        output=torch.tensor([[.2,.3],[2.,-2.]])
        labels=torch.cat((Actor.movement(output),torch.ones(2,1),torch.zeros(2,1)),dim=1)
        self.assertEqual(float(module.movement_loss(output,labels)),0)

    def test_training_changes_only_movement_on_same_observations(self):
        parent=Actor(16); candidate=copy.deepcopy(parent); x=torch.randn(32,54)
        output=torch.nn.Linear(16,2); optimizer=torch.optim.Adam(output.parameters(),lr=.01)
        h=module.features(parent,x); labels=torch.zeros(32,4)
        loss=module.movement_loss(output(h),labels); loss.backward(); optimizer.step()
        with torch.no_grad():
            candidate.layers[-1].weight[:2].copy_(output.weight); candidate.layers[-1].bias[:2].copy_(output.bias)
        module.validate_frozen_parameters(parent,candidate)
        self.assertTrue(torch.equal(parent(x)[:,2:],candidate(x)[:,2:]))


if __name__ == "__main__": unittest.main()

import importlib.util
from pathlib import Path
import sys
import unittest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
spec=importlib.util.spec_from_file_location("contact_fit",Path(__file__).resolve().parents[1]/"player-agents-fit-contact-movement.py")
fit=importlib.util.module_from_spec(spec); spec.loader.exec_module(fit)


class ContactWeightTests(unittest.TestCase):
    def test_mask_uses_own_geometry_expected_team_and_attempt(self):
        x=torch.zeros(6,54); y=torch.zeros(6,4); y[:,2]=1; x[:,46]=1; x[:,5]=.3
        x[:,4]=.5/8.4; x[:,6]=.5/16.2
        x[1,46]=0; y[2,2]=0; x[3,4]=2/8.4; x[4,5]=3/3; x[5,5]=0
        self.assertEqual(fit.critical_contact_mask(x,y).tolist(),[True,False,False,False,False,False])

    def test_invalid_observation_is_rejected(self):
        x=torch.zeros(1,54); y=torch.zeros(1,4); x[0,5]=float("nan")
        with self.assertRaises(ValueError): fit.critical_contact_mask(x,y)

    def test_near_contact_weight_changes_only_loss_weight(self):
        out=torch.tensor([[.3,.4]])
        y=torch.tensor([[0.,0.,1.,4.,1.]])
        original=fit.movement_loss(out,y)
        y[:,4]=16
        self.assertAlmostEqual(float(fit.movement_loss(out,y)),float(original)*16,places=6)


if __name__=="__main__": unittest.main()

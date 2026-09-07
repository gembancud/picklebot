import copy
from pathlib import Path
import sys
import unittest

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from player_skill_gate_rl import next_draw, likelihood, game_weights, verify_training_schedule, validate_opponent_record
from player_ppo import clipped_loss


class SkillGateRLTests(unittest.TestCase):
    def plan(self):
        return dict(version="player-skill-gate-training-v1", split="training", seedList=list(range(1071000,1071004)),
                    gamesPerGroup=1, sampledSelector=True, sampledActor=False, logitScale=.5, explorationFloor=.05,
                    opponentMode="older actor / sampled", groups=[dict(group=g, candidateTeam=(g//2)%2,
                    sampledOpponent=True, swapPartnerIdentities=bool(g&1), seeds=[1071000+g]) for g in range(4)])

    def test_only_declared_training_seeds_and_sampling_pass(self):
        verify_training_schedule(self.plan())
        for key, value in (("split","development"), ("seedList",list(range(1141000,1141004))),
                           ("sampledSelector",False), ("explorationFloor",0), ("logitScale",1)):
            plan=self.plan(); plan[key]=value
            with self.assertRaises(ValueError): verify_training_schedule(plan)

    def test_changed_team_or_opponent_fails(self):
        for key,value in (("candidateTeam",1),("sampledOpponent",False),("swapPartnerIdentities",True)):
            plan=self.plan(); plan["groups"][0][key]=value
            with self.assertRaises(ValueError): verify_training_schedule(plan)

    def test_xorshift_reference_and_range(self):
        state, draw=next_draw(1)
        self.assertEqual(state,270369); self.assertEqual(draw,1056/16777216)
        for _ in range(100):
            state,draw=next_draw(state)
            self.assertGreaterEqual(draw,0); self.assertLess(draw,1)

    def test_finite_likelihood_and_exploration_floor(self):
        logits=torch.tensor([-1000.,0,1000.]); choices=torch.tensor([1,0,0])
        logp,p=likelihood(logits,choices)
        self.assertTrue(torch.isfinite(logp).all())
        self.assertTrue(torch.allclose(p,torch.tensor([.05,.5,.95])))
        for bad in (torch.tensor([2,0,1]),torch.tensor([float("nan"),0,1])):
            with self.assertRaises(ValueError): likelihood(logits,bad)

    def test_game_rewards_are_shared_and_long_games_do_not_dominate(self):
        reward,weight=game_weights([1,-1],[2,6])
        self.assertEqual(reward.tolist(),[1,1,-1,-1,-1,-1,-1,-1])
        self.assertAlmostEqual(float(weight[:2].sum()),float(weight[2:].sum()))
        # All-loss collection retains a legitimate zero-baseline gradient.
        self.assertEqual(game_weights([-1],[2])[0].tolist(),[-1,-1])
        for outcomes,lengths in (([0],[1]),([1],[0]),([],[])):
            with self.assertRaises(ValueError): game_weights(outcomes,lengths)

    def test_winning_sample_increases_its_probability(self):
        for choice,direction in ((1,-1),(0,1)):
            logits=torch.tensor([0.],requires_grad=True)
            logp,_=likelihood(logits,torch.tensor([choice]))
            loss,_=clipped_loss(logp,logp.detach(),torch.tensor([1.]))
            loss.backward(); self.assertGreater(float(logits.grad)*direction,0)

    def test_opponent_revalidation_rounding_is_not_an_action_replacement(self):
        action=dict(moveX=0.,moveZ=0.,attempt=False,shot=0)
        row=dict(action=action,opponentSample=dict(logProbability=-1.,action=dict(action,moveX=1e-7)))
        validate_opponent_record(row,torch.zeros(2),-1.)
        for field,value in (("moveX",.1),("attempt",True),("shot",1)):
            changed=copy.deepcopy(row); changed["opponentSample"]["action"][field]=value
            with self.assertRaises(ValueError): validate_opponent_record(changed,torch.zeros(2),-1.)


if __name__ == "__main__": unittest.main()

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from player_action_ablation import validate_substitution


class ActionAblationTests(unittest.TestCase):
    def rows(self, mode="none", team=0):
        original = dict(moveX=.2, moveZ=.3, attempt=True, shot=4)
        reference = dict(moveX=-.1, moveZ=.4, attempt=False, shot=8)
        selected = dict(none=(), movement=("moveX", "moveZ"), attempt=("attempt",), shot=("shot",))[mode]
        applied = {k: reference[k] if k in selected else v for k,v in original.items()}
        return [dict(gameSeed=1198000+team, rally=0, candidateTeam=team, player=p,
                     observationTick=12, applyTick=18, observation=[0.]*54,
                     original=copy.deepcopy(original), reference=copy.deepcopy(reference), applied=copy.deepcopy(applied))
                for p in range(team*2,team*2+2)]

    def test_exact_single_component_on_both_ends(self):
        for team in (0, 1):
            for mode in ("none", "movement", "attempt", "shot"):
                self.assertEqual(validate_substitution(mode, self.rows(mode, team),1198000), 0 if mode=="none" else 2)

    def test_unselected_or_wrong_source_change_fails(self):
        for mode in ("none", "movement", "attempt", "shot"):
            rows=self.rows(mode); rows[0]["applied"]["shot"]=2
            with self.assertRaises(ValueError): validate_substitution(mode,rows,1198000)

    def test_empty_unknown_duplicate_and_missing_partner_fail(self):
        for mode,rows in (("bad",self.rows()),("none",[]),("none",self.rows()[:1]),
                          ("none",self.rows()+self.rows()[:1])):
            with self.assertRaises(ValueError): validate_substitution(mode,rows,1198000)

    def test_ownership_timing_and_shape_fail(self):
        for update in (dict(player=2),dict(candidateTeam=1),dict(gameSeed=1200000),dict(rally=16),
                       dict(observationTick=13),dict(applyTick=19),dict(observation=[0.]*53),
                       dict(observation=[float("nan")]*54)):
            rows=self.rows(); rows[0].update(update)
            with self.assertRaises(ValueError): validate_substitution("none",rows,1198000)

    def test_nonfinite_or_invalid_recorded_actions_fail(self):
        for source in ("original","reference","applied"):
            for update in (dict(moveX=float("nan")),dict(moveZ=2),dict(attempt=1),dict(shot=9)):
                rows=self.rows(); rows[0][source].update(update)
                with self.assertRaises(ValueError): validate_substitution("none",rows,1198000)

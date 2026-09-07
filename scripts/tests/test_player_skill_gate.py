import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from player_actor import Actor
from player_skill_gate import SkillGate, source_label, selected_outputs
from player_skill_gate_audit import validate_selection


class SkillGateTests(unittest.TestCase):
    def load(self, data):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "gate.json"; path.write_text(json.dumps(data))
            return SkillGate.load_export(path)[0]

    def test_round_trip(self):
        model = SkillGate(); x = torch.randn(8, 54)
        self.assertTrue(torch.equal(model(x), self.load(model.export({}))(x)))

    def test_schema_is_not_actor(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "gate.json"; path.write_text(json.dumps(SkillGate().export({})))
            with self.assertRaises(ValueError): Actor.load_export(path)
        with self.assertRaises(ValueError): self.load(Actor(32).export({}))

    def test_bad_weights_shapes_mask_or_threshold_fail(self):
        data = SkillGate().export({})
        for change in (lambda v: v["layers"][0]["weights"].pop(),
                       lambda v: v["layers"][1].update(outputs=12),
                       lambda v: v["layers"][0]["bias"].__setitem__(0, float("nan")),
                       lambda v: v.update(maskedIndices=[]), lambda v: v.update(threshold=.5)):
            modified = copy.deepcopy(data); change(modified)
            with self.assertRaises(ValueError): self.load(modified)

    def test_mask_does_not_mutate_actor_inputs(self):
        x = torch.randn(4, 54); original = x.clone(); y = SkillGate.inputs(x)
        self.assertTrue(torch.equal(x, original))
        self.assertEqual(float(y[:, 25:37].abs().sum()), 0)
        self.assertTrue(torch.equal(y[:, :25], x[:, :25]))
        self.assertTrue(torch.equal(y[:, 37:], x[:, 37:]))

    def test_invalid_observations_fail(self):
        for x in (torch.zeros(1, 55), torch.zeros(54), torch.full((1, 54), float("nan"))):
            with self.assertRaises(ValueError): SkillGate()(x)

    def test_no_cross_player_state_or_teacher_paddle_classification(self):
        gate = SkillGate(); x = torch.randn(4, 54); before = gate(x)
        x[0] += 10
        self.assertTrue(torch.equal(before[1:], gate(x)[1:]))
        before = gate(x); x[:, 25:37] += 100
        self.assertTrue(torch.equal(before, gate(x)))

    def test_selects_whole_frozen_expert_action(self):
        gate = SkillGate(); experts = [Actor(8), Actor(8)]; x = torch.randn(4, 54)
        with torch.no_grad():
            for parameter in gate.parameters(): parameter.zero_()
            for bias, selected in ((-1, 0), (0, 1), (1, 1)):
                gate.layers[1].bias.fill_(bias)
                _, choices, output = selected_outputs(gate, experts, x)
                self.assertTrue(torch.equal(output, experts[selected](x)))
                self.assertTrue(torch.all(choices == selected))

    def test_source_labels_are_declared_not_hindsight_wins(self):
        self.assertEqual(source_label(dict(fixtureVersion="incoming-skill-v1", skillProfile="kitchen")), 1)
        self.assertEqual(source_label(dict(fixtureVersion="incoming-skill-v1", skillProfile="deep")), 0)
        self.assertEqual(source_label(dict(baselineOpponent=True, teacherProbability=1)), 0)
        for record in ({}, dict(skillProfile="kitchen"), dict(fixtureVersion="incoming-skill-v1", skillProfile="unknown")):
            with self.assertRaises(ValueError): source_label(record)

    def test_replay_rejects_changed_gate_or_action(self):
        output = torch.zeros(12)
        record = dict(gateLogit=.2, selectedExpert=1, action=dict(moveX=0., moveZ=0., attempt=True, shot=0))
        validate_selection(record, .2, 1, output)
        for change in (lambda v: v.update(gateLogit=.3), lambda v: v.update(selectedExpert=0),
                       lambda v: v.update(selectedExpert=True), lambda v: v["action"].update(attempt=False),
                       lambda v: v["action"].update(moveX=.1), lambda v: v["action"].update(shot=1)):
            changed = copy.deepcopy(record); change(changed)
            with self.assertRaises(ValueError): validate_selection(changed, .2, 1, output)


if __name__ == "__main__": unittest.main()

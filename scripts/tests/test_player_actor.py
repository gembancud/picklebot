import json
from pathlib import Path
import sys
import tempfile
import unittest

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from player_actor import Actor, teacher_tensors, validate_curriculum_ownership


class ActorTests(unittest.TestCase):
    @staticmethod
    def teacher_record():
        return dict(gameSeed=1000200, player=0, tick=12, rally=0, observation=[0.] * 54,
                    action=dict(moveX=0., moveZ=0., attempt=True, shot=0))

    def test_teacher_split_excludes_final_seeds(self):
        record = self.teacher_record()
        x, y = teacher_tensors([record], 1, "training")
        self.assertEqual(tuple(x.shape), (1, 54)); self.assertEqual(tuple(y.shape), (1, 4))
        record["gameSeed"] = 1200000
        with self.assertRaises(ValueError): teacher_tensors([record], 1, "training")
        with self.assertRaises(ValueError): teacher_tensors([record], 1, "development")

    def test_teacher_rejects_invalid_owner_and_action(self):
        record = self.teacher_record(); record["player"] = 4
        with self.assertRaises(ValueError): teacher_tensors([record], 1, "training")
        record = self.teacher_record(); record["action"]["moveX"] = 2
        with self.assertRaises(ValueError): teacher_tensors([record], 1, "training")
        record = self.teacher_record(); record["action"]["shot"] = .5
        with self.assertRaises(ValueError): teacher_tensors([record], 1, "training")

    def test_teacher_rejects_bad_observations_and_counts(self):
        record = self.teacher_record(); record["observation"][0] = float("nan")
        with self.assertRaises(ValueError): teacher_tensors([record], 1, "training")
        record = self.teacher_record(); record["observation"].pop()
        with self.assertRaises(ValueError): teacher_tensors([record], 1, "training")
        with self.assertRaises(ValueError): teacher_tensors([], 1, "training")

    def test_export_round_trip_preserves_outputs(self):
        torch.manual_seed(1000000)
        model = Actor(32)
        inputs = torch.randn(10, 54)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "actor.json"
            path.write_text(json.dumps(model.export({"method": "unit test"})))
            restored, _ = Actor.load_export(path)
        self.assertTrue(torch.equal(model(inputs), restored(inputs)))

    def test_movement_is_finite_and_has_unit_disk_bound(self):
        raw = torch.tensor([[0., 0.], [100., -100.], [-2., .5]])
        move = Actor.movement(raw)
        self.assertTrue(torch.isfinite(move).all())
        self.assertTrue((torch.linalg.vector_norm(move, dim=1) <= 1.000001).all())
        self.assertTrue(torch.equal(move[0], torch.zeros(2)))

    def test_non_finite_model_is_rejected(self):
        value = Actor(8).export({})
        value["layers"][0]["weights"][0] = float("nan")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "actor.json"; path.write_text(json.dumps(value))
            with self.assertRaises(ValueError):
                Actor.load_export(path)

    def test_player_batch_has_no_cross_player_state(self):
        model = Actor(32); inputs = torch.randn(4, 54)
        first = model(inputs).detach().clone()
        inputs[0] += 100
        second = model(inputs).detach()
        self.assertTrue(torch.equal(first[1:], second[1:]))

    def curriculum(self):
        rows = [dict(self.teacher_record(), player=i, candidateTeam=0) for i in (0, 1)]
        report = dict(seed=1000200, initialCandidateTeam=0, teacherDecisions=1, actorDecisions=1,
                      gameResults=[dict(gameSeed=1000200, candidateTeam=0)])
        return rows, report

    def test_curriculum_allows_only_candidate_pair(self):
        rows, report = self.curriculum()
        validate_curriculum_ownership(rows, report)
        rows[1]["player"] = 2
        with self.assertRaises(ValueError): validate_curriculum_ownership(rows, report)

    def test_curriculum_alternates_court_ends(self):
        rows, report = self.curriculum()
        report["gameResults"].append(dict(gameSeed=1000201, candidateTeam=1))
        report["actorDecisions"] += 2
        rows.extend(dict(self.teacher_record(), gameSeed=1000201, candidateTeam=1, player=i) for i in (2, 3))
        validate_curriculum_ownership(rows, report)
        rows[-1]["candidateTeam"] = 0
        with self.assertRaises(ValueError): validate_curriculum_ownership(rows, report)

    def test_curriculum_rejects_duplicates_and_missing_partner(self):
        rows, report = self.curriculum()
        rows[1] = dict(rows[0])
        with self.assertRaises(ValueError): validate_curriculum_ownership(rows, report)
        rows, report = self.curriculum()
        rows[1]["tick"] += 12
        with self.assertRaises(ValueError): validate_curriculum_ownership(rows, report)

    def test_curriculum_rejects_unreported_game_and_counts(self):
        rows, report = self.curriculum()
        report["teacherDecisions"] += 1
        with self.assertRaises(ValueError): validate_curriculum_ownership(rows, report)
        rows, report = self.curriculum()
        rows[1]["gameSeed"] += 1
        with self.assertRaises(ValueError): validate_curriculum_ownership(rows, report)


if __name__ == "__main__":
    unittest.main()

import importlib.util
import json
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


spec = importlib.util.spec_from_file_location("player_refresh", Path(__file__).parents[1] / "player-agents-refresh.py")
refresh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(refresh)


class RefreshTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.path = self.root / "artifacts/player-agents/curriculum.json"
        self.path.parent.mkdir(parents=True)
        self.report = dict(sourceHash="source", seed=1013000, split="training", baselineOpponent=True,
                           teacherProbability=1, fixedShot=0,
                           gameResults=[dict(candidateTeam=0, metrics=dict(infeasiblePaddleSteps=0,
                               playerMaxSpeed=[3.8]*4, playerMaxAcceleration=[14.01]*4,
                               playerMaxPaddleSpeed=[12.0]*4, playerMaxPaddleAcceleration=[100.03]*4,
                               playerMaxReach=[.62]*4))])
        self.path.write_text(json.dumps(self.report))
        self.root_patch = patch.object(refresh, "ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    def complete(self, expected=None):
        state = {"running": False, "status": "complete: artifacts/player-agents/curriculum.json"}
        with patch.object(refresh.driver, "evaluate", return_value=state), patch.object(refresh, "teacher_data") as data:
            result = refresh.wait_curriculum(expected, 1013000, "training", "source")
            data.assert_called_once_with(self.path, "training")
            return result

    def test_exact_completed_report_is_validated(self):
        self.assertEqual(self.complete(self.path), self.path)

    def test_different_existing_job_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "different curriculum"):
            self.complete(self.path.with_name("other.json"))

    def test_stale_source_and_wrong_split_are_rejected(self):
        for field, value in (("sourceHash", "old"), ("split", "development"), ("seed", 1013001)):
            with self.subTest(field=field):
                self.path.write_text(json.dumps({**self.report, field: value}))
                with self.assertRaisesRegex(ValueError, "identity or settings"):
                    self.complete()

    def test_mixed_teacher_settings_are_rejected(self):
        self.path.write_text(json.dumps({**self.report, "teacherProbability": .5}))
        with self.assertRaisesRegex(ValueError, "identity or settings"):
            self.complete()

    def test_incomplete_collection_cannot_start_fitting(self):
        with patch.object(refresh.driver, "evaluate", return_value={"running": False, "status": "incomplete_game: report.json"}), \
                patch.object(refresh, "teacher_data") as data:
            with self.assertRaisesRegex(RuntimeError, "did not complete"):
                refresh.wait_curriculum(self.path, 1013000, "training", "source")
            data.assert_not_called()

    def test_all_shot_curriculum_is_explicit(self):
        self.path.write_text(json.dumps({**self.report, "fixedShot": -1}))
        with patch.object(refresh, "teacher_data"):
            refresh.validate_curriculum(self.path, 1013000, "training", "source", -1)
            with self.assertRaisesRegex(ValueError, "identity or settings"):
                refresh.validate_curriculum(self.path, 1013000, "training", "source")

    def test_unsafe_teacher_data_is_rejected_before_fitting(self):
        self.report["gameResults"][0]["metrics"]["playerMaxPaddleAcceleration"][1] = 150
        self.path.write_text(json.dumps(self.report))
        with self.assertRaisesRegex(ValueError, "motor bound"):
            self.complete()

    def test_four_player_teacher_checks_both_teams(self):
        self.report["baselineOpponent"] = False
        self.report["gameResults"][0]["candidateTeam"] = -1
        refresh.validate_teacher_motors(self.report)
        self.report["gameResults"][0]["metrics"]["playerMaxReach"][3] = .7
        with self.assertRaisesRegex(ValueError, "motor bound"):
            refresh.validate_teacher_motors(self.report)

    def test_four_player_curriculum_requires_explicit_mode(self):
        self.report["baselineOpponent"] = False
        self.report["gameResults"][0]["candidateTeam"] = -1
        self.path.write_text(json.dumps(self.report))
        with patch.object(refresh, "teacher_data"):
            refresh.validate_curriculum(self.path,1013000,"training","source",four_player=True)
            with self.assertRaisesRegex(ValueError,"identity or settings"):
                refresh.validate_curriculum(self.path,1013000,"training","source")
        self.report["baselineOpponent"] = True
        self.path.write_text(json.dumps(self.report))
        with patch.object(refresh,"teacher_data"), self.assertRaisesRegex(ValueError,"identity or settings"):
            refresh.validate_curriculum(self.path,1013000,"training","source",four_player=True)

    def test_missing_teacher_measurements_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Missing teacher"):
            refresh.validate_teacher_motors({})

    def test_learner_only_collection_requires_the_recorded_actor(self):
        self.path.write_text(json.dumps({**self.report, "teacherProbability": 0, "actorHash": "expected"}))
        with patch.object(refresh, "teacher_data"), patch.object(refresh, "file_hash", return_value="expected"):
            refresh.validate_curriculum(self.path, 1013000, "training", "source", teacher_probability=0, actor_path=self.path)
            with self.assertRaisesRegex(ValueError, "collection actor"):
                refresh.validate_curriculum(self.path, 1013000, "training", "source", teacher_probability=0)

    def test_wrong_collection_actor_cannot_supply_correction_data(self):
        self.path.write_text(json.dumps({**self.report, "teacherProbability": 0, "actorHash": "wrong"}))
        with patch.object(refresh, "teacher_data"), patch.object(refresh, "file_hash", return_value="expected"):
            with self.assertRaisesRegex(ValueError, "collection actor"):
                refresh.validate_curriculum(self.path, 1013000, "training", "source", teacher_probability=0, actor_path=self.path)

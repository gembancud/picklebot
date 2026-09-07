import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("player_train_loop", SCRIPTS / "player-agents-train-loop.py")
loop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loop)


class TrainLoopTests(unittest.TestCase):
    def test_invalid_entropy_is_rejected_before_creating_a_run(self):
        for value in ("nan", "inf", "-0.1"):
            with self.subTest(value=value), patch.object(sys, "argv", ["train", "actor.json", "--entropy", value]), \
                 patch.object(Path, "mkdir") as mkdir, patch("sys.stderr"), self.assertRaises(SystemExit) as error:
                loop.main()
            self.assertEqual(error.exception.code, 2)
            mkdir.assert_not_called()

    def test_default_and_single_opponent_are_unchanged(self):
        self.assertEqual(loop.opponent_schedule(), [None])
        actor = Path("actor.json")
        self.assertEqual(loop.opponent_schedule(actor), [actor.resolve()])

    def test_pool_preserves_order_and_optional_baseline(self):
        actors = [Path("second.json"), Path("first.json")]
        self.assertEqual(loop.opponent_schedule(pool=actors, include_baseline=True),
                         [path.resolve() for path in actors] + [None])

    def test_resume_index_rotates_without_replacing_opponents(self):
        actors = [Path("first.json"), Path("second.json")]
        self.assertEqual(loop.opponent_schedule(pool=actors, include_baseline=True, start_index=1),
                         [actors[1].resolve(), None, actors[0].resolve()])

    def test_resume_index_cannot_skip_outside_the_pool(self):
        for index in (-1, 3):
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, "start index"):
                loop.opponent_schedule(pool=[Path("first"), Path("second")], include_baseline=True, start_index=index)

    def test_ambiguous_duplicate_and_oversized_pools_fail(self):
        invalid = [dict(opponent=Path("one"), pool=[Path("two")]),
                   dict(include_baseline=True), dict(pool=[Path("one"), Path("./one")]),
                   dict(pool=[Path(str(i)) for i in range(5)]),
                   dict(pool=[Path(str(i)) for i in range(4)], include_baseline=True)]
        for kwargs in invalid:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                loop.opponent_schedule(**kwargs)

    def test_all_fixed_opponents_are_checked(self):
        manifest = [dict(file="first", sha256="a"), dict(file="second", sha256="b")]
        with patch.object(loop, "file_hash", side_effect=["a", "b"]) as hash_file:
            loop.check_opponents(manifest)
            self.assertEqual(hash_file.call_count, 2)
        with patch.object(loop, "file_hash", side_effect=["a", "changed"]), \
             self.assertRaisesRegex(RuntimeError, "Saved opponent changed: second"):
            loop.check_opponents(manifest)

    def collect_fixture(self, development, infeasible=0):
        report = dict(seed=1145000 if development else 1032000, actorHash="hash",
                      sourceHash="source", status="complete", opponentHash="hash",
                      sampledActor=not development, rewardMode="game_win",
                      split="development" if development else "training",
                      games=[dict(complete=True, candidateTeam=0, metrics=dict(
                          infeasiblePaddleSteps=infeasible,
                          playerMaxSpeed=[3.8]*4, playerMaxAcceleration=[14.01]*4,
                          playerMaxPaddleSpeed=[12.0]*4,
                          playerMaxPaddleAcceleration=[100.03]*4,
                          playerMaxReach=[.62]*4))])
        with patch.object(loop, "source_hash", return_value="source"), \
             patch.object(loop, "file_hash", return_value="hash"), \
             patch.object(loop, "evaluate", side_effect=["started", dict(
                 running=False, status="complete: artifacts/player-agents/test.json")]), \
             patch.object(loop.time, "sleep"), \
             patch.object(Path, "read_text", return_value=json.dumps(report)):
            return loop.collect(loop.ROOT / "actor.json", None, report["seed"],
                                32, development, "source")

    def test_training_and_development_require_safe_motor_measurements(self):
        for development in (False, True):
            with self.subTest(development=development):
                self.assertEqual(self.collect_fixture(development),
                                 loop.ROOT / "artifacts/player-agents/test.json")

    def test_unsafe_development_stops_before_another_training_iteration(self):
        for development in (False, True):
            with self.subTest(development=development), self.assertRaisesRegex(ValueError, "Infeasible"):
                self.collect_fixture(development, infeasible=1)

    def envelope(self, result):
        return {"success": True, "data": {"target": {"projectPath": str(loop.ROOT)}, "result": result}}

    def test_success_returns_value(self):
        self.assertEqual(loop.unity_value(self.envelope({"success": True, "result": "complete: report"})), "complete: report")

    def test_outer_failure_is_not_success(self):
        with self.assertRaises(RuntimeError):
            loop.unity_value({"success": False, "data": None, "errors": ["timeout"]})

    def test_inner_failure_is_not_success(self):
        with self.assertRaises(RuntimeError):
            loop.unity_value(self.envelope({"success": False, "result": "running"}))

    def test_wrong_editor_project_is_rejected(self):
        response = self.envelope({"success": True, "result": "running"})
        response["data"]["target"]["projectPath"] = "/private/tmp/different-project"
        with self.assertRaises(RuntimeError):
            loop.unity_value(response)


if __name__ == "__main__":
    unittest.main()

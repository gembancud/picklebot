import copy
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
spec = importlib.util.spec_from_file_location("stage", Path(__file__).resolve().parents[1] / "player-stage-evaluate.py")
stage = importlib.util.module_from_spec(spec); spec.loader.exec_module(stage)


class StageEvaluationTests(unittest.TestCase):
    def state(self):
        return dict(playing=True, busy=False, jobs=[], source="source", generatedCallbackDetection=True)

    def test_ready_state_passes(self):
        stage.validate_state(self.state(), "source", idle=True)

    def test_stopped_or_unreliable_editor_is_rejected(self):
        for key, value in (("playing", False), ("generatedCallbackDetection", False), ("source", "different"), ("busy", 0), ("jobs", None)):
            state = self.state(); state[key] = value
            with self.assertRaises(ValueError): stage.validate_state(state, "source", idle=True)

    def test_busy_or_inconsistent_idle_state_is_rejected(self):
        state = self.state(); state["busy"] = True
        with self.assertRaises(RuntimeError): stage.validate_state(state, "source", idle=True)
        stage.validate_state(state, "source")
        state = self.state(); state["jobs"] = [{"name": "TickFinal"}]
        with self.assertRaises(RuntimeError): stage.validate_state(state, "source", idle=True)

    def test_artifact_paths_must_stay_inside_player_evidence(self):
        valid = "artifacts/player-agents/example.json"
        self.assertEqual(stage.artifact_path(valid), stage.ROOT / valid)
        for value in ("/tmp/outside.json", "artifacts/player-agents/../../../outside.json", {}, None):
            with self.assertRaises((ValueError, TypeError)): stage.artifact_path(value)
        with self.assertRaises(ValueError): stage.artifact_path(valid, "model-comparison-")

    def test_unexpected_job_stops_probe_observation(self):
        state = self.state(); state.update(busy=True, jobs=[dict(name="TickFinal")])
        with mock.patch.object(stage, "unity_state", return_value=state), mock.patch.object(stage.time, "sleep"):
            with self.assertRaisesRegex(RuntimeError, "Unexpected concurrent"):
                stage.wait_probe("source", "TickServeReturn")

    def test_probe_wait_tracks_same_callback_until_idle(self):
        running = self.state(); running.update(busy=True, jobs=[dict(name="<Execute>g__TickServeReturn|4")])
        with mock.patch.object(stage, "unity_state", side_effect=[running, self.state()]) as read, mock.patch.object(stage.time, "sleep"):
            stage.wait_probe("source", "TickServeReturn")
            self.assertEqual(read.call_count, 2)


if __name__ == "__main__": unittest.main()

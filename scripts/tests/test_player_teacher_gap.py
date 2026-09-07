import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from player_teacher_gap import validate_pair
from player_shot_quality import audit_trace
import test_player_shot_quality


class TeacherGapTests(unittest.TestCase):
    def fixture(self):
        reference = test_player_shot_quality.ShotQualityTests().fixture()
        for key in ("sourceHash", "configurationHash", "contactHash", "teamsHash", "protocolHash", "baselineHash"):
            reference[key] = key
        report = dict(reference, version="player-teacher-gap-v1", modes=2, expectedCases=64, sampledActor=False, rows=[])
        for fixture in range(32):
            control = reference["rows"][fixture*11+9]
            for mode in (0, 1):
                report["rows"].append(dict(copy.deepcopy(control), index=fixture*2+mode, mode=mode,
                    fixedCanonicalShot=-1 if mode == 0 else -2, tracePath=f"gap-{fixture}-{mode}",
                    traceHash=control["traceHash"] if mode == 0 else "actor"))
        return report, reference

    def test_matched_controls(self):
        validate_pair(*self.fixture())

    def test_changed_control_source_or_start_is_rejected(self):
        for mutate in (lambda r: r.update(sourceHash="changed"),
                       lambda r: r["rows"][0].update(traceHash="changed"),
                       lambda r: r["rows"][1].update(canonicalBall=[9, 9, 9]),
                       lambda r: r["rows"].pop()):
            report, reference = self.fixture(); mutate(report)
            with self.assertRaises(ValueError): validate_pair(report, reference)

    def test_actor_outcome_cannot_inherit_teacher_success(self):
        report, reference = self.fixture(); report["rows"][1]["events"] = []
        with self.assertRaises(ValueError): validate_pair(report, reference)

    def shadow_trace(self):
        records = test_player_shot_quality.ShotQualityTests().trace()
        result = []
        for record in records:
            result.append(record)
            if record["type"] == "decision" and record["player"] < 2:
                result.append(dict(type="shadow-teacher", player=record["player"], tick=record["tick"],
                                   action=dict(moveX=1, moveZ=0, attempt=True, shot=3)))
        return result

    def check(self, records, allow=True):
        row = test_player_shot_quality.ShotQualityTests().fixture()["rows"][0]
        decisions = []
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "trace.jsonl"
            path.write_text("\n".join(json.dumps(r) for r in records))
            result = audit_trace(path, row, allow_shadow=allow, on_decision=decisions.append)
        return result, decisions

    def test_shadow_labels_do_not_replace_actions(self):
        result, decisions = self.check(self.shadow_trace())
        self.assertEqual(result["shadow"]["teacherHitActorLeave"], 2)
        self.assertEqual(result["shadow"]["movementSquaredError"], 2)
        self.assertTrue(all(not d["action"]["attempt"] for d in decisions))
        self.assertTrue(all(d["action"]["shot"] == 0 for d in decisions))

    def test_missing_wrong_owner_or_unexpected_labels_fail(self):
        records = self.shadow_trace()
        with self.assertRaises(ValueError): self.check(records, allow=False)
        for mutate in (lambda r: r.pop(1), lambda r: r[1].update(player=1),
                       lambda r: r[1].update(tick=12), lambda r: r[1]["action"].update(moveX=float("nan"))):
            changed = copy.deepcopy(records); mutate(changed)
            with self.assertRaises(ValueError): self.check(changed)


if __name__ == "__main__": unittest.main()

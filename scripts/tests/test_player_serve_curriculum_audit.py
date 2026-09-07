from pathlib import Path
import sys
import unittest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from player_serve_curriculum_audit import phase_coverage, validate_source_schedule


class ServeCurriculumAuditTests(unittest.TestCase):
    def test_extra_source_requires_explicit_plan(self):
        plan = dict(additionalTraining=["short", "deep"], trainingReport="serve")
        sources = [dict(report=p) for p in ("serve", "short", "deep", "normal")]
        with self.assertRaisesRegex(ValueError, "schedule"):
            validate_source_schedule(sources, plan, "training")
        plan["additionalTraining"].append("normal")
        validate_source_schedule(sources, plan, "training")

    def test_reordered_or_wrong_primary_source_is_rejected(self):
        plan = dict(additionalDevelopment=["short", "deep"], developmentReport="serve")
        with self.assertRaisesRegex(ValueError, "schedule"):
            validate_source_schedule([dict(report=p) for p in ("serve", "deep", "short")], plan, "development")
        with self.assertRaisesRegex(ValueError, "Primary"):
            validate_source_schedule([dict(report=p) for p in ("wrong", "short", "deep")], plan, "development")

    def test_missing_third_shot_phase_is_rejected(self):
        x = torch.zeros(3, 54); x[0, 40] = 1; x[1:, 42] = 1
        tensors = [(x, torch.zeros(3, 4))]
        with self.assertRaisesRegex(ValueError, "no examples"):
            phase_coverage(tensors, ["serveFlight", "returnFlight", "rally"])
        x[1, 42] = 0; x[1, 41] = 1
        self.assertEqual(phase_coverage(tensors, ["returnFlight"])["returnFlight"], 1)

    def test_ambiguous_phase_is_rejected(self):
        x = torch.zeros(1, 54); x[0, 40:42] = 1
        with self.assertRaisesRegex(ValueError, "Invalid phase"):
            phase_coverage([(x, torch.zeros(1, 4))], [])


if __name__ == "__main__":
    unittest.main()

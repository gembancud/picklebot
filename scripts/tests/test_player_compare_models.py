import copy
import importlib.util
from pathlib import Path
import sys
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("player_compare_models", SCRIPTS / "player-compare-models.py")
comparison = importlib.util.module_from_spec(spec); spec.loader.exec_module(comparison)


class ModelComparisonTests(unittest.TestCase):
    def test_current_actor_keeps_its_training_source(self):
        self.assertEqual(comparison.actor_provenance({'sourceHash': 'current'}, 'current'),
                         dict(trainingSourceHash='current', historicalCandidate=False))

    def test_historical_actor_requires_opt_in_and_keeps_old_hash(self):
        with self.assertRaisesRegex(ValueError, 'explicit'):
            comparison.actor_provenance({'sourceHash': 'old'}, 'current')
        self.assertEqual(comparison.actor_provenance({'sourceHash': 'old'}, 'current', True),
                         dict(trainingSourceHash='old', historicalCandidate=True))

    def test_historical_permission_does_not_allow_missing_provenance(self):
        for metadata in ({}, {'sourceHash': ''}, {'sourceHash': None}):
            with self.subTest(metadata=metadata), self.assertRaises(ValueError):
                comparison.actor_provenance(metadata, 'current', True)

    def plan(self):
        return dict(split="development", sampledActor=False, gamesPerGroup=1,
                    seedList=list(range(1141000, 1141008)),
                    groups=[dict(group=g, candidateTeam=(g//2)%2, sampleBaseline=g>=4,
                                 swapPartnerIdentities=bool(g&1), seeds=[1141000+g]) for g in range(8)])

    def test_exact_paired_schedule_passes(self):
        comparison.validate_schedule(self.plan(), 1141000)

    def test_final_seeds_and_final_labels_are_rejected(self):
        with self.assertRaises(ValueError): comparison.validate_schedule(self.plan(), 1200000)
        plan = self.plan(); plan["split"] = "final"
        with self.assertRaises(ValueError): comparison.validate_schedule(plan, 1141000)

    def test_missing_or_reassigned_group_is_rejected(self):
        plan = self.plan(); plan["groups"].pop()
        with self.assertRaises(ValueError): comparison.validate_schedule(plan, 1141000)
        for field, value in (("candidateTeam", 1), ("sampleBaseline", True), ("swapPartnerIdentities", True), ("seeds", [1141001])):
            plan = copy.deepcopy(self.plan()); plan["groups"][0][field] = value
            with self.assertRaises(ValueError): comparison.validate_schedule(plan, 1141000)

    def test_sampled_actor_or_different_game_count_is_rejected(self):
        for field, value in (("sampledActor", True), ("gamesPerGroup", 2), ("seedList", [1141000])):
            plan = self.plan(); plan[field] = value
            with self.assertRaises(ValueError): comparison.validate_schedule(plan, 1141000)

    def test_sampled_schedule_requires_explicit_matching_request(self):
        plan = self.plan(); plan["sampledActor"] = True
        comparison.validate_schedule(plan, 1141000, sampled_actor=True)
        with self.assertRaises(ValueError): comparison.validate_schedule(plan, 1141000)
        with self.assertRaises(ValueError): comparison.validate_schedule(self.plan(), 1141000, sampled_actor=True)

    def test_sampled_schedule_still_rejects_final_seeds_and_changed_pairing(self):
        plan = self.plan(); plan["sampledActor"] = True
        with self.assertRaises(ValueError): comparison.validate_schedule(plan, 1200000, sampled_actor=True)
        plan["groups"][1]["swapPartnerIdentities"] = False
        with self.assertRaises(ValueError): comparison.validate_schedule(plan, 1141000, sampled_actor=True)

    def test_sampling_request_must_be_boolean(self):
        for mode in (1, 0, "true", None):
            with self.assertRaises(ValueError): comparison.validate_schedule(self.plan(), 1141000, sampled_actor=mode)

    def test_default_rejects_stale_contact_override(self):
        comparison.validate_comparison_override({}, {}, 0)
        record = dict(flatPitchOffsetDegrees=-3, experimentalContactOverride=True, candidateContactParameters=[1])
        with self.assertRaises(ValueError): comparison.validate_comparison_override(record, record, 0)
        comparison.validate_comparison_override(record, record, -3)

    def test_contact_override_matches_the_reserved_parameters(self):
        plan = dict(flatPitchOffsetDegrees=-3, experimentalContactOverride=True, candidateContactParameters=[1])
        report = copy.deepcopy(plan); report["candidateContactParameters"] = [2]
        with self.assertRaises(ValueError): comparison.validate_comparison_override(plan, report, -3)
        report = copy.deepcopy(plan); report["experimentalContactOverride"] = False
        with self.assertRaises(ValueError): comparison.validate_comparison_override(plan, report, -3)
        for offset in (7, float("nan")):
            with self.assertRaises(ValueError): comparison.validate_comparison_override(plan, plan, offset)


if __name__ == "__main__": unittest.main()

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import torch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from player_actor import Actor

spec = importlib.util.spec_from_file_location("player_imitation", Path(__file__).parents[1] / "player-agents-imitate.py")
imitation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(imitation)


class RetentionLossTests(unittest.TestCase):
    def test_serve_subset_keeps_selected_owned_labels_without_changing_source(self):
        x = torch.zeros(5,54); x[range(5),torch.tensor([39,40,41,40,43])] = 1
        y = torch.arange(20).reshape(5,4).float()
        sx, sy, meta = imitation.serve_flight_subset(x,y)
        self.assertTrue(torch.equal(sx,x[[1,3]])); self.assertTrue(torch.equal(sy,y[[1,3]]))
        self.assertEqual(meta['originalRows'],5); self.assertEqual(meta['observationIndex'],40)
        self.assertEqual(meta['selectedIndicesHash'], imitation.serve_flight_subset(x,y)[2]['selectedIndicesHash'])
        sx[0,40] = 0; self.assertEqual(x[1,40],1)

    def test_serve_subset_rejects_missing_or_ambiguous_phase(self):
        for indices in ([], [39], [39,40]):
            x = torch.zeros(2,54); x[:,indices] = 1
            with self.assertRaises(ValueError): imitation.serve_flight_subset(x,torch.zeros(2,4))

    def test_disabled_option_does_not_require_a_parent(self):
        imitation.validate_retention_options(0, None)
        imitation.validate_retention_options(10, "actor.json")

    def test_invalid_weight_and_missing_parent_are_rejected(self):
        for weight in (-1, float("inf"), float("nan"), True):
            with self.assertRaises(ValueError): imitation.validate_retention_options(weight, "actor.json")
        with self.assertRaises(ValueError): imitation.validate_retention_options(1, None)

    def test_identical_outputs_have_zero_retention_cost(self):
        torch.manual_seed(41); outputs = torch.randn(24, 12)
        loss, metrics = imitation.retention_from_outputs(outputs, outputs)
        self.assertAlmostEqual(loss.item(), 0, places=6)
        self.assertEqual(metrics["retentionHitFlipRate"], 0)
        self.assertEqual(metrics["retentionShotFlipRate"], 0)

    def test_each_output_component_is_penalized(self):
        for index, metric in ((0,"retentionMovementLatentMSE"),(2,"retentionHitKL"),(3,"retentionShotKL")):
            old = torch.zeros(4,12); new = old.clone(); new[:,index] = 2
            loss, metrics = imitation.retention_from_outputs(new,old)
            self.assertGreater(loss.item(),0)
            self.assertGreater(metrics[metric],0)

    def test_reference_has_no_gradient_and_student_moves_toward_it(self):
        old = torch.zeros(8,12,requires_grad=True)
        new = torch.full((8,12),.5,requires_grad=True)
        with torch.no_grad(): new[:,3] = 2
        before,_ = imitation.retention_from_outputs(new,old)
        before.backward()
        self.assertIsNone(old.grad)
        with torch.no_grad(): new -= .1 * new.grad
        after,_ = imitation.retention_from_outputs(new,old)
        self.assertLess(after.item(),before.item())

    def test_extreme_hit_logits_remain_finite(self):
        old = torch.zeros(4,12); new = old.clone()
        old[:,2] = torch.tensor([-1000,1000,-1000,1000])
        new[:,2] = -old[:,2]
        loss,metrics = imitation.retention_from_outputs(new,old)
        self.assertTrue(torch.isfinite(loss))
        self.assertEqual(metrics["retentionHitFlipRate"],1)

    def test_malformed_or_nonfinite_outputs_fail(self):
        for new in (torch.zeros(2,11),torch.zeros(0,12),torch.full((2,12),float("nan"))):
            with self.assertRaises(ValueError): imitation.retention_from_outputs(new,torch.zeros(2,12))


class InitialActorTests(unittest.TestCase):
    def test_source_balancing_gives_small_and_large_datasets_equal_mass(self):
        weights = imitation.source_sampling_weights([10, 1000, 100])
        self.assertEqual(len(weights), 1110)
        for start, end in ((0, 10), (10, 1010), (1010, 1110)):
            self.assertAlmostEqual(weights[start:end].sum().item(), 1.0)

    def test_source_balancing_rejects_empty_or_invalid_sources(self):
        for lengths in ([], [0], [-1], [2.5], [True]):
            with self.assertRaises(ValueError): imitation.source_sampling_weights(lengths)

    def test_validation_selection_uses_equal_source_metrics(self):
        metrics = imitation.average_source_metrics([dict(loss=1.0, hitRecall=.8), dict(loss=3.0, hitRecall=1.0)])
        self.assertEqual(metrics, dict(loss=2.0, hitRecall=.9))
        with self.assertRaises(ValueError): imitation.average_source_metrics([])
        with self.assertRaises(ValueError): imitation.average_source_metrics([dict(loss=1), dict(other=2)])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "actor.json"
        self.model = Actor(8)
        self.meta = dict(sourceHash="current", configurationHash="physics", contactModelHash="contact",
                         protocolHash="protocol", baselineManifestHash="baseline", trainingSteps=10)
        self.path.write_text(json.dumps(self.model.export(self.meta)))
        self.source = patch.object(imitation, "source_hash", return_value="current")
        self.source.start()
        self.addCleanup(self.source.stop)

    def test_current_actor_preserves_exact_parameters_before_fitting(self):
        loaded, parent = imitation.initial_model(self.path, 8, self.meta)
        self.assertEqual(parent["trainingSteps"], 10)
        for a, b in zip(self.model.parameters(), loaded.parameters()):
            self.assertTrue(torch.equal(a, b))

    def test_stale_source_is_rejected(self):
        self.path.write_text(json.dumps(self.model.export({**self.meta, "sourceHash": "old"})))
        with self.assertRaisesRegex(ValueError, "sourceHash"):
            imitation.initial_model(self.path, 8, self.meta)

    def test_different_configuration_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "configurationHash"):
            imitation.initial_model(self.path, 8, {**self.meta, "configurationHash": "other"})

    def test_wrong_hidden_width_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "width"):
            imitation.initial_model(self.path, 16, self.meta)

    def test_absent_parent_keeps_fresh_initialization(self):
        model, parent = imitation.initial_model(None, 8, self.meta)
        self.assertIsNone(parent)
        self.assertEqual(model.layers[0].out_features, 8)

    def test_explicit_historical_initialization_keeps_parent_provenance_and_file(self):
        self.path.write_text(json.dumps(self.model.export({**self.meta, "sourceHash": "older-runtime"})))
        before = self.path.read_bytes()
        loaded, parent = imitation.initial_model(self.path, 8, self.meta, allow_historical=True)
        self.assertEqual(parent["sourceHash"], "older-runtime")
        self.assertEqual(self.path.read_bytes(), before)
        for a, b in zip(self.model.parameters(), loaded.parameters()):
            self.assertTrue(torch.equal(a, b))

    def test_historical_opt_in_does_not_relax_other_compatibility_checks(self):
        for key in ("configurationHash", "contactModelHash", "protocolHash", "baselineManifestHash"):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, key):
                imitation.initial_model(self.path, 8, {**self.meta, key: "other"}, allow_historical=True)

    def test_historical_opt_in_requires_an_actor_and_a_known_source(self):
        with self.assertRaisesRegex(ValueError, "requires"):
            imitation.initial_model(None, 8, self.meta, allow_historical=True)
        self.path.write_text(json.dumps(self.model.export({**self.meta, "sourceHash": ""})))
        with self.assertRaisesRegex(ValueError, "sourceHash"):
            imitation.initial_model(self.path, 8, self.meta, allow_historical=True)

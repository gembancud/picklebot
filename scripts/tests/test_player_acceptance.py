import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from player_acceptance import audit_baseline, validate_runner_artifacts, wilson_lower


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.protocol = json.loads((SCRIPTS.parent / "config/player-agents/evaluation-v1.json").read_text())
        self.expected = dict(sourceHash="fixture-source", actorHash="fixture-actor", configurationHash="fixture-physics",
                             contactModelHash="fixture-contact", protocolHash="fixture-protocol",
                             baselineManifestHash="fixture-manifest", opponentHash="fixture-baseline")
        self.reports = []
        for mode in ("baseline / maximum probability", "baseline / sampled"):
            for team in (0, 1):
                for swapped in (False, True):
                    report = dict(self.expected, split="final", status="complete", historicalCandidate=False,
                                  actorTrainingSourceHash="fixture-source", dataPath="", opponentMode=mode,
                                  swapPartnerIdentities=swapped, sampledActor=False, physicsHz=240, decisionTicks=12,
                                  actionLatencyTicks=6, games=[], rallies=[])
                    for _ in range(10):
                        seed = 1200000 + len(self.reports) * 10 + len(report["games"])
                        score = [0, 0]; score[team] = 11
                        identities = list(range(4))
                        if swapped:
                            identities[team * 2], identities[team * 2 + 1] = identities[team * 2 + 1], identities[team * 2]
                        counts = [int(i // 2 == team) for i in range(4)]
                        first = [dict(player=i, identity=identities[i], observationPlayer=i, observationTick=0, applyTick=6)
                                 if counts[i] else None for i in range(4)]
                        report["games"].append(dict(gameSeed=seed, candidateTeam=team, complete=True, winner=team, score=score, rallies=1,
                                                   identityBySeat=identities, randomSeedBySeat=[seed * 397 + i * 7919 for i in identities],
                                                   decisionCounts=counts, firstDecisions=first))
                        report["rallies"].append(dict(gameSeed=seed, candidateTeam=team, winner=team, legalHits=[1, 1, 1, 1]))
                    self.reports.append(report)

    def test_balanced_synthetic_fixture_passes_baseline_checks_only(self):
        result = audit_baseline(self.reports, self.protocol, self.expected)
        self.assertTrue(result["baselineChecksPassed"])
        self.assertEqual(result["games"], 80)
        self.assertGreater(result["pooledWilsonLowerBound"], .95)

    def test_incomplete_game_stays_in_denominator(self):
        game = self.reports[0]["games"][0]
        game.update(complete=False, winner=-1)
        result = audit_baseline(self.reports, self.protocol, self.expected)
        self.assertEqual((result["games"], result["gameWins"], result["incompleteGames"]), (80, 79, 1))

    def test_exact_half_wins_does_not_pass_wilson_gate(self):
        self.assertLess(wilson_lower(40, 80, self.protocol["wilsonZ"]), .5)

    def test_omitted_or_repeated_game_is_rejected(self):
        for reports in (self.reports[:-1], self.reports + [copy.deepcopy(self.reports[0])]):
            with self.assertRaises(ValueError): audit_baseline(reports, self.protocol, self.expected)

    def test_training_seed_is_rejected(self):
        self.reports[0]["games"][0]["gameSeed"] = 1000000
        with self.assertRaises(ValueError): audit_baseline(self.reports, self.protocol, self.expected)

    def test_missing_partner_or_timing_evidence_is_rejected(self):
        for field in ("swapPartnerIdentities", "physicsHz"):
            reports = copy.deepcopy(self.reports); del reports[0][field]
            with self.assertRaises(ValueError): audit_baseline(reports, self.protocol, self.expected)

    def test_stale_source_is_rejected(self):
        self.reports[0]["sourceHash"] = "old-source"
        with self.assertRaises(ValueError): audit_baseline(self.reports, self.protocol, self.expected)

    def test_experimental_contact_correction_is_never_final_acceptance(self):
        for field, value in (("flatPitchOffsetDegrees", -3), ("experimentalContactOverride", True)):
            reports = copy.deepcopy(self.reports); reports[0][field] = value
            with self.assertRaisesRegex(ValueError, "Experimental contact"):
                audit_baseline(reports, self.protocol, self.expected)

    def test_label_without_real_partner_assignment_is_rejected(self):
        self.reports[1]["games"][0]["identityBySeat"] = [0, 1, 2, 3]
        with self.assertRaisesRegex(ValueError, "identities"):
            audit_baseline(self.reports, self.protocol, self.expected)

    def test_rng_streams_must_move_with_identity(self):
        self.reports[1]["games"][0]["randomSeedBySeat"].reverse()
        with self.assertRaisesRegex(ValueError, "RNG"):
            audit_baseline(self.reports, self.protocol, self.expected)

    def test_wrong_observation_owner_or_latency_is_rejected(self):
        for field, value in (("observationPlayer", 2), ("applyTick", 0), ("identity", 1)):
            reports = copy.deepcopy(self.reports)
            reports[0]["games"][0]["firstDecisions"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                audit_baseline(reports, self.protocol, self.expected)

    def test_caller_cannot_omit_provenance_checks(self):
        del self.expected["contactModelHash"]
        with self.assertRaises(ValueError): audit_baseline(self.reports, self.protocol, self.expected)

    def test_missing_seat_returns_fail(self):
        for report in self.reports:
            for rally in report["rallies"]: rally["legalHits"][3] = 0
        self.assertFalse(audit_baseline(self.reports, self.protocol, self.expected)["checks"]["allSeatsReturn"])

    def test_truncated_rallies_are_not_hidden(self):
        for report in self.reports:
            for rally in report["rallies"]: rally["winner"] = -1
        self.assertFalse(audit_baseline(self.reports, self.protocol, self.expected)["checks"]["truncation"])


class RunnerArtifactTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.folder = self.root / "artifacts/player-agents/development-evaluation-fixture"
        self.folder.mkdir(parents=True)
        snapshot = self.folder / "collector.cs"; snapshot.write_text("// test collector only\n")
        self.plan_path = self.folder / "evaluation-plan.json"
        self.report_path = self.folder / "group-0.json"
        self.completion_path = self.folder / "completion.json"
        self.plan = dict(split="development", sourceHash="source", actorHash="actor", protocolHash="protocol",
                         baselineManifestHash="baseline", contactModelHash="contact", opponentHash="opponent",
                         collectorHash=self.hash(snapshot), sampledActor=False, seedList=list(range(1126000, 1126008)),
                         groups=[dict(group=g, swapPartnerIdentities=bool(g & 1), candidateTeam=(g // 2) % 2,
                                      sampleBaseline=g >= 4, seeds=[1126000 + g]) for g in range(8)])
        self.plan_path.write_text(json.dumps(self.plan))
        self.report = {k: v for k, v in self.plan.items() if k not in ("groups", "seedList")}
        self.report.update(collectorSnapshotPath=str(snapshot), evaluationPlanPath=str(self.plan_path),
                           evaluationPlanHash=self.hash(self.plan_path), group=0, swapPartnerIdentities=False,
                           initialCandidateTeam=0, opponentMode="baseline / maximum probability",
                           games=[dict(gameSeed=1126000, candidateTeam=0)])
        self.save_report_and_completion()

    @staticmethod
    def hash(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def save_report_and_completion(self):
        self.report_path.write_text(json.dumps(self.report))
        self.completion_path.write_text(json.dumps(dict(status="complete", sourceHash="source", actorHash="actor", games=8,
                                                        evaluationPlanHash=self.report["evaluationPlanHash"],
                                                        reportHashes={self.report_path.name: self.hash(self.report_path)})))

    def validate(self):
        return validate_runner_artifacts(self.report_path, self.report, self.root, self.hash)

    def test_terminal_snapshot_and_schedule_are_accepted(self):
        self.assertEqual(self.validate(), self.report["evaluationPlanHash"])

    def test_changed_snapshot_or_report_is_rejected(self):
        self.report_path.write_text("{}")
        with self.assertRaisesRegex(ValueError, "report changed"): self.validate()
        self.save_report_and_completion()
        (self.folder / "collector.cs").write_text("// modified\n")
        with self.assertRaisesRegex(ValueError, "collector"): self.validate()

    def test_missing_terminal_record_is_rejected(self):
        self.completion_path.unlink()
        with self.assertRaises(OSError): self.validate()

    def test_game_or_sampling_cannot_depart_from_reserved_schedule(self):
        self.report["games"][0]["gameSeed"] += 100
        self.save_report_and_completion()
        with self.assertRaisesRegex(ValueError, "reserved group"): self.validate()
        self.report["games"][0]["gameSeed"] -= 100
        self.report["sampledActor"] = True
        self.save_report_and_completion()
        with self.assertRaisesRegex(ValueError, "sampledActor"): self.validate()


if __name__ == "__main__": unittest.main()

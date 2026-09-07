import copy
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import player_actor


class IncomingReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name).resolve()
        self.snapshot = root / "artifacts/player-agents/collector.cs"
        self.snapshot.parent.mkdir(parents=True)
        self.snapshot.write_text("// recorded collector\n")
        self.root = patch.object(player_actor, "ROOT", root)
        self.root.start(); self.addCleanup(self.root.stop)
        self.report = dict(candidateOnly=True, fixtureVersion="incoming-skill-v1", games=0, baselineOpponent=False,
                           physicsHz=240, decisionTicks=12, actionLatencyTicks=6, requestedFixtures=2,
                           collectorSnapshotPath="artifacts/player-agents/collector.cs",
                           collectorHash=hashlib.sha256(self.snapshot.read_bytes()).hexdigest(),
                           gameResults=[dict(complete=False, winner=-1), dict(complete=False, winner=-1)])

    def test_recorded_injected_fixtures_are_valid(self):
        player_actor.validate_incoming_report(self.report)

    def test_injected_fixtures_cannot_claim_match_wins(self):
        for field, value in (("games", 1), ("baselineOpponent", True), ("candidateOnly", False)):
            with self.subTest(field=field), self.assertRaises(ValueError):
                player_actor.validate_incoming_report({**self.report, field: value})
        report = copy.deepcopy(self.report)
        report["gameResults"][0].update(complete=True, winner=0)
        with self.assertRaises(ValueError):
            player_actor.validate_incoming_report(report)

    def test_changed_collector_snapshot_is_rejected(self):
        self.snapshot.write_text("// changed\n")
        with self.assertRaisesRegex(ValueError, "snapshot changed"):
            player_actor.validate_incoming_report(self.report)

    def test_wrong_timing_or_incomplete_fixture_count_is_rejected(self):
        for field, value in (("physicsHz", 120), ("decisionTicks", 6), ("actionLatencyTicks", 0), ("requestedFixtures", 4)):
            with self.subTest(field=field), self.assertRaises(ValueError):
                player_actor.validate_incoming_report({**self.report, field: value})

    def profile_report(self, profile):
        report = copy.deepcopy(self.report)
        kitchen = profile == "kitchen"
        report.update(skillProfile=profile, ranges=dict(lane=[-2, 2] if kitchen else [-2.7, 2.7],
            height=[1.1, 1.5], ballDepth=[.15, .7], velocityX=[-.8, .8], velocityY=[.8, 1.8],
            velocityZ=[-3.6, -2.7] if kitchen else [-8.7, -7.3],
            playerDepth=[1.8, 3.2] if kitchen else [3.4, 6.6], playerXJitter=[-.35, .35]))
        for team, game in enumerate(report["gameResults"]):
            starts = []
            for player in range(4):
                sign = 1 if player < 2 else -1
                depth = (2.1 if kitchen else 4.5) if player // 2 == team else 6
                starts.append([(1.55 if player % 2 == 0 else -1.55) * sign, 0, -sign * depth])
            game.update(candidateTeam=team, canonicalBall=[0, 1.2, .4],
                        canonicalVelocity=[0, 1.2, -3 if kitchen else -8], playerStarts=starts,
                        legalHit=True, legalLanding=True, legalKitchenGroundstroke=kitchen)
        return report

    def test_both_disclosed_profiles_preserve_mirrored_reset_ranges(self):
        for profile in ("deep", "kitchen"):
            player_actor.validate_incoming_report(self.profile_report(profile))

    def test_changed_profile_or_reset_ranges_are_rejected(self):
        for mutation in (lambda r: r.update(skillProfile="easy"),
                         lambda r: r["ranges"].update(playerDepth=[0, 8]),
                         lambda r: r["ranges"].update(velocityZ=[-3.6, float("nan")])):
            report = self.profile_report("kitchen"); mutation(report)
            with self.assertRaises(ValueError): player_actor.validate_incoming_report(report)

    def test_out_of_range_or_nonfinite_initial_ball_is_rejected(self):
        for field, value in (("canonicalBall", [3, 1.2, .4]),
                             ("canonicalVelocity", [0, 1.2, -8]),
                             ("canonicalVelocity", [0, float("nan"), -3])):
            report = self.profile_report("kitchen"); report["gameResults"][0][field] = value
            with self.assertRaises(ValueError): player_actor.validate_incoming_report(report)

    def test_wrong_player_side_or_depth_is_rejected(self):
        for player, position in ((0, [1.55, 0, 2.1]), (0, [1.55, 0, -6]), (2, [-1.55, 0, 2.1])):
            report = self.profile_report("kitchen"); report["gameResults"][0]["playerStarts"][player] = position
            with self.assertRaises(ValueError): player_actor.validate_incoming_report(report)

    def test_groundstroke_or_landing_requires_a_legal_hit(self):
        report = self.profile_report("kitchen"); report["gameResults"][0]["legalHit"] = False
        with self.assertRaises(ValueError): player_actor.validate_incoming_report(report)

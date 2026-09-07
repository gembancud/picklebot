import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from player_skill_retention import coverage, compare, actor_only_short, validate_replayed_action


def fixture():
    report = dict(status="complete", error=None, fixtureVersion="coverage-development-v1",
        split="development", seedBase=1115000, lanes=[-2.6, -.2, .2, 2.6], depths=[3.5, 6],
        physicsHz=240, decisionTicks=12, actionLatencyTicks=6,
        incomingCanonicalPosition=[0, 1.2, .4], incomingCanonicalVelocity=[0, 1.2, -8],
        sourceHash="source", configurationHash="config", contactModelHash="contact",
        protocolHash="protocol", scriptHash="script", actorHash="parent", cases=[])
    for index in range(48):
        number = index // 3
        team = number // 8
        mode = ["learned", "movement_disabled", "diagnostic_teacher"][index % 3]
        report["cases"].append(dict(mode=mode, seed=1115000 + number, candidateTeam=team,
            lane=report["lanes"][number % 4], depth=report["depths"][number // 4 % 2],
            legalHit=mode != "movement_disabled", legalLanding=mode != "movement_disabled",
            movementDistance=[0]*4,
            metrics=dict(infeasiblePaddleSteps=0, playerMaxSpeed=[3.8]*4,
                playerMaxAcceleration=[14]*4, playerMaxPaddleSpeed=[12]*4,
                playerMaxPaddleAcceleration=[100]*4, playerMaxReach=[.62]*4),
            decisions=[dict(player=p, observationTick=0, applyTick=6, observation=[0]*54)
                       for p in range(team * 2, team * 2 + 2)]))
    return report


class RetentionTests(unittest.TestCase):
    def test_equal_coverage_passes_without_claiming_match_strength(self):
        parent = fixture(); child = copy.deepcopy(parent); child["actorHash"] = "child"
        result = compare(parent, child)
        self.assertTrue(result["retentionChecksPassed"])
        self.assertEqual(len(result["groups"]), 4)
        self.assertIn("does not prove match strength", result["limitation"])

    def test_depth_regression_is_not_hidden_by_aggregate(self):
        parent = fixture(); child = copy.deepcopy(parent); child["actorHash"] = "child"
        child["cases"][12].update(legalHit=False, legalLanding=False)
        result = compare(parent, child)
        self.assertFalse(result["retentionChecksPassed"])
        self.assertEqual(result["groups"][1]["regressions"], ["contacts", "legalLandings"])

    def test_changed_provenance_and_same_actor_are_rejected(self):
        for key in ("sourceHash", "configurationHash", "contactModelHash", "protocolHash", "scriptHash", "actorHash"):
            parent = fixture(); child = copy.deepcopy(parent); child["actorHash"] = "child"
            child[key] = "parent" if key == "actorHash" else "changed"
            with self.subTest(key=key), self.assertRaises(ValueError): compare(parent, child)

    def test_incomplete_or_changed_schedule_is_rejected(self):
        for mutation in (lambda r: r["cases"].pop(), lambda r: r.update(split="final"),
                         lambda r: r["cases"][0].update(seed=1), lambda r: r.update(decisionTicks=6)):
            report = fixture(); mutation(report)
            with self.assertRaises(ValueError): coverage(report)

    def test_all_four_motor_limits_are_checked(self):
        for player in range(4):
            report = fixture(); report["cases"][0]["metrics"]["playerMaxSpeed"][player] = 4
            with self.assertRaises(ValueError): coverage(report)

    def test_decision_ownership_timing_and_finiteness_are_checked(self):
        for update in (dict(player=2), dict(observationTick=1), dict(applyTick=7),
                       dict(observation=[float("nan")]*54), dict(observation=[0]*53)):
            report = fixture(); report["cases"][0]["decisions"][0].update(update)
            with self.assertRaises(ValueError): coverage(report)
        for duplicate in (True, False):
            report = fixture(); decisions = report["cases"][0]["decisions"]
            if duplicate: decisions.append(copy.deepcopy(decisions[0]))
            else: decisions.pop()
            with self.assertRaises(ValueError): coverage(report)

    def test_outcome_and_disabled_movement_are_checked(self):
        for mutation in (lambda c: c.update(legalHit=False, legalLanding=True),
                         lambda c: c.update(legalHit=1),
                         lambda c: c.update(movementDistance=[.01, 0, 0, 0])):
            report = fixture(); mutation(report["cases"][1])
            with self.assertRaises(ValueError): coverage(report)

    def test_short_report_requires_only_actor_control(self):
        report = dict(status="complete", split="development", skillProfile="kitchen", actorHash="child",
            teacherProbability=0, teacherDecisions=0, actorDecisions=1, rows=1,
            gameResults=[dict(legalHit=True, legalLanding=True, legalKitchenGroundstroke=True)])
        rows = [dict(executedBy="actor")]
        self.assertEqual(actor_only_short(report, rows, "child")["legalLandings"], 1)
        for update in (dict(teacherProbability=.1), dict(teacherDecisions=1), dict(actorDecisions=2),
                       dict(rows=2), dict(actorHash="other"), dict(split="training")):
            with self.assertRaises(ValueError): actor_only_short({**report, **update}, rows, "child")
        with self.assertRaises(ValueError): actor_only_short(report, [dict(executedBy="teacher")], "child")

    def test_replay_rejects_changed_or_nonfinite_applied_actions(self):
        action = dict(moveX=.2, moveZ=-.3, attempt=True, shot=4)
        validate_replayed_action(action, [.2, -.3], True, 4)
        for update in (dict(moveX=.21), dict(moveZ=float("nan")), dict(moveX=float("inf")),
                       dict(attempt=1), dict(attempt=False), dict(shot=4.), dict(shot=5)):
            with self.assertRaises(ValueError): validate_replayed_action({**action, **update}, [.2, -.3], True, 4)

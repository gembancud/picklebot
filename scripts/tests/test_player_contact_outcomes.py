import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from player_contact_outcomes import classify_shot, summarize, summarize_execution, validate_contact_override, summarize_fault_context


class FaultContextTests(unittest.TestCase):
    def report(self, team=0, hitter=0):
        return dict(rallies=[dict(candidateTeam=team, gameSeed=1198000, rally=1, events=[
            dict(kind="hit", player=hitter, time=1.),
            dict(kind="fault", player=team*2, winner=1-team, fault="BodyContact", time=1.1)])])

    def test_both_ends_distinguish_own_partner_and_opponent_hits(self):
        for team in (0, 1):
            for hitter, context in ((team*2, "after own hit"), (team*2+1, "after teammate hit"),
                                    ((1-team)*2, "after opponent hit")):
                result = summarize_fault_context(self.report(team, hitter))
                self.assertEqual(result["bodyFaultsByContext"], {context: 1})
                self.assertAlmostEqual(result["bodyFaults"][0]["secondsSinceHit"], .1)

    def test_no_prior_hit_is_unknown_not_an_incoming_return(self):
        report = self.report(); report["rallies"][0]["events"].pop(0)
        row = summarize_fault_context(report)["bodyFaults"][0]
        self.assertEqual(row["context"], "before recorded hit")
        self.assertIsNone(row["secondsSinceHit"])

    def test_bounce_and_new_hit_update_context(self):
        report = self.report(); events = report["rallies"][0]["events"]
        events.insert(1, dict(kind="bounce", time=1.02))
        self.assertTrue(summarize_fault_context(report)["bodyFaults"][0]["bounceSinceHit"])
        events.insert(2, dict(kind="hit", player=2, time=1.05))
        row = summarize_fault_context(report)["bodyFaults"][0]
        self.assertEqual(row["context"], "after opponent hit")
        self.assertFalse(row["bounceSinceHit"])

    def test_opponent_fault_is_not_a_candidate_fault(self):
        report = self.report(); report["rallies"][0]["events"][-1].update(player=2, winner=0)
        self.assertEqual(summarize_fault_context(report)["candidateFaults"], {})

    def test_each_rally_resets_prior_hit(self):
        report = self.report(); second = copy.deepcopy(report["rallies"][0])
        second["events"].pop(0); report["rallies"].append(second)
        self.assertEqual(summarize_fault_context(report)["bodyFaultsByContext"],
                         {"after own hit": 1, "before recorded hit": 1})

    def test_malformed_ownership_and_time_fail(self):
        for update in (dict(winner=-1), dict(player=2), dict(time=.9), dict(time=float("nan"))):
            report = self.report(); report["rallies"][0]["events"][-1].update(update)
            with self.assertRaises(ValueError): summarize_fault_context(report)


class ContactOutcomeTests(unittest.TestCase):
    def fixture(self):
        shot = dict(eventIndex=0, player=2, time=1, planned=True, target=[1, 0, -4],
                    phaseBefore="Rally", selectedShot=2)
        events = [dict(kind="hit", player=2, time=1), dict(kind="bounce", position=[1, 0, -3])]
        return shot, events

    def test_legal_landing_is_not_reclassified_by_later_loss(self):
        shot, events = self.fixture()
        events.append(dict(kind="fault", winner=0, fault="KitchenMomentum"))
        self.assertEqual(classify_shot(shot, events), dict(outcome="legal landing", targetError=1))

    def test_opponent_volley_is_not_a_missing_landing_failure(self):
        shot, events = self.fixture(); events[1] = dict(kind="hit", player=0)
        self.assertEqual(classify_shot(shot, events)["outcome"], "intercepted before landing")

    def test_fault_ownership_uses_rule_winner_not_contact_player(self):
        shot, events = self.fixture()
        for winner, owner in ((1, "opponent"), (0, "candidate")):
            events[1] = dict(kind="fault", winner=winner, fault="Out", player=-1)
            self.assertEqual(classify_shot(shot, events)["outcome"], owner + " fault before landing / Out")

    def test_accidental_contacts_do_not_claim_planned_target_accuracy(self):
        shot, events = self.fixture(); shot["planned"] = False
        self.assertIsNone(classify_shot(shot, events)["targetError"])

    def test_summary_requires_exact_shot_and_metric_ownership(self):
        shot, events = self.fixture()
        report = dict(rallies=[dict(candidateTeam=1, shots=[shot], events=events)],
                      games=[dict(candidateTeam=1, metrics=dict(legalHits=[7, 9, 1, 0]))])
        self.assertEqual(summarize(report)["candidateShots"], 1)
        bad = copy.deepcopy(report); bad["rallies"][0]["shots"].append(shot)
        with self.assertRaises(ValueError): summarize(bad)
        bad = copy.deepcopy(report); bad["games"][0]["metrics"]["legalHits"][2] = 2
        with self.assertRaises(ValueError): summarize(bad)

    def test_truncation_and_missing_events_remain_unresolved(self):
        shot, events = self.fixture()
        self.assertEqual(classify_shot(shot, events[:1])["outcome"], "no recorded landing or interception")
        events[1] = dict(kind="training time limit - no point")
        self.assertEqual(classify_shot(shot, events)["outcome"], "truncated before landing")


class ContactOverrideTests(unittest.TestCase):
    def fixture(self, offset=-3):
        frozen = dict(strokes=[dict(pitch=5, timing=.01, brushBias=2, speed=1, brush=1) for _ in range(3)])
        report = dict(flatPitchOffsetDegrees=offset, experimentalContactOverride=offset != 0,
                      candidateContactParameters=copy.deepcopy(frozen["strokes"]))
        report["candidateContactParameters"][0]["pitch"] += offset
        return frozen, report

    def test_only_reported_flat_pitch_changes(self):
        frozen, report = self.fixture(); validate_contact_override(report, frozen)
        report["candidateContactParameters"][1]["pitch"] -= 3
        with self.assertRaises(ValueError): validate_contact_override(report, frozen)

    def test_hidden_speed_or_label_change_fails(self):
        frozen, report = self.fixture(); report["candidateContactParameters"][0]["speed"] = 1.1
        with self.assertRaises(ValueError): validate_contact_override(report, frozen)
        frozen, report = self.fixture(); report["experimentalContactOverride"] = False
        with self.assertRaises(ValueError): validate_contact_override(report, frozen)

    def test_older_reports_are_unmodified_not_silent_overrides(self):
        frozen, report = self.fixture(); validate_contact_override({}, frozen)
        del report["candidateContactParameters"]
        with self.assertRaises(ValueError): validate_contact_override(report, frozen)

    def test_large_and_nonfinite_offsets_fail(self):
        for offset in (-7, 7, float("nan")):
            frozen, report = self.fixture(offset)
            with self.assertRaises(ValueError): validate_contact_override(report, frozen)


class ContactExecutionTests(unittest.TestCase):
    def fixture(self, player=0, selected=5):
        sign = 1 if player < 2 else -1
        shot = dict(eventIndex=0, player=player, time=1, planned=True,
                    target=[0, 0, 4*sign], phaseBefore="Rally", selectedShot=selected,
                    plannedNormal=[0, 0, sign], paddleVelocity=[0, 0, 5*sign],
                    plannedSwing=7, plannedImpactAt=.98,
                    contacts=[dict(surface="RoundedHittingFace", outgoing=[0, 2, 8*sign], spin=[30*sign, 0, 0])])
        events = [dict(kind="hit", player=player, time=1), dict(kind="bounce", position=[0, 0, 3*sign])]
        return dict(rallies=[dict(candidateTeam=player//2, shots=[shot], events=events)])

    def test_mirrored_ends_keep_speed_depth_and_spin_sign(self):
        for player in (0, 2):
            row = summarize_execution(self.fixture(player))["byShot"][0]
            self.assertEqual(row["meanDepthError"], -1)
            self.assertEqual(row["meanPlannedNormalSpeed"], 7)
            self.assertEqual(row["meanActualNormalSpeed"], 5)
            self.assertAlmostEqual(row["meanContactDelaySeconds"], .02)
            self.assertEqual(row["meanSignedSpin"], 30)
            self.assertEqual(row["spinDirectionOrFlatnessPassed"], 1)

    def test_slice_and_flat_thresholds_use_actual_spin(self):
        for selected, spin, expected in ((7, -30, 1), (7, 30, 0), (0, 24, 1), (0, 25, 0)):
            report = self.fixture(selected=selected)
            report["rallies"][0]["shots"][0]["contacts"][0]["spin"] = [spin, 0, 0]
            row = summarize_execution(report)["byShot"][0]
            self.assertEqual(row["spinDirectionOrFlatnessPassed"], expected)

    def test_surface_events_do_not_inflate_legal_shot_count(self):
        report = self.fixture(); shot = report["rallies"][0]["shots"][0]
        second = copy.deepcopy(shot["contacts"][0]); second["surface"] = "NonContactHandle"
        shot["contacts"].append(second)
        row = summarize_execution(report)["byShot"][0]
        self.assertEqual(row["shots"], 1)
        self.assertEqual(row["spinSamples"], 2)
        self.assertEqual(row["contactSurfaces"], {"RoundedHittingFace": 1, "NonContactHandle": 1})

    def test_missing_old_trace_fields_are_not_zero_measurements(self):
        report = self.fixture(); shot = report["rallies"][0]["shots"][0]
        del shot["contacts"]; del shot["paddleVelocity"]
        row = summarize_execution(report)["byShot"][0]
        self.assertEqual(row["missingContactTraces"], 1)
        self.assertEqual(row["plannedExecutionSamples"], 0)
        self.assertIsNone(row["meanActualNormalSpeed"])
        self.assertIsNone(row["meanSignedSpin"])

    def test_unplanned_contact_does_not_claim_plan_accuracy(self):
        report = self.fixture(); report["rallies"][0]["shots"][0]["planned"] = False
        row = summarize_execution(report)["byShot"][0]
        self.assertEqual(row["plannedExecutionSamples"], 0)
        self.assertIsNone(row["meanDepthError"])
        self.assertEqual(row["spinSamples"], 1)

    def test_vertical_and_missing_spin_are_separate_from_wrong_spin(self):
        report = self.fixture(); contact = report["rallies"][0]["shots"][0]["contacts"][0]
        contact["outgoing"] = [0, 8, 0]
        row = summarize_execution(report)["byShot"][0]
        self.assertEqual(row["verticalOutgoingContacts"], 1)
        self.assertEqual(row["spinSamples"], 0)
        del contact["spin"]
        row = summarize_execution(report)["byShot"][0]
        self.assertEqual(row["missingSpinContacts"], 1)
        self.assertEqual(row["verticalOutgoingContacts"], 0)

    def test_nonfinite_execution_values_fail(self):
        for field in ("paddleVelocity", "plannedNormal"):
            report = self.fixture(); report["rallies"][0]["shots"][0][field][0] = float("nan")
            with self.assertRaises(ValueError): summarize_execution(report)
        report = self.fixture(); report["rallies"][0]["shots"][0]["plannedImpactAt"] = float("inf")
        with self.assertRaises(ValueError): summarize_execution(report)


if __name__ == "__main__": unittest.main()

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from player_shot_quality import summarize, outcome, audit_trace


class ShotQualityTests(unittest.TestCase):
    def fixture(self):
        rows = []
        for fixture in range(32):
            team = fixture % 2
            events = [dict(kind="hit", player=team*2), dict(kind="bounce", position=[0, 0, 4 if team == 0 else -4])]
            for mode in range(11):
                rows.append(dict(index=len(rows), fixture=fixture, mode=mode,
                    fixedCanonicalShot=-1 if mode == 9 else 0 if mode == 10 else mode,
                    gameSeed=1199000+fixture, candidateTeam=team, profile="deep" if fixture < 16 else "kitchen",
                    completeGame=False, canonicalBall=[0, 1, 0], canonicalVelocity=[0, 0, -8],
                    playerStarts=[[0, 0, 0] for _ in range(4)], initialObservations=[[0]*54 for _ in range(4)],
                    legalHit=True, legalLanding=True, outcome="legal landing", events=copy.deepcopy(events),
                    ticks=1, decisions=4, seconds=1/240, metrics=dict(physicsSteps=1), tracePath=f"case-{len(rows)}",
                    traceHash="same" if mode in (0, 10) else str(mode)))
        return dict(version="player-shot-quality-v1", status="complete", error=None, split="development-diagnostic",
                    fixtures=32, modes=11, seedBase=1199000, expectedCases=352, physicsHz=240,
                    decisionTicks=12, actionLatencyTicks=6, maximumSeconds=6, rows=rows)

    def test_complete_matched_schedule(self):
        result = summarize(self.fixture())
        self.assertEqual(result["exactRepeatedControls"], 32)
        self.assertEqual(len(result["groups"]), 4)
        self.assertTrue(all(g["hindsightAnyFixedLanding"] == 8 for g in result["groups"]))

    def test_same_initial_state_and_repeat_are_required(self):
        for key, value in (("canonicalBall", [0, 2, 0]), ("traceHash", "changed"), ("ticks", 2)):
            report = self.fixture(); report["rows"][10][key] = value
            with self.assertRaises(ValueError): summarize(report)

    def test_incomplete_and_wrong_identity_rejected(self):
        for mutation in (lambda r: r["rows"].pop(), lambda r: r["rows"].reverse(),
                         lambda r: r.update(status="running"), lambda r: r["rows"][1].update(mode=True)):
            report = self.fixture(); mutation(report)
            with self.assertRaises(ValueError): summarize(report)

    def test_hindsight_opportunity_is_not_a_sampled_teacher_success(self):
        report = self.fixture(); row = report["rows"][9]
        row.update(events=[], legalHit=False, legalLanding=False, outcome="no hit / Out")
        result = summarize(report)
        self.assertEqual(result["groups"][0]["sampledMissButFixedSuccess"], [0])
        self.assertFalse(result["opportunities"][0]["sampledTeacherLegal"])

    def test_first_event_after_hit_controls_landing(self):
        events = [dict(kind="hit", player=0), dict(kind="fault"), dict(kind="bounce", position=[0, 0, 4])]
        self.assertEqual(outcome(events, 0), (True, False))
        self.assertEqual(outcome(events, 1), (False, False))
        events[1] = dict(kind="hit", player=2)
        self.assertEqual(outcome(events, 0), (True, False))

    def trace(self):
        rows = [dict(type="decision", player=i, tick=0, applyTick=6, observation=[0]*54,
                     action=dict(moveX=0, moveZ=0, attempt=False, shot=0)) for i in range(4)]
        players = [dict(position=[0, 0, 0], velocity=[0, 0, 0], paddle=[0, 0, 0],
                        paddleVelocity=[0, 0, 0], angularVelocity=[0, 0, 0], hand=[0, 0, 0],
                        shoulder=[0, 0, 0], rotation=[0, 0, 0, 1]) for _ in range(4)]
        rows.append(dict(type="step", tick=1, time=1/240, ball=[0, 0, 0], velocity=[0, 0, 0],
                         spin=[0, 0, 0], players=players, events=self.fixture()["rows"][0]["events"]))
        return rows

    def check_trace(self, records):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "trace.jsonl"
            path.write_text("\n".join(json.dumps(r) for r in records))
            return audit_trace(path, self.fixture()["rows"][0])

    def test_trace_checks_decisions_latency_and_all_four_players(self):
        self.assertEqual(self.check_trace(self.trace())["steps"], 1)
        for mutation in (lambda r: r[0].update(applyTick=5), lambda r: r[0].update(player=1),
                         lambda r: r[2]["action"].update(attempt=True),
                         lambda r: r[-1]["players"][3].update(paddleVelocity=[13, 0, 0]),
                         lambda r: r[-1]["players"][0].update(hand=[1, 0, 0]),
                         lambda r: r[0].update(observation=[float("nan")]*54)):
            records = self.trace(); mutation(records)
            with self.assertRaises(ValueError): self.check_trace(records)

    def test_fixed_shot_and_final_events_must_match(self):
        records = self.trace(); records[0]["action"].update(attempt=True, shot=3)
        with self.assertRaises(ValueError): self.check_trace(records)
        records = self.trace(); records[-1]["events"] = []
        with self.assertRaises(ValueError): self.check_trace(records)


if __name__ == "__main__": unittest.main()

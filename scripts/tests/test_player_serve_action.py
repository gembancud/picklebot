from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from player_serve_return import validate_replacement, validate_sample_action, validate_contact_execution, validate_window_action, contact_point_metrics


class ServeActionTests(unittest.TestCase):
    def setUp(self):
        self.actor=dict(moveX=.1,moveZ=.2,attempt=True,shot=4)
        self.teacher=dict(moveX=-.3,moveZ=.4,attempt=False,shot=8)

    def test_only_receiver_movement_can_change(self):
        applied=dict(self.actor,moveX=-.3,moveZ=.4)
        validate_replacement(self.actor,self.teacher,applied,3,True)
        with self.assertRaisesRegex(ValueError,"unselected"):
            validate_replacement(self.actor,self.teacher,applied,3,False)
        with self.assertRaisesRegex(ValueError,"unselected"):
            validate_replacement(self.actor,self.teacher,dict(applied,attempt=False),3,True)

    def test_only_receiver_shot_can_change(self):
        validate_replacement(self.actor,self.teacher,dict(self.actor,shot=8),4,True)
        with self.assertRaisesRegex(ValueError,"unselected"):
            validate_replacement(self.actor,self.teacher,self.teacher,4,True)

    def test_normal_actor_and_teacher_controls(self):
        validate_replacement(self.actor,None,self.actor,0,True)
        validate_replacement(self.teacher,self.teacher,self.teacher,2,True)
        with self.assertRaisesRegex(ValueError,"Unexpected"):
            validate_replacement(self.actor,self.teacher,self.actor,1,True)

    def test_teacher_action_must_be_bounded(self):
        for bad in (dict(self.teacher,moveX=float("nan")),dict(self.teacher,moveZ=2),dict(self.teacher,shot=9)):
            with self.assertRaisesRegex(ValueError,"Invalid teacher"):
                validate_replacement(self.actor,bad,self.actor,3,False)

    def test_second_unit_circle_normalization(self):
        sampled=dict(self.actor,moveX=.421935976,moveZ=-.906625748)
        applied=dict(sampled,moveX=.421935916,moveZ=-.9066256)
        validate_sample_action(sampled,applied)
        for bad in (dict(applied,shot=6),dict(applied,attempt=False),dict(applied,moveX=.42194)):
            with self.assertRaisesRegex(ValueError,"differs"):
                validate_sample_action(sampled,bad)

    def test_non_unit_movement_drift_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"differs"):
            validate_sample_action(self.actor,dict(self.actor,moveX=.10000001))

    def contact_row(self):
        vectors={k:[0.,0.,0.] for k in ("impact","normal","bodyPosition","bodyVelocity","paddlePosition",
            "paddleVelocity","paddleNormal","requestedMovement","appliedMovement","ball","ballVelocity")}
        before=dict(vectors,tick=240,time=1.,impactAt=1.1,phase=-.1,swingSpeed=4.,paddleStepFeasible=True)
        after=dict(before,tick=241,time=1+1/240,phase=1+1/240-1.1)
        return dict(returnHit=True,events=[dict(kind="hit",time=after["time"])],returnContactExecution=dict(before=before,after=after))

    def test_contact_execution_matches_physics_step(self):
        row=self.contact_row(); validate_contact_execution(row)
        row["returnContactExecution"]["after"]["tick"]+=1
        with self.assertRaisesRegex(ValueError,"timing"):
            validate_contact_execution(row)

    def test_contact_execution_rejects_false_phase_and_bad_vectors(self):
        row=self.contact_row(); row["returnContactExecution"]["after"]["phase"]+=.01
        with self.assertRaisesRegex(ValueError,"phase"): validate_contact_execution(row)
        row=self.contact_row(); row["returnContactExecution"]["before"]["paddleVelocity"]=[float("nan"),0,0]
        with self.assertRaisesRegex(ValueError,"vector"): validate_contact_execution(row)

    def test_contact_execution_requires_a_real_hit(self):
        validate_contact_execution(dict(returnHit=False,returnContactExecution=None))
        row=self.contact_row(); row["returnHit"]=False
        with self.assertRaisesRegex(ValueError,"without a hit"): validate_contact_execution(row)

    def test_stop_window_changes_movement_only(self):
        decision=dict(player=1,original=self.actor,teacherAction=self.teacher,action=dict(self.actor,moveX=0,moveZ=0),
            controlWindow=True,windowState=dict(time=1.,impactAt=1.15,hits=1,planned=True))
        validate_window_action(decision,3,1)
        decision["action"]["shot"]=3
        with self.assertRaisesRegex(ValueError,"unselected"): validate_window_action(decision,3,1)

    def test_window_cannot_control_a_partner_or_start_early(self):
        decision=dict(player=1,original=self.actor,teacherAction=self.teacher,action=self.actor,
            controlWindow=True,windowState=dict(time=1.,impactAt=1.15,hits=1,planned=True))
        with self.assertRaisesRegex(ValueError,"window"): validate_window_action(decision,3,0)
        decision["windowState"]["impactAt"]=1.3
        with self.assertRaisesRegex(ValueError,"window"): validate_window_action(decision,3,1)

    def test_teacher_window_changes_no_discrete_action(self):
        decision=dict(player=1,original=self.actor,teacherAction=self.teacher,
            action=dict(self.actor,moveX=self.teacher["moveX"],moveZ=self.teacher["moveZ"]),
            controlWindow=True,windowState=dict(time=1.,impactAt=1.15,hits=1,planned=True))
        validate_window_action(decision,4,1)
        decision["action"]["attempt"]=False
        with self.assertRaisesRegex(ValueError,"unselected"): validate_window_action(decision,4,1)

    def test_point_velocity_includes_rotation(self):
        row=self.contact_row(); row.update(fixture=0,mode=0,fault="None")
        state=row["returnContactExecution"]
        for item in (state["before"],state["after"]):
            item.update(shoulder=[0,0,0],hand=[.5,0,0],paddleAngularVelocity=[0,0,1],selectedShot=0)
        state.update(point=[1,0,0],contactNormal=[0,1,0],pointVelocity=[0,1,0])
        measured=contact_point_metrics(row)
        self.assertEqual(measured["pointPhysicalNormalSpeed"],1)
        state["pointVelocity"]=[0,0,0]
        with self.assertRaisesRegex(ValueError,"replay"): contact_point_metrics(row)


if __name__ == "__main__": unittest.main()

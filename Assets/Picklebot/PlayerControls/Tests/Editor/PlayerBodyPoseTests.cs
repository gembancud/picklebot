using NUnit.Framework;
using Picklebot.Doubles;
using UnityEngine;

namespace Picklebot.PlayerControls.Tests
{
    public sealed class PlayerBodyPoseTests
    {
        private static PlayerControlState State(float z,bool grounded=true,float height=0,float yaw=180)=>
            new PlayerControlState(new Vector3(0,height,z),Vector3.zero,yaw,0,1,0,grounded);
        private static void Report(DoublesRules rules,PlayerBodyPose pose,PlayerControlState state,float time)
        {
            var support=new PlayerSupportState(pose.Left,pose.Right,state,1,DoublesRules.HalfWidth,DoublesRules.Kitchen);
            rules.Feet(3,support.touchesKitchen,support.bothFeetOutside,support.balanceRecovered,time);
        }
        private static DoublesRules Rally()
        {
            var r=new DoublesRules();r.Serve(r.Server,true,true,true,true,false,false,false,0);
            int receiver=r.DesignatedReceiver;
            r.Bounce(new Vector3(r.ServiceX(receiver),0,4),1);r.Hit(receiver,2);
            r.Bounce(new Vector3(0,0,-4),3);r.Hit(r.Server,4);return r;
        }
        [Test] public void StanceFeetStayFixedUntilSwingAndLegSegmentsKeepTheirLength()
        {
            var motor=new PlayerControlMotor();var pose=new PlayerBodyPose(motor.State);var initial=pose.Left.center;
            for(int i=0;i<10;i++)pose.Step(motor.Step(new PlayerControlCommand{move=Vector2.up},1f/240),1f/240);
            Assert.AreEqual(initial,pose.Left.center);Assert.IsTrue(pose.Left.supported);
            Assert.That(Vector3.Distance(pose.LeftHip,pose.LeftKnee),Is.EqualTo(.46f).Within(1e-5f));
            Assert.That(Vector3.Distance(pose.LeftKnee,pose.Left.center),Is.EqualTo(.46f).Within(1e-5f));
        }
        [Test] public void TurningSprintingCrouchingAndJumpingRemainWithinLegReach()
        {
            var motor=new PlayerControlMotor();var pose=new PlayerBodyPose(motor.State);
            for(int i=0;i<4800;i++)
            {
                var command=new PlayerControlCommand{move=new Vector2(Mathf.Sin(i*.005f),Mathf.Cos(i*.005f)),
                    facingYaw=i*.5f,sprint=true,crouch=i%700<150?1:0,jump=i%450<40};
                var state=motor.Step(command,1f/240);pose.Step(state,1f/240);
                Assert.LessOrEqual(pose.MaxLegExtension,.92001f);
                Assert.That(Vector3.Distance(pose.RightHip,pose.RightKnee),Is.EqualTo(.46f).Within(2e-5f));
                Assert.That(Vector3.Distance(pose.RightKnee,pose.Right.center),Is.EqualTo(.46f).Within(2e-5f));
                if(!state.grounded) { Assert.IsFalse(pose.Left.supported);Assert.IsFalse(pose.Right.supported); }
            }
        }
        [Test] public void TakeoffCannotTeleportTrailingFeetUnderTheBody()
        {
            const float dt=1f/240;
            var motor=new PlayerControlMotor();var pose=new PlayerBodyPose(motor.State);
            for(int i=0;i<80;i++)pose.Step(motor.Step(new PlayerControlCommand{move=Vector2.up,sprint=true},dt),dt);
            var oldRoot=motor.State.position;var oldLeft=pose.Left.center;var oldRight=pose.Right.center;
            var state=motor.Step(new PlayerControlCommand{move=Vector2.up,sprint=true,jump=true},dt);pose.Step(state,dt);
            Assert.IsFalse(state.grounded);
            Assert.LessOrEqual((pose.Left.center-oldLeft-(state.position-oldRoot)).magnitude,6*dt+1e-5f);
            Assert.LessOrEqual((pose.Right.center-oldRight-(state.position-oldRoot)).magnitude,6*dt+1e-5f);
        }
        [Test] public void RotatedShoeFootprintCountsBoundaryContact()
        {
            var forward=new PlayerFootPose(new Vector3(0,.055f,DoublesRules.Kitchen+.13f),0,true);
            var sideways=new PlayerFootPose(forward.center,90,true);
            Assert.IsTrue(forward.TouchesKitchen(DoublesRules.HalfWidth,DoublesRules.Kitchen));
            Assert.IsFalse(sideways.TouchesKitchen(DoublesRules.HalfWidth,DoublesRules.Kitchen));
            Assert.IsFalse(new PlayerFootPose(forward.center,0,false).TouchesKitchen(DoublesRules.HalfWidth,DoublesRules.Kitchen));
        }
        [Test] public void JumpingOutOfKitchenDoesNotRestoreVolleyEligibility()
        {
            var rules=Rally();var ground=State(1);var pose=new PlayerBodyPose(ground);Report(rules,pose,ground,5);
            var air=State(3,false,.2f);pose.Step(air,1f/240);Report(rules,pose,air,6);
            rules.Hit(3,7);Assert.AreEqual(Fault.KitchenVolley,rules.LastFault);
        }
        [Test] public void OutsideJumpVolleyKeepsMomentumPendingUntilKitchenLanding()
        {
            var rules=Rally();var ground=State(3);var pose=new PlayerBodyPose(ground);Report(rules,pose,ground,5);
            var air=State(3,false,.2f);pose.Step(air,1f/240);Report(rules,pose,air,6);
            rules.Hit(3,7);Assert.IsFalse(rules.Dead);
            rules.Fail(0,Fault.SecondBounce,8);Assert.IsFalse(rules.ResolveRally());
            var landing=State(1);pose.Step(landing,1f/240);Report(rules,pose,landing,9);
            Assert.AreEqual(Fault.KitchenMomentum,rules.LastFault);Assert.AreEqual(0,rules.Winner);
        }
        [Test] public void BothFeetLandingOutsideRestoresEligibilityWithoutAirborneShortcut()
        {
            var rules=Rally();var ground=State(1);var pose=new PlayerBodyPose(ground);Report(rules,pose,ground,5);
            var air=State(3,false,.2f);pose.Step(air,1f/240);Report(rules,pose,air,6);
            var landing=State(3);pose.Step(landing,1f/240);Report(rules,pose,landing,7);
            rules.Hit(3,8);Assert.IsFalse(rules.Dead);
        }
        [Test] public void PoseSnapshotCannotMutateWorldSupportState()
        {
            var world=new PlayerControlWorld();var before=world.PoseFor(0).Left.center;
            world.PoseFor(0).Reset(State(1));Assert.AreEqual(before,world.PoseFor(0).Left.center);
        }
    }
}

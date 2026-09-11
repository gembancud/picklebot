using System;
using NUnit.Framework;
using UnityEngine;

namespace Picklebot.PlayerControls.Tests
{
    public sealed class PlayerPaddleControlTests
    {
        [Test] public void AggressiveRequestsRespectAllHardBounds()
        {
            const float dt=1f/240;var shoulder=new Vector3(0,1.36f,0);var motor=new PlayerPaddleControl(shoulder,0);
            int feasible=0;
            for(int i=0;i<1200;i++)
            {
                var previous=motor.State;
                bool ok=motor.TryStep(shoulder,shoulder,0,new PlayerPaddleCommand{localHandTarget=new Vector3(Mathf.Sin(i*.01f),-.2f,Mathf.Cos(i*.01f)),
                    localFeedVelocity=Vector3.forward*30,localEuler=new Vector3(60,100*Mathf.Sin(i*.01f),80)},dt);
                if(!ok) { Assert.AreEqual(previous.position,motor.State.position);continue; }
                feasible++;var state=motor.State;
                Assert.LessOrEqual(state.velocity.magnitude,12.0002f);
                Assert.LessOrEqual((state.velocity-previous.velocity).magnitude/dt,100.03f);
                Assert.LessOrEqual(Vector3.Distance(state.Hand,shoulder),.62001f);
                Assert.LessOrEqual(Quaternion.Angle(previous.rotation,state.rotation),12*Mathf.Rad2Deg*dt+.002f);
                Assert.That(Vector3.Distance(state.position,previous.position+state.velocity*dt),Is.LessThan(1e-6f));
            }
            Assert.Greater(feasible,1000,"Repeated rejected actions cannot count as a working motor.");
        }
        [Test] public void ReadyPaddleFollowsRealJumpCrouchAndTurningShoulder()
        {
            const float dt=1f/240;var world=new PlayerControlWorld();var commands=new PlayerControlCommand[4];
            for(int i=0;i<1200;i++)
            {
                commands[0]=new PlayerControlCommand{move=new Vector2(Mathf.Sin(i*.01f),Mathf.Cos(i*.01f))*.3f,
                    facingYaw=i*.3f,crouch=i%400<100?1:0,jump=i%300<30,sprint=true};
                commands[2].facingYaw=commands[3].facingYaw=180;
                var prior=world.PaddleFor(0);world.Step(commands,dt);var paddle=world.PaddleFor(0);
                Assert.LessOrEqual(Vector3.Distance(paddle.Hand,world.PoseFor(0).Shoulder),.62001f);
                Assert.LessOrEqual((paddle.velocity-prior.velocity).magnitude/dt,100.03f);
            }
        }
        [Test] public void ImpossibleShoulderMotionDoesNotTeleportThePaddle()
        {
            var motor=new PlayerPaddleControl(Vector3.zero,0);var before=motor.State;
            Assert.IsFalse(motor.TryStep(Vector3.zero,Vector3.right*10,0,PlayerPaddleCommand.Ready,1f/240));
            Assert.AreEqual(before.position,motor.State.position);Assert.AreEqual(before.velocity,motor.State.velocity);
        }
        [Test] public void RecordedReadyTransitionBrakesWithoutDroppingWristMotionInstantly()
        {
            // Exact rejected state from intent-probe-03-wrist.json, step 675.
            var oldShoulder=new Vector3(-1.18586683f,1.156335f,5.189693f);
            var shoulder=new Vector3(-1.19014001f,1.16216826f,5.19413185f);
            var before=new PlayerPaddleState(new Vector3(-1.45295286f,1.03724408f,4.77429438f),
                new Quaternion(-.0000106861116f,1,.000197872519f,.0000429167412f),
                new Vector3(4.94303846f,1.47117233f,-1.95882404f),new Vector3(-11.7104683f,2.54248381f,-.632424235f));
            var motor=new PlayerPaddleControl(oldShoulder,180);
            typeof(PlayerPaddleControl).GetProperty("State").SetValue(motor,before);
            const float dt=1f/240;
            Assert.IsTrue(motor.TryStep(oldShoulder,shoulder,180,PlayerPaddleCommand.Ready,dt));
            var after=motor.State;
            Assert.Greater(motor.WristRecoverySteps,0);
            Assert.LessOrEqual(after.velocity.magnitude,12.0002f);
            Assert.LessOrEqual((after.velocity-before.velocity).magnitude/dt,100.03f);
            Assert.LessOrEqual(Vector3.Distance(after.Hand,shoulder),.62001f);
            Assert.LessOrEqual(((after.Hand-before.Hand)-(shoulder-oldShoulder)).magnitude/dt,6.0002f);
            Assert.LessOrEqual(Quaternion.Angle(before.rotation,after.rotation)/dt,12*Mathf.Rad2Deg+.02f);
            Assert.LessOrEqual(Vector3.Distance(after.position,before.position+after.velocity*dt),1e-6f);
        }
        [Test] public void InvalidFourthPaddleCommandCannotAdvanceAnyPlayer()
        {
            var world=new PlayerControlWorld();var before=world.StateFor(0);
            var commands=new PlayerControlCommand[4];commands[0].jump=true;
            var paddles=new[]{PlayerPaddleCommand.Ready,PlayerPaddleCommand.Ready,PlayerPaddleCommand.Ready,PlayerPaddleCommand.Ready};paddles[3].localEuler.x=float.NaN;
            Assert.Throws<ArgumentException>(()=>world.Step(commands,paddles,1f/240));
            Assert.AreEqual(before.position,world.StateFor(0).position);Assert.AreEqual(before.energy,world.StateFor(0).energy);
        }
    }
}

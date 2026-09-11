using System;
using NUnit.Framework;
using UnityEngine;

namespace Picklebot.PlayerControls.Tests
{
    public sealed class PlayerControlMotorTests
    {
        private const float Dt=1f/240f;
        [Test] public void DirectionalTargetsAndVectorAccelerationAreBounded()
        {
            foreach(var direction in new[]{Vector2.up,Vector2.down,Vector2.right,new Vector2(1,1)})
            {
                var motor=new PlayerControlMotor(); var previous=Vector3.zero;
                for(int i=0;i<240;i++)
                {
                    var state=motor.Step(new PlayerControlCommand{move=direction,sprint=true},Dt);
                    Assert.LessOrEqual(state.velocity.magnitude,3.8001f);
                    Assert.LessOrEqual((state.velocity-previous).magnitude/Dt,14.001f);previous=state.velocity;
                }
                if(direction==Vector2.down) Assert.LessOrEqual(motor.State.velocity.magnitude,2.3001f);
                if(direction==Vector2.right) Assert.LessOrEqual(motor.State.velocity.magnitude,3.0001f);
            }
        }
        [Test] public void AirborneRequestsCannotAddPropulsionOrTurn()
        {
            var motor=new PlayerControlMotor();
            for(int i=0;i<90;i++) motor.Step(new PlayerControlCommand{move=Vector2.up,sprint=true},Dt);
            var takeoff=motor.Step(new PlayerControlCommand{move=Vector2.up,jump=true,sprint=true},Dt);
            Assert.IsFalse(takeoff.grounded);
            for(int i=0;i<30;i++)
            {
                var s=motor.Step(new PlayerControlCommand{move=Vector2.left,jump=true,facingYaw=180,crouch=1},Dt);
                Assert.AreEqual(takeoff.velocity.x,s.velocity.x);Assert.AreEqual(takeoff.velocity.z,s.velocity.z);
                Assert.AreEqual(takeoff.facingYaw,s.facingYaw);Assert.AreEqual(takeoff.energy,s.energy);
            }
        }
        [Test] public void HeldJumpDoesNotRepeatAndLandingRequiresRecovery()
        {
            var motor=new PlayerControlMotor();float apex=0;int takeoffs=0;bool prior=true;
            for(int i=0;i<600;i++)
            {
                var s=motor.Step(new PlayerControlCommand{jump=true},Dt);apex=Mathf.Max(apex,s.position.y);
                if(prior&&!s.grounded)takeoffs++;prior=s.grounded;
                if(s.grounded) Assert.AreEqual(0,s.position.y);
            }
            Assert.AreEqual(1,takeoffs);Assert.That(apex,Is.InRange(.249f,.251f));
            motor.Step(default,Dt);Assert.IsFalse(motor.Step(new PlayerControlCommand{jump=true},Dt).grounded);
        }
        [Test] public void EnergyAndStateArePrivateAndProfileIsCopied()
        {
            var profile=new PlayerControlProfile();var a=new PlayerControlMotor(profile);var b=new PlayerControlMotor(profile);
            profile.acceleration=999;
            for(int i=0;i<3000;i++) a.Step(new PlayerControlCommand{move=Vector2.up,sprint=true},Dt);
            Assert.That(a.State.energy,Is.InRange(0,1));Assert.AreEqual(1,b.State.energy);Assert.AreEqual(Vector3.zero,b.State.position);
            float tired=a.State.energy;
            for(int i=0;i<3000;i++) a.Step(default,Dt);
            Assert.Greater(a.State.energy,tired);Assert.LessOrEqual(a.State.energy,1);
        }
        [Test] public void BrakingAndResetAreDeterministic()
        {
            var a=new PlayerControlMotor();var b=new PlayerControlMotor();
            for(int i=0;i<400;i++)
            {
                var command=new PlayerControlCommand{move=i<150?Vector2.up:Vector2.zero,sprint=true};
                Assert.AreEqual(a.Step(command,Dt).position,b.Step(command,Dt).position);
            }
            Assert.AreEqual(Vector3.zero,a.State.velocity);
            a.Reset(new Vector3(1,0,2));Assert.AreEqual(1,a.State.energy);Assert.IsTrue(a.State.grounded);
        }
        [Test] public void ObservationIsPlayerLocalAndRotatesWithCourtEnd()
        {
            var a=new PlayerControlState(new Vector3(1,.1f,2),new Vector3(.5f,1,2),0,.2f,.7f,0,false);
            var b=new PlayerControlState(new Vector3(-1,.1f,-2),new Vector3(-.5f,1,-2),180,.2f,.7f,0,false);
            var first=PlayerControlObservation.Capture(a,0);var second=PlayerControlObservation.Capture(b,180);
            Assert.AreEqual(PlayerControlObservation.Count,first.Length);
            for(int i=0;i<first.Length;i++)Assert.AreEqual(first[i],second[i],.00001f);
            first[7]=0;Assert.AreEqual(.7f,second[7]);
        }
        [Test] public void JumpIsDeniedDuringLandingRecovery()
        {
            var motor=new PlayerControlMotor();motor.Step(new PlayerControlCommand{jump=true},Dt);
            for(int i=0;i<300&&!motor.State.grounded;i++)motor.Step(default,Dt);
            Assert.Greater(motor.State.landingRemaining,0);
            Assert.IsTrue(motor.Step(new PlayerControlCommand{jump=true},Dt).grounded);
        }
        [Test] public void TurningCannotBypassTheVectorAccelerationLimit()
        {
            var motor=new PlayerControlMotor();
            for(int i=0;i<120;i++)motor.Step(new PlayerControlCommand{move=Vector2.up,sprint=true},Dt);
            for(int i=0;i<120;i++)
            {
                var old=motor.State.velocity;
                var s=motor.Step(new PlayerControlCommand{move=Vector2.up,sprint=true,facingYaw=180},Dt);
                Assert.LessOrEqual((s.velocity-old).magnitude/Dt,14.001f);
            }
        }
        [Test] public void GroundedCrouchReversalsHaveBoundedAccelerationAndNoBoundarySnap()
        {
            var motor=new PlayerControlMotor();float previous=0;
            for(int i=0;i<2400;i++)
            {
                var before=motor.State;
                var after=motor.Step(new PlayerControlCommand{crouch=i<600?1:i<1200?0:i%37<18?1:0},Dt);
                float actual=(after.crouch-before.crouch)/Dt;
                Assert.That(after.crouch,Is.InRange(0f,1f));Assert.LessOrEqual(Mathf.Abs(actual),2.5001f);
                Assert.LessOrEqual(Mathf.Abs(actual-previous)/Dt,10.02f);
                Assert.That(actual,Is.EqualTo(after.crouchVelocity).Within(.00003f));previous=actual;
            }
            motor.Reset(Vector3.zero);Assert.AreEqual(0,motor.State.crouchVelocity);
        }
        [Test] public void InvalidCommandsAndTimestepsFailClosed()
        {
            var motor=new PlayerControlMotor();
            Assert.Throws<ArgumentException>(()=>motor.Step(new PlayerControlCommand{crouch=float.NaN},Dt));
            Assert.Throws<ArgumentOutOfRangeException>(()=>motor.Step(default,0));
            Assert.Throws<ArgumentException>(()=>new PlayerControlMotor(new PlayerControlProfile{gravity=-1}));
        }
    }
}

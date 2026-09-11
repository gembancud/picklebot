using System;
using NUnit.Framework;
using UnityEngine;
namespace Picklebot.PlayerControls.Tests
{
    public sealed class PlayerUpperBodyBoundedV3Tests
    {
        [Test] public void MovingPelvisAndJointMotionSharePaddleLimitsAndRejectionIsAtomic()
        {
            var motor=new PlayerUpperBodyBoundedV3();var old=motor.Pose().Arm(motor.ArmAngles,PlayerGripV3.ContinentalPrototype);
            var previous=Vector3.zero;
            for(int step=1;step<=6000;step++)
            {
                float t=step*PlayerJointMotorV3.Dt;
                var pelvis=new Vector3(.6f*(1-Mathf.Cos(t)),.8f+.08f*(1-Mathf.Cos(t*.7f)),.4f*(1-Mathf.Cos(t*.8f)));
                var rotation=Quaternion.Euler(0,35*(1-Mathf.Cos(t*.6f)),0);
                var a=PlayerArmJointsV3.Ready.ToArray();a[0]=70*Mathf.Sin(t*2);a[3]=85+55*Mathf.Sin(t*1.5f);a[4]=75*Mathf.Sin(t*2.3f);
                Assert.IsTrue(motor.TryStep(new Vector3(40*Mathf.Sin(t),15*Mathf.Sin(t*.6f),20*Mathf.Sin(t*.7f)),new PlayerArmJointsV3(a),pelvis,rotation),"Step "+step);
                var next=motor.Pose().Arm(motor.ArmAngles,PlayerGripV3.ContinentalPrototype);
                var velocity=(next.paddlePosition-old.paddlePosition)/PlayerJointMotorV3.Dt;
                Assert.LessOrEqual(velocity.magnitude,12);Assert.LessOrEqual((velocity-previous).magnitude/PlayerJointMotorV3.Dt,100.01f);
                Assert.LessOrEqual(Quaternion.Angle(old.paddleRotation,next.paddleRotation)*Mathf.Deg2Rad/PlayerJointMotorV3.Dt,12);
                Assert.Less(Vector3.Distance(motor.ActualVelocity,velocity),.001f);
                old=next;previous=velocity;
            }
            var before=motor.ArmAngles.ToArray();var root=motor.Pose().pelvis;var v=motor.ActualVelocity;
            Assert.IsFalse(motor.TryStep(Vector3.zero,PlayerArmJointsV3.Ready,root+Vector3.right*100,Quaternion.identity));
            CollectionAssert.AreEqual(before,motor.ArmAngles.ToArray());Assert.AreEqual(root,motor.Pose().pelvis);Assert.AreEqual(v,motor.ActualVelocity);
        }
        [Test] public void CoordinatedTargetsAdvanceWithoutViolatingWholePaddleBounds()
        {
            var motor=new PlayerUpperBodyBoundedV3();var random=new System.Random(1300000);
            var old=motor.Pose().Arm(motor.ArmAngles,PlayerGripV3.ContinentalPrototype);var previousVelocity=Vector3.zero;
            var target=PlayerArmJointsV3.Ready;var torso=Vector3.zero;float travel=0;
            for(int step=0;step<12000;step++)
            {
                if(step%90==0)
                {
                    var angles=new float[7];for(int j=0;j<7;j++)angles[j]=Mathf.Lerp(PlayerArmJointsV3.Minimum(j),PlayerArmJointsV3.Maximum(j),(float)random.NextDouble());
                    target=new PlayerArmJointsV3(angles);torso=new Vector3(Mathf.Lerp(-60,60,(float)random.NextDouble()),Mathf.Lerp(-15,35,(float)random.NextDouble()),Mathf.Lerp(-25,25,(float)random.NextDouble()));
                }
                Assert.IsTrue(motor.TryStep(torso,target),"No frozen/rejected steps in this fixture: "+step);
                var next=motor.Pose().Arm(motor.ArmAngles,PlayerGripV3.ContinentalPrototype);
                var velocity=(next.paddlePosition-old.paddlePosition)/PlayerJointMotorV3.Dt;
                Assert.LessOrEqual(velocity.magnitude,12);
                Assert.LessOrEqual((velocity-previousVelocity).magnitude/PlayerJointMotorV3.Dt,100.01f);
                Assert.LessOrEqual(Quaternion.Angle(old.paddleRotation,next.paddleRotation)*Mathf.Deg2Rad/PlayerJointMotorV3.Dt,12);
                travel+=Vector3.Distance(old.paddlePosition,next.paddlePosition);old=next;previousVelocity=velocity;
            }
            Assert.Greater(travel,10,"A stationary paddle is not a solution.");
            var before=motor.ArmAngles.ToArray();var prior=motor.ActualVelocity;
            Assert.Throws<ArgumentException>(()=>motor.TryStep(new Vector3(float.NaN,0,0),target));
            CollectionAssert.AreEqual(before,motor.ArmAngles.ToArray());Assert.AreEqual(prior,motor.ActualVelocity);
        }
    }
}

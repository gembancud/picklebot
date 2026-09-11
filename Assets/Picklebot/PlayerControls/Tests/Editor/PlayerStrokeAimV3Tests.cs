using System;
using NUnit.Framework;
using UnityEngine;
namespace Picklebot.PlayerControls.Tests
{
    public sealed class PlayerStrokeAimV3Tests
    {
        [Test] public void AimingFindsReachableContactTargetsFromDifferentPelvisOrientations()
        {
            foreach(float yaw in new[]{0f,90f,180f,270f})
            {
                var pelvis=new Vector3(1,.8f,-3);var rotation=Quaternion.Euler(0,yaw,0);
                var desired=PlayerTorsoKinematicsV3.Evaluate(pelvis,rotation,new Vector3(15,8,-4)).Arm(new PlayerArmJointsV3(new[]{-20f,30f,25f,70f,25f,-10f,5f}),PlayerGripV3.ContinentalPrototype);
                var result=PlayerStrokeAimV3.Solve(pelvis,rotation,Vector3.zero,PlayerArmJointsV3.Ready,desired.PaddlePoint(PlayerStrokeAimV3.FacePoint),desired.paddleRotation*Vector3.forward);
                Assert.IsTrue(result.Reached,"Residual position="+result.positionError+" normal="+result.normalErrorDegrees);
            }
        }
        [Test] public void UnreachableAimIsReportedAndInvalidDirectionRejected()
        {
            var result=PlayerStrokeAimV3.Solve(Vector3.up*.8f,Quaternion.identity,Vector3.zero,PlayerArmJointsV3.Ready,Vector3.right*10,Vector3.forward);
            Assert.IsFalse(result.Reached);Assert.Greater(result.positionError,8);
            Assert.Throws<ArgumentException>(()=>PlayerStrokeAimV3.Solve(Vector3.zero,Quaternion.identity,Vector3.zero,PlayerArmJointsV3.Ready,Vector3.zero,Vector3.zero));
        }
        [Test] public void ContactPointIntentionExecutesThroughBoundedMotor()
        {
            var motor=new PlayerUpperBodyBoundedV3();var old=motor.Pose().Arm(motor.ArmAngles,PlayerGripV3.ContinentalPrototype);
            var point=old.PaddlePoint(PlayerStrokeAimV3.FacePoint)+new Vector3(.06f,.04f,.05f);
            var normal=Quaternion.AngleAxis(8,Vector3.up)*(old.paddleRotation*Vector3.forward);
            var aim=PlayerStrokeAimV3.Solve(motor.Pose().pelvis,Quaternion.identity,motor.TorsoAngles,motor.ArmAngles,point,normal);
            Assert.IsTrue(aim.Reached);var previous=Vector3.zero;
            for(int tick=0;tick<480;tick++)
            {
                Assert.IsTrue(motor.TryStep(aim.torso,aim.arm));
                Assert.LessOrEqual(motor.ActualVelocity.magnitude,12);Assert.LessOrEqual((motor.ActualVelocity-previous).magnitude/PlayerJointMotorV3.Dt,100.01f);previous=motor.ActualVelocity;
            }
            var actual=motor.Pose().Arm(motor.ArmAngles,PlayerGripV3.ContinentalPrototype);
            Assert.Less(Vector3.Distance(actual.PaddlePoint(PlayerStrokeAimV3.FacePoint),point),.006f);
            Assert.Less(Vector3.Angle(actual.paddleRotation*Vector3.forward,normal),2);
        }
    }
}

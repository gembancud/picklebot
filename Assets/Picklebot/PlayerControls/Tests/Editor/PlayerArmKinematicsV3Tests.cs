using System;
using NUnit.Framework;
using UnityEngine;
namespace Picklebot.PlayerControls.Tests
{
    public sealed class PlayerArmKinematicsV3Tests
    {
        private static PlayerArmPoseV3 Pose(float[] angles)=>PlayerArmKinematicsV3.Evaluate(new Vector3(.19f,1.36f,0),Quaternion.identity,new PlayerArmJointsV3(angles),PlayerGripV3.ContinentalPrototype);
        [Test] public void HandleStaysAcrossPalmThroughForearmAndWristMotion()
        {
            for(int i=0;i<40;i++)
            {
                var a=PlayerArmJointsV3.Ready.ToArray();a[4]=80*Mathf.Sin(i);a[5]=60*Mathf.Sin(i*.4f);a[6]=25*Mathf.Sin(i*.3f);
                var p=Pose(a);var handle=p.paddleRotation*Vector3.up;
                Assert.Less(Mathf.Abs(Vector3.Dot(handle,p.PalmNormal)),1e-5f,"Handle must not emerge through the palm.");
                Assert.Less(Mathf.Abs(Vector3.Dot(handle,p.FingerDirection)),1e-5f,"Handle must not extend along fingers.");
                Assert.Greater(Vector3.Dot(handle,p.AcrossPalm),.99999f);
                Assert.Less(Vector3.Distance(p.PaddlePoint(PlayerPaddleControl.GripLocal),p.hand),1e-6f);
            }
        }
        [Test] public void ClosedGripCrossesTheHandInsteadOfExtendingAlongTheForearm()
        {
            var a=PlayerArmJointsV3.Ready.ToArray();a[5]=0;a[6]=0;
            var pose=Pose(a);var forearm=(pose.hand-pose.elbow).normalized;
            var handle=pose.paddleRotation*Vector3.up;
            Assert.Less(Mathf.Abs(Vector3.Dot(forearm,handle)),1e-5f);
            Assert.Less(Vector3.Distance(pose.PaddlePoint(PlayerPaddleControl.GripLocal),pose.hand),1e-6f);
        }
        [Test] public void ElbowCannotReverseAndWristAndForearmCannotRotateWithoutLimit()
        {
            foreach(int joint in new[]{3,4,5,6})
            {
                var a=PlayerArmJointsV3.Ready.ToArray();a[joint]=PlayerArmJointsV3.Minimum(joint)-.01f;
                Assert.Throws<ArgumentException>(()=>new PlayerArmJointsV3(a));
                a[joint]=PlayerArmJointsV3.Maximum(joint)+.01f;
                Assert.Throws<ArgumentException>(()=>new PlayerArmJointsV3(a));
            }
            var reversed=PlayerArmJointsV3.Ready.ToArray();reversed[3]=-20;
            Assert.Throws<ArgumentException>(()=>new PlayerArmJointsV3(reversed));
        }
        [Test] public void BonesKeepTheirLengthsAndPaddleKeepsItsGrip()
        {
            for(int i=0;i<100;i++)
            {
                var a=new[]{70*Mathf.Sin(i),30+35*Mathf.Sin(i*.3f),30+40*Mathf.Sin(i*.2f),80+55*Mathf.Sin(i*.15f),70*Mathf.Sin(i*.4f),50*Mathf.Sin(i*.5f),25*Mathf.Sin(i*.6f)};
                var p=Pose(a);
                Assert.That(Vector3.Distance(p.shoulder,p.elbow),Is.EqualTo(.32f).Within(1e-6f));
                Assert.That(Vector3.Distance(p.elbow,p.wrist),Is.EqualTo(.25f).Within(1e-6f));
                Assert.That(Vector3.Distance(p.wrist,p.hand),Is.EqualTo(.06f).Within(1e-6f));
                Assert.LessOrEqual(Vector3.Distance(p.shoulder,p.hand),.62001f);
                Assert.Less(Vector3.Distance(p.PaddlePoint(PlayerGripV3.ContinentalPrototype.pointOnPaddle),p.hand),1e-6f);
            }
        }
        [Test] public void WristBendsAroundDistinctJointAndCarriesTheGrippedPaddle()
        {
            var a=PlayerArmJointsV3.Ready.ToArray();var first=Pose(a);a[5]+=15;var next=Pose(a);
            Assert.Less(Vector3.Distance(first.wrist,next.wrist),1e-6f);
            Assert.Greater(Vector3.Distance(first.hand,next.hand),.01f);
            Assert.Greater(Vector3.Angle(first.paddleRotation*Vector3.forward,next.paddleRotation*Vector3.forward),14.9f);
            var rates=new float[7];rates[5]=2;
            Assert.Less(first.PointVelocity(first.wrist,rates).magnitude,1e-6f);
            Assert.That(first.PointVelocity(first.hand,rates).magnitude,Is.EqualTo(.12f).Within(1e-5f));
            Assert.Less(Vector3.Distance(next.PaddlePoint(PlayerPaddleControl.GripLocal),next.hand),1e-6f);
        }
        [Test] public void JointDerivedContactVelocitiesMatchActualPoseChanges()
        {
            var angles=PlayerArmJointsV3.Ready.ToArray();var center=Pose(angles);var local=new Vector3(.04f,.1f,.008f);
            const float dt=.001f;
            for(int joint=0;joint<7;joint++)
            {
                var rates=new float[7];rates[joint]=1.3f;var before=(float[])angles.Clone();var after=(float[])angles.Clone();
                before[joint]-=1.3f*dt*Mathf.Rad2Deg;after[joint]+=1.3f*dt*Mathf.Rad2Deg;
                var measured=(Pose(after).PaddlePoint(local)-Pose(before).PaddlePoint(local))/(2*dt);
                Assert.Less(Vector3.Distance(measured,center.PointVelocity(center.PaddlePoint(local),rates)),.001f,"Joint "+joint);
            }
        }
        [Test] public void RootTranslationAndRotationAddTheirPhysicalContactVelocity()
        {
            var p=Pose(PlayerArmJointsV3.Ready.ToArray());var point=p.PaddlePoint(new Vector3(0,.0635f,0));
            var rootVelocity=new Vector3(1,0,2);var omega=new Vector3(0,2,0);
            Assert.Less(Vector3.Distance(p.PointVelocity(point,new float[7],rootVelocity,omega),rootVelocity+Vector3.Cross(omega,point-p.shoulder)),1e-6f);
        }
        [Test] public void JointInputsAreOwnedAndInvalidPosesAreRejected()
        {
            var values=PlayerArmJointsV3.Ready.ToArray();var joints=new PlayerArmJointsV3(values);values[0]=99;
            Assert.AreEqual(0,joints[0]);Assert.Throws<ArgumentException>(()=>new PlayerArmJointsV3(new float[7]));
            values[0]=float.NaN;Assert.Throws<ArgumentException>(()=>new PlayerArmJointsV3(values));
            Assert.Throws<ArgumentException>(()=>PlayerArmKinematicsV3.Evaluate(Vector3.zero,Quaternion.identity,joints,default));
        }
    }
}

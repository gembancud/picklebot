using System;
using NUnit.Framework;
using UnityEngine;
namespace Picklebot.PlayerControls.Tests
{
    public sealed class PlayerTorsoKinematicsV3Tests
    {
        [Test] public void WholeChainVelocityMatchesMovingPelvisTorsoAndArm()
        {
            const float dt=.001f;
            var pelvis=new Vector3(1,.8f,2);var velocity=new Vector3(.8f,.1f,-.4f);
            var rotation=Quaternion.Euler(0,30,0);var omega=new Vector3(0,.6f,0);
            var angles=new Vector3(20,10,-5);var rates=new Vector3(.7f,-.4f,.3f);
            var joints=PlayerArmJointsV3.Ready.ToArray();var armRates=new[]{.2f,.3f,-.1f,.4f,-.2f,.5f,.3f};
            var point=new Vector3(.03f,.1f,.008f);
            var torso=PlayerTorsoKinematicsV3.Evaluate(pelvis,rotation,angles);
            var arm=torso.Arm(new PlayerArmJointsV3(joints),PlayerGripV3.ContinentalPrototype);
            var positions=new Vector3[2];
            for(int i=0;i<2;i++)
            {
                float t=i==0?-dt:dt;var a=(float[])joints.Clone();
                for(int j=0;j<a.Length;j++)a[j]+=armRates[j]*t*Mathf.Rad2Deg;
                var body=PlayerTorsoKinematicsV3.Evaluate(pelvis+velocity*t,
                    Quaternion.AngleAxis(omega.magnitude*t*Mathf.Rad2Deg,omega.normalized)*rotation,angles+rates*t*Mathf.Rad2Deg);
                positions[i]=body.Arm(new PlayerArmJointsV3(a),PlayerGripV3.ContinentalPrototype).PaddlePoint(point);
            }
            var actual=(positions[1]-positions[0])/(2*dt);
            var calculated=torso.PaddlePointVelocity(arm,arm.PaddlePoint(point),armRates,rates,velocity,omega);
            Assert.Less(Vector3.Distance(actual,calculated),.001f);
        }
        [Test] public void LeanChangesReachWithoutStretchingTheArm()
        {
            var straight=PlayerTorsoKinematicsV3.Evaluate(Vector3.up*.8f,Quaternion.identity,Vector3.zero);
            var leaned=PlayerTorsoKinematicsV3.Evaluate(Vector3.up*.8f,Quaternion.identity,new Vector3(30,25,10));
            var a=straight.Arm(PlayerArmJointsV3.Ready,PlayerGripV3.ContinentalPrototype);
            var b=leaned.Arm(PlayerArmJointsV3.Ready,PlayerGripV3.ContinentalPrototype);
            Assert.Greater(Vector3.Distance(a.hand,b.hand),.1f);
            Assert.That(Vector3.Distance(a.shoulder,a.hand),Is.EqualTo(Vector3.Distance(b.shoulder,b.hand)).Within(1e-6f));
            Assert.Throws<ArgumentException>(()=>PlayerTorsoKinematicsV3.Evaluate(Vector3.zero,Quaternion.identity,new Vector3(61,0,0)));
        }
    }
}

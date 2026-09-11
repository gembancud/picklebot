using System;
using NUnit.Framework;
using UnityEngine;
namespace Picklebot.PlayerControls.Tests
{
    public sealed class PlayerJointMotorV3Tests
    {
        [Test] public void ReversalsRespectRangeSpeedAccelerationAndActualDisplacement()
        {
            var motor=new PlayerJointMotorV3(22,22,150,360,1800);var random=new System.Random(73);
            float target=150;
            for(int i=0;i<30000;i++)
            {
                if(i%113==0)target=i%339==0?22:i%339==113?150:22+(float)random.NextDouble()*128;
                float previous=motor.Angle,rate=motor.Rate;motor.Step(target);
                Assert.That(motor.Angle,Is.InRange(22,150));Assert.LessOrEqual(Mathf.Abs(motor.Rate),360);
                Assert.LessOrEqual(Mathf.Abs(motor.Rate-rate),1800*PlayerJointMotorV3.Dt+.001f);
                Assert.That((motor.Angle-previous)/PlayerJointMotorV3.Dt,Is.EqualTo(motor.Rate).Within(.004f));
            }
            for(int i=0;i<2000;i++)motor.Step(150);
            Assert.That(motor.Angle,Is.EqualTo(150).Within(.001f));Assert.Less(Mathf.Abs(motor.Rate),.01f);
        }
        [TestCase(7.786234e-10f)] // Exact free-movement failure state.
        [TestCase(1e-12f)]
        [TestCase(1e-9f)]
        [TestCase(1e-7f)]
        [TestCase(1e-5f)]
        [TestCase(.001f)]
        public void BoundaryApproachPreservesBoundsWithoutSnapping(float distance)
        {
            // Both lower and upper limits, including the zero-valued limit
            // where the original subtractive formula lost precision.
            foreach(bool upper in new[]{false,true})
            {
                var motor=new PlayerJointMotorV3(upper?-distance:distance,upper?-140:0,upper?0:140,180,900);
                for(int tick=0;tick<64;tick++)
                {
                    float before=motor.Angle,rate=motor.Rate;motor.Step(0);
                    Assert.That(motor.Angle,Is.InRange(motor.minimum,motor.maximum));
                    Assert.LessOrEqual(Mathf.Abs(motor.Rate-rate),900*PlayerJointMotorV3.Dt+.001f);
                    Assert.LessOrEqual(Mathf.Abs(motor.Angle),Mathf.Abs(before));
                    Assert.That(motor.Angle,Is.EqualTo(before+motor.Rate*PlayerJointMotorV3.Dt));
                }
            }
        }

        [Test] public void UpperBodyMovesGraduallyAndKeepsPaddleAttached()
        {
            var motor=new PlayerUpperBodyMotorV3();var values=PlayerArmJointsV3.Ready.ToArray();values[0]=70;values[3]=35;
            var target=new PlayerArmJointsV3(values);
            motor.Step(new Vector3(50,25,-15),target);
            Assert.Less(motor.TorsoAngles.x,1);Assert.Less(motor.ArmAngles[0],1);
            for(int i=0;i<1000;i++)motor.Step(new Vector3(50,25,-15),target);
            var torso=motor.Pose(Vector3.up*.8f,Quaternion.identity);var arm=torso.Arm(motor.ArmAngles,PlayerGripV3.ContinentalPrototype);
            Assert.Less(Vector3.Distance(arm.hand,arm.PaddlePoint(PlayerPaddleControl.GripLocal)),1e-6f);
            Assert.That(motor.TorsoAngles.x,Is.EqualTo(50).Within(.001f));
            Assert.That(motor.ArmAngles[3],Is.EqualTo(35).Within(.001f));
        }
        [Test] public void InvalidRequestDoesNotAdvanceTheUpperBody()
        {
            var motor=new PlayerUpperBodyMotorV3();
            Assert.Throws<ArgumentException>(()=>motor.Step(new Vector3(0,float.NaN,0),PlayerArmJointsV3.Ready));
            Assert.AreEqual(Vector3.zero,motor.TorsoAngles);Assert.AreEqual(0,motor.ArmAngles[0]);
        }
    }
}

using System;
using Picklebot.Doubles;
using Picklebot.PlayerControls;
using UnityEngine;
namespace Picklebot.PlayerControlsIntegration
{
    public static class PlayerArticulatedFrameV3
    {
        public static PlayerBodyFrame ComposeBounded(PlayerBodyFrame locomotion,PlayerUpperBodyBoundedV3 motor)
        {
            if(motor==null)throw new ArgumentNullException(nameof(motor));
            var torso=motor.Pose();var arm=torso.Arm(motor.ArmAngles,PlayerGripV3.ContinentalPrototype);
            var frame=Compose(locomotion,torso,arm,Vector3.zero,new float[7],Vector3.zero,Vector3.zero);
            frame.paddleVelocity=motor.ActualVelocity;frame.paddleAngularVelocity=motor.ActualAngularVelocity;
            return frame;
        }
        // Locomotion owns root, legs, support flags. Upper-body joints own the arm/paddle.
        public static PlayerBodyFrame Compose(PlayerBodyFrame locomotion,PlayerTorsoPoseV3 torso,
            PlayerArmPoseV3 arm,Vector3 torsoRates,float[] armRates,Vector3 pelvisVelocity,Vector3 pelvisAngularVelocity)
        {
            if(torso==null||arm==null||Vector3.Distance(locomotion.pelvis,torso.pelvis)>.00001f
                ||Vector3.Distance(arm.PaddlePoint(PlayerBody.GripLocal),arm.hand)>.00001f)
                throw new ArgumentException("Articulated pose must use the locomotion pelvis and physical paddle grip.");
            var f=locomotion;f.articulatedUpperBody=true;f.torsoRotation=torso.rotation;
            f.shoulder=arm.shoulder;f.rightElbow=arm.elbow;f.rightWrist=arm.wrist;f.paddlePosition=arm.paddlePosition;f.paddleRotation=arm.paddleRotation;
            f.paddleVelocity=torso.PaddlePointVelocity(arm,arm.paddlePosition,armRates,torsoRates,pelvisVelocity,pelvisAngularVelocity);
            f.paddleAngularVelocity=arm.AngularVelocity(armRates,torso.AngularVelocity(torsoRates,pelvisAngularVelocity));
            return f;
        }
    }
}

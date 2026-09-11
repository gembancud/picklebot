using System;
using UnityEngine;
namespace Picklebot.PlayerControls
{
    // Reduced kinematic torso. Limits are provisional, not measured anatomy or balance.
    public sealed class PlayerTorsoPoseV3
    {
        public readonly Vector3 pelvis,shoulder;
        public readonly Quaternion rotation;
        private readonly Vector3[] axes;
        internal PlayerTorsoPoseV3(Vector3 pelvis,Quaternion rotation,Vector3[] axes)
        {
            this.pelvis=pelvis;this.rotation=rotation;this.axes=axes;
            shoulder=pelvis+rotation*new Vector3(.19f,.56f,0);
        }
        public Vector3 AngularVelocity(Vector3 rates,Vector3 pelvisAngularVelocity)
        {
            PlayerArmKinematicsV3.CheckVector(rates);PlayerArmKinematicsV3.CheckVector(pelvisAngularVelocity);
            return pelvisAngularVelocity+axes[0]*rates.x+axes[1]*rates.y+axes[2]*rates.z;
        }
        public Vector3 ShoulderVelocity(Vector3 rates,Vector3 pelvisVelocity,Vector3 pelvisAngularVelocity)
        {
            PlayerArmKinematicsV3.CheckVector(pelvisVelocity);
            return pelvisVelocity+Vector3.Cross(AngularVelocity(rates,pelvisAngularVelocity),shoulder-pelvis);
        }
        public PlayerArmPoseV3 Arm(PlayerArmJointsV3 joints,PlayerGripV3 grip)
            =>PlayerArmKinematicsV3.Evaluate(shoulder,rotation,joints,grip);
        public Vector3 PaddlePointVelocity(PlayerArmPoseV3 arm,Vector3 point,float[] armRates,
            Vector3 torsoRates,Vector3 pelvisVelocity,Vector3 pelvisAngularVelocity)
        {
            if(arm==null || Vector3.Distance(arm.shoulder,shoulder)>.00001f)
                throw new ArgumentException("Arm must attach to this torso shoulder.");
            return arm.PointVelocity(point,armRates,ShoulderVelocity(torsoRates,pelvisVelocity,pelvisAngularVelocity),
                AngularVelocity(torsoRates,pelvisAngularVelocity));
        }
    }
    public static class PlayerTorsoKinematicsV3
    {
        // x: axial turn, y: forward lean, z: lateral lean, in degrees.
        // Rate vectors use the same order in radians/sec. Pelvis motion comes from locomotion.
        public static PlayerTorsoPoseV3 Evaluate(Vector3 pelvis,Quaternion pelvisRotation,Vector3 degrees)
        {
            PlayerArmKinematicsV3.CheckVector(pelvis);PlayerArmKinematicsV3.CheckRotation(pelvisRotation);
            PlayerArmKinematicsV3.CheckVector(degrees);
            if(Mathf.Abs(degrees.x)>60 || degrees.y < -15 || degrees.y>35 || Mathf.Abs(degrees.z)>25)
                throw new ArgumentException("Torso outside prototype limits.");
            var axes=new Vector3[3];var q=pelvisRotation;
            axes[0]=q*Vector3.up;q*=Quaternion.AngleAxis(degrees.x,Vector3.up);
            axes[1]=q*Vector3.right;q*=Quaternion.AngleAxis(degrees.y,Vector3.right);
            axes[2]=q*Vector3.forward;q*=Quaternion.AngleAxis(degrees.z,Vector3.forward);
            return new PlayerTorsoPoseV3(pelvis,q,axes);
        }
    }
}

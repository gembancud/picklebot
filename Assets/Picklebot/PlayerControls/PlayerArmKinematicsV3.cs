using System;
using UnityEngine;
namespace Picklebot.PlayerControls
{
    // Prototype joint conventions and limits, not measured human calibration.
    // Angles are degrees; rates passed to PointVelocity are radians/second.
    public sealed class PlayerArmJointsV3
    {
        public const int Count=7;
        public static readonly string[] Names={"shoulder.yaw","shoulder.flexion","shoulder.abduction",
            "elbow.flexion","forearm.rotation","wrist.flexion","wrist.deviation"};
        private static readonly float[] minimum={-100,-45,-30,22,-90,-65,-30};
        private static readonly float[] maximum={100,130,110,150,90,65,30};
        private readonly float[] values;
        public float this[int i]=>values[i];
        public static float Minimum(int i)=>minimum[i];
        public static float Maximum(int i)=>maximum[i];
        public static PlayerArmJointsV3 Ready=>new PlayerArmJointsV3(new[]{0f,15f,10f,90f,45f,-20f,0f});
        public PlayerArmJointsV3(float[] degrees)
        {
            if(degrees==null||degrees.Length!=Count)throw new ArgumentException("Seven arm joint angles required.");
            values=(float[])degrees.Clone();
            for(int i=0;i<Count;i++)if(!float.IsFinite(values[i])||values[i]<minimum[i]||values[i]>maximum[i])throw new ArgumentException("Arm joint outside prototype limits: "+Names[i]);
        }
        public float[] ToArray()=>(float[])values.Clone();
    }
    public readonly struct PlayerGripV3
    {
        public readonly Quaternion paddleInHand;
        public readonly Vector3 pointOnPaddle;
        // Hand reference: distal axis -Y, palm normal +Z. The handle crosses
        // the closed hand along +X, tangent to the palm plane. It must not
        // extend through the palm (+Z) or along the fingers (-Y).
        // The 45-degree bevel convention is provisional, not calibrated anatomy.
        // Wrist posture is represented by joints, not baked into this transform.
        public static PlayerGripV3 ContinentalPrototype=>new PlayerGripV3(
            Quaternion.AngleAxis(-90,Vector3.forward)*Quaternion.AngleAxis(45,Vector3.up),PlayerPaddleControl.GripLocal);
        private PlayerGripV3(Quaternion orientation,Vector3 point)
        {
            PlayerArmKinematicsV3.CheckRotation(orientation);PlayerArmKinematicsV3.CheckVector(point);
            paddleInHand=orientation;pointOnPaddle=point;
        }
    }
    public sealed class PlayerArmPoseV3
    {
        public readonly Vector3 shoulder,elbow,wrist,hand,paddlePosition;
        public readonly Quaternion paddleRotation,handRotation;
        public Vector3 PalmNormal=>handRotation*Vector3.forward;
        public Vector3 FingerDirection=>handRotation*Vector3.down;
        public Vector3 AcrossPalm=>handRotation*Vector3.right;
        private readonly Vector3[] axes,pivots;
        internal PlayerArmPoseV3(Vector3 shoulder,Vector3 elbow,Vector3 wrist,Vector3 hand,Quaternion handRotation,PlayerGripV3 grip,Vector3[] axes,Vector3[] pivots)
        {
            this.shoulder=shoulder;this.elbow=elbow;this.wrist=wrist;this.hand=hand;this.handRotation=handRotation;
            paddleRotation=handRotation*grip.paddleInHand;paddlePosition=hand-paddleRotation*grip.pointOnPaddle;
            this.axes=axes;this.pivots=pivots;
        }
        public Vector3 PaddlePoint(Vector3 local)=>paddlePosition+paddleRotation*local;
        public Vector3 PointVelocity(Vector3 worldPoint,float[] jointRates,Vector3 shoulderVelocity=default,Vector3 bodyAngularVelocity=default)
        {
            if(jointRates==null||jointRates.Length!=PlayerArmJointsV3.Count)throw new ArgumentException("Seven joint rates required.");
            PlayerArmKinematicsV3.CheckVector(worldPoint);PlayerArmKinematicsV3.CheckVector(shoulderVelocity);PlayerArmKinematicsV3.CheckVector(bodyAngularVelocity);
            var velocity=shoulderVelocity+Vector3.Cross(bodyAngularVelocity,worldPoint-shoulder);
            for(int i=0;i<jointRates.Length;i++)
            {
                if(!float.IsFinite(jointRates[i]))throw new ArgumentException("Finite joint rates required.");
                velocity+=Vector3.Cross(axes[i]*jointRates[i],worldPoint-pivots[i]);
            }
            return velocity;
        }
        public Vector3 AngularVelocity(float[] jointRates,Vector3 bodyAngularVelocity=default)
        {
            // Validate through the same rate contract; translation is irrelevant.
            PointVelocity(hand,jointRates,default,bodyAngularVelocity);
            var result=bodyAngularVelocity;for(int i=0;i<jointRates.Length;i++)result+=axes[i]*jointRates[i];return result;
        }
    }
    public static class PlayerArmKinematicsV3
    {
        public const float UpperLength=.32f,ForearmLength=.25f,HandLength=.06f;
        internal static void CheckVector(Vector3 p)
        {if(!float.IsFinite(p.x)||!float.IsFinite(p.y)||!float.IsFinite(p.z))throw new ArgumentException("Finite vector required.");}
        internal static void CheckRotation(Quaternion q)
        {float n=q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w;if(!float.IsFinite(n)||Mathf.Abs(n-1)>.001f)throw new ArgumentException("Unit rotation required.");}
        public static PlayerArmPoseV3 Evaluate(Vector3 shoulder,Quaternion bodyRotation,PlayerArmJointsV3 joints,PlayerGripV3 grip)
        {
            CheckVector(shoulder);CheckRotation(bodyRotation);CheckRotation(grip.paddleInHand);CheckVector(grip.pointOnPaddle);
            if(joints==null)throw new ArgumentNullException(nameof(joints));
            var axes=new Vector3[7];var pivots=new Vector3[7];var q=bodyRotation;
            for(int i=0;i<3;i++)pivots[i]=shoulder;
            axes[0]=q*Vector3.up;q*=Quaternion.AngleAxis(joints[0],Vector3.up);
            axes[1]=q*Vector3.left;q*=Quaternion.AngleAxis(joints[1],Vector3.left);
            axes[2]=q*Vector3.forward;q*=Quaternion.AngleAxis(joints[2],Vector3.forward);
            var elbow=shoulder+q*Vector3.down*UpperLength;
            pivots[3]=pivots[4]=elbow;
            axes[3]=q*Vector3.left;q*=Quaternion.AngleAxis(joints[3],Vector3.left);
            var wrist=elbow+q*Vector3.down*ForearmLength;
            axes[4]=q*Vector3.down;q*=Quaternion.AngleAxis(joints[4],Vector3.down);
            pivots[5]=pivots[6]=wrist;
            axes[5]=q*Vector3.right;q*=Quaternion.AngleAxis(joints[5],Vector3.right);
            axes[6]=q*Vector3.forward;q*=Quaternion.AngleAxis(joints[6],Vector3.forward);
            var hand=wrist+q*Vector3.down*HandLength;
            return new PlayerArmPoseV3(shoulder,elbow,wrist,hand,q,grip,axes,pivots);
        }
    }
}

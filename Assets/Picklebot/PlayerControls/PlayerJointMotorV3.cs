using System;
using UnityEngine;
namespace Picklebot.PlayerControls
{
    // Internal pose motor, not a policy action schema or calibrated muscle model.
    // Semi-implicit fixed-step integration: rates are those actually used to move joints.
    public sealed class PlayerJointMotorV3
    {
        public const float Dt=1f/240f;
        public float Angle { get; private set; }
        public float Rate { get; private set; } // degrees/second
        public readonly float minimum,maximum,maxRate,maxAcceleration;
        public PlayerJointMotorV3(float initial,float minimum,float maximum,float maxRate,float maxAcceleration)
        {
            if(!float.IsFinite(initial)||!float.IsFinite(minimum)||!float.IsFinite(maximum)
                ||!float.IsFinite(maxRate)||!float.IsFinite(maxAcceleration)||minimum>=maximum
                ||initial<minimum||initial>maximum||maxRate<=0||maxAcceleration<=0)
                throw new ArgumentException("Invalid joint motor profile.");
            Angle=initial;this.minimum=minimum;this.maximum=maximum;
            this.maxRate=maxRate;this.maxAcceleration=maxAcceleration;
        }
        private float SafeRate(float distance,float brakingFraction=1)
        {
            // Conservative braking reserve includes the next integration step.
            // Rationalize sqrt(dv² + 2ad) - dv: subtracting nearly equal
            // floats overestimates tiny braking speeds near a joint limit.
            double acceleration=(double)maxAcceleration*brakingFraction;
            double d=Math.Max(0,(double)distance),dv=acceleration*Dt;
            double twiceAD=2*acceleration*d;
            float bound=(float)(twiceAD/(Math.Sqrt(dv*dv+twiceAD)+dv));
            // Round inward by one representable positive float so the final
            // float integration cannot step past the boundary by rounding up.
            return bound<=0?0:BitConverter.Int32BitsToSingle(BitConverter.SingleToInt32Bits(bound)-1);
        }
        internal PlayerJointMotorV3 Fork()=>(PlayerJointMotorV3)MemberwiseClone();
        internal Vector2 RateInterval(float brakingFraction=1)=>new Vector2(Mathf.Max(-maxRate,Rate-maxAcceleration*Dt,-SafeRate(Angle-minimum,brakingFraction)),
            Mathf.Min(maxRate,Rate+maxAcceleration*Dt,SafeRate(maximum-Angle,brakingFraction)));
        internal void CommitRate(float rate){Angle+=rate*Dt;Rate=rate;}
        public void Step(float target)
        {
            if(!float.IsFinite(target)||target<minimum||target>maximum)throw new ArgumentException("Target outside joint range.");
            float error=target-Angle;
            float desired=Mathf.Sign(error)*Mathf.Min(maxRate,SafeRate(Mathf.Abs(error)));
            float next=Mathf.MoveTowards(Rate,desired,maxAcceleration*Dt);
            float low=Mathf.Max(-maxRate,-SafeRate(Angle-minimum));
            float high=Mathf.Min(maxRate,SafeRate(maximum-Angle));
            next=Mathf.Clamp(next,low,high);
            if(Mathf.Abs(next-Rate)>maxAcceleration*Dt+.001f)
                throw new InvalidOperationException("Joint cannot brake within its bounds.");
            float angle=Angle+next*Dt;
            if(angle<minimum || angle>maximum)throw new InvalidOperationException("Joint integration escaped range.");
            Angle=angle;Rate=next;
        }
    }
    public sealed class PlayerUpperBodyMotorV3
    {
        private readonly PlayerJointMotorV3[] torso,arm;
        public PlayerUpperBodyMotorV3()
        {
            torso=new[]{new PlayerJointMotorV3(0,-60,60,180,900),
                new PlayerJointMotorV3(0,-15,35,90,450),new PlayerJointMotorV3(0,-25,25,90,450)};
            var ready=PlayerArmJointsV3.Ready;
            arm=new PlayerJointMotorV3[7];
            // Provisional rates/accelerations; do not interpret as measured human limits.
            for(int i=0;i<7;i++)arm[i]=new PlayerJointMotorV3(ready[i],PlayerArmJointsV3.Minimum(i),PlayerArmJointsV3.Maximum(i),i<4?360:480,i<4?1800:2400);
        }
        internal PlayerUpperBodyMotorV3 Fork()
        {
            var copy=new PlayerUpperBodyMotorV3();
            for(int i=0;i<3;i++)copy.torso[i]=torso[i].Fork();
            for(int i=0;i<7;i++)copy.arm[i]=arm[i].Fork();
            return copy;
        }
        internal PlayerJointMotorV3 Joint(int i)=>i<3?torso[i]:arm[i-3];
        public Vector3 TorsoAngles=>new Vector3(torso[0].Angle,torso[1].Angle,torso[2].Angle);
        public Vector3 TorsoRates=>new Vector3(torso[0].Rate,torso[1].Rate,torso[2].Rate)*Mathf.Deg2Rad;
        public PlayerArmJointsV3 ArmAngles
        {get{var a=new float[7];for(int i=0;i<7;i++)a[i]=arm[i].Angle;return new PlayerArmJointsV3(a);}}
        public float[] ArmRates
        {get{var a=new float[7];for(int i=0;i<7;i++)a[i]=arm[i].Rate*Mathf.Deg2Rad;return a;}}
        public void Step(Vector3 torsoTarget,PlayerArmJointsV3 armTarget)
        {
            if(armTarget==null)throw new ArgumentNullException(nameof(armTarget));
            // Validate the complete request before advancing any joint.
            PlayerTorsoKinematicsV3.Evaluate(Vector3.zero,Quaternion.identity,torsoTarget);
            for(int i=0;i<3;i++)torso[i].Step(torsoTarget[i]);
            for(int i=0;i<7;i++)arm[i].Step(armTarget[i]);
        }
        public PlayerTorsoPoseV3 Pose(Vector3 pelvis,Quaternion pelvisRotation)
            =>PlayerTorsoKinematicsV3.Evaluate(pelvis,pelvisRotation,TorsoAngles);
    }
}

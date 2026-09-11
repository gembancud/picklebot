using System;
using UnityEngine;
namespace Picklebot.PlayerControls
{
    // Prototype coordinated solver including a proposed pelvis pose. Failure is atomic:
    // caller must not advance locomotion or physics after false.
    public sealed partial class PlayerUpperBodyBoundedV3
    {
        // Prefer using one eighth of joint acceleration to approach range limits;
        // leave additional acceleration available for coupled paddle motion.
        // This slows approach to joint limits without reducing joint range or
        // relaxing the actual joint and whole-paddle acceptance limits.
        private const float JointLimitBrakingFraction=.125f;
        private PlayerUpperBodyMotorV3 motor=new PlayerUpperBodyMotorV3();
        private Vector3 previousVelocity,pelvis=Vector3.up*.8f;
        private Quaternion pelvisRotation=Quaternion.identity;
        public Vector3 ActualAngularVelocity {get; private set;}
        public PlayerUpperBodyBoundedV3(){}
        public PlayerUpperBodyBoundedV3(Vector3 pelvis,Quaternion rotation)
        {PlayerArmKinematicsV3.CheckVector(pelvis);PlayerArmKinematicsV3.CheckRotation(rotation);this.pelvis=pelvis;pelvisRotation=rotation;}
        public PlayerUpperBodyBoundedV3 Fork()
        {var copy=(PlayerUpperBodyBoundedV3)MemberwiseClone();copy.motor=motor.Fork();return copy;}
        public Vector3 TorsoAngles=>motor.TorsoAngles;
        public PlayerArmJointsV3 ArmAngles=>motor.ArmAngles;
        public Vector3 TorsoRates=>motor.TorsoRates;
        public float[] ArmRates=>motor.ArmRates;
        public Vector3 ActualVelocity=>previousVelocity;
        public PlayerTorsoPoseV3 Pose()=>motor.Pose(pelvis,pelvisRotation);
        private PlayerArmPoseV3 Evaluate(float[] rates,Vector3 nextPelvis,Quaternion nextRotation)
        {
            var t=motor.TorsoAngles;var a=motor.ArmAngles.ToArray();
            for(int i=0;i<3;i++)t[i]+=rates[i]*Mathf.Rad2Deg*PlayerJointMotorV3.Dt;
            for(int i=0;i<7;i++)a[i]+=rates[i+3]*Mathf.Rad2Deg*PlayerJointMotorV3.Dt;
            return PlayerTorsoKinematicsV3.Evaluate(nextPelvis,nextRotation,t).Arm(new PlayerArmJointsV3(a),PlayerGripV3.ContinentalPrototype);
        }
        private static void Project(float[] rates,Vector3[] jacobian,Vector3 error,float radius)
        {
            float length=error.magnitude;if(length<=radius)return;
            var direction=error/length;var gradient=new float[10];float denominator=0;
            for(int j=0;j<10;j++){gradient[j]=Vector3.Dot(jacobian[j],direction);denominator+=gradient[j]*gradient[j];}
            if(denominator<1e-10f)return;
            float correction=(length-radius)/denominator;
            for(int j=0;j<10;j++)rates[j]-=correction*gradient[j];
        }
        public bool TryStep(Vector3 torsoTarget,PlayerArmJointsV3 armTarget)=>TryStep(torsoTarget,armTarget,pelvis,pelvisRotation);
        public bool TryStep(Vector3 torsoTarget,PlayerArmJointsV3 armTarget,Vector3 nextPelvis,Quaternion nextRotation)
        {
            PlayerArmKinematicsV3.CheckVector(nextPelvis);PlayerArmKinematicsV3.CheckRotation(nextRotation);
            if(armTarget==null)throw new ArgumentNullException(nameof(armTarget));
            PlayerTorsoKinematicsV3.Evaluate(Vector3.zero,Quaternion.identity,torsoTarget);
            var rates=new float[10];var bounds=new Vector2[10];
            for(int i=0;i<10;i++)
            {
                var joint=motor.Joint(i);var trial=joint.Fork();trial.Step(i<3?torsoTarget[i]:armTarget[i-3]);
                rates[i]=trial.Rate*Mathf.Deg2Rad;bounds[i]=joint.RateInterval(JointLimitBrakingFraction)*Mathf.Deg2Rad;
            }
            if(TryRates(rates,bounds,nextPelvis,nextRotation))return true;
            // The extra reserve is a preference, not a new physical limit.
            // Retry from the unchanged motor using the original hard limits.
            for(int i=0;i<10;i++)
            {
                var joint=motor.Joint(i);var trial=joint.Fork();trial.Step(i<3?torsoTarget[i]:armTarget[i-3]);
                rates[i]=trial.Rate*Mathf.Deg2Rad;bounds[i]=joint.RateInterval()*Mathf.Deg2Rad;
            }
            return TryRates(rates,bounds,nextPelvis,nextRotation);
        }
        private bool TryRates(float[] rates,Vector2[] bounds,Vector3 nextPelvis,Quaternion nextRotation)
        {
            // An empty joint interval cannot be repaired by clamping.
            for(int j=0;j<bounds.Length;j++)if(bounds[j].x>bounds[j].y)return false;
            var old=Pose().Arm(motor.ArmAngles,PlayerGripV3.ContinentalPrototype);
            var torso=motor.Pose(nextPelvis,nextRotation);var basePose=torso.Arm(motor.ArmAngles,PlayerGripV3.ContinentalPrototype);
            var linear=new Vector3[10];var angular=new Vector3[10];
            for(int i=0;i<10;i++)
            {
                var tr=Vector3.zero;var ar=new float[7];if(i<3)tr[i]=1;else ar[i-3]=1;
                linear[i]=torso.PaddlePointVelocity(basePose,basePose.paddlePosition,ar,tr,Vector3.zero,Vector3.zero);
                angular[i]=basePose.AngularVelocity(ar,torso.AngularVelocity(tr,Vector3.zero));
            }
            // Rare coupled pelvis/joint states need more projection passes.
            // Early acceptance preserves the original fast path and all limits.
            for(int iteration=0;iteration<8192;iteration++)
            {
                for(int j=0;j<10;j++)rates[j]=Mathf.Clamp(rates[j],bounds[j].x,bounds[j].y);
                var next=Evaluate(rates,nextPelvis,nextRotation);var v=(next.paddlePosition-old.paddlePosition)/PlayerJointMotorV3.Dt;
                var dq=next.paddleRotation*Quaternion.Inverse(old.paddleRotation);if(dq.w<0)dq=new Quaternion(-dq.x,-dq.y,-dq.z,-dq.w);
                dq.ToAngleAxis(out float angle,out Vector3 axis);
                var omega=angle<.00001f?Vector3.zero:axis*angle*Mathf.Deg2Rad/PlayerJointMotorV3.Dt;
                if(v.magnitude<=12 && (v-previousVelocity).magnitude<=100*PlayerJointMotorV3.Dt && Quaternion.Angle(old.paddleRotation,next.paddleRotation)*Mathf.Deg2Rad/PlayerJointMotorV3.Dt<=11.99f)
                {
                    for(int j=0;j<10;j++)motor.Joint(j).CommitRate(rates[j]*Mathf.Rad2Deg);
                    previousVelocity=v;ActualAngularVelocity=omega;pelvis=nextPelvis;pelvisRotation=nextRotation;return true;
                }
                // Preserve the existing fast path. If its fixed Jacobian stalls,
                // refresh derivatives at the proposed pose before projecting again.
                // Acceptance still checks the actual finite-step motion and bounds.
                if(iteration>=4096)
                {
                    var nextAngles=motor.TorsoAngles;
                    for(int j=0;j<3;j++)nextAngles[j]+=rates[j]*Mathf.Rad2Deg*PlayerJointMotorV3.Dt;
                    var nextTorso=PlayerTorsoKinematicsV3.Evaluate(nextPelvis,nextRotation,nextAngles);
                    for(int j=0;j<10;j++)
                    {
                        var tr=Vector3.zero;var ar=new float[7];if(j<3)tr[j]=1;else ar[j-3]=1;
                        linear[j]=nextTorso.PaddlePointVelocity(next,next.paddlePosition,ar,tr,Vector3.zero,Vector3.zero);
                        angular[j]=next.AngularVelocity(ar,nextTorso.AngularVelocity(tr,Vector3.zero));
                    }
                }
                Project(rates,linear,v,11.95f);
                Project(rates,linear,v-previousVelocity,99*PlayerJointMotorV3.Dt);
                Project(rates,angular,omega,11.95f);
            }
            return false;
        }
    }
}

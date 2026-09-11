using System;
using UnityEngine;
namespace Picklebot.PlayerControls
{
    public sealed partial class PlayerUpperBodyBoundedV3
    {
        // Task-space velocity tracking with box constraints from the same joint motors.
        // A true return means the physical step is feasible, not that the target was reached.
        public bool TryTrack(Vector3 facePoint,Vector3 faceNormal,Vector3 feedVelocity)
            =>TryTrack(facePoint,faceNormal,feedVelocity,pelvis,pelvisRotation);
        public bool TryTrack(Vector3 facePoint,Vector3 faceNormal,Vector3 feedVelocity,Vector3 nextPelvis,Quaternion nextRotation)
        {
            PlayerArmKinematicsV3.CheckVector(facePoint);PlayerArmKinematicsV3.CheckVector(faceNormal);
            PlayerArmKinematicsV3.CheckVector(feedVelocity);PlayerArmKinematicsV3.CheckVector(nextPelvis);PlayerArmKinematicsV3.CheckRotation(nextRotation);
            if(faceNormal.sqrMagnitude<1e-8f)throw new ArgumentException("Face normal is required.");
            faceNormal.Normalize();
            var old=Pose().Arm(motor.ArmAngles,PlayerGripV3.ContinentalPrototype);
            var torso=motor.Pose(nextPelvis,nextRotation);var pose=torso.Arm(motor.ArmAngles,PlayerGripV3.ContinentalPrototype);
            var p=pose.PaddlePoint(PlayerStrokeAimV3.FacePoint);var n=pose.paddleRotation*Vector3.forward;
            var rootVelocity=(p-old.PaddlePoint(PlayerStrokeAimV3.FacePoint))/PlayerJointMotorV3.Dt;
            var rootNormalRate=(n-old.paddleRotation*Vector3.forward)/PlayerJointMotorV3.Dt;
            var velocity=Vector3.ClampMagnitude(feedVelocity+(facePoint-p)*20,12)-rootVelocity;
            var normalRate=Vector3.ProjectOnPlane(faceNormal-n,n)*30-rootNormalRate;
            const float normalWeight=.7f,regularization=.0001f;
            var linear=new Vector3[10];var direction=new Vector3[10];var rates=new float[10];var bounds=new Vector2[10];
            for(int i=0;i<10;i++)
            {
                var tr=Vector3.zero;var ar=new float[7];if(i<3)tr[i]=1;else ar[i-3]=1;
                linear[i]=torso.PaddlePointVelocity(pose,p,ar,tr,Vector3.zero,Vector3.zero);
                direction[i]=Vector3.Cross(pose.AngularVelocity(ar,torso.AngularVelocity(tr,Vector3.zero)),n)*normalWeight;
                bounds[i]=motor.Joint(i).RateInterval()*Mathf.Deg2Rad;
                rates[i]=Mathf.Clamp(motor.Joint(i).Rate*Mathf.Deg2Rad,bounds[i].x,bounds[i].y);
            }
            var h=new float[10,10];var b=new float[10];
            for(int i=0;i<10;i++)
            {
                b[i]=Vector3.Dot(linear[i],velocity)+Vector3.Dot(direction[i],normalRate*normalWeight);
                for(int j=0;j<10;j++)h[i,j]=Vector3.Dot(linear[i],linear[j])+Vector3.Dot(direction[i],direction[j])+(i==j?regularization:0);
            }
            // Coordinate minimization of a convex quadratic within joint rate intervals.
            for(int iteration=0;iteration<96;iteration++)
            {
                float change=0;
                for(int i=0;i<10;i++)
                {
                    float residual=b[i];for(int j=0;j<10;j++)residual-=h[i,j]*rates[j];
                    float next=Mathf.Clamp(rates[i]+residual/h[i,i],bounds[i].x,bounds[i].y);
                    change=Mathf.Max(change,Mathf.Abs(next-rates[i]));rates[i]=next;
                }
                if(change<1e-5f)break;
            }
            return TryRates(rates,bounds,nextPelvis,nextRotation);
        }
    }
}

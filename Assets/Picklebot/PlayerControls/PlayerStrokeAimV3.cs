using System;
using UnityEngine;
namespace Picklebot.PlayerControls
{
    // Geometric aiming only. This does not certify collision clearance, time-to-contact,
    // or a legal return. All execution must still pass PlayerUpperBodyBoundedV3.
    public static class PlayerStrokeAimV3
    {
        public static readonly Vector3 FacePoint=new Vector3(0,.0635f,0);
        public sealed class Result
        {
            public readonly Vector3 torso;
            public readonly PlayerArmJointsV3 arm;
            public readonly float positionError,normalErrorDegrees;
            public bool Reached=>positionError<=.005f&&normalErrorDegrees<=2;
            internal Result(Vector3 t,PlayerArmJointsV3 a,float p,float n)
            {torso=t;arm=a;positionError=p;normalErrorDegrees=n;}
        }
        private static float Minimum(int i)=>i<3?(i==0?-60:i==1?-15:-25):PlayerArmJointsV3.Minimum(i-3);
        private static float Maximum(int i)=>i<3?(i==0?60:i==1?35:25):PlayerArmJointsV3.Maximum(i-3);
        private static PlayerArmPoseV3 Pose(float[] q,Vector3 pelvis,Quaternion rotation,out PlayerTorsoPoseV3 torso)
        {
            torso=PlayerTorsoKinematicsV3.Evaluate(pelvis,rotation,new Vector3(q[0],q[1],q[2]));
            var a=new float[7];Array.Copy(q,3,a,0,7);
            return torso.Arm(new PlayerArmJointsV3(a),PlayerGripV3.ContinentalPrototype);
        }
        private static float Error(PlayerArmPoseV3 pose,Vector3 point,Vector3 normal)
            =>(point-pose.PaddlePoint(FacePoint)).sqrMagnitude+.04f*(normal-pose.paddleRotation*Vector3.forward).sqrMagnitude;
        public static Result Solve(Vector3 pelvis,Quaternion rotation,Vector3 initialTorso,PlayerArmJointsV3 initialArm,Vector3 point,Vector3 normal)
        {
            PlayerArmKinematicsV3.CheckVector(point);PlayerArmKinematicsV3.CheckVector(normal);
            if(normal.sqrMagnitude<1e-8f)throw new ArgumentException("A face direction is required.");
            if(initialArm==null)throw new ArgumentNullException(nameof(initialArm));
            normal.Normalize();var q=new float[10];for(int i=0;i<3;i++)q[i]=initialTorso[i];for(int i=0;i<7;i++)q[i+3]=initialArm[i];
            var pose=Pose(q,pelvis,rotation,out var torso);
            for(int iteration=0;iteration<64;iteration++)
            {
                var p=pose.PaddlePoint(FacePoint);var n=pose.paddleRotation*Vector3.forward;
                if(Vector3.Distance(p,point)<.002f&&Vector3.Angle(n,normal)<.5f)break;
                var e=new double[6];var ep=point-p;var en=(normal-n)*.2f;
                for(int k=0;k<3;k++){e[k]=ep[k];e[k+3]=en[k];}
                var j=new double[6,10];
                for(int k=0;k<10;k++)
                {
                    var tr=Vector3.zero;var ar=new float[7];if(k<3)tr[k]=1;else ar[k-3]=1;
                    var dp=torso.PaddlePointVelocity(pose,p,ar,tr,Vector3.zero,Vector3.zero);
                    var dn=Vector3.Cross(pose.AngularVelocity(ar,torso.AngularVelocity(tr,Vector3.zero)),n)*.2f;
                    for(int r=0;r<3;r++){j[r,k]=dp[r];j[r+3,k]=dn[r];}
                }
                // Damped least squares in task space; normal error leaves paddle roll free.
                var m=new double[6,7];
                for(int r=0;r<6;r++){for(int c=0;c<6;c++){for(int k=0;k<10;k++)m[r,c]+=j[r,k]*j[c,k];if(r==c)m[r,c]+=.0001;}m[r,6]=e[r];}
                for(int c=0;c<6;c++)
                {
                    int pivot=c;for(int r=c+1;r<6;r++)if(Math.Abs(m[r,c])>Math.Abs(m[pivot,c]))pivot=r;
                    for(int k=c;k<7;k++){double tmp=m[c,k];m[c,k]=m[pivot,k];m[pivot,k]=tmp;}
                    double d=m[c,c];for(int k=c;k<7;k++)m[c,k]/=d;
                    for(int r=0;r<6;r++)if(r!=c){double f=m[r,c];for(int k=c;k<7;k++)m[r,k]-=f*m[c,k];}
                }
                var delta=new float[10];for(int k=0;k<10;k++){double d=0;for(int r=0;r<6;r++)d+=j[r,k]*m[r,6];delta[k]=Mathf.Clamp((float)d,-.2f,.2f)*Mathf.Rad2Deg;}
                bool improved=false;float error=Error(pose,point,normal);
                for(int line=0;line<8;line++)
                {
                    var trial=new float[10];for(int k=0;k<10;k++)trial[k]=Mathf.Clamp(q[k]+delta[k]*Mathf.Pow(.5f,line),Minimum(k),Maximum(k));
                    var next=Pose(trial,pelvis,rotation,out var nextTorso);
                    if(Error(next,point,normal)>=error)continue;
                    q=trial;pose=next;torso=nextTorso;improved=true;break;
                }
                if(!improved)break;
            }
            var angles=new float[7];Array.Copy(q,3,angles,0,7);
            return new Result(new Vector3(q[0],q[1],q[2]),new PlayerArmJointsV3(angles),Vector3.Distance(point,pose.PaddlePoint(FacePoint)),Vector3.Angle(normal,pose.paddleRotation*Vector3.forward));
        }
    }
}

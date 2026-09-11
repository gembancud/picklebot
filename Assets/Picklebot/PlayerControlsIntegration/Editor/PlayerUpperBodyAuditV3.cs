using System;
using System.IO;
using Picklebot.PlayerControls;
using Picklebot.Doubles;
using UnityEngine;
namespace Picklebot.PlayerControlsIntegration.Editor
{
    public static class PlayerUpperBodyAuditV3
    {
        [Serializable] public sealed class Report
        {
            public string note="Adversarial joint targets with stationary pelvis. Diagnostic only; no policy or final-evaluation seeds.";
            public int rejectedSteps; public bool coordinated; public int steps,seed=1300000,speedViolations,accelerationViolations,angularViolations,firstViolation=-1;
            public float maxSpeed,maxAcceleration,maxAngularSpeed,maxReach,maxVelocityDiscrepancy;
            public Vector3 firstTorso;
            public float[] firstArm;
        }
        public static string Run(string path,bool coordinated=false)
        {
            if(File.Exists(path))throw new IOException("Use a new audit path.");
            var report=new Report{coordinated=coordinated};var bounded=new PlayerUpperBodyBoundedV3();var random=new System.Random(report.seed);var motor=new PlayerUpperBodyMotorV3();
            var torso=motor.Pose(Vector3.up*.8f,Quaternion.identity);
            var old=torso.Arm(motor.ArmAngles,PlayerGripV3.ContinentalPrototype);var previousVelocity=Vector3.zero;
            var target=PlayerArmJointsV3.Ready;var torsoTarget=Vector3.zero;
            for(int step=0;step<12000;step++)
            {
                if(step%90==0)
                {
                    var angles=new float[7];for(int j=0;j<7;j++)angles[j]=Mathf.Lerp(PlayerArmJointsV3.Minimum(j),PlayerArmJointsV3.Maximum(j),(float)random.NextDouble());
                    target=new PlayerArmJointsV3(angles);
                    torsoTarget=new Vector3(Mathf.Lerp(-60,60,(float)random.NextDouble()),Mathf.Lerp(-15,35,(float)random.NextDouble()),Mathf.Lerp(-25,25,(float)random.NextDouble()));
                }
                if(coordinated){if(!bounded.TryStep(torsoTarget,target)){report.rejectedSteps++;break;}torso=bounded.Pose();}else{motor.Step(torsoTarget,target);torso=motor.Pose(Vector3.up*.8f,Quaternion.identity);}
                var pose=torso.Arm(coordinated?bounded.ArmAngles:motor.ArmAngles,PlayerGripV3.ContinentalPrototype);
                var velocity=(pose.paddlePosition-old.paddlePosition)/DoublesWorld.Dt;
                float speed=velocity.magnitude,acceleration=(velocity-previousVelocity).magnitude/DoublesWorld.Dt;
                float omega=Quaternion.Angle(old.paddleRotation,pose.paddleRotation)*Mathf.Deg2Rad/DoublesWorld.Dt;
                var analytic=torso.PaddlePointVelocity(pose,pose.paddlePosition,coordinated?bounded.ArmRates:motor.ArmRates,coordinated?bounded.TorsoRates:motor.TorsoRates,Vector3.zero,Vector3.zero);
                report.maxSpeed=Mathf.Max(report.maxSpeed,speed);report.maxAcceleration=Mathf.Max(report.maxAcceleration,acceleration);
                report.maxAngularSpeed=Mathf.Max(report.maxAngularSpeed,omega);report.maxReach=Mathf.Max(report.maxReach,Vector3.Distance(pose.shoulder,pose.hand));
                report.maxVelocityDiscrepancy=Mathf.Max(report.maxVelocityDiscrepancy,Vector3.Distance(analytic,velocity));
                bool bad=false;
                if(speed>PlayerBody.PaddleSpeed+.01f){report.speedViolations++;bad=true;}
                if(acceleration>PlayerBody.PaddleAcceleration+.01f){report.accelerationViolations++;bad=true;}
                if(omega>PlayerBody.AngularSpeed+.01f){report.angularViolations++;bad=true;}
                if(bad&&report.firstViolation<0){report.firstViolation=step;report.firstTorso=motor.TorsoAngles;report.firstArm=motor.ArmAngles.ToArray();}
                previousVelocity=velocity;old=pose;report.steps++;
            }
            var json=JsonUtility.ToJson(report,true);File.WriteAllText(path,json);return json;
        }
    }
}

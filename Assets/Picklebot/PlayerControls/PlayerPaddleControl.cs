using System;
using UnityEngine;

namespace Picklebot.PlayerControls
{
    [Serializable] public struct PlayerPaddleCommand
    {
        // Hand target, wrist angles and feed are body-local, with no ball planner.
        public Vector3 localHandTarget,localEuler,localFeedVelocity;
        public static PlayerPaddleCommand Ready=>new PlayerPaddleCommand{localHandTarget=new Vector3(0,-.20f,.35f)};
        internal void Validate()
        {
            foreach(var v in new[]{localHandTarget,localEuler,localFeedVelocity})
                if(!float.IsFinite(v.x)||!float.IsFinite(v.y)||!float.IsFinite(v.z))throw new ArgumentException("Non-finite paddle command.");
        }
    }
    public readonly struct PlayerPaddleState
    {
        public readonly Vector3 position,velocity,angularVelocity;
        public readonly Quaternion rotation;
        public Vector3 Hand=>position+rotation*PlayerPaddleControl.GripLocal;
        public PlayerPaddleState(Vector3 p,Quaternion r,Vector3 v,Vector3 w)
        { position=p;rotation=r;velocity=v;angularVelocity=w; }
    }
    public sealed class PlayerPaddleControl
    {
        public const float Speed=12,Acceleration=100,AngularSpeed=12,Reach=.62f;
        public static readonly Vector3 GripLocal=new Vector3(0,-.1397f,0);
        public PlayerPaddleState State { get; private set; }
        public int ReserveRecoverySteps { get; private set; }
        public int WristRecoverySteps { get; private set; }
        public PlayerPaddleControl(Vector3 shoulder,float yaw)
        {
            var rotation=Quaternion.Euler(0,yaw,0);
            State=new PlayerPaddleState(shoulder+rotation*PlayerPaddleCommand.Ready.localHandTarget-rotation*GripLocal,rotation,Vector3.zero,Vector3.zero);
        }
        public PlayerPaddleControl Fork()=>(PlayerPaddleControl)MemberwiseClone();
        public bool TryStep(Vector3 oldShoulder,Vector3 shoulder,float yaw,PlayerPaddleCommand command,float dt)
        {
            command.Validate();
            if(!float.IsFinite(dt)||dt<=0||dt>.05f)throw new ArgumentOutOfRangeException(nameof(dt));
            foreach(var v in new[]{oldShoulder,shoulder})if(!float.IsFinite(v.x)||!float.IsFinite(v.y)||!float.IsFinite(v.z))throw new ArgumentException("Invalid shoulder.");
            if(!float.IsFinite(yaw))throw new ArgumentException("Invalid facing.");
            var facing=Quaternion.Euler(0,yaw,0);
            var angles=new Vector3(Mathf.Clamp(Mathf.DeltaAngle(0,command.localEuler.x),-65,65),
                Mathf.Clamp(Mathf.DeltaAngle(0,command.localEuler.y),-105,105),Mathf.Clamp(Mathf.DeltaAngle(0,command.localEuler.z),-85,85));
            var wantedRotation=Quaternion.RotateTowards(State.rotation,facing*Quaternion.Euler(angles),AngularSpeed*Mathf.Rad2Deg*dt);
            var shoulderVelocity=(shoulder-oldShoulder)/dt;
            var oldOffset=State.Hand-oldShoulder;
            var radial=oldOffset.sqrMagnitude<1e-8f?facing*Vector3.forward:oldOffset.normalized;
            for(int trial=0;trial<30;trial++)
            {
                bool recovering=trial>=10;int orientation=trial%10;
                float fraction=orientation==9?0:Mathf.Pow(.5f,orientation);
                var rotation=Quaternion.Slerp(State.rotation,wantedRotation,fraction);
                // Returning to ready can demand an instantaneous wrist stop.
                // Its disappearing grip velocity can make linear braking and
                // the hand-relative speed limit incompatible. Retain a bounded
                // portion of the previous rotation while translation recovers.
                // These are additional orientations, never relaxed constraints.
                if(trial>=20)
                {
                    var previousOmega=Vector3.ClampMagnitude(State.angularVelocity,AngularSpeed);
                    float speed=Mathf.Max(0,previousOmega.magnitude-80*dt*orientation);
                    rotation=speed<1e-6f?State.rotation:Quaternion.AngleAxis(speed*dt*Mathf.Rad2Deg,previousOmega.normalized)*State.rotation;
                }
                var hand=shoulder+facing*Vector3.ClampMagnitude(command.localHandTarget,.58f);
                var target=hand-rotation*GripLocal;
                var velocity=recovering ? State.velocity-radial*(Acceleration*dt)
                    : facing*command.localFeedVelocity+(target-State.position)*28;
                var gripVelocity=(rotation*GripLocal-State.rotation*GripLocal)/dt;
                var relativeFrame=gripVelocity-shoulderVelocity;
                var reachCenter=(shoulder-State.position-rotation*GripLocal)/dt;
                float reachRadius=(Reach-1e-5f)/dt;
                float outwardLimit=Mathf.Sqrt(40*Mathf.Max(0,.60f-oldOffset.magnitude))-Vector3.Dot(relativeFrame,radial);
                // The same velocity must satisfy speed, acceleration, reach and
                // braking reserve. No final hand-position projection is allowed.
                for(int k=0;k<256;k++)
                {
                    var previous=velocity;
                    velocity=Vector3.ClampMagnitude(velocity,Speed);
                    velocity=State.velocity+Vector3.ClampMagnitude(velocity-State.velocity,Acceleration*dt);
                    velocity=reachCenter+Vector3.ClampMagnitude(velocity-reachCenter,reachRadius);
                    velocity=Vector3.ClampMagnitude(velocity+relativeFrame,6)-relativeFrame;
                    if(!recovering)velocity-=radial*Mathf.Max(0,Vector3.Dot(velocity,radial)-outwardLimit);
                    if((velocity-previous).sqrMagnitude<1e-12f)break;
                }
                if(velocity.magnitude>Speed+1e-4f || (velocity-State.velocity).magnitude>Acceleration*dt+1e-4f ||
                    (velocity-reachCenter).magnitude>reachRadius+1e-4f || (velocity+relativeFrame).magnitude>6.0001f ||
                    (!recovering&&Vector3.Dot(velocity,radial)>outwardLimit+1e-4f))continue;
                var delta=rotation*Quaternion.Inverse(State.rotation);delta.ToAngleAxis(out float angle,out var axis);if(angle>180)angle-=360;
                var omega=Mathf.Abs(angle)<1e-5f?Vector3.zero:axis*angle*Mathf.Deg2Rad/dt;
                State=new PlayerPaddleState(State.position+velocity*dt,rotation,velocity,omega);if(recovering)ReserveRecoverySteps++;if(trial>=20)WristRecoverySteps++;return true;
            }
            // Mutually infeasible constraints are a failed trial, never a pass.
            return false;
        }
    }
}

using System;
using UnityEngine;

namespace Picklebot.PlayerControls
{
    public readonly struct PlayerFootPose
    {
        public readonly Vector3 center;
        public readonly float yaw;
        public readonly bool supported;
        public PlayerFootPose(Vector3 center,float yaw,bool supported)
        { this.center=center;this.yaw=yaw;this.supported=supported; }
        // Rectangle/rectangle separating-axis test: rotated shoe contact patch.
        // Edge contact counts as kitchen contact, including the boundary line.
        public bool TouchesKitchen(float halfWidth,float kitchen)
        {
            if(!supported)return false;
            float angle=yaw*Mathf.Deg2Rad,c=Mathf.Cos(angle),s=Mathf.Sin(angle);
            float x=center.x,z=center.z;
            return Mathf.Abs(x)<=halfWidth+.065f*Mathf.Abs(c)+.14f*Mathf.Abs(s)
                && Mathf.Abs(z)<=kitchen+.065f*Mathf.Abs(s)+.14f*Mathf.Abs(c)
                && Mathf.Abs(x*c-z*s)<=.065f+halfWidth*Mathf.Abs(c)+kitchen*Mathf.Abs(s)
                && Mathf.Abs(x*s+z*c)<=.14f+halfWidth*Mathf.Abs(s)+kitchen*Mathf.Abs(c);
        }
    }

    public readonly struct PlayerSupportState
    {
        public readonly bool touchesKitchen,bothFeetOutside,balanceRecovered;
        public PlayerSupportState(PlayerFootPose left,PlayerFootPose right,PlayerControlState root,
            int courtSide,float halfWidth,float kitchen)
        {
            if(courtSide!=-1 && courtSide!=1)throw new ArgumentOutOfRangeException(nameof(courtSide));
            touchesKitchen=left.TouchesKitchen(halfWidth,kitchen)||right.TouchesKitchen(halfWidth,kitchen);
            bothFeetOutside=left.supported&&right.supported&&!touchesKitchen;
            // Momentum ends when movement toward the non-volley zone stops
            // (USAP 2026, Section 2: Momentum). Sideways/backward movement does
            // not require a full standstill. Preserve grounded outside supports
            // and landing lockout; neither an airborne apex nor kitchen contact
            // can clear a pending volley. The .02 m/s tolerance is unchanged.
            balanceRecovered=bothFeetOutside&&root.grounded&&root.landingRemaining==0
                && root.velocity.z*-courtSide<=.02f;
        }
    }

    // Analytic gait/IK prototype, not a muscle or force/balance simulation.
    // Stance feet stay fixed. One swing foot moves at a time on flat ground.
    public sealed class PlayerBodyPose
    {
        public const float LegLength=.46f;
        public PlayerFootPose Left { get; private set; }
        public PlayerFootPose Right { get; private set; }
        public Vector3 Pelvis { get; private set; }
        public Vector3 Shoulder { get; private set; }
        public Vector3 LeftHip { get; private set; }
        public Vector3 RightHip { get; private set; }
        public Vector3 LeftKnee { get; private set; }
        public Vector3 RightKnee { get; private set; }
        public float MaxLegExtension { get; private set; }
        private float swingTime,fromYaw,targetYaw;
        private Vector3 from,target;
        private int swing=-1;
        private bool wasGrounded;
        private Vector3 previousRoot;
        public PlayerBodyPose(PlayerControlState state) { Reset(state); }
        public PlayerBodyPose Fork()=>(PlayerBodyPose)MemberwiseClone();
        private static Vector3 Goal(PlayerControlState s,int side)=>s.position+Quaternion.Euler(0,s.facingYaw,0)*new Vector3(side*.16f,.055f,0);
        public void Reset(PlayerControlState state)
        {
            Left=new PlayerFootPose(Goal(state,-1),state.facingYaw,state.grounded);
            Right=new PlayerFootPose(Goal(state,1),state.facingYaw,state.grounded);
            wasGrounded=state.grounded;previousRoot=state.position;swing=-1;swingTime=0;Pose(state);
        }
        public void Step(PlayerControlState state,float dt)
        {
            if(!float.IsFinite(dt)||dt<=0||dt>.05f)throw new ArgumentOutOfRangeException(nameof(dt));
            if(!state.grounded || !wasGrounded)
            {
                // Carry the existing foot pose into flight. Reposition relative
                // to the moving root at a bounded 6 m/s; do not snap under it.
                var translation=state.position-previousRoot;
                Left=AirFoot(Left,Goal(state,-1),translation,state,dt);
                Right=AirFoot(Right,Goal(state,1),translation,state,dt);
                swing=-1;swingTime=0;
            }
            else
            {
                var leftGoal=Goal(state,-1);var rightGoal=Goal(state,1);
                if(swing<0)
                {
                    float ld=Vector3.Distance(Left.center,leftGoal),rd=Vector3.Distance(Right.center,rightGoal);
                    if(Mathf.Max(ld,rd)>.10f || Mathf.Abs(Mathf.DeltaAngle(Left.yaw,state.facingYaw))>20 || Mathf.Abs(Mathf.DeltaAngle(Right.yaw,state.facingYaw))>20)
                    {
                        swing=ld>=rd?0:1;swingTime=0;
                        var foot=swing==0?Left:Right;from=foot.center;fromYaw=foot.yaw;
                        target=(swing==0?leftGoal:rightGoal)+new Vector3(state.velocity.x,0,state.velocity.z)*.04f;
                        targetYaw=state.facingYaw;
                    }
                }
                if(swing>=0)
                {
                    swingTime=Mathf.Min(.08f,swingTime+dt);float t=swingTime/.08f;
                    var center=Vector3.Lerp(from,target,t*t*(3-2*t))+Vector3.up*(Mathf.Sin(t*Mathf.PI)*.06f);
                    var foot=new PlayerFootPose(center,Mathf.LerpAngle(fromYaw,targetYaw,t),t>=1);
                    if(swing==0)Left=foot;else Right=foot;
                    if(t>=1)swing=-1;
                }
            }
            wasGrounded=state.grounded;previousRoot=state.position;Pose(state);
        }
        private static PlayerFootPose AirFoot(PlayerFootPose foot,Vector3 goal,Vector3 translation,PlayerControlState state,float dt)
        {
            var carried=foot.center+translation;
            var center=Vector3.MoveTowards(carried,goal,6*dt);
            // Flat-floor landing arrests sole height; horizontal placement is
            // retained, and subsequent grounded steps use the normal gait.
            if(state.grounded)center.y=.055f;
            return new PlayerFootPose(center,Mathf.MoveTowardsAngle(foot.yaw,state.facingYaw,360*dt),state.grounded);
        }
        private void Pose(PlayerControlState state)
        {
            var rotation=Quaternion.Euler(0,state.facingYaw,0);
            Pelvis=state.position+Vector3.up*Mathf.Lerp(.80f,.45f,state.crouch);
            Shoulder=state.position+rotation*new Vector3(.19f,Mathf.Lerp(1.36f,.80f,state.crouch),0);
            LeftHip=Pelvis-rotation*Vector3.right*.13f;RightHip=Pelvis+rotation*Vector3.right*.13f;
            MaxLegExtension=Mathf.Max(Vector3.Distance(LeftHip,Left.center),Vector3.Distance(RightHip,Right.center));
            if(MaxLegExtension>2*LegLength+1e-5f)throw new InvalidOperationException("Gait exceeded physical leg reach; do not stretch the rendered leg.");
            LeftKnee=Knee(LeftHip,Left.center,rotation*Vector3.forward);
            RightKnee=Knee(RightHip,Right.center,rotation*Vector3.forward);
        }
        private static Vector3 Knee(Vector3 hip,Vector3 foot,Vector3 forward)
        {
            var axis=(foot-hip).normalized;var bend=Vector3.ProjectOnPlane(forward,axis).normalized;
            if(bend.sqrMagnitude<.01f)bend=Vector3.ProjectOnPlane(Vector3.right,axis).normalized;
            return (hip+foot)*.5f+bend*Mathf.Sqrt(Mathf.Max(0,LegLength*LegLength-(foot-hip).sqrMagnitude*.25f));
        }
    }
}

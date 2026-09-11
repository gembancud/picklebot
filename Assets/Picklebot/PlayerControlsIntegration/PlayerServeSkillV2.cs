using Picklebot.Doubles;
using Picklebot.Core;
using Picklebot.PlayerControls;
using UnityEngine;

namespace Picklebot.PlayerControlsIntegration
{
    // Disclosed deterministic drop-serve reset skill. It uses the existing
    // flight/interception planner and moves the actual body and paddle only.
    public sealed class PlayerServeSkillV2
    {
        private float faceUpOffset=.1035f,lateralOffset=.40f,targetDepth=4.2f;
        private readonly StrokeController stroke=new StrokeController{SpeedScale=1.25f,PitchBias=-4f};
        public bool Planned=>stroke.Planned;
        public Vector3 PlannedImpact=>stroke.Impact;
        public float PlannedImpactAt=>stroke.ImpactAt;
        public void Reset()=>stroke.Reset();
        public PlayerActionV2 Action(PlayerControlMatch match)
        {
            var world=match.World;int player=world.Rules.Server;int side=world.Players[player].Side;
            stroke.Kind=StrokeKind.Flat;
            stroke.Plan(world,player,new Vector2(world.Rules.ServiceX(world.Rules.DesignatedReceiver),targetDepth));
            if(!stroke.Planned)return default;
            var root=match.Controls.StateFor(player);var pose=match.Controls.PoseFor(player);
            var facing=Quaternion.Euler(0,player<2?0:180,0);
            var rotation=Quaternion.LookRotation(stroke.Normal);
            float phase=world.Time-stroke.ImpactAt;
            var velocity=stroke.Normal*stroke.Swing;
            PlayerSwingTrajectoryV2.Sample(velocity,phase,out var travel,out var requestedFeed);
            var target=stroke.Impact-stroke.Normal*(CourtGeometryV1.BallRadius+.008f)-rotation*Vector3.up*faceUpOffset
                +travel;
            var hand=target+rotation*PlayerPaddleControl.GripLocal;
            var feet=new Vector3(stroke.Impact.x+side*lateralOffset,0,side*(phase<-.16f?7.30f:6.50f));
            var wanted=Vector3.ClampMagnitude((feet-root.position)*4,2.5f);
            var local=Quaternion.Inverse(facing)*wanted;
            var values=default(PlayerActionV2).ToArray();
            values[5]=phase>-.16f?1:0;
            float effort=(values[5]>.5f?1:.72f)*Mathf.Lerp(.55f,1,root.energy)*Mathf.Lerp(1,.55f,root.crouch);
            values[0]=local.x/(3*effort);values[1]=local.z/((local.z>=0?3.8f:2.3f)*effort);
            values[3]=Mathf.InverseLerp(1.36f,.80f,Mathf.Clamp(hand.y+.35f,.80f,1.36f));
            var localHand=Quaternion.Inverse(facing)*(hand-pose.Shoulder)/.62f;
            values[6]=localHand.x;values[7]=localHand.y;values[8]=localHand.z;
            var angles=(Quaternion.Inverse(facing)*rotation).eulerAngles;
            values[9]=Mathf.DeltaAngle(0,angles.x)/65;values[10]=Mathf.DeltaAngle(0,angles.y)/105;values[11]=Mathf.DeltaAngle(0,angles.z)/85;
            if(requestedFeed.sqrMagnitude>0)
            {var feed=Quaternion.Inverse(facing)*requestedFeed/12;values[12]=feed.x;values[13]=feed.y;values[14]=feed.z;}
            return new PlayerActionV2(values);
        }
    }
}

using Picklebot.Core;
using Picklebot.Doubles;
using Picklebot.PlayerAgents;
using Picklebot.PlayerControls;
using UnityEngine;
namespace Picklebot.PlayerControlsIntegration
{
    // A private planner per player. It requests paddle motion, never root motion
    // or a designated hitter. All requests pass through PlayerPaddleControl.
    public sealed class PlayerIntentSwingV2
    {
        private readonly PlayerContactPlan contact=new PlayerContactPlan();
        private readonly PlayerContactCalibrationV2 calibration;
        public PlayerIntentSwingV2(PlayerContactCalibrationV2 calibration=null){this.calibration=calibration;}
        private int lastShot=-1;
        private float nextAttempt;
        public bool Planned=>contact.Planned;
        public void Reset(){contact.Reset();lastShot=-1;nextAttempt=0;}
        public PlayerActionV2 Action(PlayerControlMatch match,int player,PlayerActionV2 action,PlayerShotIntentV2 intent)
        {
            if(!intent.enabled){Reset();return action;}
            var world=match.World;
            if(contact.Planned&&world.Time>contact.ImpactAt+.055f){contact.Reset();nextAttempt=0;}
            bool committed=contact.Planned&&world.Time>=contact.ImpactAt-.13f&&world.Time<=contact.ImpactAt+.055f;
            if(lastShot!=intent.shot&&(!committed||!intent.attempt)){contact.Reset();lastShot=intent.shot;nextAttempt=0;}
            var choice=new PlayerAction{shot=lastShot};
            contact.Kind=TeamPolicy.Kind(lastShot);
            calibration?.Apply(contact.Kind,contact.Residuals);
            if(!intent.attempt){contact.Reset();nextAttempt=0;}
            else if(world.Time>=nextAttempt)
            {nextAttempt=world.Time+.05f;if(!contact.Plan(world,player,choice.WorldShotTarget(player)))contact.Reset();}
            var values=action.ToArray();
            if(!contact.Planned)return action;
            var root=match.Controls.StateFor(player);var pose=match.Controls.PoseFor(player);
            var facing=Quaternion.Euler(0,root.facingYaw,0);
            var rotation=contact.Rotation(world.Players[player].Side);
            var target=contact.Impact-contact.Normal*(CourtGeometryV1.BallRadius+.008f)-rotation*Vector3.up*.0635f;
            float phase=world.Time-contact.ImpactAt;
            float brush=(contact.Kind==StrokeKind.Topspin?2.4f:contact.Kind==StrokeKind.Slice?-2.4f:0)*contact.BrushScale+contact.BrushBias;
            var velocity=contact.Normal*contact.Swing+Vector3.ProjectOnPlane(Vector3.up,contact.Normal).normalized*brush;
            target+=velocity*Mathf.Clamp(phase,-.06f,.055f);
            var hand=target+rotation*PlayerPaddleControl.GripLocal;
            if(intent.legacyAutoPosture)values[3]=Mathf.InverseLerp(1.36f,.80f,Mathf.Clamp(hand.y+.35f,.80f,1.36f));
            var local=Quaternion.Inverse(facing)*(hand-pose.Shoulder)/.62f;
            values[6]=local.x;values[7]=local.y;values[8]=local.z;
            var angles=(Quaternion.Inverse(facing)*rotation).eulerAngles;
            values[9]=Mathf.DeltaAngle(0,angles.x)/65;values[10]=Mathf.DeltaAngle(0,angles.y)/105;values[11]=Mathf.DeltaAngle(0,angles.z)/85;
            var feed=phase>-.06f&&phase<.055f?Quaternion.Inverse(facing)*velocity/12:Vector3.zero;
            values[12]=feed.x;values[13]=feed.y;values[14]=feed.z;
            return new PlayerActionV2(values);
        }
    }
}

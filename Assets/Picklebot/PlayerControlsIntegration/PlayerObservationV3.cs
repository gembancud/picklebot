using System;
using System.Linq;
using Picklebot.PlayerAgents;
using Picklebot.PlayerControls;
using UnityEngine;
namespace Picklebot.PlayerControlsIntegration
{
    public sealed class PlayerObservationV3
    {
        public const string Version="player-observation-v3-joints-124";
        public const int Count=124;
        public readonly int player,tick;
        private readonly float[] values;
        public float[] ToArray()=>(float[])values.Clone();
        private static readonly string[] JointNames=new[]{"torso.turn","torso.forwardLean","torso.lateralLean"}.Concat(PlayerArmJointsV3.Names).ToArray();
        public static readonly string[] Fields=PlayerObservation.Fields.Concat(PlayerControlObservation.Fields.Select(s=>"control."+s))
            .Concat(new[]{"control.turnRate","control.crouchRate","shoulder.x","shoulder.y","shoulder.z"})
            .Concat(new[]{"left","right"}.SelectMany(f=>new[]{"x","y","z","yaw.sin","yaw.cos","supported"}.Select(s=>"foot."+f+"."+s)))
            .Concat(new[]{"rule.establishedOutside","rule.volleyMomentumPending"})
            .Concat(JointNames.Select(n=>"joint.angle."+n)).Concat(JointNames.Select(n=>"joint.rate."+n))
            .Concat(PlayerActionV3.Fields.Take(17).Select(s=>"active."+s)).Concat(new[]{"ball.heldByServer","offHand.angle","offHand.rate","active.offHand.lift"}).ToArray();
        public PlayerObservationV3(int player,int tick,float[] values)
        {
            if(player<0||player>3||tick<0||values==null||values.Length!=Count||values.Any(v=>!float.IsFinite(v)))throw new ArgumentException("Invalid V3 observation.");
            this.player=player;this.tick=tick;this.values=(float[])values.Clone();
        }
        public PlayerObservationV3 Copy()=>new PlayerObservationV3(player,tick,values);
        public static PlayerObservationV3 Capture(PlayerLearningMatchV3 match,int player,int tick)
        {
            var root=match.Controls.StateFor(player);var legs=match.Controls.PoseFor(player);var upper=match.Controls.UpperFor(player);
            var values=new float[Count];int offset=0;
            void Add(params float[] part){Array.Copy(part,0,values,offset,part.Length);offset+=part.Length;}
            void Spatial(Vector3 point){var v=PlayerObservation.ToLocal(point-root.position,player);Add(v.x,v.y/2,v.z);}
            void Foot(PlayerFootPose foot){Spatial(foot.center);float yaw=Mathf.DeltaAngle(player<2?0:180,foot.yaw)*Mathf.Deg2Rad;Add(Mathf.Sin(yaw),Mathf.Cos(yaw),foot.supported?1:0);}
            Add(PlayerObservation.Capture(match.World,player,tick).values);Add(PlayerControlObservation.Capture(root,player<2?0:180));
            Add(match.Controls.TurnRateFor(player)/180,root.crouchVelocity/2.5f);Spatial(upper.Pose().shoulder);Foot(legs.Left);Foot(legs.Right);
            Add(match.World.Rules.EstablishedOutside(player)?1:0,match.World.Rules.VolleyMomentumPending(player)?1:0);
            var t=upper.TorsoAngles;Add(t.x/60,t.y/(t.y>=0?35:15),t.z/25);
            for(int i=0;i<7;i++)Add(2*(upper.ArmAngles[i]-PlayerArmJointsV3.Minimum(i))/(PlayerArmJointsV3.Maximum(i)-PlayerArmJointsV3.Minimum(i))-1);
            var tr=upper.TorsoRates;Add(tr.x/Mathf.PI,tr.y/(Mathf.PI/2),tr.z/(Mathf.PI/2));var ar=upper.ArmRates;
            for(int i=0;i<7;i++)Add(ar[i]/((i<4?360:480)*Mathf.Deg2Rad));
            // Retain the previous 121 fields exactly; append the new proprioception.
            Add(match.ActiveFor(player).ToArray().Take(17).ToArray());Add(match.BallHeld?1:0);
            Add(match.Controls.OffHandAngleFor(player)/140,match.Controls.OffHandRateFor(player)/180,match.ActiveFor(player)[17]);
            if(offset!=Count||Fields.Length!=Count)throw new InvalidOperationException("V3 observation schema mismatch.");
            return new PlayerObservationV3(player,tick,values);
        }
    }
}

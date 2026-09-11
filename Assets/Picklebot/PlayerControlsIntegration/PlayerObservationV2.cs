using System;
using System.Linq;
using Picklebot.PlayerAgents;
using Picklebot.PlayerControls;
using UnityEngine;

namespace Picklebot.PlayerControlsIntegration
{
    // Explicit V2 schema: old 54 values are an identifiable prefix, not an implicit
    // change to PlayerObservation or permission to load an old actor as V2.
    public sealed class PlayerObservationV2
    {
        public const string Version="player-observation-v2-direct-96";
        public const int Count=96;
        public readonly int player,tick;
        public readonly float[] values;
        public static readonly string[] Fields=PlayerObservation.Fields
            .Concat(PlayerControlObservation.Fields.Select(s=>"control."+s))
            .Concat(new[]{"shoulder.x","shoulder.y","shoulder.z"})
            .Concat(new[]{"left","right"}.SelectMany(foot=>new[]{"x","y","z","yaw.sin","yaw.cos","supported"}.Select(s=>"foot."+foot+"."+s)))
            .Concat(new[]{"rule.establishedOutside","rule.volleyMomentumPending"})
            .Concat(PlayerActionV2.Fields.Select(s=>"active."+s)).ToArray();
        public PlayerObservationV2(int player,int tick,float[] values)
        {
            if(player<0||player>3||tick<0||values==null||values.Length!=Count||values.Any(v=>!float.IsFinite(v)))
                throw new ArgumentException("Invalid V2 observation.");
            this.player=player;this.tick=tick;this.values=(float[])values.Clone();
        }
        public PlayerObservationV2 Copy()=>new PlayerObservationV2(player,tick,values);
        public static PlayerObservationV2 Capture(PlayerControlMatch match,int player,int tick,PlayerActionV2 active)
        {
            var root=match.Controls.StateFor(player);var pose=match.Controls.PoseFor(player);
            var values=new float[Count];int offset=0;
            void Add(float[] part) { Array.Copy(part,0,values,offset,part.Length);offset+=part.Length; }
            void Spatial(Vector3 point)
            { var v=PlayerObservation.ToLocal(point-root.position,player);Add(new[]{v.x,v.y/2,v.z}); }
            void Foot(PlayerFootPose foot)
            {
                Spatial(foot.center);float a=Mathf.DeltaAngle(player<2?0:180,foot.yaw)*Mathf.Deg2Rad;
                Add(new[]{Mathf.Sin(a),Mathf.Cos(a),foot.supported?1f:0f});
            }
            Add(PlayerObservation.Capture(match.World,player,tick).values);
            Add(PlayerControlObservation.Capture(root,player<2?0:180));
            Spatial(pose.Shoulder);Foot(pose.Left);Foot(pose.Right);
            Add(new[]{match.World.Rules.EstablishedOutside(player)?1f:0f,match.World.Rules.VolleyMomentumPending(player)?1f:0f});
            Add(active.ToArray());
            if(offset!=Count||Fields.Length!=Count)throw new InvalidOperationException("V2 observation schema mismatch.");
            return new PlayerObservationV2(player,tick,values);
        }
    }
}

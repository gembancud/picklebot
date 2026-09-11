using System;
using System.Linq;
using UnityEngine;
namespace Picklebot.PlayerControls
{
    // Direct learned commands. No shot classes, intercept targets or stroke phases.
    public readonly struct PlayerActionV3
    {
        public const string Version="player-action-v3-joints-18";
        public const int Count=18;
        private readonly float[] values;
        public static readonly string[] Fields=new[]{"move.x","move.z","turn.rate","crouch","jump","sprint",
            "torso.turn","torso.forwardLean","torso.lateralLean"}
            .Concat(PlayerArmJointsV3.Names.Select(n=>"arm."+n)).Concat(new[]{"serve.release","offHand.lift"}).ToArray();
        public float this[int i]=>values==null?0:values[i];
        public float[] ToArray()=>values==null?new float[Count]:(float[])values.Clone();
        public PlayerActionV3(float[] source)
        {
            if(source==null||source.Length!=Count)throw new ArgumentException("V3 needs 18 action values.");
            values=(float[])source.Clone();
            for(int i=0;i<Count;i++)
            {if(!float.IsFinite(values[i]))throw new ArgumentException("Non-finite V3 action.");values[i]=Mathf.Clamp(values[i],i==3||i==4||i==5||i==16||i==17?0:-1,1);}
        }
        public bool Release=>this[16]>=.5f;
        public Vector3 TorsoTarget=>new Vector3(this[6]*60,this[7]*(this[7]>=0?35:15),this[8]*25);
        public PlayerArmJointsV3 ArmTarget
        {
            get{var ready=PlayerArmJointsV3.Ready;var a=new float[7];for(int i=0;i<7;i++)
                a[i]=ready[i]+this[i+9]*(this[i+9]>=0?PlayerArmJointsV3.Maximum(i)-ready[i]:ready[i]-PlayerArmJointsV3.Minimum(i));return new PlayerArmJointsV3(a);}
        }
        public PlayerControlCommand Movement(float yaw)=>new PlayerControlCommand{move=new Vector2(this[0],this[1]),
            facingYaw=yaw,crouch=this[3],jump=this[4]>=.5f,sprint=this[5]>=.5f};
    }
}

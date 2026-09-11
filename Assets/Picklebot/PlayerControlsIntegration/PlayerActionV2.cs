using System;
using Picklebot.PlayerControls;
using UnityEngine;

namespace Picklebot.PlayerControlsIntegration
{
    // Versioned direct control contract. No V1 shot logits are interpreted here.
    public readonly struct PlayerActionV2
    {
        public const string Version="player-action-v2-direct-15";
        public const int Count=15;
        private readonly float[] values;
        private static readonly float[] ready={0,0,0,0,0,0,0,-.20f/.62f,.35f/.62f,0,0,0,0,0,0};
        public static readonly string[] Fields={"move.x","move.z","facing.attackYaw","crouch","jump","sprint",
            "hand.x","hand.y","hand.z","wrist.pitch","wrist.yaw","wrist.roll","feed.x","feed.y","feed.z"};
        public float this[int index]=>(values??ready)[index];
        public float[] ToArray()=>(float[])(values??ready).Clone();
        public PlayerActionV2(float[] source)
        {
            if(source==null||source.Length!=Count)throw new ArgumentException("V2 requires exactly 15 action values.");
            values=(float[])source.Clone();
            for(int i=0;i<Count;i++)
            {
                if(!float.IsFinite(values[i]))throw new ArgumentException("Non-finite V2 action.");
                values[i]=Mathf.Clamp(values[i],i>=3&&i<=5?0:-1,1);
            }
            var move=Vector2.ClampMagnitude(new Vector2(values[0],values[1]),1);values[0]=move.x;values[1]=move.y;
        }
        public PlayerControlCommand Movement(int player)
        {
            if(player<0||player>3)throw new ArgumentOutOfRangeException(nameof(player));
            return new PlayerControlCommand{move=new Vector2(this[0],this[1]),facingYaw=(player<2?0:180)+180*this[2],
                crouch=this[3],jump=this[4]>=.5f,sprint=this[5]>=.5f};
        }
        public PlayerPaddleCommand Paddle()=>new PlayerPaddleCommand{
            localHandTarget=new Vector3(this[6],this[7],this[8])*.62f,
            localEuler=new Vector3(this[9]*65,this[10]*105,this[11]*85),
            localFeedVelocity=new Vector3(this[12],this[13],this[14])*12};
    }
}

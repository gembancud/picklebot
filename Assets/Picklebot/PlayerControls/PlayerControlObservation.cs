using System;
using UnityEngine;

namespace Picklebot.PlayerControls
{
    // Versioned proprioception for future policy integration. Not appended to
    // the frozen 54-value V1 observation or fed to existing weights implicitly.
    public static class PlayerControlObservation
    {
        public const string Version="player-control-observation-v2-prototype";
        public const int Count=10;
        public static readonly string[] Fields={"facing.sin","facing.cos","body.vx","body.vz",
            "root.height","root.vy","crouch","energy","grounded","landing.remaining"};

        public static float[] Capture(PlayerControlState state, float attackingYaw, PlayerControlProfile profile=null)
        {
            var p=(profile??new PlayerControlProfile()).CopyValidated();
            if(!float.IsFinite(attackingYaw))throw new ArgumentException("Invalid reference heading.");
            float relative=Mathf.DeltaAngle(attackingYaw,state.facingYaw)*Mathf.Deg2Rad;
            var velocity=Quaternion.Euler(0,-state.facingYaw,0)*state.velocity;
            var values=new[]{Mathf.Sin(relative),Mathf.Cos(relative),velocity.x/p.forwardSpeed,velocity.z/p.forwardSpeed,
                state.position.y/p.jumpHeight,state.velocity.y/Mathf.Sqrt(2*p.gravity*p.jumpHeight),state.crouch,state.energy,
                state.grounded?1f:0f,state.landingRemaining/p.landingRecoverySeconds};
            foreach(float value in values)if(!float.IsFinite(value))throw new ArgumentException("Non-finite control observation.");
            return values;
        }
    }
}

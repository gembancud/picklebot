using System;
using UnityEngine;

namespace Picklebot.PlayerControls
{
    // Explicit prototype parameters, not empirically calibrated human limits.
    [Serializable]
    public sealed class PlayerControlProfile
    {
        public float forwardSpeed = 3.8f, lateralSpeed = 3f, backwardSpeed = 2.3f;
        public float acceleration = 14f, braking = 14f, turnDegreesPerSecond = 360f;
        public float gravity = 9.81f, jumpHeight = .25f, landingRecoverySeconds = .18f;
        public float jumpEnergy = .12f, sprintDrainPerSecond = .12f, recoveryPerSecond = .08f;
        public float crouchRate = 2.5f, crouchAcceleration = 10f;

        public PlayerControlProfile CopyValidated()
        {
            foreach (float value in new[] { forwardSpeed, lateralSpeed, backwardSpeed, acceleration, braking,
                turnDegreesPerSecond, gravity, jumpHeight, landingRecoverySeconds, jumpEnergy,
                sprintDrainPerSecond, recoveryPerSecond, crouchRate, crouchAcceleration })
                if (!float.IsFinite(value) || value <= 0) throw new ArgumentException("Control parameters must be positive and finite.");
            if (lateralSpeed > forwardSpeed || backwardSpeed > forwardSpeed || jumpEnergy > 1)
                throw new ArgumentException("Invalid directional speed or energy limits.");
            return (PlayerControlProfile)MemberwiseClone();
        }
    }

    public struct PlayerControlCommand
    {
        // Movement is body-local, not a target position or privileged ball plan.
        public Vector2 move;
        public float facingYaw, crouch;
        public bool jump, sprint;

        public PlayerControlCommand Validated()
        {
            if (!float.IsFinite(move.x) || !float.IsFinite(move.y) || !float.IsFinite(facingYaw) || !float.IsFinite(crouch))
                throw new ArgumentException("Non-finite player command.");
            return new PlayerControlCommand { move = Vector2.ClampMagnitude(move, 1), facingYaw = Mathf.Repeat(facingYaw, 360),
                crouch = Mathf.Clamp01(crouch), jump = jump, sprint = sprint };
        }
    }

    public readonly struct PlayerControlState
    {
        public readonly Vector3 position, velocity;
        public readonly float facingYaw, crouch, energy, landingRemaining, crouchVelocity;
        public readonly bool grounded;
        public PlayerControlState(Vector3 position, Vector3 velocity, float facingYaw, float crouch, float energy, float landingRemaining, bool grounded, float crouchVelocity=0)
        { this.position=position; this.velocity=velocity; this.facingYaw=facingYaw; this.crouch=crouch; this.energy=energy; this.landingRemaining=landingRemaining; this.grounded=grounded; this.crouchVelocity=crouchVelocity; }
    }

    // One instance per player. Flat-ground locomotion kernel only: court/partner
    // contacts and paddle/IK integration belong to the adapter, not hidden here.
    public sealed class PlayerControlMotor
    {
        public const string Version = "player-controls-v2-prototype";
        private readonly PlayerControlProfile profile;
        private bool jumpHeld;
        public PlayerControlState State { get; private set; }

        public PlayerControlMotor(PlayerControlProfile profile = null)
        { this.profile=(profile ?? new PlayerControlProfile()).CopyValidated(); Reset(Vector3.zero); }

        public void Reset(Vector3 groundPosition, float facingYaw = 0)
        {
            if (!float.IsFinite(groundPosition.x) || !float.IsFinite(groundPosition.z) || groundPosition.y != 0 || !float.IsFinite(facingYaw))
                throw new ArgumentException("Reset requires a finite point on flat ground.");
            State=new PlayerControlState(groundPosition,Vector3.zero,Mathf.Repeat(facingYaw,360),0,1,0,true);
            jumpHeld=false;
        }

        internal PlayerControlMotor Fork()
        {
            var copy=new PlayerControlMotor(profile);copy.State=State;copy.jumpHeld=jumpHeld;return copy;
        }

        internal void ApplyHorizontalContact(Vector2 position,Vector2 velocity)
        {
            var s=State;
            State=new PlayerControlState(new Vector3(position.x,s.position.y,position.y),
                new Vector3(velocity.x,s.velocity.y,velocity.y),s.facingYaw,s.crouch,s.energy,s.landingRemaining,s.grounded,s.crouchVelocity);
        }

        public PlayerControlState Step(PlayerControlCommand command, float dt, int enclosureSide = 0)
        {
            command=command.Validated();
            if (!float.IsFinite(dt) || dt <= 0 || dt > .05f) throw new ArgumentOutOfRangeException(nameof(dt));
            var s=State;
            var position=s.position;
            var velocity=s.velocity;
            float yaw=s.facingYaw, crouch=s.crouch, energy=s.energy, crouchVelocity=s.crouchVelocity;
            float recovery=Mathf.Max(0,s.landingRemaining-dt);
            bool grounded=s.grounded;
            bool risingJump=command.jump && !jumpHeld;
            jumpHeld=command.jump;
            if (grounded)
            {
                yaw=Mathf.MoveTowardsAngle(yaw,command.facingYaw,profile.turnDegreesPerSecond*dt);
                // Crouch reversal must not instantly change shoulder velocity.
                // Reserve braking distance to the physical [0,1] posture bounds.
                float a=profile.crouchAcceleration, dv=a*dt;
                float error=command.crouch-crouch;
                float wantedCrouch=Mathf.Sign(error)*Mathf.Min(profile.crouchRate,Mathf.Sqrt(dv*dv+2*a*Mathf.Abs(error))-dv);
                crouchVelocity=Mathf.MoveTowards(crouchVelocity,wantedCrouch,dv);
                float lower=-(Mathf.Sqrt(dv*dv+2*a*crouch)-dv);
                float upper=Mathf.Sqrt(dv*dv+2*a*(1-crouch))-dv;
                crouchVelocity=Mathf.Clamp(crouchVelocity,lower,upper);
                crouch=Mathf.Clamp01(crouch+crouchVelocity*dt);
                // Low energy reduces requested speed. Acceleration remains bounded;
                // velocity is not abruptly rescaled when energy or heading changes.
                float effort=(command.sprint ? 1f : .72f)*Mathf.Lerp(.55f,1f,energy);
                float crouchScale=Mathf.Lerp(1f,.55f,crouch);
                var local=new Vector3(command.move.x*profile.lateralSpeed,0,
                    command.move.y*(command.move.y>=0 ? profile.forwardSpeed : profile.backwardSpeed));
                var target=Quaternion.Euler(0,yaw,0)*local*effort*crouchScale;
                if (recovery > 0) target=Vector3.zero;
                var horizontal=new Vector3(velocity.x,0,velocity.z);
                bool slowing=Vector3.Dot(target-horizontal,horizontal)<0;
                horizontal=Vector3.MoveTowards(horizontal,target,(slowing ? profile.braking : profile.acceleration)*dt);
                if (enclosureSide != 0)
                {
                    var limited=PlayerEnclosureBrakingV3.Constrain(new Vector2(position.x,position.z),
                        new Vector2(s.velocity.x,s.velocity.z),new Vector2(horizontal.x,horizontal.z),
                        enclosureSide,Mathf.Min(profile.acceleration,profile.braking),dt);
                    horizontal=new Vector3(limited.x,0,limited.y);
                }
                velocity=new Vector3(horizontal.x,0,horizontal.z);
                bool working=command.sprint && command.move.sqrMagnitude>.01f && recovery==0;
                bool resting=horizontal.sqrMagnitude<.01f && command.move.sqrMagnitude<.01f && recovery==0;
                energy=Mathf.Clamp01(energy+(working ? -profile.sprintDrainPerSecond*dt : resting ? profile.recoveryPerSecond*dt : 0));
                if (risingJump && s.landingRemaining==0 && energy>=profile.jumpEnergy && crouch<.8f)
                {
                    velocity.y=Mathf.Sqrt(2*profile.gravity*profile.jumpHeight);
                    energy-=profile.jumpEnergy;
                    grounded=false;crouchVelocity=0;
                }
            }
            // No mid-air steering, thrust, crouch change, yaw change or energy refill.
            position.x+=velocity.x*dt; position.z+=velocity.z*dt;
            if (!grounded)
            {
                position.y+=velocity.y*dt-.5f*profile.gravity*dt*dt;
                velocity.y-=profile.gravity*dt;
                if (position.y<=0 && velocity.y<0)
                { position.y=0;velocity.y=0;grounded=true;recovery=profile.landingRecoverySeconds; }
            }
            State=new PlayerControlState(position,velocity,yaw,crouch,energy,recovery,grounded,crouchVelocity);
            return State;
        }
    }
}

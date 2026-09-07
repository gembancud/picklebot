using Picklebot.Core;
using Picklebot.Doubles;
using UnityEngine;

namespace Picklebot.PlayerAgents
{
    // Reuse the contact plan but not its automatic foot movement. Only the
    // player's applied action sets locomotion during a rally.
    public sealed class PlayerSwing
    {
        public readonly PlayerContactPlan Contact = new PlayerContactPlan();
        public Vector3 MoveTarget { get; private set; }
        public Vector3 ShotTarget { get; private set; }
        public Vector3 RequestedVelocity { get; private set; }
        public Vector3 AppliedVelocity { get; private set; }
        public bool SafetyLimited => (RequestedVelocity - AppliedVelocity).sqrMagnitude > .000001f;
        public int SelectedShot => lastShot;
        public int RequestedShot { get; private set; }
        public bool ShotCommitted { get; private set; }
        public bool PaddleStepFeasible { get; private set; } = true;
        private int lastShot = -1;
        private float nextAttempt;

        public void Reset() { Contact.Reset(); lastShot = -1; nextAttempt = 0; ShotCommitted = false; }

        public void Step(DoublesWorld world, int player, PlayerAction action, ContactModel model)
        {
            action = action.Validated();
            var body = world.Players[player];
            int side = body.Side;
            RequestedShot = action.shot;
            // A missed contact must not stay committed to a past ball position.
            // Keep the bounded follow-through, then allow a fresh swing plan.
            if (Contact.Planned && world.Time > Contact.ImpactAt + .055f)
            { Contact.Reset(); nextAttempt = 0; }
            ShotCommitted = Contact.Planned && world.Time >= Contact.ImpactAt - .13f && world.Time <= Contact.ImpactAt + .055f;
            // The final contact/follow-through window cannot restart at each
            // 20 Hz categorical sample. The actor can still cancel the attempt.
            if (lastShot != action.shot && (!ShotCommitted || !action.attempt))
            { Contact.Reset(); lastShot = action.shot; nextAttempt = 0; }
            var selected = action; selected.shot = lastShot;
            var goal = selected.WorldShotTarget(player);
            ShotTarget = new Vector3(goal.x, 0, -side * goal.y);
            Contact.Kind = TeamPolicy.Kind(lastShot);
            if (model != null) model.strokes[(int)Contact.Kind].Apply(Contact.Residuals);
            if (!action.attempt) { Contact.Reset(); nextAttempt = 0; ShotCommitted = false; }
            else if (world.Time >= nextAttempt)
            {
                nextAttempt = world.Time + .05f;
                if (!Contact.Plan(world, player, goal)) Contact.Reset();
            }

            var rotation = Contact.Rotation(side);
            var paddle = Contact.Planned
                ? Contact.Impact - Contact.Normal * (CourtGeometryV1.BallRadius + .008f) - rotation * Vector3.up * .0635f
                : body.Position + new Vector3(-side * .19f, 1.1f, -side * .46f);
            Vector3 feed = Vector3.zero;
            if (Contact.Planned)
            {
                float phase = world.Time - Contact.ImpactAt;
                float brushSpeed = (Contact.Kind == StrokeKind.Topspin ? 2.4f : Contact.Kind == StrokeKind.Slice ? -2.4f : 0)
                    * Contact.BrushScale + Contact.BrushBias;
                var velocity = Contact.Normal * Contact.Swing
                    + Vector3.ProjectOnPlane(Vector3.up, Contact.Normal).normalized * brushSpeed;
                paddle += velocity * Mathf.Clamp(phase, -.06f, .055f);
                if (phase > -.06f && phase < .055f) feed = velocity;
            }
            // PlayerBody converts target error to wanted velocity with gain 4.
            RequestedVelocity = action.WorldVelocity(player);
            AppliedVelocity = PlayerMovement.Constrain(body, world.Players[player ^ 1], RequestedVelocity);
            MoveTarget = body.Position + AppliedVelocity / 4f;
            PaddleStepFeasible = PlayerPaddleMotor.Constrain(body, world.Players[player ^ 1], MoveTarget,
                ref paddle, ref rotation, ref feed, DoublesWorld.Dt);
            body.Step(MoveTarget, paddle, rotation, feed, world.Players[player ^ 1], DoublesWorld.Dt);
        }
    }
}

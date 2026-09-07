using Picklebot.Core;
using Picklebot.Doubles;
using UnityEngine;

namespace Picklebot.PlayerAgents
{
    // Scripted contact execution only. This object never moves a player or ball.
    // Keep the frozen baseline plan for normal contacts, with a low-ball fallback.
    public sealed class PlayerContactPlan
    {
        public readonly StrokeController Residuals = new StrokeController();
        private bool low;
        private Vector3 impact, normal;
        private float impactAt, swing, nextPlan;
        public bool Planned => low || Residuals.Planned;
        public bool LowContact => low;
        public Vector3 Impact => low ? impact : Residuals.Impact;
        public Vector3 Normal => low ? normal : Residuals.Normal;
        public float ImpactAt => low ? impactAt : Residuals.ImpactAt;
        public float Swing => low ? swing : Residuals.Swing;
        public StrokeKind Kind { get => Residuals.Kind; set => Residuals.Kind = value; }
        // The saved residual fit used upright, higher contacts. It has no
        // calibration evidence for the rolled low grip. Use neutral residuals.
        public float BrushScale => low ? 1 : Residuals.BrushScale;
        public float BrushBias => low ? 0 : Residuals.BrushBias;
        public Quaternion Rotation(int side) => Quaternion.LookRotation(Planned ? Normal : Vector3.forward * -side)
            * Quaternion.Euler(0, 0, low ? -80 : 0);
        public void Reset() { low = false; nextPlan = 0; Residuals.Reset(); }

        public bool Plan(DoublesWorld world, int player, Vector2 goal)
        {
            if (Planned && world.Time > ImpactAt + .055f) Reset();
            if (Planned && ImpactAt - world.Time < .13f) return true;
            if (world.Time < nextPlan) return Planned;
            nextPlan = world.Time + .05f;
            if (Residuals.Plan(world, player, goal)) { low = false; return true; }
            Residuals.Reset(); low = false;
            if (world.Rules.Phase == RallyPhase.AwaitServe) return false;
            var body = world.Players[player]; int side = body.Side;
            var p = world.Ball.position; var v = world.Ball.linearVelocity; var spin = world.Ball.angularVelocity;
            if (v.z * side < .1f) return false;
            bool bounced = world.Rules.Bounced, allowed = bounced || world.Rules.CanVolley;
            for (int step = 1; step <= 720; step++)
            {
                StrokeController.Fly(ref p, ref v, ref spin, world.Configuration, DoublesWorld.Dt);
                if (p.y < CourtGeometryV1.BallRadius && v.y < 0)
                {
                    if (p.z * side <= 0 || bounced) return false;
                    p.y = CourtGeometryV1.BallRadius; v.y = -v.y * world.Configuration.CourtRestitution;
                    v.x *= .97f; v.z *= .97f; allowed = bounced = true;
                }
                float time = step * DoublesWorld.Dt;
                // Kitchen groundstrokes are legal after the ball bounces.
                // Keep the original volley region; planning still moves no feet.
                float minimumContactDepth = bounced ? .4f : 2.65f;
                if (!allowed || time < .13f || p.y < .30f || p.y >= .52f || p.z * side < minimumContactDepth
                    || Mathf.Abs(p.x) > 3.7f || Mathf.Abs(p.z) > 7.5f) continue;
                var feet = new Vector3(p.x + side * .38f, 0, side * Mathf.Max(bounced ? .38f : 2.6f, side * p.z + .43f));
                var displacement = feet - body.Position;
                // Acceleration-aware reach estimate. It grants no movement command.
                float initialSpeed = Vector3.Dot(body.Velocity, displacement.normalized);
                float accelerate = Mathf.Clamp((PlayerBody.Speed - initialSpeed) / PlayerBody.Acceleration, 0, time);
                float distance = initialSpeed * accelerate + .5f * PlayerBody.Acceleration * accelerate * accelerate
                    + PlayerBody.Speed * (time - accelerate);
                if (displacement.magnitude > distance + .12f) continue;
                if (!SolveStroke(p, v, new Vector3(goal.x, CourtGeometryV1.BallRadius, -side * goal.y),
                    world.Configuration, out var n, out float speed)) continue;
                var rotation = Quaternion.LookRotation(n) * Quaternion.Euler(0, 0, -80);
                var paddle = p - n * (CourtGeometryV1.BallRadius + .008f) - rotation * Vector3.up * .0635f;
                float shoulderHeight = Mathf.MoveTowards(body.Shoulder.y, Mathf.Clamp(paddle.y + .20f, .72f, 1.5f), 1.6f * time);
                var shoulder = feet + new Vector3(-side * .19f, shoulderHeight, 0);
                if (Vector3.Distance(paddle + rotation * PlayerBody.GripLocal, shoulder) > PlayerBody.ArmUpper + PlayerBody.ArmLower - .01f) continue;
                if (Quaternion.Angle(body.Paddle.rotation, rotation) > PlayerBody.AngularSpeed * Mathf.Rad2Deg * time) continue;
                impact = p; normal = n; swing = speed;
                impactAt = world.Time + time; low = true; return true;
            }
            return false;
        }

        // Same pure inverse-flight solver as the frozen baseline. Only the
        // low-contact eligibility and grip orientation differ in this fallback.
        private static bool SolveStroke(Vector3 p, Vector3 incoming, Vector3 target, SimulationConfigV1 c, out Vector3 n, out float speed)
        {
            n = Vector3.forward; speed = 0; float best = float.PositiveInfinity;
            foreach (float duration in new[] { 1f, 1.25f, 1.5f, 1.75f })
            {
                var desired = (target - p) / duration - c.Gravity * duration * .5f;
                for (int k = 0; k < 5; k++)
                {
                    var end = p; var velocity = desired; var spin = Vector3.zero;
                    for (int i = 0; i < Mathf.RoundToInt(duration / DoublesWorld.Dt); i++)
                        StrokeController.Fly(ref end, ref velocity, ref spin, c, DoublesWorld.Dt);
                    desired += (target - end) / duration * 1.3f;
                }
                var delta = desired - incoming; var candidate = delta.normalized;
                float value = Vector3.Dot(incoming, candidate) + delta.magnitude / (1 + c.PaddleRestitution);
                if (candidate.z * (target.z - p.z) <= 0 || candidate.y < -.35f) continue;
                float cost = Mathf.Abs(value - 4) + Mathf.Max(0, value - 10) * 10 + Mathf.Abs(duration - 1.25f);
                if (cost < best) { best = cost; n = candidate; speed = Mathf.Clamp(value, -10, 10); }
            }
            return float.IsFinite(best);
        }
    }
}

using Picklebot.Doubles;
using UnityEngine;

namespace Picklebot.PlayerAgents
{
    public static class PlayerMovement
    {
        // Brake only along a requested collision course. This does not choose a
        // court position, intercept, teammate role, or movement toward the ball.
        public static Vector3 Constrain(PlayerBody body, PlayerBody partner, Vector3 requested)
        {
            var velocity = Vector3.ClampMagnitude(requested, PlayerBody.Speed);
            velocity.y = 0;
            var separation = partner.Position - body.Position; separation.y = 0;
            if (separation.sqrMagnitude > .000001f)
            {
                var toward = separation.normalized;
                float gap = Mathf.Max(0, separation.magnitude - 2 * PlayerBody.Radius - .08f);
                float otherClosing = Mathf.Max(0, Vector3.Dot(partner.Velocity, -toward));
                float allowed = Mathf.Sqrt(Mathf.Max(0, 2 * PlayerBody.Acceleration * gap - otherClosing * otherClosing));
                float closing = Vector3.Dot(velocity, toward);
                if (closing > allowed) velocity -= toward * (closing - allowed);
            }
            velocity.x = Mathf.Clamp(velocity.x, -Limit(body.Position.x + 4.2f), Limit(4.2f - body.Position.x));
            float outward = velocity.z * body.Side;
            outward = Mathf.Clamp(outward, -Limit(body.Position.z * body.Side - .38f), Limit(8.1f - body.Position.z * body.Side));
            velocity.z = outward * body.Side;

            // PlayerBody has one vector acceleration budget, not one per axis.
            // Test the complete stopping path after its next motor step. A turn
            // must not consume acceleration needed to stop at the court edge.
            var away = body.Position - partner.Position; away.y = 0;
            var repulsion = away.magnitude < .85f ? away.normalized * (.85f - away.magnitude) * 8 : Vector3.zero;
            var motorTarget = Vector3.ClampMagnitude(velocity + repulsion, PlayerBody.Speed);
            var nextVelocity = Vector3.MoveTowards(body.Velocity, motorTarget, PlayerBody.Acceleration * DoublesWorld.Dt);
            if (separation.sqrMagnitude > .000001f)
            {
                var toward = separation.normalized;
                float ownClosing = Mathf.Max(0, Vector3.Dot(nextVelocity, toward));
                float otherClosing = Mathf.Max(0, Vector3.Dot(partner.Velocity, -toward));
                // Braking a diagonal vector takes time proportional to its full
                // speed. Squared closing speed alone understates that distance.
                float reserve = (ownClosing * nextVelocity.magnitude + otherClosing * partner.Velocity.magnitude)
                    / (2 * PlayerBody.Acceleration) + (ownClosing + otherClosing) * DoublesWorld.Dt;
                if (separation.magnitude - 2 * PlayerBody.Radius - .08f < reserve)
                    return -repulsion;
            }
            // One extra step is a conservative allowance for discrete motion.
            var stop = body.Position + nextVelocity * (DoublesWorld.Dt + nextVelocity.magnitude / (2 * PlayerBody.Acceleration));
            if (Mathf.Abs(stop.x) > 4.16f || stop.z * body.Side < .42f || stop.z * body.Side > 8.06f)
                return -repulsion; // Cancel body repulsion so its motor brakes to zero.
            return velocity;
        }

        private static float Limit(float distance) => Mathf.Sqrt(2 * PlayerBody.Acceleration * Mathf.Max(0, distance - .04f));
    }
}

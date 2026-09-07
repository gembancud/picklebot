using Picklebot.Doubles;
using UnityEngine;

namespace Picklebot.PlayerAgents
{
    // Constrain a commanded paddle step before the legacy body's hard reach
    // projection. Ball contact still uses the resulting real paddle velocity.
    public static class PlayerPaddleMotor
    {
        public static bool Constrain(PlayerBody body, PlayerBody partner, Vector3 moveTarget,
            ref Vector3 target, ref Quaternion rotation, ref Vector3 feed, float dt)
        {
            Vector3 position = PredictPosition(body, partner, moveTarget, dt);
            float height = body.Shoulder.y;
            float wantedHeight = Mathf.MoveTowards(height, Mathf.Clamp(target.y + .20f, .72f, 1.5f), 1.6f * dt);
            var facing = Quaternion.LookRotation(Vector3.forward * -body.Side);
            var angles = (Quaternion.Inverse(facing) * rotation).eulerAngles;
            angles = new Vector3(Mathf.Clamp(Mathf.DeltaAngle(0, angles.x), -65, 65),
                Mathf.Clamp(Mathf.DeltaAngle(0, angles.y), -105, 105), Mathf.Clamp(Mathf.DeltaAngle(0, angles.z), -85, 85));
            var wantedRotation = Quaternion.RotateTowards(body.Paddle.rotation, facing * Quaternion.Euler(angles), PlayerBody.AngularSpeed * Mathf.Rad2Deg * dt);
            var initialTarget = target; var initialFeed = feed;
            // Slow crouch and rotation only if their combination cannot keep
            // the next hand pose within reach at the permitted acceleration.
            for (int trial = 0; trial < 27; trial++)
            {
                bool braking = trial < 9;
                bool innerRecovery = trial >= 18;
                int orientationTrial = trial % 9;
                float fraction = orientationTrial == 8 ? 0 : Mathf.Pow(.5f, orientationTrial);
                float nextHeight = Mathf.Lerp(height, wantedHeight, fraction);
                var nextRotation = Quaternion.Slerp(body.Paddle.rotation, wantedRotation, fraction);
                var shoulder = position + new Vector3(-body.Side * .19f, nextHeight, 0);
                var wantedHand = shoulder + Vector3.ClampMagnitude(initialTarget + nextRotation * PlayerBody.GripLocal - shoulder, .62f);
                var wantedPaddle = wantedHand - nextRotation * PlayerBody.GripLocal;
                var velocity = Vector3.ClampMagnitude(initialFeed + (wantedPaddle - body.Paddle.position) * 28, PlayerBody.PaddleSpeed);
                // These three convex constraints act on the same next velocity.
                var reachCenter = (shoulder - body.Paddle.position - nextRotation * PlayerBody.GripLocal) / dt;
                float reachRadius = .61999f / dt;
                var handOffset = body.Hand - body.Shoulder;
                if (innerRecovery && handOffset.magnitude > .45f) continue;
                var radial = handOffset.normalized;
                var frameVelocity = ((nextRotation * PlayerBody.GripLocal - body.Paddle.rotation * PlayerBody.GripLocal)
                    - (shoulder - body.Shoulder)) / dt;
                // A recovery step can have too little acceleration to restore
                // the preferred reserve immediately. In that case, do not
                // increase outward hand motion by rising or rotating the grip.
                // A slower posture is tried without changing the player's feet.
                var postureVelocity = (nextRotation * PlayerBody.GripLocal - body.Paddle.rotation * PlayerBody.GripLocal
                    - Vector3.up * (nextHeight - height)) / dt;
                if (!braking && Vector3.Dot(postureVelocity, radial) > .0001f) continue;
                // Reserve acceleration for braking before the reach boundary.
                // A one-step position limit alone allows an unrecoverable next step.
                float outwardLimit = Mathf.Sqrt(40f * Mathf.Max(0, .60f - handOffset.magnitude))
                    - Vector3.Dot(frameVelocity, radial);
                // Crouch and grip rotation can stop as soon as they reach
                // their targets. Do not rely on that temporary motion to
                // cancel outward paddle velocity at the following step.
                var bodyVelocity = (position - body.Position) / dt;
                float postureStoppedLimit = Mathf.Sqrt(40f * Mathf.Max(0, .60f - handOffset.magnitude))
                    + Vector3.Dot(bodyVelocity, radial);
                // If the braking reserve cannot be reached in one step,
                // use the remaining feasible acceleration to brake outward
                // motion. Continuing toward the shot target in this fallback
                // can increase outward speed until hard reach is unavoidable.
                // Radial braking takes priority over reducing tangential
                // speed, which already consumes centripetal acceleration.
                if (!braking) velocity = body.PaddleVelocity - radial * (PlayerBody.PaddleAcceleration * dt);
                // Near the shoulder, a fast inward pass can turn tangential
                // faster than the reserve can be restored in one step.
                // Brake all relative motion there, still inside the three
                // hard physical limits. Never continue toward the shot target.
                if (innerRecovery) velocity = bodyVelocity;
                // Near the tangent/acceleration intersection, 64 projections
                // can stop before a feasible velocity reaches the tolerance.
                // Keep the same constraints and early exit, with more time
                // for those narrow intersections to converge.
                for (int iteration = 0; iteration < 128; iteration++)
                {
                    var previous = velocity;
                    velocity = Vector3.ClampMagnitude(velocity, PlayerBody.PaddleSpeed);
                    velocity = body.PaddleVelocity + Vector3.ClampMagnitude(velocity - body.PaddleVelocity, PlayerBody.PaddleAcceleration * dt);
                    velocity = reachCenter + Vector3.ClampMagnitude(velocity - reachCenter, reachRadius);
                    // Bound curvature even if crouch and grip motion stop.
                    // A moving posture must not hide excessive tangential
                    // paddle speed relative to the translating body.
                    if (!innerRecovery)
                    {
                        var stoppedVelocity = velocity - bodyVelocity;
                        float radialSpeed = Vector3.Dot(stoppedVelocity, radial);
                        velocity = bodyVelocity + radial * radialSpeed
                            + Vector3.ClampMagnitude(stoppedVelocity - radial * radialSpeed, 6f);
                    }
                    // The curved hand path also needs centripetal acceleration.
                    // Reserve it with a 6 m/s shoulder-relative hand speed limit.
                    if (braking)
                    {
                        velocity = Vector3.ClampMagnitude(velocity + frameVelocity, 6f) - frameVelocity;
                        velocity -= radial * Mathf.Max(0, Vector3.Dot(velocity, radial) - outwardLimit);
                        velocity -= radial * Mathf.Max(0, Vector3.Dot(velocity, radial) - postureStoppedLimit);
                    }
                    if ((velocity - previous).sqrMagnitude < 1e-12f) break;
                }
                if (velocity.magnitude > PlayerBody.PaddleSpeed + .0001f
                    || (velocity - body.PaddleVelocity).magnitude > PlayerBody.PaddleAcceleration * dt + .0001f
                    || (!innerRecovery && Vector3.ProjectOnPlane(velocity - bodyVelocity, radial).magnitude > 6.0001f)
                    || (braking && (velocity + frameVelocity).magnitude > 6.0001f)
                    || (braking && Vector3.Dot(velocity, radial) > postureStoppedLimit + .0001f)
                    || (velocity - reachCenter).magnitude > reachRadius + .0001f) continue;
                // Target height controls the body's crouch. Compensate its
                // position servo so the requested paddle velocity stays exact.
                target.y = nextHeight - .20f;
                rotation = nextRotation;
                var commandedHand = shoulder + Vector3.ClampMagnitude(target + nextRotation * PlayerBody.GripLocal - shoulder, .62f);
                feed = velocity - (commandedHand - nextRotation * PlayerBody.GripLocal - body.Paddle.position) * 28;
                return true;
            }
            // A moving body can make the speed, acceleration and reach limits
            // mutually infeasible. Expose this; do not call it a bounded step.
            return false;
        }

        private static Vector3 PredictPosition(PlayerBody body, PlayerBody partner, Vector3 target, float dt)
        {
            target.y = 0;
            var wanted = Vector3.ClampMagnitude((target - body.Position) * 4, PlayerBody.Speed);
            var separation = body.Position - partner.Position; separation.y = 0;
            if (separation.magnitude < .85f) wanted += separation.normalized * (.85f - separation.magnitude) * 8;
            var velocity = Vector3.MoveTowards(body.Velocity, Vector3.ClampMagnitude(wanted, PlayerBody.Speed), PlayerBody.Acceleration * dt);
            var next = body.Position + velocity * dt;
            next.x = Mathf.Clamp(next.x, -4.2f, 4.2f); next.z = body.Side * Mathf.Clamp(next.z * body.Side, .38f, 8.1f);
            separation = next - partner.Position; separation.y = 0;
            if (separation.magnitude < PlayerBody.Radius * 2)
                next = partner.Position + (separation.sqrMagnitude < 1e-6f ? Vector3.right * (body.Id % 2 == 0 ? 1 : -1) : separation.normalized) * PlayerBody.Radius * 2;
            return next;
        }
    }
}

using System;
using UnityEngine;

namespace Picklebot.PlayerControls
{
    // A movement constraint for the lab enclosure, with no ball or tactical input.
    // Reserve enough distance to stop before a wall instead of asking the arm to
    // cancel an instantaneous root collision impulse on the following tick.
    public static class PlayerEnclosureBrakingV3
    {
        public static Vector2 Constrain(Vector2 position, Vector2 previous, Vector2 requested,
            int side, float acceleration, float dt)
        {
            if (side != -1 && side != 1) throw new ArgumentOutOfRangeException(nameof(side));
            if (!float.IsFinite(acceleration) || acceleration <= 0 || !float.IsFinite(dt) || dt <= 0 || dt > .05f)
                throw new ArgumentOutOfRangeException(nameof(dt));
            // Splitting the braking budget guarantees both axes can stop together.
            float axisAcceleration = acceleration / Mathf.Sqrt(2f);
            float Safe(float distance)
            {
                float dv = axisAcceleration * dt;
                return Mathf.Sqrt(dv * dv + 2 * axisAcceleration * Mathf.Max(0, distance)) - dv;
            }
            float lowZ = side < 0 ? -8.1f : .38f, highZ = side < 0 ? -.38f : 8.1f;
            var lower = new Vector2(-Safe(position.x + 4.2f), -Safe(position.y - lowZ));
            var upper = new Vector2(Safe(4.2f - position.x), Safe(highZ - position.y));
            Vector2 Box(Vector2 value) => new Vector2(Mathf.Clamp(value.x, lower.x, upper.x), Mathf.Clamp(value.y, lower.y, upper.y));
            float radius = acceleration * dt;
            var nearest = Box(previous);
            if ((nearest - previous).magnitude > radius + 1e-5f)
                throw new InvalidOperationException("Root is outside the enclosure braking viability region.");
            var candidate = Box(requested);
            if ((candidate - previous).magnitude <= radius) return candidate;
            // Euclidean projection onto the intersection of the velocity box and
            // acceleration disc. Merely clipping each axis can exceed total effort.
            float lo = 0, hi = 1;
            Vector2 At(float weight) => Box((requested + previous * weight) / (1 + weight));
            while ((At(hi) - previous).magnitude > radius && hi < 1048576) hi *= 2;
            for (int i = 0; i < 32; i++)
            {
                float mid = (lo + hi) * .5f;
                if ((At(mid) - previous).magnitude > radius) lo = mid; else hi = mid;
            }
            return At(hi);
        }
    }
}

using System;
using System.Linq;
using Picklebot.PlayerControlsIntegration;
using UnityEngine;

namespace Picklebot.PlayerLearning
{
    public enum PlayerIntentV1 { PlayBall, Recover, Cover, Yield }

    // Goals describe outcomes. They never assign a motor, stroke, path or contact time.
    // Coordinates are canonical court meters: both teams attack toward positive Z.
    public sealed class PlayerExecutionGoalV1
    {
        public const string BehaviorName = "PicklebotExecutionV1";
        public const string Contract = "execution-v1-136obs-16continuous-release";
        public const int FeatureCount = 12;
        public const int ObservationCount = PlayerObservationV3.Count + FeatureCount;
        public readonly int Seat, IssuedTick;
        public readonly PlayerIntentV1 Intent;
        public readonly bool HasMovementTarget, HasShotTarget;
        public readonly Vector2 MovementTarget, ShotTarget;
        public readonly float MovementRadius, ShotRadius;
        public static readonly string[] Fields = {
            "goal.playBall", "goal.recover", "goal.cover", "goal.yield",
            "goal.move.enabled", "goal.move.relative.x", "goal.move.relative.z", "goal.move.radius",
            "goal.shot.enabled", "goal.shot.x", "goal.shot.z", "goal.shot.radius"
        };

        public PlayerExecutionGoalV1(int seat, int issuedTick, PlayerIntentV1 intent,
            Vector2? movementTarget = null, float movementRadius = .5f,
            Vector2? shotTarget = null, float shotRadius = 1f)
        {
            if (seat < 0 || seat > 3 || issuedTick < 0 || !Enum.IsDefined(typeof(PlayerIntentV1), intent))
                throw new ArgumentException("Invalid execution goal identity or intention.");
            bool Finite(Vector2 p) => float.IsFinite(p.x) && float.IsFinite(p.y);
            if (!float.IsFinite(movementRadius) || movementRadius <= 0 || movementRadius > 3 ||
                !float.IsFinite(shotRadius) || shotRadius <= 0 || shotRadius > 3)
                throw new ArgumentException("Goal radii must be finite and in (0,3] meters.");
            if (movementTarget.HasValue && (!Finite(movementTarget.Value) ||
                Mathf.Abs(movementTarget.Value.x) > 5.048f || movementTarget.Value.y > 0 || movementTarget.Value.y < -8.7056f))
                throw new ArgumentException("Movement goal must be on this player's side, including the run-off area.");
            if (shotTarget.HasValue && (!Finite(shotTarget.Value) ||
                Mathf.Abs(shotTarget.Value.x) >= 3.048f || shotTarget.Value.y <= 0 || shotTarget.Value.y >= 6.7056f))
                throw new ArgumentException("Shot goal center must be inside the opposing court.");
            Seat = seat; IssuedTick = issuedTick; Intent = intent;
            HasMovementTarget = movementTarget.HasValue; HasShotTarget = shotTarget.HasValue;
            MovementTarget = movementTarget ?? Vector2.zero; ShotTarget = shotTarget ?? Vector2.zero;
            MovementRadius = movementRadius; ShotRadius = shotRadius;
        }

        public float[] Observe(PlayerObservationV3 observation)
        {
            if (observation == null || observation.player != Seat || observation.tick < IssuedTick)
                throw new InvalidOperationException("Goal and observation must belong to the same player and current episode.");
            var original = observation.ToArray(); var result = new float[ObservationCount];
            Array.Copy(original, result, original.Length);
            int o = original.Length; result[o + (int)Intent] = 1;
            if (HasMovementTarget)
            {
                result[o+4] = 1;
                // Existing self.x/z are canonical absolute positions scaled by 4.2/8.1.
                result[o+5] = (MovementTarget.x - original[0]*4.2f)/8.4f;
                result[o+6] = (MovementTarget.y - original[1]*8.1f)/16.2f;
                result[o+7] = MovementRadius/3;
            }
            if (HasShotTarget)
            { result[o+8] = 1; result[o+9] = ShotTarget.x/3.048f; result[o+10] = ShotTarget.y/6.7056f; result[o+11] = ShotRadius/3; }
            if (result.Any(v => !float.IsFinite(v))) throw new InvalidOperationException("Non-finite execution observation.");
            return result;
        }

        public float LandingDistance(Vector3 worldPoint)
        {
            if (!HasShotTarget) throw new InvalidOperationException("No shot target is assigned.");
            int sign = Seat < 2 ? 1 : -1;
            return Vector2.Distance(new Vector2(sign*worldPoint.x, sign*worldPoint.z), ShotTarget);
        }
    }
}

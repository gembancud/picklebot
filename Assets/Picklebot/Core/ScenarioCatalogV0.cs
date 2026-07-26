using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using UnityEngine;

namespace Picklebot.Core
{
    [Serializable]
    public struct ScenarioParametersV0
    {
        public Vector3 BallPosition;
        public Quaternion BallRotation;
        public Vector3 BallLinearVelocity;
        public Vector3 BallAngularVelocity;
        public Vector3 PaddlePosition;
        public Quaternion PaddleRotation;
        public Vector3 TargetPosition;
        public float MaximumEpisodeSeconds;

        public string CanonicalText()
        {
            return string.Join(
                "|",
                StableHashV0.Vector(BallPosition),
                StableHashV0.QuaternionValue(BallRotation),
                StableHashV0.Vector(BallLinearVelocity),
                StableHashV0.Vector(BallAngularVelocity),
                StableHashV0.Vector(PaddlePosition),
                StableHashV0.QuaternionValue(PaddleRotation),
                StableHashV0.Vector(TargetPosition),
                StableHashV0.Float(MaximumEpisodeSeconds));
        }
    }

    public static class ScenarioCatalogV0
    {
        public const string ContactFrontOn = "contact/front-on";
        public const string LaunchServeLike = "launch/serve-like";
        public const string LaunchRally = "launch/rally";
        public const string BoundaryCourt = "boundary/court";
        public const string BoundaryNonVolleyZone = "boundary/non-volley-zone";
        public const string NetClear = "net/clear";
        public const string NetContactContinues = "net/contact-continues";
        public const string ResetStateLeak = "reset/state-leak";
        public const string StabilityHighSpeed = "stability/high-speed";

        private static readonly string[] StableIds =
        {
            ContactFrontOn,
            LaunchServeLike,
            LaunchRally,
            BoundaryCourt,
            BoundaryNonVolleyZone,
            NetClear,
            NetContactContinues,
            ResetStateLeak,
            StabilityHighSpeed
        };

        public static IReadOnlyList<string> ScenarioIds => StableIds;

        public static ScenarioParametersV0 Generate(
            ResetRequestV0 request,
            SimulationConfigV0 configuration)
        {
            if (!StableIds.Contains(request.ScenarioId, StringComparer.Ordinal))
            {
                throw new ArgumentException(
                    $"Unknown Phase 0 scenario '{request.ScenarioId}'.",
                    nameof(request));
            }

            configuration.ValidateOrThrow();

            var launcher = Stream(request.Seed, "launcher");
            var ballPhysics = Stream(request.Seed, "ball_physics");
            var paddleStart = Stream(request.Seed, "paddle_start");
            var result = Defaults(request.ScenarioId, configuration.DefaultMaximumEpisodeSeconds);

            if (request.ScenarioId is ContactFrontOn or StabilityHighSpeed)
            {
                var contactLane = launcher.Range(-0.1f, 0.1f);
                result.BallPosition.x = contactLane;
                result.BallLinearVelocity.x = 0f;
                result.PaddlePosition.x = contactLane;
            }
            else
            {
                result.BallPosition.x += launcher.Range(-0.35f, 0.35f);
                result.BallLinearVelocity.x += launcher.Range(-0.3f, 0.3f);
                result.PaddlePosition.x += paddleStart.Range(-0.12f, 0.12f);
            }

            result.BallAngularVelocity = new Vector3(
                ballPhysics.Range(-5f, 5f),
                ballPhysics.Range(-10f, 10f),
                ballPhysics.Range(-5f, 5f));

            ApplyDifficulty(ref result, request.Difficulty);
            ApplyOverrides(ref result, request.Overrides);
            Validate(result);
            return result;
        }

        public static string CanonicalizeOverrides(IReadOnlyList<ResetOverrideV0> overrides)
        {
            if (overrides == null || overrides.Count == 0)
            {
                return string.Empty;
            }

            return string.Join(
                ";",
                overrides
                    .OrderBy(value => value.Key, StringComparer.Ordinal)
                    .Select(value =>
                        $"{value.Key}={value.Value.ToString("R", CultureInfo.InvariantCulture)}"));
        }

        private static Pcg32Random Stream(ulong seed, string name)
        {
            return new Pcg32Random(seed, Pcg32Random.DeriveStream(seed, name));
        }

        private static ScenarioParametersV0 Defaults(string scenarioId, float maximumSeconds)
        {
            var value = new ScenarioParametersV0
            {
                BallPosition = new Vector3(0f, 1.15f, 2.8f),
                BallRotation = Quaternion.identity,
                BallLinearVelocity = new Vector3(0f, 1.25f, -7f),
                BallAngularVelocity = Vector3.zero,
                PaddlePosition = new Vector3(0f, 1.05f, -1.35f),
                PaddleRotation = Quaternion.identity,
                TargetPosition = new Vector3(0f, 0f, 4.4f),
                MaximumEpisodeSeconds = Mathf.Min(maximumSeconds, 6f)
            };

            switch (scenarioId)
            {
                case ContactFrontOn:
                    value.BallPosition = new Vector3(0f, 1.05f, 0.25f);
                    value.BallLinearVelocity = new Vector3(0f, 0f, -7f);
                    value.PaddlePosition = new Vector3(0f, 1.05f, -1.1f);
                    value.MaximumEpisodeSeconds = 3f;
                    break;
                case LaunchServeLike:
                    value.BallPosition = new Vector3(0f, 0.75f, -5.2f);
                    value.BallLinearVelocity = new Vector3(0f, 5.8f, 8.5f);
                    value.PaddlePosition = new Vector3(0f, 1f, -5.8f);
                    value.MaximumEpisodeSeconds = 4f;
                    break;
                case LaunchRally:
                    break;
                case BoundaryCourt:
                    value.BallPosition = new Vector3(
                        CourtGeometryV0.HalfWidth,
                        0.9f,
                        CourtGeometryV0.HalfLength);
                    value.BallLinearVelocity = new Vector3(0f, -1f, 0f);
                    value.MaximumEpisodeSeconds = 2f;
                    break;
                case BoundaryNonVolleyZone:
                    value.BallPosition = new Vector3(
                        0f,
                        0.9f,
                        CourtGeometryV0.NonVolleyZoneDepth);
                    value.BallLinearVelocity = new Vector3(0f, -1f, 0f);
                    value.MaximumEpisodeSeconds = 2f;
                    break;
                case NetClear:
                    value.BallPosition = new Vector3(0f, 1.4f, -2.5f);
                    value.BallLinearVelocity = new Vector3(0f, 1.5f, 7.5f);
                    value.PaddlePosition = new Vector3(0f, 1f, -5.5f);
                    value.MaximumEpisodeSeconds = 3f;
                    break;
                case NetContactContinues:
                    value.BallPosition = new Vector3(0f, 0.86f, -1.8f);
                    value.BallLinearVelocity = new Vector3(0f, 0.15f, 6.5f);
                    value.PaddlePosition = new Vector3(0f, 1f, -5.5f);
                    value.MaximumEpisodeSeconds = 3f;
                    break;
                case ResetStateLeak:
                    value.BallPosition = new Vector3(0f, 1.2f, 2f);
                    value.BallLinearVelocity = new Vector3(1.5f, 1f, -5.5f);
                    value.MaximumEpisodeSeconds = 3f;
                    break;
                case StabilityHighSpeed:
                    value.BallPosition = new Vector3(0f, 1.05f, 1.5f);
                    value.BallLinearVelocity = new Vector3(0f, 0f, -22f);
                    value.PaddlePosition = new Vector3(0f, 1.05f, -1.1f);
                    value.MaximumEpisodeSeconds = 2f;
                    break;
            }

            return value;
        }

        private static void ApplyDifficulty(ref ScenarioParametersV0 value, string difficulty)
        {
            switch (difficulty)
            {
                case null:
                case "":
                case "default":
                    return;
                case "easy":
                    value.BallLinearVelocity *= 0.75f;
                    return;
                case "hard":
                    value.BallLinearVelocity *= 1.25f;
                    return;
                default:
                    throw new ArgumentException($"Unknown difficulty '{difficulty}'.");
            }
        }

        private static void ApplyOverrides(
            ref ScenarioParametersV0 value,
            IReadOnlyList<ResetOverrideV0> overrides)
        {
            if (overrides == null)
            {
                return;
            }

            foreach (var current in overrides)
            {
                if (!FiniteMath.IsFinite(current.Value))
                {
                    throw new ArgumentException($"Override '{current.Key}' is not finite.");
                }

                switch (current.Key)
                {
                    case "ball.position.x": value.BallPosition.x = current.Value; break;
                    case "ball.position.y": value.BallPosition.y = current.Value; break;
                    case "ball.position.z": value.BallPosition.z = current.Value; break;
                    case "ball.velocity.x": value.BallLinearVelocity.x = current.Value; break;
                    case "ball.velocity.y": value.BallLinearVelocity.y = current.Value; break;
                    case "ball.velocity.z": value.BallLinearVelocity.z = current.Value; break;
                    case "ball.angular_velocity.x": value.BallAngularVelocity.x = current.Value; break;
                    case "ball.angular_velocity.y": value.BallAngularVelocity.y = current.Value; break;
                    case "ball.angular_velocity.z": value.BallAngularVelocity.z = current.Value; break;
                    case "paddle.position.x": value.PaddlePosition.x = current.Value; break;
                    case "paddle.position.y": value.PaddlePosition.y = current.Value; break;
                    case "paddle.position.z": value.PaddlePosition.z = current.Value; break;
                    case "target.x": value.TargetPosition.x = current.Value; break;
                    case "target.z": value.TargetPosition.z = current.Value; break;
                    case "maximum_episode_seconds": value.MaximumEpisodeSeconds = current.Value; break;
                    default:
                        throw new ArgumentException($"Unknown test override '{current.Key}'.");
                }
            }
        }

        private static void Validate(ScenarioParametersV0 value)
        {
            if (!FiniteMath.IsFinite(value.BallPosition) ||
                !FiniteMath.IsFinite(value.BallRotation) ||
                !FiniteMath.IsFinite(value.BallLinearVelocity) ||
                !FiniteMath.IsFinite(value.BallAngularVelocity) ||
                !FiniteMath.IsFinite(value.PaddlePosition) ||
                !FiniteMath.IsFinite(value.PaddleRotation) ||
                !FiniteMath.IsFinite(value.TargetPosition) ||
                !FiniteMath.IsFinite(value.MaximumEpisodeSeconds) ||
                value.MaximumEpisodeSeconds <= 0f ||
                value.MaximumEpisodeSeconds > 20f)
            {
                throw new InvalidOperationException("Generated scenario parameters are invalid.");
            }
        }
    }
}

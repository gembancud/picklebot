using System;
using System.Collections.Generic;
using Picklebot.Core;
using Picklebot.Simulation;
using UnityEngine;

namespace Picklebot.Museum
{
    public enum PhysicsMuseumStationV1
    {
        DropRebound = 0,
        SpinFlight = 1,
        CourtBounce = 2,
        PaddleBrush = 3,
        NetInteraction = 4,
        FreeHit = 5
    }

    public readonly struct PhysicsMuseumStationDefinitionV1
    {
        public readonly PhysicsMuseumStationV1 Station;
        public readonly string Id;
        public readonly string ShortLabel;
        public readonly string Title;
        public readonly string Description;
        public readonly string InteractionHint;
        public readonly bool AllowsManualPaddle;
        public readonly int VariantCount;
        public readonly Vector3 CameraPosition;
        public readonly Vector3 CameraTarget;

        public PhysicsMuseumStationDefinitionV1(
            PhysicsMuseumStationV1 station,
            string id,
            string shortLabel,
            string title,
            string description,
            string interactionHint,
            bool allowsManualPaddle,
            int variantCount,
            Vector3 cameraPosition,
            Vector3 cameraTarget)
        {
            Station = station;
            Id = id;
            ShortLabel = shortLabel;
            Title = title;
            Description = description;
            InteractionHint = interactionHint;
            AllowsManualPaddle = allowsManualPaddle;
            VariantCount = variantCount;
            CameraPosition = cameraPosition;
            CameraTarget = cameraTarget;
        }
    }

    public static class PhysicsMuseumProtocolV1
    {
        public const string Version = "physics-museum-v1";
        public const ulong SeedBase = 8300000UL;
        public const int StationCount = 6;
        public const float SpinComparisonMagnitude = 62.831853f;
        public const float DropReboundCourtZ = -2f;

        private static readonly PhysicsMuseumStationDefinitionV1[] Definitions =
        {
            new(
                PhysicsMuseumStationV1.DropRebound,
                "museum/drop-rebound",
                "DROP",
                "Ball drop and rebound",
                "An official-height outdoor-ball drop. After env-v1 records the " +
                "first acrylic contact, the museum continues the same real Unity " +
                "ball to its rebound apex. The cyan marker shows the independently " +
                "measured fixture apex.",
                "SPACE launches. R restores the release. Inspect impact time, " +
                "rebound apex, drift, and energy.",
                false,
                1,
                new Vector3(4.4f, 2.7f, -6.2f),
                new Vector3(0f, 1.05f, DropReboundCourtZ)),
            new(
                PhysicsMuseumStationV1.SpinFlight,
                "museum/spin-flight",
                "SPIN",
                "Zero spin vs topspin vs backspin",
                "Three source-identical env-v1 flights differ only in x-axis " +
                "spin: zero, +10 rps topspin, and -10 rps backspin. Their " +
                "traces remain visible together for direct comparison.",
                "SPACE runs all three flights automatically. Yellow is zero " +
                "spin, coral is topspin, and cyan is backspin.",
                false,
                3,
                new Vector3(7.2f, 4.2f, -8.6f),
                new Vector3(0f, 1.2f, 0.5f)),
            new(
                PhysicsMuseumStationV1.CourtBounce,
                "museum/court-bounce",
                "BOUNCE",
                "Oblique spun court bounce",
                "A shallow, spun impact exercises env-v1 drag, Magnus lift, " +
                "acrylic restitution, and friction. The museum continues the same " +
                "real Unity ball after the first-contact episode record becomes " +
                "terminal. The cyan marker is the measured fixture rebound apex.",
                "SPACE launches. R resets. Compare incoming/outgoing velocity, " +
                "spin, rebound height, and energy.",
                false,
                1,
                new Vector3(5.2f, 2.8f, -4.8f),
                new Vector3(0f, 0.85f, -0.5f)),
            new(
                PhysicsMuseumStationV1.PaddleBrush,
                "museum/paddle-brush",
                "BRUSH",
                "Paddle brush and spin transfer",
                "A zero-spin ball approaches the real rounded kinematic paddle. " +
                "Move the paddle tangentially at contact to generate observable " +
                "topspin, backspin, or sidespin through the committed surrogate.",
                "Hold/click and move the mouse or trackpad to brush. W/S moves " +
                "depth. Q/E, A/D, and Z/X rotate the paddle.",
                true,
                1,
                new Vector3(3.7f, 2.15f, -3.0f),
                new Vector3(0f, 1.05f, 0f)),
            new(
                PhysicsMuseumStationV1.NetInteraction,
                "museum/net-interaction",
                "NET",
                "Net clearance and contact",
                "Toggle between a clean clearance and a tape/body contact. Both " +
                "run through the regulation post-span net and real env-v1 event " +
                "path, including continued flight after a net touch.",
                "V changes clearance/contact. SPACE launches the selected case. " +
                "R resets it.",
                false,
                2,
                new Vector3(5.8f, 3.2f, -5.8f),
                new Vector3(0f, 0.9f, 0f)),
            new(
                PhysicsMuseumStationV1.FreeHit,
                "museum/free-hit",
                "FREE",
                "Free-hit regulation court",
                "A regulation court, outdoor-ball flight model, rounded paddle, " +
                "and net are exposed as a hands-on feel check. This station uses " +
                "the same actions and observations intended for the numeric agent.",
                "Hold/click and move the mouse or trackpad to position/brush. " +
                "W/S moves depth. Q/E, A/D, and Z/X angle the face.",
                true,
                1,
                new Vector3(7.8f, 6.5f, -9.5f),
                new Vector3(0f, 0.75f, 0f))
        };

        private static readonly IReadOnlyList<PhysicsMuseumStationDefinitionV1>
            ReadOnlyDefinitions = Array.AsReadOnly(Definitions);

        public static IReadOnlyList<PhysicsMuseumStationDefinitionV1> Stations =>
            ReadOnlyDefinitions;

        public static PhysicsMuseumStationDefinitionV1 Definition(
            PhysicsMuseumStationV1 station)
        {
            var index = (int)station;
            if (index < 0 || index >= Definitions.Length)
            {
                throw new ArgumentOutOfRangeException(nameof(station));
            }

            return Definitions[index];
        }

        public static string VariantLabel(
            PhysicsMuseumStationV1 station,
            int variant)
        {
            ValidateVariant(station, variant);
            return station switch
            {
                PhysicsMuseumStationV1.SpinFlight => variant switch
                {
                    0 => "zero spin",
                    1 => "topspin +10 rps",
                    _ => "backspin -10 rps"
                },
                PhysicsMuseumStationV1.NetInteraction =>
                    variant == 0 ? "clean clearance" : "tape/body contact",
                _ => "standard"
            };
        }

        public static ResetRequestV0 CreateRequest(
            PhysicsMuseumStationV1 station,
            int variant = 0)
        {
            ValidateVariant(station, variant);
            var seed = SeedBase + ((ulong)(int)station * 100UL) + (ulong)variant;
            var overrides = new List<ResetOverrideV0>();
            string scenario;

            switch (station)
            {
                case PhysicsMuseumStationV1.DropRebound:
                    scenario = ScenarioCatalogV0.LaunchRally;
                    SetBall(
                        overrides,
                        new Vector3(
                            0f,
                            CalibrationFixturesV1.OfficialDropReferenceHeight -
                            CourtGeometryV1.BallRadius,
                            DropReboundCourtZ),
                        Vector3.zero,
                        Vector3.zero);
                    MovePaddleAway(overrides);
                    break;
                case PhysicsMuseumStationV1.SpinFlight:
                    scenario = ScenarioCatalogV0.LaunchRally;
                    var spin = variant switch
                    {
                        0 => 0f,
                        1 => SpinComparisonMagnitude,
                        _ => -SpinComparisonMagnitude
                    };
                    SetBall(
                        overrides,
                        new Vector3(0f, 1.15f, -5f),
                        new Vector3(0f, 2.2f, 12f),
                        new Vector3(spin, 0f, 0f));
                    MovePaddleAway(overrides);
                    break;
                case PhysicsMuseumStationV1.CourtBounce:
                    scenario = ScenarioCatalogV0.LaunchRally;
                    SetBall(
                        overrides,
                        new Vector3(0f, 1.35f, -1.5f),
                        new Vector3(3f, -4f, 4f),
                        new Vector3(0f, 0f, SpinComparisonMagnitude));
                    MovePaddleAway(overrides);
                    break;
                case PhysicsMuseumStationV1.PaddleBrush:
                    scenario = ScenarioCatalogV0.ContactFrontOn;
                    SetBall(
                        overrides,
                        new Vector3(0f, 1.05f, 0.25f),
                        new Vector3(0f, 0f, -7f),
                        Vector3.zero);
                    overrides.Add(new ResetOverrideV0("paddle.position.z", 0f));
                    break;
                case PhysicsMuseumStationV1.NetInteraction:
                    scenario = ScenarioCatalogV0.NetContactContinues;
                    SetBall(
                        overrides,
                        new Vector3(
                            0f,
                            variant == 0
                                ? CourtGeometryV1.NetCenterHeight +
                                  CourtGeometryV1.BallRadius + 0.18f
                                : CourtGeometryV1.NetCenterHeight,
                            -1.8f),
                        new Vector3(0f, variant == 0 ? 0.7f : 0.1f, 7.5f),
                        Vector3.zero);
                    MovePaddleAway(overrides);
                    break;
                case PhysicsMuseumStationV1.FreeHit:
                    scenario = ScenarioCatalogV0.LaunchRally;
                    overrides.Add(new ResetOverrideV0(
                        "ball.angular_velocity.x",
                        0f));
                    overrides.Add(new ResetOverrideV0(
                        "ball.angular_velocity.y",
                        0f));
                    overrides.Add(new ResetOverrideV0(
                        "ball.angular_velocity.z",
                        0f));
                    break;
                default:
                    throw new ArgumentOutOfRangeException(nameof(station));
            }

            overrides.Add(new ResetOverrideV0("maximum_episode_seconds", 6f));
            return new ResetRequestV0(seed, scenario, overrides: overrides);
        }

        public static PaddleActionV0 ManualAction(
            Vector3 paddlePosition,
            Quaternion paddleRotation,
            Vector2 normalizedPointer,
            bool pointerActive,
            float normalizedDepth,
            Vector3 normalizedAngularVelocity,
            SimulationConfigV1 configuration)
        {
            if (configuration == null)
            {
                throw new ArgumentNullException(nameof(configuration));
            }

            configuration.ValidateOrThrow();
            var linearWorld = Vector3.zero;
            if (pointerActive)
            {
                var target = new Vector3(
                    Mathf.Lerp(
                        -CourtGeometryV1.HalfWidth + 0.25f,
                        CourtGeometryV1.HalfWidth - 0.25f,
                        Mathf.Clamp01(normalizedPointer.x)),
                    Mathf.Lerp(
                        0.45f,
                        2.35f,
                        Mathf.Clamp01(normalizedPointer.y)),
                    paddlePosition.z);
                linearWorld = (target - paddlePosition) * 4f;
            }

            var linearLocal =
                Quaternion.Inverse(paddleRotation) * linearWorld /
                configuration.MaxPaddleLinearSpeed;
            linearLocal.z += Mathf.Clamp(normalizedDepth, -1f, 1f);
            return new PaddleActionV0(
                FiniteMath.ClampUnitCube(linearLocal),
                FiniteMath.ClampUnitCube(normalizedAngularVelocity));
        }

        public static void ValidateOrThrow()
        {
            if (Definitions.Length != StationCount)
            {
                throw new InvalidOperationException(
                    "Physics museum must expose exactly six stations.");
            }

            var ids = new HashSet<string>(StringComparer.Ordinal);
            foreach (var definition in Definitions)
            {
                if (string.IsNullOrWhiteSpace(definition.Id) ||
                    string.IsNullOrWhiteSpace(definition.ShortLabel) ||
                    string.IsNullOrWhiteSpace(definition.Title) ||
                    string.IsNullOrWhiteSpace(definition.Description) ||
                    string.IsNullOrWhiteSpace(definition.InteractionHint) ||
                    definition.VariantCount < 1 ||
                    !FiniteMath.IsFinite(definition.CameraPosition) ||
                    !FiniteMath.IsFinite(definition.CameraTarget) ||
                    !ids.Add(definition.Id))
                {
                    throw new InvalidOperationException(
                        "Physics museum station definitions are invalid.");
                }

                for (var variant = 0;
                     variant < definition.VariantCount;
                     variant++)
                {
                    var request = CreateRequest(definition.Station, variant);
                    if (request.Seed < SeedBase ||
                        request.Overrides.Count == 0)
                    {
                        throw new InvalidOperationException(
                            "Physics museum requests are invalid.");
                    }
                }
            }
        }

        private static void ValidateVariant(
            PhysicsMuseumStationV1 station,
            int variant)
        {
            var definition = Definition(station);
            if (variant < 0 || variant >= definition.VariantCount)
            {
                throw new ArgumentOutOfRangeException(nameof(variant));
            }
        }

        private static void SetBall(
            ICollection<ResetOverrideV0> overrides,
            Vector3 position,
            Vector3 velocity,
            Vector3 angularVelocity)
        {
            overrides.Add(new ResetOverrideV0("ball.position.x", position.x));
            overrides.Add(new ResetOverrideV0("ball.position.y", position.y));
            overrides.Add(new ResetOverrideV0("ball.position.z", position.z));
            overrides.Add(new ResetOverrideV0("ball.velocity.x", velocity.x));
            overrides.Add(new ResetOverrideV0("ball.velocity.y", velocity.y));
            overrides.Add(new ResetOverrideV0("ball.velocity.z", velocity.z));
            overrides.Add(new ResetOverrideV0(
                "ball.angular_velocity.x",
                angularVelocity.x));
            overrides.Add(new ResetOverrideV0(
                "ball.angular_velocity.y",
                angularVelocity.y));
            overrides.Add(new ResetOverrideV0(
                "ball.angular_velocity.z",
                angularVelocity.z));
        }

        private static void MovePaddleAway(
            ICollection<ResetOverrideV0> overrides)
        {
            overrides.Add(new ResetOverrideV0("paddle.position.x", 2.8f));
            overrides.Add(new ResetOverrideV0("paddle.position.y", 1f));
            overrides.Add(new ResetOverrideV0("paddle.position.z", -5.8f));
        }
    }
}

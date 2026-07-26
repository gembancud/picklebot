using System;
using System.Collections.Generic;
using UnityEngine;

namespace Picklebot.Core
{
    public static class EnvironmentVersion
    {
        public const string Current = "env-v0";
        public const int PhysicsTicksPerSecond = 120;
        public const int DefaultTicksPerAction = 2;
        public const float PhysicsDeltaTime = 1f / PhysicsTicksPerSecond;
    }

    public enum EpisodeStateV0
    {
        Uninitialized,
        Resetting,
        Ready,
        Running,
        Terminal
    }

    public enum LastTouchV0
    {
        None,
        Launcher,
        ControlledPaddle,
        Net,
        Floor,
        Other
    }

    public enum TerminationReasonV0
    {
        None,
        FarCourtLanding,
        NearCourtLanding,
        OutOfBoundsLanding,
        PlayableVolumeExit,
        Timeout,
        InvalidAction,
        InvalidNumericState,
        ScenarioCompleted,
        TestAbort
    }

    public enum EnvironmentEventKindV0
    {
        EpisodeStarted,
        BallLaunched,
        BallPaddleContact,
        BallNetContact,
        BallFloorContact,
        BallEnteredZone,
        BallExitedPlayableVolume,
        ActionClamped,
        EpisodeTerminated,
        InvalidNumericState
    }

    public enum ZoneClassificationV0
    {
        NearCourtIn,
        FarCourtIn,
        NearNonVolleyZone,
        FarNonVolleyZone,
        Out,
        Unknown
    }

    [Serializable]
    public readonly struct ResetOverrideV0
    {
        public readonly string Key;
        public readonly float Value;

        public ResetOverrideV0(string key, float value)
        {
            Key = string.IsNullOrWhiteSpace(key)
                ? throw new ArgumentException("Override key is required.", nameof(key))
                : key;
            Value = value;
        }
    }

    [Serializable]
    public readonly struct ResetRequestV0
    {
        public readonly ulong Seed;
        public readonly string ScenarioId;
        public readonly string Difficulty;
        public readonly IReadOnlyList<ResetOverrideV0> Overrides;

        public ResetRequestV0(
            ulong seed,
            string scenarioId,
            string difficulty = "default",
            IReadOnlyList<ResetOverrideV0> overrides = null)
        {
            Seed = seed;
            ScenarioId = scenarioId ?? throw new ArgumentNullException(nameof(scenarioId));
            Difficulty = string.IsNullOrWhiteSpace(difficulty) ? "default" : difficulty;
            Overrides = overrides ?? Array.Empty<ResetOverrideV0>();
        }
    }

    [Serializable]
    public readonly struct PaddleActionV0
    {
        public readonly Vector3 LinearVelocityLocal;
        public readonly Vector3 AngularVelocityLocal;

        public PaddleActionV0(Vector3 linearVelocityLocal, Vector3 angularVelocityLocal)
        {
            LinearVelocityLocal = linearVelocityLocal;
            AngularVelocityLocal = angularVelocityLocal;
        }

        public static PaddleActionV0 Zero => new(Vector3.zero, Vector3.zero);
    }

    [Serializable]
    public struct KinematicSnapshotV0
    {
        public Vector3 PositionWorld;
        public Quaternion RotationWorld;
        public Vector3 LinearVelocityWorld;
        public Vector3 AngularVelocityWorld;
    }

    [Serializable]
    public struct EpisodeSnapshotV0
    {
        public EpisodeStateV0 State;
        public LastTouchV0 LastTouch;
        public int ControlledPaddleContacts;
        public int BallFloorContacts;
    }

    [Serializable]
    public struct ObservationV0
    {
        public string EnvironmentVersion;
        public ulong EpisodeId;
        public ulong Seed;
        public string ScenarioId;
        public ulong PhysicsTick;
        public float ElapsedTime;
        public KinematicSnapshotV0 Ball;
        public KinematicSnapshotV0 Paddle;
        public Vector3 BallPositionFromPaddle;
        public Vector3 BallVelocityFromPaddle;
        public EpisodeSnapshotV0 Episode;
    }

    [Serializable]
    public struct RewardFeaturesV0
    {
        public int PaddleContactCount;
        public float FarCourtLanding;
        public float NearCourtLanding;
        public float OutLanding;
        public int NetContactCount;
        public float TargetDistanceAtLanding;
        public float ElapsedTime;
        public int ActionClampCount;
        public float InvalidState;
    }

    [Serializable]
    public readonly struct EnvironmentEventV0
    {
        public readonly ulong PhysicsTick;
        public readonly int Sequence;
        public readonly EnvironmentEventKindV0 Kind;
        public readonly int EntityId;
        public readonly Vector3 Position;
        public readonly Vector3 Normal;
        public readonly float Magnitude;
        public readonly string Detail;

        public EnvironmentEventV0(
            ulong physicsTick,
            int sequence,
            EnvironmentEventKindV0 kind,
            int entityId,
            Vector3 position,
            Vector3 normal,
            float magnitude = 0f,
            string detail = "")
        {
            PhysicsTick = physicsTick;
            Sequence = sequence;
            Kind = kind;
            EntityId = entityId;
            Position = position;
            Normal = normal;
            Magnitude = magnitude;
            Detail = detail ?? string.Empty;
        }
    }

    [Serializable]
    public sealed class EpisodeManifestV0
    {
        public string EnvironmentVersion;
        public string ConfigurationVersion;
        public string ConfigurationHash;
        public string PhysicsSettingsHash;
        public ulong EpisodeId;
        public ulong Seed;
        public string ScenarioId;
        public string Difficulty;
        public ScenarioParametersV0 Parameters;
        public ResetOverrideV0[] Overrides = Array.Empty<ResetOverrideV0>();

        public string CanonicalText()
        {
            return string.Join(
                "|",
                EnvironmentVersion,
                ConfigurationVersion,
                ConfigurationHash,
                PhysicsSettingsHash,
                EpisodeId,
                Seed,
                ScenarioId,
                Difficulty,
                Parameters.CanonicalText(),
                ScenarioCatalogV0.CanonicalizeOverrides(Overrides));
        }
    }

    public sealed class StepResultV0
    {
        public ObservationV0 Observation { get; }
        public IReadOnlyList<EnvironmentEventV0> Events { get; }
        public RewardFeaturesV0 RewardFeatures { get; }
        public bool IsTerminal { get; }
        public TerminationReasonV0 TerminationReason { get; }

        public StepResultV0(
            ObservationV0 observation,
            IReadOnlyList<EnvironmentEventV0> events,
            RewardFeaturesV0 rewardFeatures,
            bool isTerminal,
            TerminationReasonV0 terminationReason)
        {
            Observation = observation;
            Events = events;
            RewardFeatures = rewardFeatures;
            IsTerminal = isTerminal;
            TerminationReason = terminationReason;
        }
    }

    public interface IPicklebotEnvironmentV0
    {
        EpisodeStateV0 State { get; }
        EpisodeManifestV0 CurrentManifest { get; }
        ObservationV0 Reset(ResetRequestV0 request);
        StepResultV0 Step(PaddleActionV0 action);
    }
}

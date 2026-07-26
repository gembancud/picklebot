using System;
using UnityEngine;

namespace Picklebot.Core
{
    [CreateAssetMenu(
        fileName = "SimulationConfigV0",
        menuName = "Picklebot/Simulation Configuration V0")]
    public sealed class SimulationConfigV0 : ScriptableObject
    {
        public const string CanonicalVersion = "sim-config-v0";

        [Header("Ball")]
        [Min(0.001f)] public float BallMass = CourtGeometryV0.BallMass;
        [Min(0.001f)] public float BallDiameter = CourtGeometryV0.BallDiameter;
        [Min(0f)] public float BallLinearDamping = 0.05f;
        [Min(0f)] public float BallAngularDamping = 0.05f;
        [Range(0f, 1f)] public float BallBounciness = 0.78f;
        [Range(0f, 1f)] public float BallDynamicFriction = 0.22f;
        [Range(0f, 1f)] public float BallStaticFriction = 0.22f;

        [Header("Paddle")]
        public Vector3 PaddleSize = new(0.26f, 0.38f, 0.018f);
        [Min(0.1f)] public float PaddleMass = 0.25f;
        [Min(0.1f)] public float MaxPaddleLinearSpeed = 8f;
        [Min(0.1f)] public float MaxPaddleAngularSpeed = 18f;
        [Range(0f, 1f)] public float PaddleBounciness = 0.82f;
        [Range(0f, 1f)] public float PaddleDynamicFriction = 0.35f;
        [Range(0f, 1f)] public float PaddleStaticFriction = 0.35f;

        [Header("Court and net materials")]
        [Range(0f, 1f)] public float CourtBounciness = 0.72f;
        [Range(0f, 1f)] public float CourtDynamicFriction = 0.3f;
        [Range(0f, 1f)] public float CourtStaticFriction = 0.3f;
        [Range(0f, 1f)] public float NetBounciness = 0.2f;
        [Range(0f, 1f)] public float NetDynamicFriction = 0.4f;
        [Range(0f, 1f)] public float NetStaticFriction = 0.4f;

        [Header("Contacts and termination")]
        [Min(1)] public int ContactMinimumSeparationTicks = 2;
        [Range(0.25f, 20f)] public float DefaultMaximumEpisodeSeconds = 6f;
        [Min(0f)] public float PlayableHorizontalMargin = 2f;
        [Min(0f)] public float PlayableCeiling = 8f;
        [Min(0f)] public float PlayableFloorMargin = 1f;

        [Header("Regression")]
        [Min(0f)] public float ReplayPositionTolerance = 0.0005f;
        [Min(0f)] public float ReplayVelocityTolerance = 0.002f;

        public string ConfigurationHash => StableHashV0.Hex(CanonicalText());

        public void ValidateOrThrow()
        {
            if (!FiniteMath.IsFinite(BallMass) || BallMass <= 0f ||
                !FiniteMath.IsFinite(BallDiameter) || BallDiameter <= 0f ||
                !FiniteMath.IsFinite(BallLinearDamping) || BallLinearDamping < 0f ||
                !FiniteMath.IsFinite(BallAngularDamping) || BallAngularDamping < 0f ||
                !UnitInterval(BallBounciness) ||
                !UnitInterval(BallDynamicFriction) ||
                !UnitInterval(BallStaticFriction) ||
                !FiniteMath.IsFinite(PaddleSize) ||
                PaddleSize.x <= 0f || PaddleSize.y <= 0f || PaddleSize.z <= 0f ||
                !FiniteMath.IsFinite(PaddleMass) || PaddleMass <= 0f ||
                !FiniteMath.IsFinite(MaxPaddleLinearSpeed) || MaxPaddleLinearSpeed <= 0f ||
                !FiniteMath.IsFinite(MaxPaddleAngularSpeed) || MaxPaddleAngularSpeed <= 0f ||
                !UnitInterval(PaddleBounciness) ||
                !UnitInterval(PaddleDynamicFriction) ||
                !UnitInterval(PaddleStaticFriction) ||
                !UnitInterval(CourtBounciness) ||
                !UnitInterval(CourtDynamicFriction) ||
                !UnitInterval(CourtStaticFriction) ||
                !UnitInterval(NetBounciness) ||
                !UnitInterval(NetDynamicFriction) ||
                !UnitInterval(NetStaticFriction) ||
                ContactMinimumSeparationTicks < 1 ||
                !FiniteMath.IsFinite(DefaultMaximumEpisodeSeconds) ||
                DefaultMaximumEpisodeSeconds <= 0f ||
                DefaultMaximumEpisodeSeconds > 20f ||
                !FiniteMath.IsFinite(PlayableHorizontalMargin) ||
                PlayableHorizontalMargin < 0f ||
                !FiniteMath.IsFinite(PlayableCeiling) ||
                PlayableCeiling <= 0f ||
                !FiniteMath.IsFinite(PlayableFloorMargin) ||
                PlayableFloorMargin < 0f ||
                !FiniteMath.IsFinite(ReplayPositionTolerance) ||
                ReplayPositionTolerance < 0f ||
                !FiniteMath.IsFinite(ReplayVelocityTolerance) ||
                ReplayVelocityTolerance < 0f)
            {
                throw new InvalidOperationException("SimulationConfigV0 contains invalid values.");
            }
        }

        private static bool UnitInterval(float value)
        {
            return FiniteMath.IsFinite(value) && value >= 0f && value <= 1f;
        }

        public string CanonicalText()
        {
            return string.Join(
                "|",
                CanonicalVersion,
                StableHashV0.Float(BallMass),
                StableHashV0.Float(BallDiameter),
                StableHashV0.Float(BallLinearDamping),
                StableHashV0.Float(BallAngularDamping),
                StableHashV0.Float(BallBounciness),
                StableHashV0.Float(BallDynamicFriction),
                StableHashV0.Float(BallStaticFriction),
                StableHashV0.Vector(PaddleSize),
                StableHashV0.Float(PaddleMass),
                StableHashV0.Float(MaxPaddleLinearSpeed),
                StableHashV0.Float(MaxPaddleAngularSpeed),
                StableHashV0.Float(PaddleBounciness),
                StableHashV0.Float(PaddleDynamicFriction),
                StableHashV0.Float(PaddleStaticFriction),
                StableHashV0.Float(CourtBounciness),
                StableHashV0.Float(CourtDynamicFriction),
                StableHashV0.Float(CourtStaticFriction),
                StableHashV0.Float(NetBounciness),
                StableHashV0.Float(NetDynamicFriction),
                StableHashV0.Float(NetStaticFriction),
                ContactMinimumSeparationTicks,
                StableHashV0.Float(DefaultMaximumEpisodeSeconds),
                StableHashV0.Float(PlayableHorizontalMargin),
                StableHashV0.Float(PlayableCeiling),
                StableHashV0.Float(PlayableFloorMargin),
                StableHashV0.Float(ReplayPositionTolerance),
                StableHashV0.Float(ReplayVelocityTolerance));
        }
    }
}

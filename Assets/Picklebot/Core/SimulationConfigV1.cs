using System;
using UnityEngine;

namespace Picklebot.Core
{
    [CreateAssetMenu(
        fileName = "SimulationConfigV1",
        menuName = "Picklebot/Simulation Configuration V1")]
    public sealed class SimulationConfigV1 : ScriptableObject
    {
        public const string CanonicalVersion = "physics-calibration-v0";
        public const string EnvironmentVersion = "env-v1";
        public const string ReferenceProfile = "outdoor-40-hole-v0";
        public const string ProvisionalCalibrationState = "provisional-unfitted";

        [Header("Calibration identity")]
        public string CalibrationState = ProvisionalCalibrationState;

        [Header("Ball")]
        [Min(0.001f)] public float BallMass = CourtGeometryV1.BallMass;
        [Min(0.001f)] public float BallDiameter = CourtGeometryV1.BallDiameter;

        [Header("Environment")]
        public Vector3 Gravity = new(0f, -9.81f, 0f);
        [Min(0.001f)] public float AirDensity = 1.204f;
        public Vector3 WindVelocity = Vector3.zero;

        [Header("Aerodynamics")]
        [Min(0f)] public float DragCoefficient = 0.30f;
        [Min(0f)] public float LiftCoefficientSlope = 0.195f;
        [Min(0f)] public float MaximumLiftCoefficient = 0.25f;
        [Min(0.0001f)] public float MinimumAerodynamicSpeed = 0.01f;
        [Min(0f)] public float AngularDecayRate = 0.05f;

        [Header("Paddle")]
        public Vector3 PaddleOuterSize = CourtGeometryV1.PaddleOuterSize;
        public Vector3 PaddleFaceSize = CourtGeometryV1.PaddleFaceSize;
        [Min(0.1f)] public float MaxPaddleLinearSpeed = 8f;
        [Min(0.1f)] public float MaxPaddleAngularSpeed = 18f;

        [Header("Provisional contact surrogates")]
        [Range(0f, 1f)] public float GraniteRestitution = 0.635f;
        [Range(0f, 1f)] public float CourtRestitution = 0.64f;
        [Range(0f, 1f)] public float PaddleRestitution = 0.40f;
        [Range(0f, 1f)] public float NetRestitution = 0.10f;
        [Range(0f, 1f)] public float BallDynamicFriction = 0.10f;
        [Range(0f, 1f)] public float CourtDynamicFriction = 0.30f;
        [Range(0f, 1f)] public float PaddleDynamicFriction = 0.20f;
        [Range(0f, 1f)] public float NetDynamicFriction = 0.40f;

        [Header("Practical paddle spin-transfer surrogate")]
        [Range(0f, 1f)] public float PaddleTangentialVelocityTransfer = 0.12f;
        [Range(0f, 1f)] public float PaddleSpinTransfer = 0.35f;
        [Min(0f)] public float PaddleSpinTransferDeadband = 0.02f;
        [Min(0f)] public float MaximumPaddleContactTangentialVelocityDelta = 3f;
        [Min(0f)] public float MaximumPaddleContactSpinDelta = 35f;
        [Min(0f)] public float MaximumBallAngularSpeed = 80f;

        [Header("Contacts and termination")]
        [Min(1)] public int ContactMinimumSeparationTicks = 2;
        [Range(0.25f, 20f)] public float DefaultMaximumEpisodeSeconds = 6f;
        [Min(0f)] public float PlayableHorizontalMargin = 2f;
        [Min(0f)] public float PlayableCeiling = 8f;
        [Min(0f)] public float PlayableFloorMargin = 1f;

        [Header("Regression")]
        [Min(0f)] public float ReplayPositionTolerance = 0.0005f;
        [Min(0f)] public float ReplayVelocityTolerance = 0.002f;

        public AerodynamicParametersV1 AerodynamicParameters =>
            new(
                BallDiameter / 2f,
                AirDensity,
                DragCoefficient,
                LiftCoefficientSlope,
                MaximumLiftCoefficient,
                MinimumAerodynamicSpeed,
                WindVelocity,
                AngularDecayRate);

        public string ConfigurationHash => StableHashV0.Hex(CanonicalText());

        public void ValidateOrThrow()
        {
            if (string.IsNullOrWhiteSpace(CalibrationState) ||
                !FiniteMath.IsFinite(BallMass) || BallMass <= 0f ||
                !FiniteMath.IsFinite(BallDiameter) || BallDiameter <= 0f ||
                !FiniteMath.IsFinite(Gravity) ||
                !FiniteMath.IsFinite(PaddleOuterSize) ||
                PaddleOuterSize.x <= 0f ||
                PaddleOuterSize.y <= 0f ||
                PaddleOuterSize.z <= 0f ||
                !FiniteMath.IsFinite(PaddleFaceSize) ||
                PaddleFaceSize.x <= 0f ||
                PaddleFaceSize.y <= 0f ||
                PaddleFaceSize.z <= 0f ||
                PaddleFaceSize.x > PaddleOuterSize.x ||
                PaddleFaceSize.y >= PaddleOuterSize.y ||
                PaddleFaceSize.z > PaddleOuterSize.z ||
                !FiniteMath.IsFinite(MaxPaddleLinearSpeed) ||
                MaxPaddleLinearSpeed <= 0f ||
                !FiniteMath.IsFinite(MaxPaddleAngularSpeed) ||
                MaxPaddleAngularSpeed <= 0f ||
                !UnitInterval(GraniteRestitution) ||
                !UnitInterval(CourtRestitution) ||
                !UnitInterval(PaddleRestitution) ||
                !UnitInterval(NetRestitution) ||
                !UnitInterval(BallDynamicFriction) ||
                !UnitInterval(CourtDynamicFriction) ||
                !UnitInterval(PaddleDynamicFriction) ||
                !UnitInterval(NetDynamicFriction) ||
                !UnitInterval(PaddleTangentialVelocityTransfer) ||
                !UnitInterval(PaddleSpinTransfer) ||
                !FiniteMath.IsFinite(PaddleSpinTransferDeadband) ||
                PaddleSpinTransferDeadband < 0f ||
                !FiniteMath.IsFinite(
                    MaximumPaddleContactTangentialVelocityDelta) ||
                MaximumPaddleContactTangentialVelocityDelta <= 0f ||
                !FiniteMath.IsFinite(MaximumPaddleContactSpinDelta) ||
                MaximumPaddleContactSpinDelta <= 0f ||
                !FiniteMath.IsFinite(MaximumBallAngularSpeed) ||
                MaximumBallAngularSpeed <= 0f ||
                MaximumPaddleContactSpinDelta > MaximumBallAngularSpeed ||
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
                throw new InvalidOperationException(
                    "SimulationConfigV1 contains invalid values.");
            }

            AerodynamicParameters.ValidateOrThrow();
        }

        public string CanonicalText()
        {
            return string.Join(
                "|",
                CanonicalVersion,
                EnvironmentVersion,
                ReferenceProfile,
                CalibrationState,
                StableHashV0.Float(BallMass),
                StableHashV0.Float(BallDiameter),
                StableHashV0.Vector(Gravity),
                StableHashV0.Float(AirDensity),
                StableHashV0.Vector(WindVelocity),
                StableHashV0.Float(DragCoefficient),
                StableHashV0.Float(LiftCoefficientSlope),
                StableHashV0.Float(MaximumLiftCoefficient),
                StableHashV0.Float(MinimumAerodynamicSpeed),
                StableHashV0.Float(AngularDecayRate),
                StableHashV0.Vector(PaddleOuterSize),
                StableHashV0.Vector(PaddleFaceSize),
                StableHashV0.Float(MaxPaddleLinearSpeed),
                StableHashV0.Float(MaxPaddleAngularSpeed),
                StableHashV0.Float(GraniteRestitution),
                StableHashV0.Float(CourtRestitution),
                StableHashV0.Float(PaddleRestitution),
                StableHashV0.Float(NetRestitution),
                StableHashV0.Float(BallDynamicFriction),
                StableHashV0.Float(CourtDynamicFriction),
                StableHashV0.Float(PaddleDynamicFriction),
                StableHashV0.Float(NetDynamicFriction),
                StableHashV0.Float(PaddleTangentialVelocityTransfer),
                StableHashV0.Float(PaddleSpinTransfer),
                StableHashV0.Float(PaddleSpinTransferDeadband),
                StableHashV0.Float(
                    MaximumPaddleContactTangentialVelocityDelta),
                StableHashV0.Float(MaximumPaddleContactSpinDelta),
                StableHashV0.Float(MaximumBallAngularSpeed),
                ContactMinimumSeparationTicks,
                StableHashV0.Float(DefaultMaximumEpisodeSeconds),
                StableHashV0.Float(PlayableHorizontalMargin),
                StableHashV0.Float(PlayableCeiling),
                StableHashV0.Float(PlayableFloorMargin),
                StableHashV0.Float(ReplayPositionTolerance),
                StableHashV0.Float(ReplayVelocityTolerance));
        }

        private static bool UnitInterval(float value)
        {
            return FiniteMath.IsFinite(value) && value >= 0f && value <= 1f;
        }
    }
}

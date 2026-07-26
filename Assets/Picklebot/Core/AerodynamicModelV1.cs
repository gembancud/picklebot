using System;
using UnityEngine;

namespace Picklebot.Core
{
    [Serializable]
    public readonly struct AerodynamicParametersV1
    {
        public readonly float BallRadius;
        public readonly float AirDensity;
        public readonly float DragCoefficient;
        public readonly float LiftCoefficientSlope;
        public readonly float MaximumLiftCoefficient;
        public readonly float MinimumSpeed;
        public readonly Vector3 WindVelocity;
        public readonly float AngularDecayRate;

        public AerodynamicParametersV1(
            float ballRadius,
            float airDensity,
            float dragCoefficient,
            float liftCoefficientSlope,
            float maximumLiftCoefficient,
            float minimumSpeed,
            Vector3 windVelocity,
            float angularDecayRate)
        {
            BallRadius = ballRadius;
            AirDensity = airDensity;
            DragCoefficient = dragCoefficient;
            LiftCoefficientSlope = liftCoefficientSlope;
            MaximumLiftCoefficient = maximumLiftCoefficient;
            MinimumSpeed = minimumSpeed;
            WindVelocity = windVelocity;
            AngularDecayRate = angularDecayRate;
        }

        public void ValidateOrThrow()
        {
            if (!FiniteMath.IsFinite(BallRadius) || BallRadius <= 0f ||
                !FiniteMath.IsFinite(AirDensity) || AirDensity <= 0f ||
                !FiniteMath.IsFinite(DragCoefficient) || DragCoefficient < 0f ||
                !FiniteMath.IsFinite(LiftCoefficientSlope) ||
                LiftCoefficientSlope < 0f ||
                !FiniteMath.IsFinite(MaximumLiftCoefficient) ||
                MaximumLiftCoefficient < 0f ||
                !FiniteMath.IsFinite(MinimumSpeed) || MinimumSpeed <= 0f ||
                !FiniteMath.IsFinite(WindVelocity) ||
                !FiniteMath.IsFinite(AngularDecayRate) || AngularDecayRate < 0f)
            {
                throw new InvalidOperationException(
                    "AerodynamicParametersV1 contains invalid values.");
            }
        }
    }

    public readonly struct AerodynamicForcesV1
    {
        public readonly Vector3 RelativeAirVelocity;
        public readonly Vector3 DragForce;
        public readonly Vector3 LiftForce;
        public readonly float SpinParameter;
        public readonly float LiftCoefficient;

        public AerodynamicForcesV1(
            Vector3 relativeAirVelocity,
            Vector3 dragForce,
            Vector3 liftForce,
            float spinParameter,
            float liftCoefficient)
        {
            RelativeAirVelocity = relativeAirVelocity;
            DragForce = dragForce;
            LiftForce = liftForce;
            SpinParameter = spinParameter;
            LiftCoefficient = liftCoefficient;
        }

        public Vector3 TotalForce => DragForce + LiftForce;
    }

    public static class AerodynamicModelV1
    {
        public static AerodynamicForcesV1 Evaluate(
            Vector3 ballVelocity,
            Vector3 angularVelocity,
            AerodynamicParametersV1 parameters)
        {
            parameters.ValidateOrThrow();
            if (!FiniteMath.IsFinite(ballVelocity) ||
                !FiniteMath.IsFinite(angularVelocity))
            {
                throw new ArgumentException(
                    "Aerodynamic inputs must be finite.");
            }

            var relativeVelocity = ballVelocity - parameters.WindVelocity;
            var speed = relativeVelocity.magnitude;
            if (speed < parameters.MinimumSpeed)
            {
                return new AerodynamicForcesV1(
                    relativeVelocity,
                    Vector3.zero,
                    Vector3.zero,
                    0f,
                    0f);
            }

            var direction = relativeVelocity / speed;
            var area = Mathf.PI * parameters.BallRadius * parameters.BallRadius;
            var dynamicPressure = 0.5f * parameters.AirDensity * area * speed * speed;
            var drag = -dynamicPressure * parameters.DragCoefficient * direction;

            var perpendicularSpin =
                angularVelocity -
                (Vector3.Dot(angularVelocity, direction) * direction);
            var perpendicularSpinMagnitude = perpendicularSpin.magnitude;
            if (perpendicularSpinMagnitude < Mathf.Epsilon)
            {
                return new AerodynamicForcesV1(
                    relativeVelocity,
                    drag,
                    Vector3.zero,
                    0f,
                    0f);
            }

            var spinParameter =
                parameters.BallRadius * perpendicularSpinMagnitude / speed;
            var liftCoefficient = Mathf.Min(
                parameters.MaximumLiftCoefficient,
                parameters.LiftCoefficientSlope * spinParameter);
            var liftDirection =
                Vector3.Cross(perpendicularSpin, relativeVelocity).normalized;
            var lift = dynamicPressure * liftCoefficient * liftDirection;

            return new AerodynamicForcesV1(
                relativeVelocity,
                drag,
                lift,
                spinParameter,
                liftCoefficient);
        }

        public static float AngularVelocityMultiplier(
            float deltaTime,
            AerodynamicParametersV1 parameters)
        {
            parameters.ValidateOrThrow();
            if (!FiniteMath.IsFinite(deltaTime) || deltaTime < 0f)
            {
                throw new ArgumentOutOfRangeException(
                    nameof(deltaTime),
                    "Delta time must be finite and non-negative.");
            }

            return Mathf.Exp(-parameters.AngularDecayRate * deltaTime);
        }
    }
}

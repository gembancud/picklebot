using System;
using UnityEngine;

namespace Picklebot.Core
{
    public readonly struct PaddleSpinTransferResultV1
    {
        public readonly Vector3 LinearVelocity;
        public readonly Vector3 AngularVelocity;
        public readonly Vector3 TangentialSlipVelocity;
        public readonly Vector3 LinearVelocityDelta;
        public readonly Vector3 AngularVelocityDelta;
        public readonly bool WasApplied;
        public readonly bool WasClamped;

        public PaddleSpinTransferResultV1(
            Vector3 linearVelocity,
            Vector3 angularVelocity,
            Vector3 tangentialSlipVelocity,
            Vector3 linearVelocityDelta,
            Vector3 angularVelocityDelta,
            bool wasApplied,
            bool wasClamped)
        {
            LinearVelocity = linearVelocity;
            AngularVelocity = angularVelocity;
            TangentialSlipVelocity = tangentialSlipVelocity;
            LinearVelocityDelta = linearVelocityDelta;
            AngularVelocityDelta = angularVelocityDelta;
            WasApplied = wasApplied;
            WasClamped = wasClamped;
        }
    }

    /// <summary>
    /// Conservative deterministic surrogate for residual tangential velocity
    /// transfer at a kinematic paddle contact. The Unity solver remains
    /// authoritative for normal restitution.
    /// </summary>
    public static class PaddleSpinTransferV1
    {
        public static PaddleSpinTransferResultV1 Evaluate(
            Vector3 ballPosition,
            Vector3 ballLinearVelocity,
            Vector3 ballAngularVelocity,
            Vector3 paddlePointVelocity,
            Vector3 contactPoint,
            Vector3 contactNormal,
            SimulationConfigV1 configuration)
        {
            if (configuration == null)
            {
                throw new ArgumentNullException(nameof(configuration));
            }

            configuration.ValidateOrThrow();
            if (!FiniteMath.IsFinite(ballPosition) ||
                !FiniteMath.IsFinite(ballLinearVelocity) ||
                !FiniteMath.IsFinite(ballAngularVelocity) ||
                !FiniteMath.IsFinite(paddlePointVelocity) ||
                !FiniteMath.IsFinite(contactPoint) ||
                !FiniteMath.IsFinite(contactNormal))
            {
                throw new ArgumentException(
                    "Paddle spin-transfer inputs must be finite.");
            }

            var radius = configuration.BallDiameter / 2f;
            var contactOffset = contactPoint - ballPosition;
            var normal = contactOffset.sqrMagnitude > Mathf.Epsilon
                ? -contactOffset.normalized
                : contactNormal.normalized;
            if (normal.sqrMagnitude <= Mathf.Epsilon)
            {
                return Unchanged(
                    ballLinearVelocity,
                    ballAngularVelocity,
                    Vector3.zero);
            }

            contactOffset = -normal * radius;
            var ballSurfaceVelocity =
                ballLinearVelocity +
                Vector3.Cross(ballAngularVelocity, contactOffset);
            var relativeSurfaceVelocity =
                paddlePointVelocity - ballSurfaceVelocity;
            var tangentialSlip =
                relativeSurfaceVelocity -
                (Vector3.Dot(relativeSurfaceVelocity, normal) * normal);

            if (tangentialSlip.magnitude <=
                configuration.PaddleSpinTransferDeadband)
            {
                return Unchanged(
                    ballLinearVelocity,
                    ballAngularVelocity,
                    tangentialSlip);
            }

            var linearDelta =
                tangentialSlip *
                configuration.PaddleTangentialVelocityTransfer;
            var wasClamped = false;
            if (linearDelta.magnitude >
                configuration.MaximumPaddleContactTangentialVelocityDelta)
            {
                linearDelta = Vector3.ClampMagnitude(
                    linearDelta,
                    configuration.MaximumPaddleContactTangentialVelocityDelta);
                wasClamped = true;
            }

            var angularDelta =
                Vector3.Cross(contactOffset, tangentialSlip) /
                (radius * radius) *
                configuration.PaddleSpinTransfer;

            if (angularDelta.magnitude >
                configuration.MaximumPaddleContactSpinDelta)
            {
                angularDelta = Vector3.ClampMagnitude(
                    angularDelta,
                    configuration.MaximumPaddleContactSpinDelta);
                wasClamped = true;
            }

            var angularVelocity = ballAngularVelocity + angularDelta;
            if (angularVelocity.magnitude >
                configuration.MaximumBallAngularSpeed)
            {
                angularVelocity = Vector3.ClampMagnitude(
                    angularVelocity,
                    configuration.MaximumBallAngularSpeed);
                wasClamped = true;
            }

            return new PaddleSpinTransferResultV1(
                ballLinearVelocity + linearDelta,
                angularVelocity,
                tangentialSlip,
                linearDelta,
                angularVelocity - ballAngularVelocity,
                true,
                wasClamped);
        }

        private static PaddleSpinTransferResultV1 Unchanged(
            Vector3 linearVelocity,
            Vector3 angularVelocity,
            Vector3 tangentialSlip)
        {
            return new PaddleSpinTransferResultV1(
                linearVelocity,
                angularVelocity,
                tangentialSlip,
                Vector3.zero,
                Vector3.zero,
                false,
                false);
        }
    }
}

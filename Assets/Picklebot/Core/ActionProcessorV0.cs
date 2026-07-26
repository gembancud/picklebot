using UnityEngine;

namespace Picklebot.Core
{
    public readonly struct ProcessedPaddleActionV0
    {
        public readonly PaddleActionV0 Normalized;
        public readonly Vector3 LinearVelocityLocal;
        public readonly Vector3 AngularVelocityLocal;
        public readonly bool WasClamped;
        public readonly bool IsValid;

        public ProcessedPaddleActionV0(
            PaddleActionV0 normalized,
            Vector3 linearVelocityLocal,
            Vector3 angularVelocityLocal,
            bool wasClamped,
            bool isValid)
        {
            Normalized = normalized;
            LinearVelocityLocal = linearVelocityLocal;
            AngularVelocityLocal = angularVelocityLocal;
            WasClamped = wasClamped;
            IsValid = isValid;
        }
    }

    public static class ActionProcessorV0
    {
        public static ProcessedPaddleActionV0 Process(
            PaddleActionV0 action,
            SimulationConfigV0 configuration)
        {
            if (!FiniteMath.IsFinite(action.LinearVelocityLocal) ||
                !FiniteMath.IsFinite(action.AngularVelocityLocal))
            {
                return new ProcessedPaddleActionV0(
                    PaddleActionV0.Zero,
                    Vector3.zero,
                    Vector3.zero,
                    false,
                    false);
            }

            var clampedLinear = FiniteMath.ClampUnitCube(action.LinearVelocityLocal);
            var clampedAngular = FiniteMath.ClampUnitCube(action.AngularVelocityLocal);
            var clamped = clampedLinear != action.LinearVelocityLocal ||
                          clampedAngular != action.AngularVelocityLocal;

            return new ProcessedPaddleActionV0(
                new PaddleActionV0(clampedLinear, clampedAngular),
                clampedLinear * configuration.MaxPaddleLinearSpeed,
                clampedAngular * configuration.MaxPaddleAngularSpeed,
                clamped,
                true);
        }
    }
}

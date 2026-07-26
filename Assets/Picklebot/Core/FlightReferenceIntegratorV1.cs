using System;
using UnityEngine;

namespace Picklebot.Core
{
    public readonly struct FlightStateV1
    {
        public readonly Vector3 Position;
        public readonly Vector3 Velocity;
        public readonly Vector3 AngularVelocity;

        public FlightStateV1(
            Vector3 position,
            Vector3 velocity,
            Vector3 angularVelocity)
        {
            Position = position;
            Velocity = velocity;
            AngularVelocity = angularVelocity;
        }
    }

    public static class FlightReferenceIntegratorV1
    {
        private readonly struct Derivative
        {
            public readonly Vector3 Position;
            public readonly Vector3 Velocity;
            public readonly Vector3 AngularVelocity;

            public Derivative(
                Vector3 position,
                Vector3 velocity,
                Vector3 angularVelocity)
            {
                Position = position;
                Velocity = velocity;
                AngularVelocity = angularVelocity;
            }
        }

        public static FlightStateV1 Integrate(
            FlightStateV1 initial,
            float duration,
            float maximumStep,
            float ballMass,
            Vector3 gravity,
            AerodynamicParametersV1 aerodynamics)
        {
            if (!FiniteMath.IsFinite(initial.Position) ||
                !FiniteMath.IsFinite(initial.Velocity) ||
                !FiniteMath.IsFinite(initial.AngularVelocity) ||
                !FiniteMath.IsFinite(duration) || duration < 0f ||
                !FiniteMath.IsFinite(maximumStep) || maximumStep <= 0f ||
                !FiniteMath.IsFinite(ballMass) || ballMass <= 0f ||
                !FiniteMath.IsFinite(gravity))
            {
                throw new ArgumentException(
                    "Reference integration inputs must be finite and valid.");
            }

            aerodynamics.ValidateOrThrow();
            var state = initial;
            var elapsed = 0f;
            while (elapsed < duration)
            {
                var step = Mathf.Min(maximumStep, duration - elapsed);
                state = StepRk4(
                    state,
                    step,
                    ballMass,
                    gravity,
                    aerodynamics);
                elapsed += step;
            }

            return state;
        }

        private static FlightStateV1 StepRk4(
            FlightStateV1 state,
            float step,
            float ballMass,
            Vector3 gravity,
            AerodynamicParametersV1 aerodynamics)
        {
            var k1 = Evaluate(state, ballMass, gravity, aerodynamics);
            var k2 = Evaluate(
                Add(state, k1, step * 0.5f),
                ballMass,
                gravity,
                aerodynamics);
            var k3 = Evaluate(
                Add(state, k2, step * 0.5f),
                ballMass,
                gravity,
                aerodynamics);
            var k4 = Evaluate(
                Add(state, k3, step),
                ballMass,
                gravity,
                aerodynamics);

            var position =
                state.Position +
                ((step / 6f) *
                 (k1.Position +
                  (2f * k2.Position) +
                  (2f * k3.Position) +
                  k4.Position));
            var velocity =
                state.Velocity +
                ((step / 6f) *
                 (k1.Velocity +
                  (2f * k2.Velocity) +
                  (2f * k3.Velocity) +
                  k4.Velocity));
            var angularVelocity =
                state.AngularVelocity +
                ((step / 6f) *
                 (k1.AngularVelocity +
                  (2f * k2.AngularVelocity) +
                  (2f * k3.AngularVelocity) +
                  k4.AngularVelocity));
            return new FlightStateV1(position, velocity, angularVelocity);
        }

        private static Derivative Evaluate(
            FlightStateV1 state,
            float ballMass,
            Vector3 gravity,
            AerodynamicParametersV1 aerodynamics)
        {
            var forces = AerodynamicModelV1.Evaluate(
                state.Velocity,
                state.AngularVelocity,
                aerodynamics);
            return new Derivative(
                state.Velocity,
                gravity + (forces.TotalForce / ballMass),
                -aerodynamics.AngularDecayRate * state.AngularVelocity);
        }

        private static FlightStateV1 Add(
            FlightStateV1 state,
            Derivative derivative,
            float scale)
        {
            return new FlightStateV1(
                state.Position + (derivative.Position * scale),
                state.Velocity + (derivative.Velocity * scale),
                state.AngularVelocity +
                (derivative.AngularVelocity * scale));
        }
    }
}

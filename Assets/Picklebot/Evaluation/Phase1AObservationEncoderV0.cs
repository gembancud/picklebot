using System;
using Picklebot.Core;
using UnityEngine;

namespace Picklebot.Evaluation
{
    public static class Phase1AObservationEncoderV0
    {
        public const int Size = 37;

        public static void Encode(
            ObservationV0 observation,
            float[] destination,
            int offset = 0)
        {
            if (!ObservationValidatorV0.IsFinite(observation))
            {
                throw new ArgumentException(
                    "Observation must be finite.",
                    nameof(observation));
            }

            if (destination == null)
            {
                throw new ArgumentNullException(nameof(destination));
            }

            if (offset < 0 || destination.Length - offset < Size)
            {
                throw new ArgumentOutOfRangeException(nameof(offset));
            }

            var index = offset;
            WriteVector(
                destination,
                ref index,
                observation.Ball.PositionWorld,
                CourtGeometryV0.HalfWidth + 2f,
                8f,
                CourtGeometryV0.HalfLength + 2f);
            WriteVector(
                destination,
                ref index,
                observation.Ball.LinearVelocityWorld,
                Phase1AProtocolV0.MaximumBallLinearSpeed);
            WriteVector(
                destination,
                ref index,
                observation.Ball.AngularVelocityWorld,
                Phase1AProtocolV0.MaximumBallAngularSpeed);
            WriteVector(
                destination,
                ref index,
                observation.Paddle.PositionWorld,
                CourtGeometryV0.HalfWidth + 2f,
                8f,
                CourtGeometryV0.HalfLength + 2f);

            var rotation = FiniteMath.Canonicalize(observation.Paddle.RotationWorld);
            destination[index++] = Mathf.Clamp(rotation.x, -1f, 1f);
            destination[index++] = Mathf.Clamp(rotation.y, -1f, 1f);
            destination[index++] = Mathf.Clamp(rotation.z, -1f, 1f);
            destination[index++] = Mathf.Clamp(rotation.w, -1f, 1f);

            WriteVector(
                destination,
                ref index,
                observation.Paddle.LinearVelocityWorld,
                Phase1AProtocolV0.MaximumPaddleLinearSpeed);
            WriteVector(
                destination,
                ref index,
                observation.Paddle.AngularVelocityWorld,
                Phase1AProtocolV0.MaximumPaddleAngularSpeed);
            WriteVector(
                destination,
                ref index,
                observation.BallPositionFromPaddle,
                CourtGeometryV0.HalfWidth + 2f,
                8f,
                CourtGeometryV0.CourtLength + 4f);
            WriteVector(
                destination,
                ref index,
                observation.BallVelocityFromPaddle,
                Phase1AProtocolV0.MaximumBallLinearSpeed +
                Phase1AProtocolV0.MaximumPaddleLinearSpeed);

            destination[index++] = Mathf.Clamp01(
                observation.ElapsedTime / Phase1AProtocolV0.MaximumEpisodeSeconds);

            for (var touch = 0; touch < 6; touch++)
            {
                destination[index++] =
                    (int)observation.Episode.LastTouch == touch ? 1f : 0f;
            }

            destination[index++] = Mathf.Clamp01(
                observation.Episode.ControlledPaddleContacts / 4f);
            destination[index] = Mathf.Clamp01(
                observation.Episode.BallFloorContacts / 4f);
        }

        private static void WriteVector(
            float[] destination,
            ref int index,
            Vector3 value,
            float scale)
        {
            WriteVector(destination, ref index, value, scale, scale, scale);
        }

        private static void WriteVector(
            float[] destination,
            ref int index,
            Vector3 value,
            float xScale,
            float yScale,
            float zScale)
        {
            destination[index++] = NormalizeSigned(value.x, xScale);
            destination[index++] = NormalizeSigned(value.y, yScale);
            destination[index++] = NormalizeSigned(value.z, zScale);
        }

        private static float NormalizeSigned(float value, float scale)
        {
            return Mathf.Clamp(value / scale, -1f, 1f);
        }
    }
}

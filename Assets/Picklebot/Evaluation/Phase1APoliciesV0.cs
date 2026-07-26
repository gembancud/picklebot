using System;
using Picklebot.Core;
using UnityEngine;

namespace Picklebot.Evaluation
{
    public interface IPaddlePolicyV0
    {
        string PolicyId { get; }
        void Reset(EpisodeManifestV0 manifest);
        PaddleActionV0 Decide(ObservationV0 observation);
    }

    public sealed class ZeroPolicyV0 : IPaddlePolicyV0
    {
        public string PolicyId => "baseline/zero-v0";

        public void Reset(EpisodeManifestV0 manifest)
        {
        }

        public PaddleActionV0 Decide(ObservationV0 observation)
        {
            return PaddleActionV0.Zero;
        }
    }

    public sealed class InterceptHeuristicPolicyV0 : IPaddlePolicyV0
    {
        private const float PositionGain = 7f;
        private const float MaximumPredictionSeconds = 1.5f;
        private const float MinimumPredictionSeconds = 0.05f;
        private const float FloorLeadSeconds = 0.10f;
        private const float NearestNetPositionZ = -0.15f;
        private const float MinimumPaddleHeight = 0.10f;
        private const float MaximumPaddleHeight = 2.2f;
        private const float ContactStrokeDistance = 0.55f;
        private const float ContactStrokeSpeed = 4f;
        private const float ReturnPitchDegrees = -25f;
        private const float RotationGain = 6f;

        private Vector3 homePosition;
        private bool isReady;

        public string PolicyId => "baseline/intercept-v0";

        public void Reset(EpisodeManifestV0 manifest)
        {
            if (manifest == null)
            {
                throw new ArgumentNullException(nameof(manifest));
            }

            homePosition = manifest.Parameters.PaddlePosition;
            isReady = true;
        }

        public PaddleActionV0 Decide(ObservationV0 observation)
        {
            if (!isReady)
            {
                throw new InvalidOperationException(
                    "Reset must be called before Decide.");
            }

            if (!ObservationValidatorV0.IsFinite(observation))
            {
                return new PaddleActionV0(
                    new Vector3(float.NaN, 0f, 0f),
                    Vector3.zero);
            }

            var target = homePosition;
            var ballVelocity = observation.Ball.LinearVelocityWorld;
            var ballPosition = observation.Ball.PositionWorld;
            if (observation.Episode.LastTouch != LastTouchV0.ControlledPaddle &&
                ballVelocity.z < -0.0001f)
            {
                var homePlaneSeconds =
                    (homePosition.z - ballPosition.z) / ballVelocity.z;
                var floorSeconds = TimeToFloor(
                    ballPosition.y,
                    ballVelocity.y);
                var predictionSeconds = Mathf.Min(
                    homePlaneSeconds,
                    Mathf.Max(
                        MinimumPredictionSeconds,
                        floorSeconds - FloorLeadSeconds));
                if (predictionSeconds >= MinimumPredictionSeconds &&
                    predictionSeconds <= MaximumPredictionSeconds)
                {
                    target.z = Mathf.Clamp(
                        ballPosition.z + (ballVelocity.z * predictionSeconds),
                        homePosition.z,
                        NearestNetPositionZ);
                    predictionSeconds =
                        (target.z - ballPosition.z) / ballVelocity.z;
                    target.x =
                        ballPosition.x + (ballVelocity.x * predictionSeconds);
                    target.y = Mathf.Clamp(
                        ballPosition.y +
                        (ballVelocity.y * predictionSeconds) +
                        (0.5f * Phase1AProtocolV0.GravityY *
                         predictionSeconds * predictionSeconds),
                        MinimumPaddleHeight,
                        MaximumPaddleHeight);
                }
            }

            var desiredVelocityWorld =
                (target - observation.Paddle.PositionWorld) * PositionGain;
            if (observation.Episode.LastTouch != LastTouchV0.ControlledPaddle &&
                ballVelocity.z < -0.0001f &&
                Mathf.Abs(
                    ballPosition.z -
                    observation.Paddle.PositionWorld.z) <= ContactStrokeDistance)
            {
                desiredVelocityWorld.z += ContactStrokeSpeed;
            }

            var desiredVelocityLocal =
                Quaternion.Inverse(observation.Paddle.RotationWorld) *
                desiredVelocityWorld;
            var normalizedLinear = FiniteMath.ClampUnitCube(
                desiredVelocityLocal /
                Phase1AProtocolV0.MaximumPaddleLinearSpeed);

            var targetPitch =
                observation.Episode.LastTouch == LastTouchV0.ControlledPaddle
                    ? 0f
                    : ReturnPitchDegrees;
            var pitchError = Mathf.DeltaAngle(
                observation.Paddle.RotationWorld.eulerAngles.x,
                targetPitch);
            var normalizedAngular = new Vector3(
                Mathf.Clamp(
                    pitchError * Mathf.Deg2Rad * RotationGain /
                    Phase1AProtocolV0.MaximumPaddleAngularSpeed,
                    -1f,
                    1f),
                0f,
                0f);

            return new PaddleActionV0(normalizedLinear, normalizedAngular);
        }

        private static float TimeToFloor(float height, float verticalVelocity)
        {
            var gravityMagnitude = -Phase1AProtocolV0.GravityY;
            var discriminant =
                (verticalVelocity * verticalVelocity) +
                (2f * gravityMagnitude * Mathf.Max(0f, height));
            return (
                verticalVelocity + Mathf.Sqrt(discriminant)) /
                gravityMagnitude;
        }
    }
}

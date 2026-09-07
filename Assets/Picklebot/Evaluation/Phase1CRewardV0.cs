using System;
using Picklebot.Core;
using UnityEngine;

namespace Picklebot.Evaluation
{
    public readonly struct Phase1CRewardStateV0
    {
        public readonly float PreviousElapsedTime;
        public readonly float PreviousInterceptDistance;
        public readonly float CurrentInterceptDistance;
        public readonly bool HasControlledPaddleContact;
        public readonly PaddleActionV0 PreviousAction;
        public readonly PaddleActionV0 CurrentAction;

        public Phase1CRewardStateV0(
            float previousElapsedTime,
            float previousInterceptDistance,
            float currentInterceptDistance,
            bool hasControlledPaddleContact,
            PaddleActionV0 previousAction,
            PaddleActionV0 currentAction)
        {
            PreviousElapsedTime = previousElapsedTime;
            PreviousInterceptDistance = previousInterceptDistance;
            CurrentInterceptDistance = currentInterceptDistance;
            HasControlledPaddleContact = hasControlledPaddleContact;
            PreviousAction = previousAction;
            CurrentAction = currentAction;
        }
    }

    public readonly struct Phase1CRewardBreakdownV0
    {
        public readonly float FeatureReward;
        public readonly float InterceptionProgressReward;
        public readonly float ActionChangeReward;

        public Phase1CRewardBreakdownV0(
            float featureReward,
            float interceptionProgressReward,
            float actionChangeReward)
        {
            FeatureReward = featureReward;
            InterceptionProgressReward = interceptionProgressReward;
            ActionChangeReward = actionChangeReward;
        }

        public float Total =>
            FeatureReward + InterceptionProgressReward + ActionChangeReward;
    }

    public static class Phase1CRewardV0
    {
        public const string Version = "phase1c-reward-v0";
        public const float InterceptionProgressScale = 0.05f;
        public const float MaximumInterceptionProgressPerStep = 0.25f;
        public const float MaximumActionChangePenalty = 0.001f;

        private static readonly float MaximumSixAxisActionDistance =
            Mathf.Sqrt(24f);

        public static readonly Phase1ARewardMappingV0 BaseMapping =
            new(
                paddleContact: 0.25f,
                farCourtLanding: 1f,
                nearCourtLanding: -0.25f,
                outLanding: -0.5f,
                netContact: -0.05f,
                targetDistance: -0.05f,
                actionClamp: -0.02f,
                invalidState: -1f,
                elapsedSecond: -0.002f);

        public static Phase1CRewardBreakdownV0 Evaluate(
            RewardFeaturesV0 features,
            Phase1CRewardStateV0 state)
        {
            ValidateOrThrow(state);

            var featureReward = BaseMapping.MapStep(
                features,
                state.PreviousElapsedTime);
            var interceptionProgressReward = state.HasControlledPaddleContact
                ? 0f
                : Mathf.Clamp(
                      state.PreviousInterceptDistance -
                      state.CurrentInterceptDistance,
                      -MaximumInterceptionProgressPerStep,
                      MaximumInterceptionProgressPerStep) *
                  InterceptionProgressScale;
            var normalizedActionChange = Mathf.Clamp01(
                ActionDistance(state.PreviousAction, state.CurrentAction) /
                MaximumSixAxisActionDistance);
            var actionChangeReward =
                -normalizedActionChange * MaximumActionChangePenalty;

            var result = new Phase1CRewardBreakdownV0(
                featureReward,
                interceptionProgressReward,
                actionChangeReward);
            if (!FiniteMath.IsFinite(result.Total))
            {
                throw new InvalidOperationException(
                    "Phase 1C reward must remain finite.");
            }

            return result;
        }

        public static string CanonicalText()
        {
            return string.Join(
                "|",
                Version,
                StableHashV0.Float(BaseMapping.PaddleContact),
                StableHashV0.Float(BaseMapping.FarCourtLanding),
                StableHashV0.Float(BaseMapping.NearCourtLanding),
                StableHashV0.Float(BaseMapping.OutLanding),
                StableHashV0.Float(BaseMapping.NetContact),
                StableHashV0.Float(BaseMapping.TargetDistance),
                StableHashV0.Float(BaseMapping.ActionClamp),
                StableHashV0.Float(BaseMapping.InvalidState),
                StableHashV0.Float(BaseMapping.ElapsedSecond),
                StableHashV0.Float(InterceptionProgressScale),
                StableHashV0.Float(MaximumInterceptionProgressPerStep),
                StableHashV0.Float(MaximumActionChangePenalty));
        }

        public static string Hash => StableHashV0.Hex(CanonicalText());

        private static float ActionDistance(
            PaddleActionV0 previous,
            PaddleActionV0 current)
        {
            var linear = current.LinearVelocityLocal -
                         previous.LinearVelocityLocal;
            var angular = current.AngularVelocityLocal -
                          previous.AngularVelocityLocal;
            return Mathf.Sqrt(linear.sqrMagnitude + angular.sqrMagnitude);
        }

        private static void ValidateOrThrow(Phase1CRewardStateV0 state)
        {
            if (!FiniteMath.IsFinite(state.PreviousElapsedTime) ||
                !FiniteMath.IsFinite(state.PreviousInterceptDistance) ||
                !FiniteMath.IsFinite(state.CurrentInterceptDistance) ||
                state.PreviousElapsedTime < 0f ||
                state.PreviousInterceptDistance < 0f ||
                state.CurrentInterceptDistance < 0f ||
                !FiniteMath.IsFinite(state.PreviousAction.LinearVelocityLocal) ||
                !FiniteMath.IsFinite(state.PreviousAction.AngularVelocityLocal) ||
                !FiniteMath.IsFinite(state.CurrentAction.LinearVelocityLocal) ||
                !FiniteMath.IsFinite(state.CurrentAction.AngularVelocityLocal))
            {
                throw new ArgumentException(
                    "Phase 1C reward state must be finite and non-negative.");
            }
        }
    }
}

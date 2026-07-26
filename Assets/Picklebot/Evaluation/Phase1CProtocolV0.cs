using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Picklebot.Core;

namespace Picklebot.Evaluation
{
    public static class Phase1CProtocolV0
    {
        public const string Version = "phase1c-protocol-v0";
        public const string EnvironmentDependency = "env-v1";
        public const string ObservationVersion = "phase1c-observation-v0";
        public const string ActionVersion = "paddle-action-v0";
        public const string RewardVersion = "phase1c-reward-v0";
        public const string UnityTrainerPackage = "com.unity.ml-agents@4.0.0";
        public const string PythonTrainerPackage = "mlagents==1.1.0";
        public const int MaximumActionSteps = 1500;
        public const float TargetRadius = 1f;
        public const float MaximumBallLinearSpeed = 25f;
        public const float MaximumBallAngularSpeed = 80f;
        public const float MaximumPaddleLinearSpeed = 8f;
        public const float MaximumPaddleAngularSpeed = 18f;
        public const float MaximumEpisodeSeconds = 6f;

        public static readonly SeedRangeV0 TrainingSeeds =
            new(Phase1ASeedPartitionV0.Training, 5000000UL, 50000);

        public static readonly SeedRangeV0 ValidationSeeds =
            new(Phase1ASeedPartitionV0.Validation, 6000000UL, 1000);

        // Metadata only until a checkpoint and experiment configuration freeze.
        // This protocol deliberately exposes no request builder for this range.
        public static readonly SeedRangeV0 FinalEvaluationSeeds =
            new(Phase1ASeedPartitionV0.HeldOutEvaluation, 7000000UL, 1000);

        public static readonly Phase1ARewardMappingV0 RewardMapping =
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

        private static readonly CurriculumStageV0[] StableStages =
        {
            new(
                "p1c/contact-easy",
                ScenarioCatalogV0.ContactFrontOn,
                "easy",
                "Acquire calibrated rounded-face paddle contact.",
                TargetRadius,
                0.90f,
                0f),
            new(
                "p1c/return-easy",
                ScenarioCatalogV0.LaunchRally,
                "easy",
                "Return the calibrated outdoor ball legally over the net.",
                TargetRadius,
                0.70f,
                3f),
            new(
                "p1c/place-default",
                ScenarioCatalogV0.LaunchRally,
                "default",
                "Place calibrated legal returns near the target.",
                TargetRadius,
                0.55f,
                2f),
            new(
                "p1c/robust-hard",
                ScenarioCatalogV0.LaunchRally,
                "hard",
                "Preserve return quality through the env-v1 speed and spin envelope.",
                TargetRadius,
                0.45f,
                1.6f)
        };

        private static readonly IReadOnlyList<CurriculumStageV0> ReadOnlyStages =
            Array.AsReadOnly(StableStages);

        public static IReadOnlyList<CurriculumStageV0> CurriculumStages =>
            ReadOnlyStages;

        public static string RewardMappingHash => StableHashV0.Hex(
            RewardVersion + "|" + RewardMapping.CanonicalText());

        public static ResetRequestV0 TrainingRequest(
            int stageIndex,
            int seedIndex)
        {
            return CurriculumRequest(
                stageIndex,
                TrainingSeeds,
                seedIndex);
        }

        public static ResetRequestV0 ValidationRequest(
            int stageIndex,
            int seedIndex)
        {
            return CurriculumRequest(
                stageIndex,
                ValidationSeeds,
                seedIndex);
        }

        public static string CanonicalText()
        {
            return string.Join(
                "\n",
                Version,
                EnvironmentDependency,
                ObservationVersion,
                ActionVersion,
                RewardVersion,
                UnityTrainerPackage,
                PythonTrainerPackage,
                MaximumActionSteps.ToString(CultureInfo.InvariantCulture),
                StableHashV0.Float(TargetRadius),
                StableHashV0.Float(MaximumBallLinearSpeed),
                StableHashV0.Float(MaximumBallAngularSpeed),
                StableHashV0.Float(MaximumPaddleLinearSpeed),
                StableHashV0.Float(MaximumPaddleAngularSpeed),
                StableHashV0.Float(MaximumEpisodeSeconds),
                TrainingSeeds.CanonicalText(),
                ValidationSeeds.CanonicalText(),
                FinalEvaluationSeeds.CanonicalText(),
                RewardMappingHash,
                string.Join(
                    "\n",
                    StableStages.Select(value => value.CanonicalText())));
        }

        public static string Hash => StableHashV0.Hex(CanonicalText());

        public static void ValidateOrThrow()
        {
            if (EnvironmentDependency != SimulationConfigV1.EnvironmentVersion)
            {
                throw new InvalidOperationException(
                    "Phase 1C must depend on env-v1.");
            }

            if (TrainingSeeds.Overlaps(ValidationSeeds) ||
                TrainingSeeds.Overlaps(FinalEvaluationSeeds) ||
                ValidationSeeds.Overlaps(FinalEvaluationSeeds) ||
                TrainingSeeds.Overlaps(Phase1AProtocolV0.TrainingSeeds) ||
                TrainingSeeds.Overlaps(Phase1AProtocolV0.ValidationSeeds) ||
                TrainingSeeds.Overlaps(Phase1AProtocolV0.HeldOutEvaluationSeeds) ||
                ValidationSeeds.Overlaps(Phase1AProtocolV0.TrainingSeeds) ||
                ValidationSeeds.Overlaps(Phase1AProtocolV0.ValidationSeeds) ||
                ValidationSeeds.Overlaps(Phase1AProtocolV0.HeldOutEvaluationSeeds) ||
                FinalEvaluationSeeds.Overlaps(Phase1AProtocolV0.TrainingSeeds) ||
                FinalEvaluationSeeds.Overlaps(Phase1AProtocolV0.ValidationSeeds) ||
                FinalEvaluationSeeds.Overlaps(
                    Phase1AProtocolV0.HeldOutEvaluationSeeds))
            {
                throw new InvalidOperationException(
                    "Phase 1C seed partitions overlap reserved ranges.");
            }

            if (MaximumBallAngularSpeed < 62.831853f)
            {
                throw new InvalidOperationException(
                    "Phase 1C spin scale must contain the 10 rps calibration point.");
            }

            if (StableStages.Select(value => value.Id).Distinct().Count() !=
                StableStages.Length)
            {
                throw new InvalidOperationException(
                    "Phase 1C stage IDs must be unique.");
            }
        }

        private static ResetRequestV0 CurriculumRequest(
            int stageIndex,
            SeedRangeV0 seeds,
            int seedIndex)
        {
            if (stageIndex < 0 || stageIndex >= StableStages.Length)
            {
                throw new ArgumentOutOfRangeException(nameof(stageIndex));
            }

            var stage = StableStages[stageIndex];
            return new ResetRequestV0(
                seeds.At(seedIndex),
                stage.ScenarioId,
                stage.Difficulty,
                new[]
                {
                    new ResetOverrideV0(
                        "ball.velocity.y",
                        stage.InboundVerticalVelocity)
                });
        }
    }
}

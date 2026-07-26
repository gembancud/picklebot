using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Picklebot.Core;
using UnityEngine;

namespace Picklebot.Evaluation
{
    public enum Phase1ASeedPartitionV0
    {
        Training,
        Validation,
        HeldOutEvaluation
    }

    public readonly struct SeedRangeV0
    {
        public readonly Phase1ASeedPartitionV0 Partition;
        public readonly ulong First;
        public readonly int Count;

        public SeedRangeV0(
            Phase1ASeedPartitionV0 partition,
            ulong first,
            int count)
        {
            if (count <= 0)
            {
                throw new ArgumentOutOfRangeException(nameof(count));
            }

            Partition = partition;
            First = first;
            Count = count;
        }

        public ulong Last => First + (ulong)Count - 1UL;

        public ulong At(int index)
        {
            if (index < 0 || index >= Count)
            {
                throw new ArgumentOutOfRangeException(nameof(index));
            }

            return First + (ulong)index;
        }

        public bool Contains(ulong seed)
        {
            return seed >= First && seed <= Last;
        }

        public bool Overlaps(SeedRangeV0 other)
        {
            return First <= other.Last && other.First <= Last;
        }

        public string CanonicalText()
        {
            return $"{Partition}|{First}|{Count}|{Last}";
        }
    }

    public readonly struct CurriculumStageV0
    {
        public readonly string Id;
        public readonly string ScenarioId;
        public readonly string Difficulty;
        public readonly string LearningGoal;
        public readonly float TargetRadius;
        public readonly float PromotionThreshold;
        public readonly float InboundVerticalVelocity;

        public CurriculumStageV0(
            string id,
            string scenarioId,
            string difficulty,
            string learningGoal,
            float targetRadius,
            float promotionThreshold,
            float inboundVerticalVelocity)
        {
            Id = id ?? throw new ArgumentNullException(nameof(id));
            ScenarioId = scenarioId ?? throw new ArgumentNullException(nameof(scenarioId));
            Difficulty = difficulty ?? throw new ArgumentNullException(nameof(difficulty));
            LearningGoal = learningGoal ?? throw new ArgumentNullException(nameof(learningGoal));
            TargetRadius = targetRadius;
            PromotionThreshold = promotionThreshold;
            InboundVerticalVelocity = inboundVerticalVelocity;
        }

        public string CanonicalText()
        {
            return string.Join(
                "|",
                Id,
                ScenarioId,
                Difficulty,
                LearningGoal,
                StableHashV0.Float(TargetRadius),
                StableHashV0.Float(PromotionThreshold),
                StableHashV0.Float(InboundVerticalVelocity));
        }
    }

    public readonly struct Phase1ARewardMappingV0
    {
        public readonly float PaddleContact;
        public readonly float FarCourtLanding;
        public readonly float NearCourtLanding;
        public readonly float OutLanding;
        public readonly float NetContact;
        public readonly float TargetDistance;
        public readonly float ActionClamp;
        public readonly float InvalidState;
        public readonly float ElapsedSecond;

        public Phase1ARewardMappingV0(
            float paddleContact,
            float farCourtLanding,
            float nearCourtLanding,
            float outLanding,
            float netContact,
            float targetDistance,
            float actionClamp,
            float invalidState,
            float elapsedSecond)
        {
            PaddleContact = paddleContact;
            FarCourtLanding = farCourtLanding;
            NearCourtLanding = nearCourtLanding;
            OutLanding = outLanding;
            NetContact = netContact;
            TargetDistance = targetDistance;
            ActionClamp = actionClamp;
            InvalidState = invalidState;
            ElapsedSecond = elapsedSecond;
        }

        public float MapStep(
            RewardFeaturesV0 features,
            float previousElapsedTime)
        {
            var elapsedDelta = Mathf.Max(0f, features.ElapsedTime - previousElapsedTime);
            return
                (features.PaddleContactCount * PaddleContact) +
                (features.FarCourtLanding * FarCourtLanding) +
                (features.NearCourtLanding * NearCourtLanding) +
                (features.OutLanding * OutLanding) +
                (features.NetContactCount * NetContact) +
                (features.TargetDistanceAtLanding * TargetDistance) +
                (features.ActionClampCount * ActionClamp) +
                (features.InvalidState * InvalidState) +
                (elapsedDelta * ElapsedSecond);
        }

        public string CanonicalText()
        {
            return string.Join(
                "|",
                "phase1a-reward-v0",
                StableHashV0.Float(PaddleContact),
                StableHashV0.Float(FarCourtLanding),
                StableHashV0.Float(NearCourtLanding),
                StableHashV0.Float(OutLanding),
                StableHashV0.Float(NetContact),
                StableHashV0.Float(TargetDistance),
                StableHashV0.Float(ActionClamp),
                StableHashV0.Float(InvalidState),
                StableHashV0.Float(ElapsedSecond));
        }

        public string Hash => StableHashV0.Hex(CanonicalText());
    }

    public static class Phase1AProtocolV0
    {
        public const string Version = "phase1a-protocol-v0";
        public const string ObservationVersion = "phase1a-observation-v0";
        public const string ActionVersion = "paddle-action-v0";
        public const string TrainerSelection = "com.unity.ml-agents@4.0.3";
        public const int MaximumActionSteps = 1500;
        public const int BaselineEpisodeCount = 1000;
        public const float TargetRadius = 1f;
        public const float MaximumBallLinearSpeed = 25f;
        public const float MaximumBallAngularSpeed = 50f;
        public const float MaximumPaddleLinearSpeed = 8f;
        public const float MaximumPaddleAngularSpeed = 18f;
        public const float MaximumEpisodeSeconds = 6f;
        public const float GravityY = -9.81f;

        public static readonly SeedRangeV0 TrainingSeeds =
            new(Phase1ASeedPartitionV0.Training, 2000000UL, 50000);

        public static readonly SeedRangeV0 ValidationSeeds =
            new(Phase1ASeedPartitionV0.Validation, 3000000UL, 1000);

        public static readonly SeedRangeV0 HeldOutEvaluationSeeds =
            new(Phase1ASeedPartitionV0.HeldOutEvaluation, 4000000UL, 1000);

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
                "p1a/contact-easy",
                ScenarioCatalogV0.ContactFrontOn,
                "easy",
                "Acquire reliable paddle contact.",
                TargetRadius,
                0.90f,
                0f),
            new(
                "p1a/return-easy",
                ScenarioCatalogV0.LaunchRally,
                "easy",
                "Return the ball legally over the net.",
                TargetRadius,
                0.70f,
                3f),
            new(
                "p1a/place-default",
                ScenarioCatalogV0.LaunchRally,
                "default",
                "Place legal returns near the target.",
                TargetRadius,
                0.55f,
                2f),
            new(
                "p1a/robust-hard",
                ScenarioCatalogV0.LaunchRally,
                "hard",
                "Preserve return quality under the approved speed and spin envelope.",
                TargetRadius,
                0.45f,
                1.6f)
        };

        private static readonly IReadOnlyList<CurriculumStageV0> ReadOnlyStages =
            Array.AsReadOnly(StableStages);

        public static IReadOnlyList<CurriculumStageV0> CurriculumStages =>
            ReadOnlyStages;

        public static ResetRequestV0 TrainingRequest(
            int stageIndex,
            int seedIndex)
        {
            return CurriculumRequest(
                StableStages,
                stageIndex,
                TrainingSeeds,
                seedIndex);
        }

        public static ResetRequestV0 ValidationRequest(
            int stageIndex,
            int seedIndex)
        {
            return CurriculumRequest(
                StableStages,
                stageIndex,
                ValidationSeeds,
                seedIndex);
        }

        public static ResetRequestV0 EvaluationRequest(int index)
        {
            var seed = HeldOutEvaluationSeeds.At(index);
            var difficulty = (index % 3) switch
            {
                0 => "easy",
                1 => "default",
                _ => "hard"
            };
            var verticalVelocity = difficulty switch
            {
                "easy" => 3f,
                "default" => 2f,
                _ => 1.6f
            };
            return new ResetRequestV0(
                seed,
                ScenarioCatalogV0.LaunchRally,
                difficulty,
                new[]
                {
                    new ResetOverrideV0(
                        "ball.velocity.y",
                        verticalVelocity)
                });
        }

        public static string CanonicalText()
        {
            return string.Join(
                "\n",
                Version,
                EnvironmentVersion.Current,
                ObservationVersion,
                ActionVersion,
                TrainerSelection,
                MaximumActionSteps.ToString(CultureInfo.InvariantCulture),
                BaselineEpisodeCount.ToString(CultureInfo.InvariantCulture),
                StableHashV0.Float(TargetRadius),
                TrainingSeeds.CanonicalText(),
                ValidationSeeds.CanonicalText(),
                HeldOutEvaluationSeeds.CanonicalText(),
                RewardMapping.CanonicalText(),
                string.Join("\n", StableStages.Select(value => value.CanonicalText())));
        }

        public static string Hash => StableHashV0.Hex(CanonicalText());

        public static void ValidateOrThrow()
        {
            if (TrainingSeeds.Overlaps(ValidationSeeds) ||
                TrainingSeeds.Overlaps(HeldOutEvaluationSeeds) ||
                ValidationSeeds.Overlaps(HeldOutEvaluationSeeds))
            {
                throw new InvalidOperationException("Phase 1A seed partitions overlap.");
            }

            if (StableStages.Select(value => value.Id).Distinct().Count() !=
                StableStages.Length)
            {
                throw new InvalidOperationException("Phase 1A stage IDs must be unique.");
            }

            foreach (var stage in StableStages)
            {
                if (!ScenarioCatalogV0.ScenarioIds.Contains(stage.ScenarioId) ||
                    !FiniteMath.IsFinite(stage.TargetRadius) ||
                    stage.TargetRadius <= 0f ||
                    !FiniteMath.IsFinite(stage.PromotionThreshold) ||
                    stage.PromotionThreshold <= 0f ||
                    stage.PromotionThreshold > 1f ||
                    !FiniteMath.IsFinite(stage.InboundVerticalVelocity) ||
                    stage.InboundVerticalVelocity < 0f)
                {
                    throw new InvalidOperationException(
                        $"Phase 1A stage '{stage.Id}' is invalid.");
                }
            }
        }

        private static ResetRequestV0 CurriculumRequest(
            IReadOnlyList<CurriculumStageV0> stages,
            int stageIndex,
            SeedRangeV0 seeds,
            int seedIndex)
        {
            if (stageIndex < 0 || stageIndex >= stages.Count)
            {
                throw new ArgumentOutOfRangeException(nameof(stageIndex));
            }

            var stage = stages[stageIndex];
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

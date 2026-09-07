using System;
using System.Collections.Generic;
using System.Linq;
using Picklebot.Core;
using UnityEngine;

namespace Picklebot.Evaluation
{
    public enum Phase1C0SeedUseV0
    {
        Training,
        Validation
    }

    [Serializable]
    public sealed class Phase1C0EpisodeRecordV0
    {
        public bool provisional;
        public string protocolVersion;
        public string protocolHash;
        public string rewardHash;
        public string environmentVersion;
        public string configurationHash;
        public string seedUse;
        public string stageId;
        public ulong seed;
        public string scenarioId;
        public string difficulty;
        public string manifestHash;
        public string terminalReason;
        public int actionSteps;
        public bool paddleContact;
        public bool legalReturn;
        public bool targetHit;
        public bool netContact;
        public bool outLanding;
        public float landingError;
        public float meanActionDelta;
        public float peakPaddleSpeed;
        public float episodeReturn;
    }

    [Serializable]
    public sealed class Phase1C0MetricsSummaryV0
    {
        public bool provisional;
        public string protocolVersion;
        public string protocolHash;
        public string rewardHash;
        public int episodes;
        public float contactRate;
        public float legalReturnRate;
        public float targetHitRate;
        public float netContactRate;
        public float outRate;
        public int landingErrorSamples;
        public float meanLandingError;
        public float meanActionDelta;
        public float peakPaddleSpeed;
        public float meanEpisodeReturn;
    }

    public sealed class Phase1C0EpisodeAccumulatorV0
    {
        private readonly Phase1C0SeedUseV0 seedUse;
        private readonly int stageIndex;
        private readonly EpisodeManifestV0 manifest;

        private PaddleActionV0 previousAction;
        private float actionDeltaTotal;
        private float peakPaddleSpeed;
        private float episodeReturn;
        private float landingError = -1f;
        private int actionSteps;
        private bool paddleContact;
        private bool netContact;
        private StepResultV0 latestResult;

        public Phase1C0EpisodeAccumulatorV0(
            Phase1C0SeedUseV0 seedUse,
            int stageIndex,
            EpisodeManifestV0 manifest)
        {
            this.seedUse = seedUse;
            this.stageIndex = stageIndex;
            this.manifest = manifest ??
                throw new ArgumentNullException(nameof(manifest));

            Phase1CProtocolV0.ValidateOrThrow();
            if (stageIndex < 0 ||
                stageIndex >= Phase1CProtocolV0.CurriculumStages.Count)
            {
                throw new ArgumentOutOfRangeException(nameof(stageIndex));
            }

            var expectedRange = seedUse == Phase1C0SeedUseV0.Training
                ? Phase1CProtocolV0.TrainingSeeds
                : Phase1CProtocolV0.ValidationSeeds;
            if (!expectedRange.Contains(manifest.Seed) ||
                Phase1CProtocolV0.FinalEvaluationSeeds.Contains(manifest.Seed))
            {
                throw new ArgumentException(
                    "Episode seed is not legal for its Phase 1C0 use.",
                    nameof(manifest));
            }
        }

        public void Observe(
            StepResultV0 result,
            PaddleActionV0 action,
            float stepReward)
        {
            if (result == null)
            {
                throw new ArgumentNullException(nameof(result));
            }

            if (latestResult?.IsTerminal == true)
            {
                throw new InvalidOperationException(
                    "A terminal episode cannot accept another step.");
            }

            if (!FiniteMath.IsFinite(action.LinearVelocityLocal) ||
                !FiniteMath.IsFinite(action.AngularVelocityLocal) ||
                !FiniteMath.IsFinite(stepReward))
            {
                throw new ArgumentException(
                    "Metric inputs must remain finite.");
            }

            actionDeltaTotal += ActionDistance(previousAction, action);
            previousAction = action;
            episodeReturn += stepReward;
            actionSteps++;
            latestResult = result;

            peakPaddleSpeed = Mathf.Max(
                peakPaddleSpeed,
                result.Observation.Paddle.LinearVelocityWorld.magnitude);
            paddleContact |= result.RewardFeatures.PaddleContactCount > 0;
            netContact |= result.RewardFeatures.NetContactCount > 0;
            if (result.RewardFeatures.FarCourtLanding > 0f)
            {
                landingError =
                    result.RewardFeatures.TargetDistanceAtLanding;
            }
        }

        public Phase1C0EpisodeRecordV0 Complete()
        {
            if (latestResult == null || !latestResult.IsTerminal)
            {
                throw new InvalidOperationException(
                    "Episode metrics require a terminal step.");
            }

            var terminalReason = latestResult.TerminationReason;
            var legalReturn =
                paddleContact &&
                terminalReason == TerminationReasonV0.FarCourtLanding;
            var targetHit =
                legalReturn &&
                landingError >= 0f &&
                landingError <=
                Phase1CProtocolV0.CurriculumStages[stageIndex].TargetRadius;

            return new Phase1C0EpisodeRecordV0
            {
                provisional = true,
                protocolVersion = Phase1CProtocolV0.Version,
                protocolHash = Phase1CProtocolV0.Hash,
                rewardHash = Phase1CProtocolV0.RewardMappingHash,
                environmentVersion = manifest.EnvironmentVersion,
                configurationHash = manifest.ConfigurationHash,
                seedUse = seedUse.ToString(),
                stageId = Phase1CProtocolV0.CurriculumStages[stageIndex].Id,
                seed = manifest.Seed,
                scenarioId = manifest.ScenarioId,
                difficulty = manifest.Difficulty,
                manifestHash = StableHashV0.Hex(manifest.CanonicalText()),
                terminalReason = terminalReason.ToString(),
                actionSteps = actionSteps,
                paddleContact = paddleContact,
                legalReturn = legalReturn,
                targetHit = targetHit,
                netContact = netContact,
                outLanding =
                    terminalReason == TerminationReasonV0.OutOfBoundsLanding,
                landingError = landingError,
                meanActionDelta =
                    actionSteps == 0 ? 0f : actionDeltaTotal / actionSteps,
                peakPaddleSpeed = peakPaddleSpeed,
                episodeReturn = episodeReturn
            };
        }

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
    }

    public static class Phase1C0MetricsV0
    {
        public static Phase1C0MetricsSummaryV0 Aggregate(
            IReadOnlyList<Phase1C0EpisodeRecordV0> episodes)
        {
            if (episodes == null)
            {
                throw new ArgumentNullException(nameof(episodes));
            }

            if (episodes.Count == 0 ||
                episodes.Any(value =>
                    value == null ||
                    !value.provisional ||
                    value.protocolHash != Phase1CProtocolV0.Hash ||
                    Phase1CProtocolV0.FinalEvaluationSeeds.Contains(value.seed)))
            {
                throw new ArgumentException(
                    "Phase 1C0 metrics require provisional, current-protocol, non-final episodes.",
                    nameof(episodes));
            }

            var landingErrors = episodes
                .Where(value => value.legalReturn && value.landingError >= 0f)
                .Select(value => value.landingError)
                .ToArray();
            return new Phase1C0MetricsSummaryV0
            {
                provisional = true,
                protocolVersion = Phase1CProtocolV0.Version,
                protocolHash = Phase1CProtocolV0.Hash,
                rewardHash = Phase1CProtocolV0.RewardMappingHash,
                episodes = episodes.Count,
                contactRate = Rate(episodes.Count(value => value.paddleContact), episodes.Count),
                legalReturnRate = Rate(episodes.Count(value => value.legalReturn), episodes.Count),
                targetHitRate = Rate(episodes.Count(value => value.targetHit), episodes.Count),
                netContactRate = Rate(episodes.Count(value => value.netContact), episodes.Count),
                outRate = Rate(episodes.Count(value => value.outLanding), episodes.Count),
                landingErrorSamples = landingErrors.Length,
                meanLandingError =
                    landingErrors.Length == 0 ? -1f : landingErrors.Average(),
                meanActionDelta = episodes.Average(value => value.meanActionDelta),
                peakPaddleSpeed = episodes.Max(value => value.peakPaddleSpeed),
                meanEpisodeReturn = episodes.Average(value => value.episodeReturn)
            };
        }

        private static float Rate(int numerator, int denominator)
        {
            return denominator == 0 ? 0f : (float)numerator / denominator;
        }
    }
}

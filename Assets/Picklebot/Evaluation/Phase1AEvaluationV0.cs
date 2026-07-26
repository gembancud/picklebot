using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using Picklebot.Core;
using Unity.Profiling;
using UnityEngine;

namespace Picklebot.Evaluation
{
    [Serializable]
    public sealed class Phase1AEpisodeResultV0
    {
        public string policyId;
        public ulong seed;
        public string scenarioId;
        public string difficulty;
        public string manifestHash;
        public string terminalReason;
        public string launchSpeedBucket;
        public string spinBucket;
        public string placementBucket;
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
    public sealed class Phase1ABucketResultV0
    {
        public string bucket;
        public int episodes;
        public float contactRate;
        public float legalReturnRate;
        public float targetHitRate;
    }

    [Serializable]
    public sealed class Phase1ABaselineResultV0
    {
        public string policyId;
        public int episodes;
        public int terminalEpisodes;
        public float contactRate;
        public float legalReturnRate;
        public float targetHitRate;
        public float targetHitGivenLegalReturn;
        public float netContactRate;
        public float outRate;
        public float playableVolumeExitRate;
        public int landingErrorSamples;
        public float meanLandingError;
        public float meanActionDelta;
        public float peakPaddleSpeed;
        public float meanEpisodeReturn;
        public Phase1ABucketResultV0[] launchSpeedBuckets;
        public Phase1ABucketResultV0[] spinBuckets;
        public Phase1ABucketResultV0[] placementBuckets;
    }

    [Serializable]
    public sealed class Phase1ABaselineReportV0
    {
        public string protocolVersion;
        public string protocolHash;
        public string environmentVersion;
        public string observationVersion;
        public string actionVersion;
        public string rewardMappingHash;
        public string unityVersion;
        public string platform;
        public string sourceCommit;
        public ulong firstSeed;
        public ulong lastSeed;
        public int episodesPerPolicy;
        public float targetRadius;
        public bool passed;
        public Phase1ABaselineResultV0[] baselines;
    }

    [Serializable]
    public sealed class Phase1AReadinessReportV0
    {
        public string protocolVersion;
        public string environmentVersion;
        public string policyId;
        public string unityVersion;
        public string platform;
        public string sourceCommit;
        public int measuredActionSteps;
        public int completedEpisodes;
        public double elapsedMilliseconds;
        public double actionStepsPerSecond;
        public string allocationMetric;
        public bool allocationCounterAvailable;
        public long allocatedBytes;
        public double allocatedBytesPerAction;
        public double minimumActionStepsPerSecond;
        public double maximumAllocatedBytesPerAction;
        public bool passed;
    }

    public sealed class Phase1ABaselineRunV0
    {
        public Phase1ABaselineResultV0 Baseline { get; }
        public IReadOnlyList<Phase1AEpisodeResultV0> Episodes { get; }

        public Phase1ABaselineRunV0(
            Phase1ABaselineResultV0 baseline,
            IReadOnlyList<Phase1AEpisodeResultV0> episodes)
        {
            Baseline = baseline;
            Episodes = episodes;
        }
    }

    public static class Phase1AEvaluatorV0
    {
        private const double MinimumActionStepsPerSecond = 500d;
        private const double MaximumAllocatedBytesPerAction = 4096d;

        public static Phase1ABaselineRunV0 Evaluate(
            IPicklebotEnvironmentV0 environment,
            IPaddlePolicyV0 policy,
            int firstIndex,
            int episodeCount)
        {
            if (environment == null)
            {
                throw new ArgumentNullException(nameof(environment));
            }

            if (policy == null)
            {
                throw new ArgumentNullException(nameof(policy));
            }

            if (firstIndex < 0 ||
                episodeCount <= 0 ||
                firstIndex + episodeCount >
                Phase1AProtocolV0.HeldOutEvaluationSeeds.Count)
            {
                throw new ArgumentOutOfRangeException(nameof(episodeCount));
            }

            var episodes = new List<Phase1AEpisodeResultV0>(episodeCount);
            for (var offset = 0; offset < episodeCount; offset++)
            {
                var request = Phase1AProtocolV0.EvaluationRequest(firstIndex + offset);
                var observation = environment.Reset(request);
                var manifest = environment.CurrentManifest;
                policy.Reset(manifest);

                var previousAction = PaddleActionV0.Zero;
                var previousElapsed = 0f;
                var actionDeltaTotal = 0f;
                var peakPaddleSpeed = 0f;
                var episodeReturn = 0f;
                var paddleContact = false;
                var netContact = false;
                var landingError = -1f;
                StepResultV0 result = null;
                var actionSteps = 0;

                while (actionSteps < Phase1AProtocolV0.MaximumActionSteps)
                {
                    var action = policy.Decide(observation);
                    actionDeltaTotal += ActionDistance(previousAction, action);
                    previousAction = action;
                    result = environment.Step(action);
                    actionSteps++;
                    observation = result.Observation;
                    peakPaddleSpeed = Mathf.Max(
                        peakPaddleSpeed,
                        observation.Paddle.LinearVelocityWorld.magnitude);
                    paddleContact |= result.RewardFeatures.PaddleContactCount > 0;
                    netContact |= result.RewardFeatures.NetContactCount > 0;
                    if (result.RewardFeatures.FarCourtLanding > 0f)
                    {
                        landingError =
                            result.RewardFeatures.TargetDistanceAtLanding;
                    }

                    episodeReturn += Phase1AProtocolV0.RewardMapping.MapStep(
                        result.RewardFeatures,
                        previousElapsed);
                    previousElapsed = result.RewardFeatures.ElapsedTime;
                    if (result.IsTerminal)
                    {
                        break;
                    }
                }

                var terminalReason =
                    result?.TerminationReason ?? TerminationReasonV0.None;
                var legalReturn =
                    paddleContact &&
                    terminalReason == TerminationReasonV0.FarCourtLanding;
                var targetHit =
                    legalReturn &&
                    landingError >= 0f &&
                    landingError <= Phase1AProtocolV0.TargetRadius;
                episodes.Add(new Phase1AEpisodeResultV0
                {
                    policyId = policy.PolicyId,
                    seed = request.Seed,
                    scenarioId = request.ScenarioId,
                    difficulty = request.Difficulty,
                    manifestHash = StableHashV0.Hex(manifest.CanonicalText()),
                    terminalReason = terminalReason.ToString(),
                    launchSpeedBucket =
                        LaunchSpeedBucket(manifest.Parameters.BallLinearVelocity.magnitude),
                    spinBucket =
                        SpinBucket(manifest.Parameters.BallAngularVelocity.magnitude),
                    placementBucket =
                        PlacementBucket(manifest.Parameters.BallPosition.x),
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
                });
            }

            return new Phase1ABaselineRunV0(
                Aggregate(policy.PolicyId, episodes),
                episodes);
        }

        public static Phase1AReadinessReportV0 MeasureReadiness(
            IPicklebotEnvironmentV0 environment,
            IPaddlePolicyV0 policy,
            int measuredActionSteps,
            string sourceCommit)
        {
            if (measuredActionSteps <= 0)
            {
                throw new ArgumentOutOfRangeException(nameof(measuredActionSteps));
            }

            var requestIndex = 0;
            var observation = environment.Reset(
                new ResetRequestV0(
                    Phase1AProtocolV0.ValidationSeeds.At(requestIndex),
                    ScenarioCatalogV0.LaunchRally));
            policy.Reset(environment.CurrentManifest);

            for (var warmup = 0; warmup < 256; warmup++)
            {
                var warmupResult = environment.Step(policy.Decide(observation));
                observation = warmupResult.Observation;
                if (warmupResult.IsTerminal)
                {
                    requestIndex =
                        (requestIndex + 1) % Phase1AProtocolV0.ValidationSeeds.Count;
                    observation = environment.Reset(
                        new ResetRequestV0(
                            Phase1AProtocolV0.ValidationSeeds.At(requestIndex),
                            ScenarioCatalogV0.LaunchRally));
                    policy.Reset(environment.CurrentManifest);
                }
            }

            using var allocationRecorder = ProfilerRecorder.StartNew(
                ProfilerCategory.Memory,
                "GC Allocated In Frame");
            var allocationCounterAvailable = allocationRecorder.Valid;
            var allocatedBefore = allocationCounterAvailable
                ? allocationRecorder.CurrentValue
                : 0L;
            var stopwatch = Stopwatch.StartNew();
            var completedEpisodes = 0;

            for (var step = 0; step < measuredActionSteps; step++)
            {
                var result = environment.Step(policy.Decide(observation));
                observation = result.Observation;
                if (!result.IsTerminal)
                {
                    continue;
                }

                completedEpisodes++;
                requestIndex =
                    (requestIndex + 1) % Phase1AProtocolV0.ValidationSeeds.Count;
                observation = environment.Reset(
                    new ResetRequestV0(
                        Phase1AProtocolV0.ValidationSeeds.At(requestIndex),
                        ScenarioCatalogV0.LaunchRally));
                policy.Reset(environment.CurrentManifest);
            }

            stopwatch.Stop();
            var allocatedAfter = allocationCounterAvailable
                ? allocationRecorder.CurrentValue
                : 0L;
            var allocatedBytes = Math.Max(0L, allocatedAfter - allocatedBefore);
            var stepsPerSecond =
                measuredActionSteps / stopwatch.Elapsed.TotalSeconds;
            var bytesPerAction = allocationCounterAvailable
                ? (double)allocatedBytes / measuredActionSteps
                : double.PositiveInfinity;
            return new Phase1AReadinessReportV0
            {
                protocolVersion = Phase1AProtocolV0.Version,
                environmentVersion = EnvironmentVersion.Current,
                policyId = policy.PolicyId,
                unityVersion = Application.unityVersion,
                platform = Application.platform.ToString(),
                sourceCommit = sourceCommit,
                measuredActionSteps = measuredActionSteps,
                completedEpisodes = completedEpisodes,
                elapsedMilliseconds = stopwatch.Elapsed.TotalMilliseconds,
                actionStepsPerSecond = stepsPerSecond,
                allocationMetric = "GC Allocated In Frame (measurement-window delta)",
                allocationCounterAvailable = allocationCounterAvailable,
                allocatedBytes = allocatedBytes,
                allocatedBytesPerAction = bytesPerAction,
                minimumActionStepsPerSecond = MinimumActionStepsPerSecond,
                maximumAllocatedBytesPerAction = MaximumAllocatedBytesPerAction,
                passed =
                    allocationCounterAvailable &&
                    stepsPerSecond >= MinimumActionStepsPerSecond &&
                    bytesPerAction <= MaximumAllocatedBytesPerAction
            };
        }

        private static Phase1ABaselineResultV0 Aggregate(
            string policyId,
            IReadOnlyList<Phase1AEpisodeResultV0> episodes)
        {
            var terminalEpisodes = episodes.Count(value =>
                value.terminalReason != TerminationReasonV0.None.ToString());
            var contacts = episodes.Count(value => value.paddleContact);
            var legalReturns = episodes.Count(value => value.legalReturn);
            var targetHits = episodes.Count(value => value.targetHit);
            var landingSamples = episodes
                .Where(value => value.legalReturn && value.landingError >= 0f)
                .ToArray();
            return new Phase1ABaselineResultV0
            {
                policyId = policyId,
                episodes = episodes.Count,
                terminalEpisodes = terminalEpisodes,
                contactRate = Rate(contacts, episodes.Count),
                legalReturnRate = Rate(legalReturns, episodes.Count),
                targetHitRate = Rate(targetHits, episodes.Count),
                targetHitGivenLegalReturn = Rate(targetHits, legalReturns),
                netContactRate =
                    Rate(episodes.Count(value => value.netContact), episodes.Count),
                outRate =
                    Rate(episodes.Count(value => value.outLanding), episodes.Count),
                playableVolumeExitRate = Rate(
                    episodes.Count(value =>
                        value.terminalReason ==
                        TerminationReasonV0.PlayableVolumeExit.ToString()),
                    episodes.Count),
                landingErrorSamples = landingSamples.Length,
                meanLandingError = landingSamples.Length == 0
                    ? -1f
                    : landingSamples.Average(value => value.landingError),
                meanActionDelta =
                    episodes.Average(value => value.meanActionDelta),
                peakPaddleSpeed =
                    episodes.Max(value => value.peakPaddleSpeed),
                meanEpisodeReturn =
                    episodes.Average(value => value.episodeReturn),
                launchSpeedBuckets = AggregateBuckets(
                    episodes,
                    value => value.launchSpeedBucket),
                spinBuckets = AggregateBuckets(
                    episodes,
                    value => value.spinBucket),
                placementBuckets = AggregateBuckets(
                    episodes,
                    value => value.placementBucket)
            };
        }

        private static Phase1ABucketResultV0[] AggregateBuckets(
            IReadOnlyList<Phase1AEpisodeResultV0> episodes,
            Func<Phase1AEpisodeResultV0, string> selector)
        {
            return episodes
                .GroupBy(selector)
                .OrderBy(group => group.Key, StringComparer.Ordinal)
                .Select(group =>
                {
                    var values = group.ToArray();
                    return new Phase1ABucketResultV0
                    {
                        bucket = group.Key,
                        episodes = values.Length,
                        contactRate =
                            Rate(values.Count(value => value.paddleContact), values.Length),
                        legalReturnRate =
                            Rate(values.Count(value => value.legalReturn), values.Length),
                        targetHitRate =
                            Rate(values.Count(value => value.targetHit), values.Length)
                    };
                })
                .ToArray();
        }

        private static float Rate(int numerator, int denominator)
        {
            return denominator == 0 ? 0f : (float)numerator / denominator;
        }

        private static float ActionDistance(
            PaddleActionV0 first,
            PaddleActionV0 second)
        {
            var linear = second.LinearVelocityLocal - first.LinearVelocityLocal;
            var angular = second.AngularVelocityLocal - first.AngularVelocityLocal;
            return Mathf.Sqrt(
                (linear.sqrMagnitude + angular.sqrMagnitude) / 6f);
        }

        private static string LaunchSpeedBucket(float speed)
        {
            if (speed < 6f)
            {
                return "slow";
            }

            return speed < 8f ? "medium" : "fast";
        }

        private static string SpinBucket(float spin)
        {
            if (spin < 5f)
            {
                return "low";
            }

            return spin < 10f ? "medium" : "high";
        }

        private static string PlacementBucket(float x)
        {
            if (x < -0.12f)
            {
                return "left";
            }

            return x > 0.12f ? "right" : "center";
        }
    }
}

using System;
using System.Diagnostics;
using Picklebot.Core;
using Unity.Profiling;
using UnityEngine;

namespace Picklebot.Evaluation
{
    [Serializable]
    public sealed class Phase1BReadinessReportV1
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
        public double phase1ASourceExactActionStepsPerSecond;
        public double maximumAllowedRegressionFraction;
        public double minimumActionStepsPerSecond;
        public double maximumAllocatedBytesPerAction;
        public bool passed;
    }

    public static class Phase1BReadinessV1
    {
        public const double Phase1ASourceExactActionStepsPerSecond =
            4439.057401673214;
        public const double AbsoluteMinimumActionStepsPerSecond = 500.0;
        public const double MaximumRegressionFraction = 0.25;
        public const double MaximumAllocatedBytesPerAction = 4096.0;

        public static double RequiredActionStepsPerSecond =>
            Math.Max(
                AbsoluteMinimumActionStepsPerSecond,
                Phase1ASourceExactActionStepsPerSecond *
                (1.0 - MaximumRegressionFraction));

        public static Phase1BReadinessReportV1 Measure(
            IPicklebotEnvironmentV1 environment,
            IPaddlePolicyV0 policy,
            int measuredActionSteps,
            string sourceCommit)
        {
            if (environment == null)
            {
                throw new ArgumentNullException(nameof(environment));
            }

            if (policy == null)
            {
                throw new ArgumentNullException(nameof(policy));
            }

            if (measuredActionSteps <= 0)
            {
                throw new ArgumentOutOfRangeException(
                    nameof(measuredActionSteps));
            }

            var requestIndex = 0;
            var observation = environment.Reset(
                new ResetRequestV0(
                    Phase1CProtocolV0.ValidationSeeds.At(requestIndex),
                    ScenarioCatalogV0.LaunchRally));
            policy.Reset(environment.CurrentManifest);

            for (var warmup = 0; warmup < 256; warmup++)
            {
                var warmupResult = environment.Step(
                    policy.Decide(observation));
                observation = warmupResult.Observation;
                if (warmupResult.IsTerminal)
                {
                    requestIndex =
                        (requestIndex + 1) %
                        Phase1CProtocolV0.ValidationSeeds.Count;
                    observation = environment.Reset(
                        new ResetRequestV0(
                            Phase1CProtocolV0.ValidationSeeds.At(requestIndex),
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
                    (requestIndex + 1) %
                    Phase1CProtocolV0.ValidationSeeds.Count;
                observation = environment.Reset(
                    new ResetRequestV0(
                        Phase1CProtocolV0.ValidationSeeds.At(requestIndex),
                        ScenarioCatalogV0.LaunchRally));
                policy.Reset(environment.CurrentManifest);
            }

            stopwatch.Stop();
            var allocatedAfter = allocationCounterAvailable
                ? allocationRecorder.CurrentValue
                : 0L;
            var allocatedBytes = Math.Max(
                0L,
                allocatedAfter - allocatedBefore);
            var stepsPerSecond =
                measuredActionSteps / stopwatch.Elapsed.TotalSeconds;
            var bytesPerAction = allocationCounterAvailable
                ? (double)allocatedBytes / measuredActionSteps
                : double.PositiveInfinity;
            return new Phase1BReadinessReportV1
            {
                protocolVersion = Phase1CProtocolV0.Version,
                environmentVersion = SimulationConfigV1.EnvironmentVersion,
                policyId = policy.PolicyId,
                unityVersion = Application.unityVersion,
                platform = Application.platform.ToString(),
                sourceCommit = sourceCommit,
                measuredActionSteps = measuredActionSteps,
                completedEpisodes = completedEpisodes,
                elapsedMilliseconds = stopwatch.Elapsed.TotalMilliseconds,
                actionStepsPerSecond = stepsPerSecond,
                allocationMetric =
                    "GC Allocated In Frame (measurement-window delta)",
                allocationCounterAvailable = allocationCounterAvailable,
                allocatedBytes = allocatedBytes,
                allocatedBytesPerAction = bytesPerAction,
                phase1ASourceExactActionStepsPerSecond =
                    Phase1ASourceExactActionStepsPerSecond,
                maximumAllowedRegressionFraction =
                    MaximumRegressionFraction,
                minimumActionStepsPerSecond =
                    RequiredActionStepsPerSecond,
                maximumAllocatedBytesPerAction =
                    MaximumAllocatedBytesPerAction,
                passed =
                    allocationCounterAvailable &&
                    stepsPerSecond >= RequiredActionStepsPerSecond &&
                    bytesPerAction <= MaximumAllocatedBytesPerAction
            };
        }
    }
}

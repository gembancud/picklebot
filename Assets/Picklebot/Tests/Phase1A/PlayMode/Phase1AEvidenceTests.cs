using System;
using System.Collections;
using System.IO;
using System.Linq;
using NUnit.Framework;
using Picklebot.Core;
using Picklebot.Evaluation;
using Picklebot.Simulation;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;

namespace Picklebot.Tests.Phase1A.PlayMode
{
    public sealed class Phase1AEvidenceTests
    {
        [UnityTest]
        [Category("Evidence")]
        [Explicit("Run through scripts/phase1a-evidence.sh or by exact test name.")]
        public IEnumerator GenerateCommittedBaselineAndReadinessEvidence()
        {
            var load = SceneManager.LoadSceneAsync(
                "Phase0Environment",
                LoadSceneMode.Single);
            Assert.That(load, Is.Not.Null);
            while (!load.isDone)
            {
                yield return null;
            }

            yield return null;
            var runner =
                UnityEngine.Object.FindAnyObjectByType<PicklebotDebugRunnerV0>();
            Assert.That(runner, Is.Not.Null);
            runner.enabled = false;
            var environment =
                UnityEngine.Object.FindAnyObjectByType<PicklebotEnvironmentV0>();
            Assert.That(environment, Is.Not.Null);

            Phase1AProtocolV0.ValidateOrThrow();
            var zero = Phase1AEvaluatorV0.Evaluate(
                environment,
                new ZeroPolicyV0(),
                firstIndex: 0,
                episodeCount: Phase1AProtocolV0.BaselineEpisodeCount);
            yield return null;
            var intercept = Phase1AEvaluatorV0.Evaluate(
                environment,
                new InterceptHeuristicPolicyV0(),
                firstIndex: 0,
                episodeCount: Phase1AProtocolV0.BaselineEpisodeCount);
            yield return null;

            var sourceCommit =
                Environment.GetEnvironmentVariable("PICKLEBOT_SOURCE_COMMIT") ??
                "uncommitted";
            var readiness = Phase1AEvaluatorV0.MeasureReadiness(
                environment,
                new InterceptHeuristicPolicyV0(),
                measuredActionSteps: 20000,
                sourceCommit);
            var baselines = new[] { zero.Baseline, intercept.Baseline };
            var report = new Phase1ABaselineReportV0
            {
                protocolVersion = Phase1AProtocolV0.Version,
                protocolHash = Phase1AProtocolV0.Hash,
                environmentVersion = EnvironmentVersion.Current,
                observationVersion = Phase1AProtocolV0.ObservationVersion,
                actionVersion = Phase1AProtocolV0.ActionVersion,
                rewardMappingHash = Phase1AProtocolV0.RewardMapping.Hash,
                unityVersion = Application.unityVersion,
                platform = Application.platform.ToString(),
                sourceCommit = sourceCommit,
                firstSeed = Phase1AProtocolV0.HeldOutEvaluationSeeds.First,
                lastSeed = Phase1AProtocolV0.HeldOutEvaluationSeeds.Last,
                episodesPerPolicy = Phase1AProtocolV0.BaselineEpisodeCount,
                targetRadius = Phase1AProtocolV0.TargetRadius,
                passed =
                    baselines.All(value =>
                        value.terminalEpisodes == value.episodes) &&
                    zero.Episodes.Concat(intercept.Episodes).All(value =>
                        value.terminalReason !=
                        TerminationReasonV0.InvalidAction.ToString() &&
                        value.terminalReason !=
                        TerminationReasonV0.InvalidNumericState.ToString() &&
                        value.terminalReason !=
                        TerminationReasonV0.None.ToString()) &&
                    readiness.passed,
                baselines = baselines
            };

            var outputDirectory = Path.GetFullPath(Path.Combine(
                Application.dataPath,
                "..",
                "docs",
                "evidence",
                "phase1a"));
            Directory.CreateDirectory(outputDirectory);
            File.WriteAllText(
                Path.Combine(outputDirectory, "summary.json"),
                JsonUtility.ToJson(report, true));
            File.WriteAllText(
                Path.Combine(outputDirectory, "readiness.json"),
                JsonUtility.ToJson(readiness, true));

            using (var writer = new StreamWriter(
                       Path.Combine(outputDirectory, "episodes.jsonl"),
                       false))
            {
                foreach (var episode in zero.Episodes.Concat(intercept.Episodes))
                {
                    writer.WriteLine(JsonUtility.ToJson(episode));
                }
            }

            Assert.That(zero.Baseline.episodes, Is.EqualTo(1000));
            Assert.That(intercept.Baseline.episodes, Is.EqualTo(1000));
            Assert.That(zero.Baseline.terminalEpisodes, Is.EqualTo(1000));
            Assert.That(intercept.Baseline.terminalEpisodes, Is.EqualTo(1000));
            Assert.That(readiness.passed, Is.True);
            Assert.That(report.passed, Is.True);
        }
    }
}

using System.Collections;
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
    public sealed class Phase1AEvaluationPlayModeTests
    {
        private PicklebotEnvironmentV0 environment;

        [UnitySetUp]
        public IEnumerator SetUp()
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
            var runner = Object.FindAnyObjectByType<PicklebotDebugRunnerV0>();
            Assert.That(runner, Is.Not.Null);
            runner.enabled = false;
            environment = Object.FindAnyObjectByType<PicklebotEnvironmentV0>();
            Assert.That(environment, Is.Not.Null);
        }

        [Test]
        public void RealSceneObservationEncodesToFiniteFrozenShape()
        {
            var observation = environment.Reset(
                Phase1AProtocolV0.EvaluationRequest(0));
            var encoded = new float[Phase1AObservationEncoderV0.Size];

            Phase1AObservationEncoderV0.Encode(observation, encoded);

            Assert.That(encoded.All(FiniteMath.IsFinite), Is.True);
            Assert.That(
                encoded.All(value => value >= -1f && value <= 1f),
                Is.True);
        }

        [Test]
        public void BothBaselinesRunOnHeldOutEnvironmentContract()
        {
            var zero = Phase1AEvaluatorV0.Evaluate(
                environment,
                new ZeroPolicyV0(),
                firstIndex: 0,
                episodeCount: 6);
            var intercept = Phase1AEvaluatorV0.Evaluate(
                environment,
                new InterceptHeuristicPolicyV0(),
                firstIndex: 6,
                episodeCount: 6);

            Assert.That(zero.Baseline.episodes, Is.EqualTo(6));
            Assert.That(zero.Baseline.terminalEpisodes, Is.EqualTo(6));
            Assert.That(intercept.Baseline.episodes, Is.EqualTo(6));
            Assert.That(intercept.Baseline.terminalEpisodes, Is.EqualTo(6));
            Assert.That(
                zero.Episodes.Concat(intercept.Episodes).All(value =>
                    value.terminalReason != TerminationReasonV0.None.ToString()),
                Is.True);
        }

        [Test]
        public void ReadinessProbeMeasuresTheRealStepPath()
        {
            var report = Phase1AEvaluatorV0.MeasureReadiness(
                environment,
                new InterceptHeuristicPolicyV0(),
                measuredActionSteps: 512,
                sourceCommit: "playmode-smoke");

            Assert.That(report.measuredActionSteps, Is.EqualTo(512));
            Assert.That(report.completedEpisodes, Is.GreaterThan(0));
            Assert.That(report.actionStepsPerSecond, Is.GreaterThan(0d));
            Assert.That(report.allocationCounterAvailable, Is.True);
            Assert.That(report.allocatedBytesPerAction, Is.GreaterThanOrEqualTo(0d));
        }
    }
}

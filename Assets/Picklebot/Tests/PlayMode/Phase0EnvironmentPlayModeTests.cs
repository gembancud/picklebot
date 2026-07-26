using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using Picklebot.Core;
using Picklebot.Simulation;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;

namespace Picklebot.Tests.PlayMode
{
    public sealed class Phase0EnvironmentPlayModeTests
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
            var runner = UnityEngine.Object.FindAnyObjectByType<PicklebotDebugRunnerV0>();
            Assert.That(runner, Is.Not.Null);
            runner.enabled = false;
            environment = UnityEngine.Object.FindAnyObjectByType<PicklebotEnvironmentV0>();
            Assert.That(environment, Is.Not.Null);
        }

        [TearDown]
        public void TearDown()
        {
            Time.timeScale = 1f;
        }

        [Test]
        public void SceneHasAllCanonicalDependencies()
        {
            Assert.That(environment.Configuration, Is.Not.Null);
            Assert.That(environment.Ball, Is.Not.Null);
            Assert.That(environment.Paddle, Is.Not.Null);
            Assert.That(
                environment.Ball.mass,
                Is.EqualTo(CourtGeometryV0.BallMass).Within(0.000001f));
            Assert.That(
                environment.Ball.collisionDetectionMode,
                Is.EqualTo(CollisionDetectionMode.ContinuousDynamic));
            Assert.That(environment.Paddle.isKinematic, Is.True);
            Assert.That(Physics.simulationMode, Is.EqualTo(SimulationMode.Script));
            var netIdentity = UnityEngine.Object
                .FindObjectsByType<CollisionIdentityV0>()
                .Single(value => value.Kind == CollisionEntityKindV0.Net);
            Assert.That(
                netIdentity.GetComponentsInChildren<BoxCollider>().Length,
                Is.EqualTo(2));
        }

        [Test]
        public void IdenticalSeedGenerationIsBitIdentical()
        {
            var request = new ResetRequestV0(
                500UL,
                ScenarioCatalogV0.LaunchRally);
            environment.Reset(request);
            var first = environment.CurrentManifest.Parameters.CanonicalText();
            environment.Reset(request);
            var second = environment.CurrentManifest.Parameters.CanonicalText();
            Assert.That(second, Is.EqualTo(first));
        }

        [Test]
        public void ResetClearsMotionContactsCountersAndQueuedState()
        {
            var request = new ResetRequestV0(
                99UL,
                ScenarioCatalogV0.ResetStateLeak);
            var initial = environment.Reset(request);
            for (var index = 0; index < 8; index++)
            {
                environment.Step(new PaddleActionV0(
                    new Vector3(0.5f, 0f, 0f),
                    new Vector3(0f, 0.25f, 0f)));
            }

            var reset = environment.Reset(request);
            Assert.That(reset.PhysicsTick, Is.Zero);
            Assert.That(reset.ElapsedTime, Is.Zero);
            Assert.That(reset.Episode.State, Is.EqualTo(EpisodeStateV0.Ready));
            Assert.That(reset.Episode.ControlledPaddleContacts, Is.Zero);
            Assert.That(reset.Episode.BallFloorContacts, Is.Zero);
            Assert.That(reset.Ball.PositionWorld, Is.EqualTo(initial.Ball.PositionWorld));
            Assert.That(reset.Ball.LinearVelocityWorld, Is.EqualTo(initial.Ball.LinearVelocityWorld));
            Assert.That(reset.Paddle.PositionWorld, Is.EqualTo(initial.Paddle.PositionWorld));
            Assert.That(reset.Paddle.LinearVelocityWorld, Is.EqualTo(Vector3.zero));
            Assert.That(environment.RecentEvents, Is.Empty);
        }

        [Test]
        public void InvalidActionTerminatesWithoutAdvancingPhysics()
        {
            environment.Reset(new ResetRequestV0(
                1UL,
                ScenarioCatalogV0.LaunchRally));
            var result = environment.Step(new PaddleActionV0(
                new Vector3(float.NaN, 0f, 0f),
                Vector3.zero));

            Assert.That(result.IsTerminal, Is.True);
            Assert.That(
                result.TerminationReason,
                Is.EqualTo(TerminationReasonV0.InvalidAction));
            Assert.That(result.Observation.PhysicsTick, Is.Zero);
            Assert.That(
                result.Events.Last().Kind,
                Is.EqualTo(EnvironmentEventKindV0.EpisodeTerminated));
        }

        [Test]
        public void FiniteOutOfRangeActionIsClampedAndDiagnosed()
        {
            environment.Reset(new ResetRequestV0(
                2UL,
                ScenarioCatalogV0.LaunchRally));
            var result = environment.Step(new PaddleActionV0(
                new Vector3(2f, -3f, 0f),
                new Vector3(0f, 0f, 4f)));

            Assert.That(result.IsTerminal, Is.False);
            Assert.That(result.RewardFeatures.ActionClampCount, Is.EqualTo(1));
            Assert.That(
                result.Observation.Episode.LastTouch,
                Is.EqualTo(LastTouchV0.Launcher));
            Assert.That(
                environment.PaddleCommandLinearVelocityWorld.magnitude,
                Is.EqualTo(
                        new Vector3(1f, -1f, 0f).magnitude *
                        environment.Configuration.MaxPaddleLinearSpeed)
                    .Within(0.000001f));
            Assert.That(
                FiniteMath.IsFinite(environment.PaddleCommandLinearVelocityWorld),
                Is.True);
            Assert.That(
                result.Events.Any(value =>
                    value.Kind == EnvironmentEventKindV0.ActionClamped),
                Is.True);
        }

        [Test]
        public void BoundaryFloorContactClassifiesLineAsFarCourt()
        {
            var request = new ResetRequestV0(
                3UL,
                ScenarioCatalogV0.BoundaryCourt,
                overrides: new[]
                {
                    new ResetOverrideV0("ball.position.x", CourtGeometryV0.HalfWidth),
                    new ResetOverrideV0("ball.position.z", CourtGeometryV0.HalfLength),
                    new ResetOverrideV0("ball.velocity.x", 0f),
                    new ResetOverrideV0("ball.velocity.y", -1f),
                    new ResetOverrideV0("ball.velocity.z", 0f)
                });
            environment.Reset(request);
            var result = RunUntilTerminal();

            Assert.That(
                result.TerminationReason,
                Is.EqualTo(TerminationReasonV0.FarCourtLanding));
            Assert.That(result.RewardFeatures.FarCourtLanding, Is.EqualTo(1f));
            Assert.That(
                result.Events.Any(value =>
                    value.Kind == EnvironmentEventKindV0.BallFloorContact),
                Is.True);
            AssertOrdered(result.Events);
        }

        [Test]
        public void FrontOnScenarioProducesOneLogicalPaddleContact()
        {
            environment.Reset(new ResetRequestV0(
                4UL,
                ScenarioCatalogV0.ContactFrontOn));
            var result = RunUntilTerminal();
            var contacts = environment.RecentEvents.Count(value =>
                value.Kind == EnvironmentEventKindV0.BallPaddleContact);

            Assert.That(contacts, Is.EqualTo(1));
            Assert.That(
                result.Observation.Episode.ControlledPaddleContacts,
                Is.EqualTo(1));
        }

        [Test]
        public void HighSpeedScenarioUsesCcdAndRegistersPaddle()
        {
            environment.Reset(new ResetRequestV0(
                5UL,
                ScenarioCatalogV0.StabilityHighSpeed));
            var result = RunUntilTerminal();

            Assert.That(
                result.Observation.Episode.ControlledPaddleContacts,
                Is.GreaterThanOrEqualTo(1));
            Assert.That(ObservationValidatorV0.IsFinite(result.Observation), Is.True);
        }

        [Test]
        public void NetContactIsRecordedAndFlightContinuesToClassifiedTerminal()
        {
            environment.Reset(new ResetRequestV0(
                6UL,
                ScenarioCatalogV0.NetContactContinues,
                overrides: new[]
                {
                    new ResetOverrideV0("ball.position.x", 0f),
                    new ResetOverrideV0("ball.velocity.x", 0f)
                }));
            var result = RunUntilTerminal();
            var events = environment.RecentEvents.ToArray();

            Assert.That(
                events.Any(value => value.Kind == EnvironmentEventKindV0.BallNetContact),
                Is.True);
            Assert.That(result.TerminationReason, Is.Not.EqualTo(TerminationReasonV0.None));
            Assert.That(result.TerminationReason, Is.Not.EqualTo(TerminationReasonV0.InvalidNumericState));
        }

        [Test]
        public void NetClearScenarioDoesNotTouchNet()
        {
            environment.Reset(new ResetRequestV0(
                61UL,
                ScenarioCatalogV0.NetClear,
                overrides: new[]
                {
                    new ResetOverrideV0("ball.position.x", 0f),
                    new ResetOverrideV0("ball.velocity.x", 0f)
                }));
            var result = RunUntilTerminal();

            Assert.That(
                environment.RecentEvents.Any(value =>
                    value.Kind == EnvironmentEventKindV0.BallNetContact),
                Is.False);
            Assert.That(result.TerminationReason, Is.Not.EqualTo(TerminationReasonV0.None));
        }

        [Test]
        public void OutLandingIsClassified()
        {
            environment.Reset(new ResetRequestV0(
                62UL,
                ScenarioCatalogV0.BoundaryCourt,
                overrides: new[]
                {
                    new ResetOverrideV0(
                        "ball.position.x",
                        CourtGeometryV0.HalfWidth + 0.5f),
                    new ResetOverrideV0("ball.position.z", 4f),
                    new ResetOverrideV0("ball.velocity.x", 0f),
                    new ResetOverrideV0("ball.velocity.y", -1f),
                    new ResetOverrideV0("ball.velocity.z", 0f)
                }));
            var result = RunUntilTerminal();

            Assert.That(
                result.TerminationReason,
                Is.EqualTo(TerminationReasonV0.OutOfBoundsLanding));
            Assert.That(result.RewardFeatures.OutLanding, Is.EqualTo(1f));
        }

        [Test]
        public void PlayableVolumeExitIsClassified()
        {
            environment.Reset(new ResetRequestV0(
                63UL,
                ScenarioCatalogV0.LaunchRally,
                overrides: new[]
                {
                    new ResetOverrideV0("ball.position.y", 7.99f),
                    new ResetOverrideV0("ball.velocity.x", 0f),
                    new ResetOverrideV0("ball.velocity.y", 5f),
                    new ResetOverrideV0("ball.velocity.z", 0f)
                }));
            var result = RunUntilTerminal();

            Assert.That(
                result.TerminationReason,
                Is.EqualTo(TerminationReasonV0.PlayableVolumeExit));
            Assert.That(
                result.Events.Any(value =>
                    value.Kind == EnvironmentEventKindV0.BallExitedPlayableVolume),
                Is.True);
        }

        [Test]
        public void ScenarioTimeoutIsExactAndClassified()
        {
            environment.Reset(new ResetRequestV0(
                7UL,
                ScenarioCatalogV0.LaunchRally,
                overrides: new[]
                {
                    new ResetOverrideV0("ball.position.y", 5f),
                    new ResetOverrideV0("ball.velocity.x", 0f),
                    new ResetOverrideV0("ball.velocity.y", 0f),
                    new ResetOverrideV0("ball.velocity.z", 0f),
                    new ResetOverrideV0("maximum_episode_seconds", 0.016f)
                }));
            var result = RunUntilTerminal();

            Assert.That(
                result.TerminationReason,
                Is.EqualTo(TerminationReasonV0.Timeout));
            Assert.That(result.Observation.PhysicsTick, Is.EqualTo(2UL));
        }

        [Test]
        public void TimeScaleDoesNotChangeSimulatedReplay()
        {
            var first = ReplayAtTimeScale(1f);
            var second = ReplayAtTimeScale(8f);
            Assert.That(second.Termination, Is.EqualTo(first.Termination));
            Assert.That(second.EventKinds, Is.EqualTo(first.EventKinds));
            Assert.That(
                Vector3.Distance(second.FinalPosition, first.FinalPosition),
                Is.LessThanOrEqualTo(environment.Configuration.ReplayPositionTolerance));
            Assert.That(
                Vector3.Distance(second.FinalVelocity, first.FinalVelocity),
                Is.LessThanOrEqualTo(environment.Configuration.ReplayVelocityTolerance));
        }

        [Test]
        public void RecordedActionReplayProducesStableEventsAndTerminal()
        {
            var first = ReplayFixedActions();
            var second = ReplayFixedActions();

            Assert.That(second.Termination, Is.EqualTo(first.Termination));
            Assert.That(second.EventKinds, Is.EqualTo(first.EventKinds));
            Assert.That(
                Vector3.Distance(second.FinalPosition, first.FinalPosition),
                Is.LessThanOrEqualTo(environment.Configuration.ReplayPositionTolerance));
            Assert.That(
                Vector3.Distance(second.FinalVelocity, first.FinalVelocity),
                Is.LessThanOrEqualTo(environment.Configuration.ReplayVelocityTolerance));
        }

        [Test]
        public void StepAfterTerminalFailsVisibly()
        {
            environment.Reset(new ResetRequestV0(
                8UL,
                ScenarioCatalogV0.LaunchRally,
                overrides: new[]
                {
                    new ResetOverrideV0("maximum_episode_seconds", 0.01f)
                }));
            RunUntilTerminal();
            Assert.Throws<InvalidOperationException>(
                () => environment.Step(PaddleActionV0.Zero));
        }

        private StepResultV0 RunUntilTerminal(int maximumActions = 1500)
        {
            StepResultV0 result = null;
            for (var index = 0; index < maximumActions; index++)
            {
                result = environment.Step(PaddleActionV0.Zero);
                Assert.That(ObservationValidatorV0.IsFinite(result.Observation), Is.True);
                if (result.IsTerminal)
                {
                    return result;
                }
            }

            Assert.Fail($"Episode did not terminate within {maximumActions} actions.");
            return result;
        }

        private ReplayResult ReplayAtTimeScale(float scale)
        {
            Time.timeScale = scale;
            return ReplayFixedActions();
        }

        private ReplayResult ReplayFixedActions()
        {
            environment.Reset(new ResetRequestV0(
                42UL,
                ScenarioCatalogV0.LaunchRally));
            var kinds = new List<EnvironmentEventKindV0>();
            StepResultV0 result = null;
            for (var index = 0; index < 1500; index++)
            {
                var action = index < 20
                    ? new PaddleActionV0(
                        new Vector3(0.05f, 0f, 0f),
                        new Vector3(0f, 0.02f, 0f))
                    : PaddleActionV0.Zero;
                result = environment.Step(action);
                kinds.AddRange(result.Events.Select(value => value.Kind));
                if (result.IsTerminal)
                {
                    return new ReplayResult(
                        result.TerminationReason,
                        kinds.ToArray(),
                        result.Observation.Ball.PositionWorld,
                        result.Observation.Ball.LinearVelocityWorld);
                }
            }

            Assert.Fail("Replay did not terminate.");
            return default;
        }

        private static void AssertOrdered(IReadOnlyList<EnvironmentEventV0> events)
        {
            foreach (var group in events.GroupBy(value => value.PhysicsTick))
            {
                var expectedSequence = 0;
                var priorPhase = -1;
                foreach (var current in group)
                {
                    Assert.That(current.Sequence, Is.EqualTo(expectedSequence++));
                    var phase = EventOrderingV0.Phase(current.Kind);
                    Assert.That(phase, Is.GreaterThanOrEqualTo(priorPhase));
                    priorPhase = phase;
                }
            }
        }

        private readonly struct ReplayResult
        {
            public readonly TerminationReasonV0 Termination;
            public readonly EnvironmentEventKindV0[] EventKinds;
            public readonly Vector3 FinalPosition;
            public readonly Vector3 FinalVelocity;

            public ReplayResult(
                TerminationReasonV0 termination,
                EnvironmentEventKindV0[] eventKinds,
                Vector3 finalPosition,
                Vector3 finalVelocity)
            {
                Termination = termination;
                EventKinds = eventKinds;
                FinalPosition = finalPosition;
                FinalVelocity = finalVelocity;
            }
        }
    }
}

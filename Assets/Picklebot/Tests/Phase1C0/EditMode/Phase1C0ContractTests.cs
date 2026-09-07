using System;
using System.Linq;
using NUnit.Framework;
using Picklebot.Core;
using Picklebot.Evaluation;
using UnityEngine;

namespace Picklebot.Tests.Phase1C0.EditMode
{
    public sealed class Phase1C0ContractTests
    {
        [Test]
        public void ProtocolUsesCurrentTrainerPairAndDisjointSeeds()
        {
            Phase1CProtocolV0.ValidateOrThrow();

            Assert.That(
                Phase1CProtocolV0.UnityTrainerPackage,
                Is.EqualTo("com.unity.ml-agents@4.0.3"));
            Assert.That(
                Phase1CProtocolV0.PythonTrainerPackage,
                Is.EqualTo("mlagents==1.1.0"));
            Assert.That(
                Phase1CProtocolV0.TrainingSeeds.Overlaps(
                    Phase1CProtocolV0.ValidationSeeds),
                Is.False);
            Assert.That(
                Phase1CProtocolV0.TrainingSeeds.Overlaps(
                    Phase1CProtocolV0.FinalEvaluationSeeds),
                Is.False);
            Assert.That(
                Phase1CProtocolV0.ValidationSeeds.Overlaps(
                    Phase1CProtocolV0.FinalEvaluationSeeds),
                Is.False);
        }

        [Test]
        public void ProtocolExposesNoFinalEvaluationRequestBuilder()
        {
            var publicBuilders = typeof(Phase1CProtocolV0)
                .GetMethods()
                .Where(value => value.IsPublic && value.IsStatic)
                .Select(value => value.Name)
                .ToArray();

            Assert.That(publicBuilders, Does.Contain("TrainingRequest"));
            Assert.That(publicBuilders, Does.Contain("ValidationRequest"));
            Assert.That(
                publicBuilders.Any(value =>
                    value.Contains("Final", StringComparison.Ordinal) ||
                    value.Contains("Evaluation", StringComparison.Ordinal)),
                Is.False);
        }

        [Test]
        public void ObservationEncoderWritesExactlyThirtySevenFiniteValues()
        {
            var destination = Enumerable
                .Repeat(float.NaN, Phase1CObservationEncoderV0.Size + 2)
                .ToArray();
            Phase1CObservationEncoderV0.Encode(
                ExampleObservation(),
                destination,
                1);

            Assert.That(Phase1CObservationEncoderV0.Size, Is.EqualTo(37));
            Assert.That(destination[0], Is.NaN);
            Assert.That(destination[^1], Is.NaN);
            Assert.That(
                destination
                    .Skip(1)
                    .Take(Phase1CObservationEncoderV0.Size)
                    .All(value =>
                        FiniteMath.IsFinite(value) &&
                        value >= -1f &&
                        value <= 1f),
                Is.True);
        }

        [Test]
        public void RewardAddsBoundedProgressAndSmoothnessTerms()
        {
            var features = new RewardFeaturesV0
            {
                PaddleContactCount = 1,
                FarCourtLanding = 1f,
                TargetDistanceAtLanding = 2f,
                ElapsedTime = 0.5f
            };
            var state = new Phase1CRewardStateV0(
                previousElapsedTime: 0.25f,
                previousInterceptDistance: 1f,
                currentInterceptDistance: 0.75f,
                hasControlledPaddleContact: false,
                previousAction: PaddleActionV0.Zero,
                currentAction: new PaddleActionV0(
                    Vector3.one,
                    Vector3.one));

            var reward = Phase1CRewardV0.Evaluate(features, state);

            Assert.That(reward.FeatureReward, Is.EqualTo(1.1495f).Within(0.000001f));
            Assert.That(
                reward.InterceptionProgressReward,
                Is.EqualTo(0.0125f).Within(0.000001f));
            Assert.That(
                reward.ActionChangeReward,
                Is.EqualTo(-0.0005f).Within(0.000001f));
            Assert.That(reward.Total, Is.EqualTo(1.1615f).Within(0.000001f));
            Assert.That(Phase1CRewardV0.Hash, Has.Length.EqualTo(16));
            Assert.That(
                Phase1CProtocolV0.RewardMappingHash,
                Is.EqualTo(Phase1CRewardV0.Hash));
        }

        [Test]
        public void RewardStopsProgressShapingAfterPaddleContact()
        {
            var reward = Phase1CRewardV0.Evaluate(
                default,
                new Phase1CRewardStateV0(
                    previousElapsedTime: 0f,
                    previousInterceptDistance: 5f,
                    currentInterceptDistance: 0f,
                    hasControlledPaddleContact: true,
                    previousAction: PaddleActionV0.Zero,
                    currentAction: PaddleActionV0.Zero));

            Assert.That(reward.InterceptionProgressReward, Is.Zero);
            Assert.That(reward.Total, Is.Zero);
        }

        [Test]
        public void EvaluationAssemblyStillHasNoTrainerDependency()
        {
            var references = typeof(Phase1CProtocolV0)
                .Assembly
                .GetReferencedAssemblies()
                .Select(value => value.Name)
                .ToArray();

            Assert.That(references, Does.Not.Contain("Picklebot.Simulation"));
            Assert.That(
                references.Any(value => value.Contains("MLAgents")),
                Is.False);
            Assert.That(
                references.Any(value => value.Contains("MCPForUnity")),
                Is.False);
        }

        [Test]
        public void EpisodeMetricsRejectFinalSeedsAndAggregateNamedOutcomes()
        {
            Assert.Throws<ArgumentException>(() =>
                new Phase1C0EpisodeAccumulatorV0(
                    Phase1C0SeedUseV0.Validation,
                    1,
                    ExampleManifest(
                        Phase1CProtocolV0.FinalEvaluationSeeds.First)));

            var legal = CompletedRecord(
                Phase1CProtocolV0.ValidationSeeds.At(0),
                TerminationReasonV0.FarCourtLanding,
                paddleContact: true,
                netContact: false,
                landingError: 0.5f);
            var outRecord = CompletedRecord(
                Phase1CProtocolV0.ValidationSeeds.At(1),
                TerminationReasonV0.OutOfBoundsLanding,
                paddleContact: false,
                netContact: true,
                landingError: -1f);

            var summary = Phase1C0MetricsV0.Aggregate(
                new[] { legal, outRecord });

            Assert.That(summary.provisional, Is.True);
            Assert.That(summary.episodes, Is.EqualTo(2));
            Assert.That(summary.contactRate, Is.EqualTo(0.5f));
            Assert.That(summary.legalReturnRate, Is.EqualTo(0.5f));
            Assert.That(summary.targetHitRate, Is.EqualTo(0.5f));
            Assert.That(summary.netContactRate, Is.EqualTo(0.5f));
            Assert.That(summary.outRate, Is.EqualTo(0.5f));
            Assert.That(summary.landingErrorSamples, Is.EqualTo(1));
            Assert.That(summary.meanLandingError, Is.EqualTo(0.5f));
        }

        private static Phase1C0EpisodeRecordV0 CompletedRecord(
            ulong seed,
            TerminationReasonV0 terminalReason,
            bool paddleContact,
            bool netContact,
            float landingError)
        {
            var accumulator = new Phase1C0EpisodeAccumulatorV0(
                Phase1C0SeedUseV0.Validation,
                1,
                ExampleManifest(seed));
            var features = new RewardFeaturesV0
            {
                PaddleContactCount = paddleContact ? 1 : 0,
                NetContactCount = netContact ? 1 : 0,
                FarCourtLanding =
                    terminalReason == TerminationReasonV0.FarCourtLanding
                        ? 1f
                        : 0f,
                OutLanding =
                    terminalReason == TerminationReasonV0.OutOfBoundsLanding
                        ? 1f
                        : 0f,
                TargetDistanceAtLanding = landingError,
                ElapsedTime = 0.1f
            };
            accumulator.Observe(
                new StepResultV0(
                    ExampleObservation(),
                    Array.Empty<EnvironmentEventV0>(),
                    features,
                    isTerminal: true,
                    terminalReason),
                PaddleActionV0.Zero,
                stepReward: paddleContact ? 1f : -0.5f);
            return accumulator.Complete();
        }

        private static EpisodeManifestV0 ExampleManifest(ulong seed)
        {
            return new EpisodeManifestV0
            {
                EnvironmentVersion = SimulationConfigV1.EnvironmentVersion,
                ConfigurationVersion = SimulationConfigV1.CanonicalVersion,
                ConfigurationHash = "provisional-test",
                PhysicsSettingsHash = "test",
                EpisodeId = 1UL,
                Seed = seed,
                ScenarioId = ScenarioCatalogV0.LaunchRally,
                Difficulty = "easy",
                Parameters = new ScenarioParametersV0
                {
                    BallPosition = new Vector3(0f, 1.15f, 2.8f),
                    BallRotation = Quaternion.identity,
                    BallLinearVelocity = new Vector3(0f, 1.25f, -7f),
                    BallAngularVelocity = Vector3.zero,
                    PaddlePosition = new Vector3(0f, 1.05f, -1.35f),
                    PaddleRotation = Quaternion.identity,
                    TargetPosition = new Vector3(0f, 0f, 4.4f),
                    MaximumEpisodeSeconds = 6f
                }
            };
        }

        private static ObservationV0 ExampleObservation()
        {
            return new ObservationV0
            {
                EnvironmentVersion = SimulationConfigV1.EnvironmentVersion,
                EpisodeId = 1UL,
                Seed = Phase1CProtocolV0.TrainingSeeds.First,
                ScenarioId = ScenarioCatalogV0.LaunchRally,
                PhysicsTick = 12UL,
                ElapsedTime = 0.1f,
                Ball = new KinematicSnapshotV0
                {
                    PositionWorld = new Vector3(0.2f, 1.2f, 2f),
                    RotationWorld = Quaternion.identity,
                    LinearVelocityWorld = new Vector3(-0.1f, 1f, -7f),
                    AngularVelocityWorld = new Vector3(1f, 2f, 3f)
                },
                Paddle = new KinematicSnapshotV0
                {
                    PositionWorld = new Vector3(0f, 1.05f, -1.35f),
                    RotationWorld = Quaternion.identity,
                    LinearVelocityWorld = new Vector3(0.2f, 0f, 0f),
                    AngularVelocityWorld = Vector3.zero
                },
                BallPositionFromPaddle = new Vector3(0.2f, 0.15f, 3.35f),
                BallVelocityFromPaddle = new Vector3(-0.3f, 1f, -7f),
                Episode = new EpisodeSnapshotV0
                {
                    State = EpisodeStateV0.Running,
                    LastTouch = LastTouchV0.Launcher
                }
            };
        }
    }
}

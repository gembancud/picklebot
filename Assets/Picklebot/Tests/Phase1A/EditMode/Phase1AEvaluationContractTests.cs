using System;
using System.Linq;
using NUnit.Framework;
using Picklebot.Core;
using Picklebot.Evaluation;
using UnityEngine;

namespace Picklebot.Tests.Phase1A.EditMode
{
    public sealed class Phase1AEvaluationContractTests
    {
        [Test]
        public void SeedPartitionsAreVersionedAndDisjoint()
        {
            Phase1AProtocolV0.ValidateOrThrow();

            Assert.That(
                Phase1AProtocolV0.TrainingSeeds.Overlaps(
                    Phase1AProtocolV0.ValidationSeeds),
                Is.False);
            Assert.That(
                Phase1AProtocolV0.TrainingSeeds.Overlaps(
                    Phase1AProtocolV0.HeldOutEvaluationSeeds),
                Is.False);
            Assert.That(
                Phase1AProtocolV0.ValidationSeeds.Overlaps(
                    Phase1AProtocolV0.HeldOutEvaluationSeeds),
                Is.False);
            Assert.That(
                Phase1AProtocolV0.HeldOutEvaluationSeeds.Count,
                Is.EqualTo(Phase1AProtocolV0.BaselineEpisodeCount));
            Assert.That(Phase1AProtocolV0.Hash, Has.Length.EqualTo(16));
        }

        [Test]
        public void EvaluationRequestsUseOnlyHeldOutSeeds()
        {
            for (var index = 0;
                 index < Phase1AProtocolV0.HeldOutEvaluationSeeds.Count;
                 index++)
            {
                var request = Phase1AProtocolV0.EvaluationRequest(index);
                Assert.That(
                    Phase1AProtocolV0.HeldOutEvaluationSeeds.Contains(request.Seed),
                    Is.True);
                Assert.That(
                    Phase1AProtocolV0.TrainingSeeds.Contains(request.Seed),
                    Is.False);
                Assert.That(
                    Phase1AProtocolV0.ValidationSeeds.Contains(request.Seed),
                    Is.False);
                Assert.That(
                    request.ScenarioId,
                    Is.EqualTo(ScenarioCatalogV0.LaunchRally));
                Assert.That(request.Overrides.Count, Is.EqualTo(1));
                Assert.That(
                    request.Overrides[0].Key,
                    Is.EqualTo("ball.velocity.y"));
                Assert.That(request.Overrides[0].Value, Is.GreaterThan(0f));
            }
        }

        [Test]
        public void EvaluationRequestsCoverEveryApprovedDifficulty()
        {
            var difficulties = Enumerable.Range(0, 9)
                .Select(index => Phase1AProtocolV0.EvaluationRequest(index).Difficulty)
                .Distinct()
                .OrderBy(value => value)
                .ToArray();

            Assert.That(
                difficulties,
                Is.EqualTo(new[] { "default", "easy", "hard" }));
        }

        [Test]
        public void CurriculumOrderAndPromotionThresholdsAreStable()
        {
            Assert.That(
                Phase1AProtocolV0.CurriculumStages
                    .Select(value => value.Id)
                    .ToArray(),
                Is.EqualTo(new[]
                {
                    "p1a/contact-easy",
                    "p1a/return-easy",
                    "p1a/place-default",
                    "p1a/robust-hard"
                }));
            Assert.That(
                Phase1AProtocolV0.CurriculumStages
                    .Select(value => value.PromotionThreshold)
                    .ToArray(),
                Is.EqualTo(new[] { 0.90f, 0.70f, 0.55f, 0.45f }));
        }

        [Test]
        public void CurriculumRequestsStayInsideTheirAssignedSeedPartition()
        {
            for (var stage = 0;
                 stage < Phase1AProtocolV0.CurriculumStages.Count;
                 stage++)
            {
                var training = Phase1AProtocolV0.TrainingRequest(stage, stage);
                var validation = Phase1AProtocolV0.ValidationRequest(stage, stage);

                Assert.That(
                    Phase1AProtocolV0.TrainingSeeds.Contains(training.Seed),
                    Is.True);
                Assert.That(
                    Phase1AProtocolV0.ValidationSeeds.Contains(validation.Seed),
                    Is.True);
                Assert.That(training.ScenarioId, Is.EqualTo(
                    Phase1AProtocolV0.CurriculumStages[stage].ScenarioId));
                Assert.That(validation.Difficulty, Is.EqualTo(
                    Phase1AProtocolV0.CurriculumStages[stage].Difficulty));
            }
        }

        [Test]
        public void ObservationEncoderWritesExactlyTheFrozenShape()
        {
            var destination = Enumerable.Repeat(float.NaN, 41).ToArray();
            Phase1AObservationEncoderV0.Encode(
                ExampleObservation(),
                destination,
                2);

            Assert.That(Phase1AObservationEncoderV0.Size, Is.EqualTo(37));
            Assert.That(destination[0], Is.NaN);
            Assert.That(destination[1], Is.NaN);
            Assert.That(destination[39], Is.NaN);
            Assert.That(destination[40], Is.NaN);
            Assert.That(
                destination.Skip(2).Take(37).All(value =>
                    FiniteMath.IsFinite(value) &&
                    value >= -1f &&
                    value <= 1f),
                Is.True);
        }

        [Test]
        public void ObservationEncoderUsesOneHotLastTouch()
        {
            var destination = new float[Phase1AObservationEncoderV0.Size];
            Phase1AObservationEncoderV0.Encode(
                ExampleObservation(),
                destination);

            Assert.That(destination.Skip(29).Take(6).Sum(), Is.EqualTo(1f));
            Assert.That(
                destination[29 + (int)LastTouchV0.ControlledPaddle],
                Is.EqualTo(1f));
        }

        [Test]
        public void ObservationEncoderRejectsShortBuffers()
        {
            Assert.Throws<ArgumentOutOfRangeException>(() =>
                Phase1AObservationEncoderV0.Encode(
                    ExampleObservation(),
                    new float[Phase1AObservationEncoderV0.Size - 1]));
        }

        [Test]
        public void RewardMappingUsesElapsedDeltaNotAbsoluteTime()
        {
            var features = new RewardFeaturesV0
            {
                PaddleContactCount = 1,
                FarCourtLanding = 1f,
                NetContactCount = 1,
                TargetDistanceAtLanding = 2f,
                ElapsedTime = 0.5f
            };

            var reward = Phase1AProtocolV0.RewardMapping.MapStep(
                features,
                previousElapsedTime: 0.25f);

            Assert.That(reward, Is.EqualTo(1.0995f).Within(0.000001f));
            Assert.That(Phase1AProtocolV0.RewardMapping.Hash, Has.Length.EqualTo(16));
        }

        [Test]
        public void ZeroPolicyAlwaysProducesCanonicalZeroAction()
        {
            var policy = new ZeroPolicyV0();
            policy.Reset(ExampleManifest());
            var action = policy.Decide(ExampleObservation());

            Assert.That(action.LinearVelocityLocal, Is.EqualTo(Vector3.zero));
            Assert.That(action.AngularVelocityLocal, Is.EqualTo(Vector3.zero));
        }

        [Test]
        public void InterceptPolicyProducesFiniteBoundedActions()
        {
            var policy = new InterceptHeuristicPolicyV0();
            policy.Reset(ExampleManifest());
            var action = policy.Decide(ExampleObservation());

            Assert.That(FiniteMath.IsFinite(action.LinearVelocityLocal), Is.True);
            Assert.That(FiniteMath.IsFinite(action.AngularVelocityLocal), Is.True);
            Assert.That(action.LinearVelocityLocal.x, Is.InRange(-1f, 1f));
            Assert.That(action.LinearVelocityLocal.y, Is.InRange(-1f, 1f));
            Assert.That(action.LinearVelocityLocal.z, Is.InRange(-1f, 1f));
        }

        [Test]
        public void EvaluationAssemblyDoesNotReferenceSimulationTrainerOrMcp()
        {
            var references = typeof(Phase1AProtocolV0)
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

        private static EpisodeManifestV0 ExampleManifest()
        {
            return new EpisodeManifestV0
            {
                EnvironmentVersion = EnvironmentVersion.Current,
                ConfigurationVersion = SimulationConfigV0.CanonicalVersion,
                ConfigurationHash = "test",
                PhysicsSettingsHash = "test",
                EpisodeId = 1UL,
                Seed = 4000000UL,
                ScenarioId = ScenarioCatalogV0.LaunchRally,
                Difficulty = "default",
                Parameters = new ScenarioParametersV0
                {
                    BallPosition = new Vector3(0.2f, 1.15f, 2.8f),
                    BallRotation = Quaternion.identity,
                    BallLinearVelocity = new Vector3(-0.1f, 1.25f, -7f),
                    BallAngularVelocity = new Vector3(1f, 2f, 3f),
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
                EnvironmentVersion = EnvironmentVersion.Current,
                EpisodeId = 1UL,
                Seed = 4000000UL,
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
                    LastTouch = LastTouchV0.ControlledPaddle,
                    ControlledPaddleContacts = 1,
                    BallFloorContacts = 0
                }
            };
        }
    }
}

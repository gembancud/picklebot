using System.Linq;
using NUnit.Framework;
using Picklebot.Core;
using Picklebot.Evaluation;
using Picklebot.Simulation;
using UnityEngine;

namespace Picklebot.Tests.Phase1B.PlayMode
{
    public sealed class Phase1BCalibratedEnvironmentTests
    {
        private PicklebotEnvironmentFixtureV1 fixture;

        [SetUp]
        public void SetUp()
        {
            fixture = PicklebotEnvironmentFactoryV1.Create();
        }

        [TearDown]
        public void TearDown()
        {
            fixture?.Destroy();
        }

        [Test]
        public void FactoryBuildsCalibratedV1GeometryAndBodySettings()
        {
            var environment = fixture.Environment;
            var observation = environment.Reset(new ResetRequestV0(
                100UL,
                ScenarioCatalogV0.LaunchRally));

            Assert.That(
                environment.CurrentManifest.EnvironmentVersion,
                Is.EqualTo("env-v1"));
            Assert.That(
                environment.CurrentManifest.ConfigurationVersion,
                Is.EqualTo(SimulationConfigV1.CanonicalVersion));
            Assert.That(observation.EnvironmentVersion, Is.EqualTo("env-v1"));
            Assert.That(environment.Ball.useGravity, Is.False);
            Assert.That(environment.Ball.linearDamping, Is.Zero);
            Assert.That(environment.Ball.angularDamping, Is.Zero);
            Assert.That(
                environment.Ball.collisionDetectionMode,
                Is.EqualTo(CollisionDetectionMode.ContinuousDynamic));
            Assert.That(environment.Paddle.isKinematic, Is.True);

            Assert.That(fixture.PaddleFaceCollider, Is.TypeOf<MeshCollider>());
            var meshCollider = (MeshCollider)fixture.PaddleFaceCollider;
            Assert.That(meshCollider.convex, Is.True);
            Assert.That(
                Vector3.Distance(
                    meshCollider.sharedMesh.bounds.size,
                    CourtGeometryV1.PaddleFaceSize),
                Is.LessThan(0.000001f));
            Assert.That(
                fixture.PaddleFaceCollider
                    .GetComponentInParent<CollisionIdentityV0>().Kind,
                Is.EqualTo(CollisionEntityKindV0.ControlledPaddle));
            Assert.That(
                fixture.PaddleHandleCollider
                    .GetComponentInParent<CollisionIdentityV0>().Kind,
                Is.EqualTo(CollisionEntityKindV0.Other));

            Assert.That(fixture.NetColliders.Count, Is.EqualTo(4));
            Assert.That(
                fixture.NetColliders.Sum(value => value.transform.localScale.x),
                Is.EqualTo(CourtGeometryV1.NetPostSpan).Within(0.000001f));
        }

        [Test]
        public void IntegratedStepAppliesQuadraticDragAndExplicitGravity()
        {
            var environment = fixture.Environment;
            environment.Reset(new ResetRequestV0(
                101UL,
                ScenarioCatalogV0.LaunchRally,
                overrides: new[]
                {
                    new ResetOverrideV0("ball.position.x", 2f),
                    new ResetOverrideV0("ball.position.y", 4f),
                    new ResetOverrideV0("ball.position.z", -4f),
                    new ResetOverrideV0("ball.velocity.x", 0f),
                    new ResetOverrideV0("ball.velocity.y", 0f),
                    new ResetOverrideV0("ball.velocity.z", 10f),
                    new ResetOverrideV0("ball.angular_velocity.x", 0f),
                    new ResetOverrideV0("ball.angular_velocity.y", 0f),
                    new ResetOverrideV0("ball.angular_velocity.z", 0f),
                    new ResetOverrideV0("paddle.position.x", -2f),
                    new ResetOverrideV0("maximum_episode_seconds", 2f)
                }));

            var result = environment.Step(PaddleActionV0.Zero);

            Assert.That(result.IsTerminal, Is.False);
            Assert.That(environment.LastAerodynamicForces.DragForce.z, Is.LessThan(0f));
            Assert.That(environment.LastAerodynamicForces.LiftForce, Is.EqualTo(Vector3.zero));
            Assert.That(result.Observation.Ball.LinearVelocityWorld.z, Is.LessThan(10f));
            Assert.That(result.Observation.Ball.LinearVelocityWorld.y, Is.LessThan(0f));
        }

        [Test]
        public void IntegratedPaddleBrushGeneratesObservableSymmetricSpin()
        {
            var upwardBrushSpin = RunIntegratedBrush(0.2f);
            var downwardBrushSpin = RunIntegratedBrush(-0.2f);

            Assert.That(upwardBrushSpin.magnitude, Is.GreaterThan(0.1f));
            Assert.That(downwardBrushSpin.magnitude, Is.GreaterThan(0.1f));
            Assert.That(
                Vector3.Dot(upwardBrushSpin, downwardBrushSpin),
                Is.LessThan(0f));
            Assert.That(
                upwardBrushSpin.magnitude,
                Is.LessThanOrEqualTo(
                    fixture.Configuration.MaximumBallAngularSpeed));
            Assert.That(
                downwardBrushSpin.magnitude,
                Is.LessThanOrEqualTo(
                    fixture.Configuration.MaximumBallAngularSpeed));
        }

        [Test]
        public void UnityFlightTracksIndependentRk4Reference()
        {
            var environment = fixture.Environment;
            var initialPosition = new Vector3(2f, 4f, -4f);
            var initialVelocity = new Vector3(0f, 2f, 12f);
            var initialSpin = new Vector3(31.415927f, 0f, 0f);
            environment.Reset(new ResetRequestV0(
                103UL,
                ScenarioCatalogV0.LaunchRally,
                overrides: new[]
                {
                    new ResetOverrideV0("ball.position.x", initialPosition.x),
                    new ResetOverrideV0("ball.position.y", initialPosition.y),
                    new ResetOverrideV0("ball.position.z", initialPosition.z),
                    new ResetOverrideV0("ball.velocity.x", initialVelocity.x),
                    new ResetOverrideV0("ball.velocity.y", initialVelocity.y),
                    new ResetOverrideV0("ball.velocity.z", initialVelocity.z),
                    new ResetOverrideV0("ball.angular_velocity.x", initialSpin.x),
                    new ResetOverrideV0("ball.angular_velocity.y", initialSpin.y),
                    new ResetOverrideV0("ball.angular_velocity.z", initialSpin.z),
                    new ResetOverrideV0("paddle.position.x", -2f),
                    new ResetOverrideV0("maximum_episode_seconds", 2f)
                }));

            StepResultV0 result = null;
            for (var action = 0; action < 30; action++)
            {
                result = environment.Step(PaddleActionV0.Zero);
                Assert.That(result.IsTerminal, Is.False);
            }

            var reference = FlightReferenceIntegratorV1.Integrate(
                new FlightStateV1(
                    initialPosition,
                    initialVelocity,
                    initialSpin),
                0.5f,
                0.001f,
                fixture.Configuration.BallMass,
                fixture.Configuration.Gravity,
                fixture.Configuration.AerodynamicParameters);

            Assert.That(
                Vector3.Distance(
                    result.Observation.Ball.PositionWorld,
                    reference.Position),
                Is.LessThanOrEqualTo(0.05f));
            Assert.That(
                Vector3.Distance(
                    result.Observation.Ball.LinearVelocityWorld,
                    reference.Velocity),
                Is.LessThanOrEqualTo(0.05f));
        }

        [Test]
        public void SameSeedAndActionsReplayInsideV1Tolerance()
        {
            var first = Replay();
            var second = Replay();

            Assert.That(second.Termination, Is.EqualTo(first.Termination));
            Assert.That(
                Vector3.Distance(second.Position, first.Position),
                Is.LessThanOrEqualTo(fixture.Configuration.ReplayPositionTolerance));
            Assert.That(
                Vector3.Distance(second.Velocity, first.Velocity),
                Is.LessThanOrEqualTo(fixture.Configuration.ReplayVelocityTolerance));
        }

        [Test]
        public void ProvisionalOfficialDropFixtureIsDeterministicAndFinite()
        {
            var first = CalibrationFixturesV1.RunBallDrop(
                fixture.Configuration,
                DropReleaseDatumV1.BallTop);
            var second = CalibrationFixturesV1.RunBallDrop(
                fixture.Configuration,
                DropReleaseDatumV1.BallTop);

            Assert.That(first.Completed, Is.True);
            Assert.That(first.FirstImpactTime, Is.GreaterThan(0f));
            var gravityOnlyImpactTime = Mathf.Sqrt(
                2f *
                (first.InitialCenterHeight - fixture.Configuration.BallDiameter / 2f) /
                fixture.Configuration.Gravity.magnitude);
            Assert.That(
                Mathf.Abs(first.FirstImpactTime - gravityOnlyImpactTime),
                Is.LessThanOrEqualTo(0.01f));
            Assert.That(
                first.FirstReboundTopHeight,
                Is.InRange(
                    CalibrationFixturesV1.OfficialMinimumReboundTopHeight,
                    CalibrationFixturesV1.OfficialMaximumReboundTopHeight));
            Assert.That(first.HorizontalDrift, Is.LessThanOrEqualTo(0.01f));
            Assert.That(
                first.PostImpactMechanicalEnergy,
                Is.LessThanOrEqualTo(first.PreImpactMechanicalEnergy + 0.00001f));
            Assert.That(second.FirstImpactTime, Is.EqualTo(first.FirstImpactTime));
            Assert.That(
                second.FirstReboundTopHeight,
                Is.EqualTo(first.FirstReboundTopHeight).Within(0.000001f));
            Assert.That(second.HorizontalDrift, Is.EqualTo(first.HorizontalDrift));
        }

        [TestCase(5f)]
        [TestCase(10f)]
        [TestCase(15f)]
        public void StationaryPaddleSurrogateStaysInsidePBCoRLimit(float speed)
        {
            var result = CalibrationFixturesV1.RunPaddleImpact(
                fixture.Configuration,
                speed,
                0f);

            Assert.That(result.Completed, Is.True);
            Assert.That(result.EffectiveRestitution, Is.LessThanOrEqualTo(0.43f));
            Assert.That(result.EffectiveRestitution, Is.InRange(0.37f, 0.43f));
            Assert.That(result.BallKineticEnergyRatio, Is.LessThanOrEqualTo(1f));
        }

        [Test]
        public void MovingPaddleProducesMonotonicOutgoingSpeed()
        {
            var paddleSpeeds = new[] { 0f, 2f, 4f, 6f };
            var results = paddleSpeeds
                .Select(value => CalibrationFixturesV1.RunPaddleImpact(
                    fixture.Configuration,
                    10f,
                    value))
                .ToArray();

            Assert.That(results.All(value => value.Completed), Is.True);
            for (var index = 1; index < results.Length; index++)
            {
                Assert.That(
                    results[index].OutgoingBallSpeed,
                    Is.GreaterThan(results[index - 1].OutgoingBallSpeed));
                Assert.That(
                    results[index].EffectiveRestitution,
                    Is.LessThanOrEqualTo(0.43f));
            }
        }

        [Test]
        public void OffCenterAndObliquePaddleImpactsAreFiniteSymmetricAndMeasureSpinTransfer()
        {
            var left = CalibrationFixturesV1.RunPaddleImpact(
                fixture.Configuration,
                10f,
                0f,
                new Vector2(-0.04f, 0f),
                0f,
                Vector3.zero);
            var right = CalibrationFixturesV1.RunPaddleImpact(
                fixture.Configuration,
                10f,
                0f,
                new Vector2(0.04f, 0f),
                0f,
                Vector3.zero);
            var oblique = CalibrationFixturesV1.RunPaddleImpact(
                fixture.Configuration,
                10f,
                0f,
                new Vector2(0f, 0.04f),
                3f,
                Vector3.zero);
            var reverseOblique = CalibrationFixturesV1.RunPaddleImpact(
                fixture.Configuration,
                10f,
                0f,
                new Vector2(0f, 0.04f),
                -3f,
                Vector3.zero);

            Assert.That(
                left.Completed &&
                right.Completed &&
                oblique.Completed &&
                reverseOblique.Completed,
                Is.True);
            Assert.That(
                Vector3.Distance(left.OutgoingBallVelocity, right.OutgoingBallVelocity),
                Is.LessThanOrEqualTo(0.001f));
            Assert.That(
                Vector3.Distance(left.OutgoingAngularVelocity, right.OutgoingAngularVelocity),
                Is.LessThanOrEqualTo(0.001f));
            Assert.That(FiniteMath.IsFinite(oblique.OutgoingBallVelocity), Is.True);
            Assert.That(FiniteMath.IsFinite(oblique.OutgoingAngularVelocity), Is.True);
            Assert.That(
                FiniteMath.IsFinite(oblique.TangentialVelocityChange),
                Is.True);
            Assert.That(
                FiniteMath.IsFinite(oblique.AngularVelocityChange),
                Is.True);
            Assert.That(
                oblique.TangentialVelocityChange,
                Is.EqualTo(Mathf.Abs(
                    oblique.OutgoingBallVelocity.x -
                    oblique.IncomingBallVelocity.x)));
            Assert.That(
                oblique.AngularVelocityChange,
                Is.EqualTo(Vector3.Distance(
                    oblique.OutgoingAngularVelocity,
                    oblique.IncomingAngularVelocity)));
            Assert.That(oblique.AngularVelocityChange, Is.GreaterThan(0.1f));
            Assert.That(
                Vector3.Dot(
                    oblique.OutgoingAngularVelocity,
                    reverseOblique.OutgoingAngularVelocity),
                Is.LessThan(0f));
            Assert.That(
                oblique.OutgoingAngularVelocity.magnitude,
                Is.LessThanOrEqualTo(
                    fixture.Configuration.MaximumBallAngularSpeed));
            Assert.That(
                reverseOblique.OutgoingAngularVelocity.magnitude,
                Is.LessThanOrEqualTo(
                    fixture.Configuration.MaximumBallAngularSpeed));
            Assert.That(oblique.EffectiveRestitution, Is.LessThanOrEqualTo(0.43f));
            Assert.That(oblique.BallKineticEnergyRatio, Is.LessThanOrEqualTo(1f));
        }

        [Test]
        public void ProvisionalCourtFixtureCoversVerticalShallowAndSpunImpacts()
        {
            var cases = new[]
            {
                CalibrationFixturesV1.RunCourtImpact(
                    fixture.Configuration,
                    new Vector3(0f, -5f, 0f),
                    Vector3.zero),
                CalibrationFixturesV1.RunCourtImpact(
                    fixture.Configuration,
                    new Vector3(4f, -3f, 0f),
                    Vector3.zero),
                CalibrationFixturesV1.RunCourtImpact(
                    fixture.Configuration,
                    new Vector3(3f, -4f, 0f),
                    new Vector3(0f, 0f, 62.831853f))
            };

            foreach (var result in cases)
            {
                Assert.That(result.Completed, Is.True);
                Assert.That(result.LogicalContactCount, Is.EqualTo(1));
                Assert.That(FiniteMath.IsFinite(result.OutgoingVelocity), Is.True);
                Assert.That(
                    FiniteMath.IsFinite(result.OutgoingAngularVelocity),
                    Is.True);
                Assert.That(result.FirstReboundTopHeight, Is.GreaterThan(0f));
                Assert.That(
                    result.PostImpactMechanicalEnergy,
                    Is.LessThanOrEqualTo(
                        result.PreImpactMechanicalEnergy + 0.00001f));
            }
        }

        [Test]
        public void RegulationNetFixtureCoversClearanceTapeBodyAndPostSpan()
        {
            var clean = CalibrationFixturesV1.RunNetImpact(
                fixture.Configuration,
                0f,
                CourtGeometryV1.NetCenterHeight +
                    CourtGeometryV1.BallRadius +
                    0.08f,
                new Vector3(0f, 0f, 10f),
                Vector3.zero);
            var tape = CalibrationFixturesV1.RunNetImpact(
                fixture.Configuration,
                0f,
                CourtGeometryV1.NetCenterHeight,
                new Vector3(0f, 0f, 10f),
                Vector3.zero);
            var body = CalibrationFixturesV1.RunNetImpact(
                fixture.Configuration,
                0f,
                0.45f,
                new Vector3(0f, 0f, 10f),
                new Vector3(31.415927f, 0f, 0f));
            var postSpan = CalibrationFixturesV1.RunNetImpact(
                fixture.Configuration,
                CourtGeometryV1.HalfWidth + 0.15f,
                0.45f,
                new Vector3(0f, 0f, 10f),
                Vector3.zero);

            Assert.That(clean.ContactDetected, Is.False);
            Assert.That(clean.FinalVelocity.z, Is.GreaterThan(0f));
            foreach (var result in new[] { tape, body, postSpan })
            {
                Assert.That(result.ContactDetected, Is.True);
                Assert.That(result.ContinuedFlight, Is.True);
                Assert.That(FiniteMath.IsFinite(result.FinalVelocity), Is.True);
                Assert.That(
                    FiniteMath.IsFinite(result.FinalAngularVelocity),
                    Is.True);
                Assert.That(result.KineticEnergyRatio, Is.LessThanOrEqualTo(1f));
            }
        }

        [Test]
        public void CalibratedReadinessProbeMeasuresTheEnvV1StepPath()
        {
            var report = Phase1BReadinessV1.Measure(
                fixture.Environment,
                new InterceptHeuristicPolicyV0(),
                measuredActionSteps: 512,
                sourceCommit: "playmode-smoke");

            Assert.That(report.environmentVersion, Is.EqualTo("env-v1"));
            Assert.That(
                report.protocolVersion,
                Is.EqualTo(Phase1CProtocolV0.Version));
            Assert.That(report.measuredActionSteps, Is.EqualTo(512));
            Assert.That(report.completedEpisodes, Is.GreaterThan(0));
            Assert.That(report.actionStepsPerSecond, Is.GreaterThan(0d));
            Assert.That(report.allocationCounterAvailable, Is.True);
            Assert.That(
                report.allocatedBytesPerAction,
                Is.GreaterThanOrEqualTo(0d));
        }

        private ReplayResult Replay()
        {
            fixture.Environment.Reset(new ResetRequestV0(
                102UL,
                ScenarioCatalogV0.LaunchRally));

            StepResultV0 result = null;
            for (var index = 0; index < 1500; index++)
            {
                result = fixture.Environment.Step(PaddleActionV0.Zero);
                Assert.That(
                    ObservationValidatorV0.IsFinite(result.Observation),
                    Is.True);
                if (result.IsTerminal)
                {
                    return new ReplayResult(
                        result.TerminationReason,
                        result.Observation.Ball.PositionWorld,
                        result.Observation.Ball.LinearVelocityWorld);
                }
            }

            Assert.Fail("V1 replay did not terminate.");
            return default;
        }

        private Vector3 RunIntegratedBrush(float normalizedVerticalSpeed)
        {
            var environment = fixture.Environment;
            environment.Reset(new ResetRequestV0(
                104UL,
                ScenarioCatalogV0.ContactFrontOn,
                overrides: new[]
                {
                    new ResetOverrideV0("ball.angular_velocity.x", 0f),
                    new ResetOverrideV0("ball.angular_velocity.y", 0f),
                    new ResetOverrideV0("ball.angular_velocity.z", 0f),
                    new ResetOverrideV0("paddle.position.z", 0f)
                }));
            var action = new PaddleActionV0(
                new Vector3(0f, normalizedVerticalSpeed, 0f),
                Vector3.zero);

            for (var step = 0; step < 12; step++)
            {
                var result = environment.Step(action);
                if (result.Events.Any(value =>
                        value.Kind ==
                        EnvironmentEventKindV0.BallPaddleContact))
                {
                    return result.Observation.Ball.AngularVelocityWorld;
                }

                if (result.IsTerminal)
                {
                    break;
                }
            }

            Assert.Fail("Integrated brush fixture did not contact the paddle.");
            return Vector3.zero;
        }

        private readonly struct ReplayResult
        {
            public readonly TerminationReasonV0 Termination;
            public readonly Vector3 Position;
            public readonly Vector3 Velocity;

            public ReplayResult(
                TerminationReasonV0 termination,
                Vector3 position,
                Vector3 velocity)
            {
                Termination = termination;
                Position = position;
                Velocity = velocity;
            }
        }
    }
}

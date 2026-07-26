using System.Linq;
using NUnit.Framework;
using Picklebot.Core;
using Picklebot.Evaluation;
using UnityEngine;

namespace Picklebot.Tests.Phase1B.EditMode
{
    public sealed class Phase1BCalibrationCoreTests
    {
        private SimulationConfigV1 configuration;

        [SetUp]
        public void SetUp()
        {
            configuration = ScriptableObject.CreateInstance<SimulationConfigV1>();
        }

        [TearDown]
        public void TearDown()
        {
            Object.DestroyImmediate(configuration);
        }

        [Test]
        public void V1GeometryMatchesCalibrationSpecification()
        {
            Assert.That(CourtGeometryV1.CourtLength, Is.EqualTo(13.4112f));
            Assert.That(CourtGeometryV1.CourtWidth, Is.EqualTo(6.0960f));
            Assert.That(CourtGeometryV1.NonVolleyZoneDepth, Is.EqualTo(2.1336f));
            Assert.That(CourtGeometryV1.NetPostSpan, Is.EqualTo(6.7056f));
            Assert.That(CourtGeometryV1.NetSidelineHeight, Is.EqualTo(0.9144f));
            Assert.That(CourtGeometryV1.NetCenterHeight, Is.EqualTo(0.8636f));
            Assert.That(
                CourtGeometryV1.NetHeightAtX(0f),
                Is.EqualTo(CourtGeometryV1.NetCenterHeight));
            Assert.That(
                CourtGeometryV1.NetHeightAtX(CourtGeometryV1.HalfWidth),
                Is.EqualTo(CourtGeometryV1.NetSidelineHeight));
            Assert.That(
                CourtGeometryV1.NetHeightAtX(
                    CourtGeometryV1.HalfNetPostSpan - 0.001f),
                Is.EqualTo(CourtGeometryV1.NetSidelineHeight));
            Assert.That(CourtGeometryV1.BallMass, Is.EqualTo(0.024f));
            Assert.That(CourtGeometryV1.BallDiameter, Is.EqualTo(0.074f));
            Assert.That(CourtGeometryV1.PaddleWidth, Is.EqualTo(0.2032f));
            Assert.That(CourtGeometryV1.PaddleLength, Is.EqualTo(0.4064f));
            Assert.That(
                CourtGeometryV1.PaddleWidth + CourtGeometryV1.PaddleLength,
                Is.EqualTo(0.6096f).Within(0.000001f));
            Assert.That(
                CourtGeometryV1.PaddleFaceLength +
                CourtGeometryV1.PaddleHandleLength,
                Is.EqualTo(CourtGeometryV1.PaddleLength).Within(0.000001f));
        }

        [Test]
        public void DefaultConfigurationIsValidButExplicitlyProvisional()
        {
            Assert.DoesNotThrow(configuration.ValidateOrThrow);
            Assert.That(
                configuration.CalibrationState,
                Is.EqualTo(SimulationConfigV1.ProvisionalCalibrationState));
            Assert.That(
                SimulationConfigV1.EnvironmentVersion,
                Is.EqualTo("env-v1"));
            Assert.That(
                configuration.DragCoefficient,
                Is.EqualTo(0.30f));
            Assert.That(
                configuration.LiftCoefficientSlope,
                Is.EqualTo(0.195f));
        }

        [Test]
        public void ConfigurationHashChangesWithAerodynamicCoefficient()
        {
            var original = configuration.ConfigurationHash;
            configuration.DragCoefficient += 0.01f;
            Assert.That(configuration.ConfigurationHash, Is.Not.EqualTo(original));
        }

        [Test]
        public void ZeroRelativeSpeedProducesNoAerodynamicForce()
        {
            configuration.WindVelocity = new Vector3(2f, 0f, -1f);
            var result = AerodynamicModelV1.Evaluate(
                configuration.WindVelocity,
                new Vector3(10f, 20f, 30f),
                configuration.AerodynamicParameters);

            Assert.That(result.RelativeAirVelocity, Is.EqualTo(Vector3.zero));
            Assert.That(result.TotalForce, Is.EqualTo(Vector3.zero));
            Assert.That(result.SpinParameter, Is.Zero);
            Assert.That(result.LiftCoefficient, Is.Zero);
        }

        [Test]
        public void DragOpposesMotionAndMatchesPublishedCoefficientModel()
        {
            var velocity = new Vector3(0f, 0f, 10f);
            var result = AerodynamicModelV1.Evaluate(
                velocity,
                Vector3.zero,
                configuration.AerodynamicParameters);

            Assert.That(Vector3.Dot(result.DragForce, velocity), Is.LessThan(0f));
            Assert.That(
                result.DragForce.magnitude,
                Is.EqualTo(0.07767318f).Within(0.000001f));
            Assert.That(result.LiftForce, Is.EqualTo(Vector3.zero));
        }

        [Test]
        public void SpinLiftUsesPerpendicularSpinAndCorrectDirections()
        {
            var velocity = new Vector3(0f, 0f, 10f);
            var topSpin = AerodynamicModelV1.Evaluate(
                velocity,
                new Vector3(62.831853f, 0f, 0f),
                configuration.AerodynamicParameters);
            var backSpin = AerodynamicModelV1.Evaluate(
                velocity,
                new Vector3(-62.831853f, 0f, 0f),
                configuration.AerodynamicParameters);
            var axialSpin = AerodynamicModelV1.Evaluate(
                velocity,
                new Vector3(0f, 0f, 62.831853f),
                configuration.AerodynamicParameters);

            Assert.That(topSpin.LiftForce.y, Is.LessThan(0f));
            Assert.That(backSpin.LiftForce.y, Is.GreaterThan(0f));
            Assert.That(
                topSpin.LiftForce.magnitude,
                Is.EqualTo(backSpin.LiftForce.magnitude).Within(0.000001f));
            Assert.That(axialSpin.LiftForce, Is.EqualTo(Vector3.zero));
            Assert.That(axialSpin.SpinParameter, Is.Zero);
        }

        [Test]
        public void ZeroSpinCannotProduceSyntheticMagnusLift()
        {
            var result = AerodynamicModelV1.Evaluate(
                new Vector3(3f, 4f, 5f),
                Vector3.zero,
                configuration.AerodynamicParameters);

            Assert.That(result.LiftCoefficient, Is.Zero);
            Assert.That(result.LiftForce, Is.EqualTo(Vector3.zero));
        }

        [Test]
        public void AngularDecayIsStableAndTimeStepComposable()
        {
            var halfStep = AerodynamicModelV1.AngularVelocityMultiplier(
                0.5f,
                configuration.AerodynamicParameters);
            var fullStep = AerodynamicModelV1.AngularVelocityMultiplier(
                1f,
                configuration.AerodynamicParameters);

            Assert.That(halfStep, Is.InRange(0f, 1f));
            Assert.That(halfStep * halfStep, Is.EqualTo(fullStep).Within(0.000001f));
        }

        [Test]
        public void ReferenceIntegratorMatchesVacuumBallistics()
        {
            var aerodynamics = new AerodynamicParametersV1(
                CourtGeometryV1.BallRadius,
                configuration.AirDensity,
                0f,
                0f,
                0f,
                configuration.MinimumAerodynamicSpeed,
                Vector3.zero,
                0f);
            var initial = new FlightStateV1(
                new Vector3(0f, 2f, 0f),
                new Vector3(1f, 2f, 3f),
                Vector3.zero);

            var result = FlightReferenceIntegratorV1.Integrate(
                initial,
                1f,
                0.001f,
                configuration.BallMass,
                configuration.Gravity,
                aerodynamics);
            var expected =
                initial.Position +
                initial.Velocity +
                (0.5f * configuration.Gravity);

            Assert.That(
                Vector3.Distance(result.Position, expected),
                Is.LessThan(0.0001f));
            Assert.That(
                Vector3.Distance(
                    result.Velocity,
                    initial.Velocity + configuration.Gravity),
                Is.LessThan(0.0001f));
        }

        [Test]
        public void PublishedModelDragReducesReferenceDownrangeTravel()
        {
            var initial = new FlightStateV1(
                new Vector3(0f, 2f, 0f),
                new Vector3(0f, 2f, 12f),
                Vector3.zero);
            var calibrated = FlightReferenceIntegratorV1.Integrate(
                initial,
                0.5f,
                0.001f,
                configuration.BallMass,
                configuration.Gravity,
                configuration.AerodynamicParameters);
            var vacuumParameters = new AerodynamicParametersV1(
                CourtGeometryV1.BallRadius,
                configuration.AirDensity,
                0f,
                0f,
                0f,
                configuration.MinimumAerodynamicSpeed,
                Vector3.zero,
                0f);
            var vacuum = FlightReferenceIntegratorV1.Integrate(
                initial,
                0.5f,
                0.001f,
                configuration.BallMass,
                configuration.Gravity,
                vacuumParameters);

            Assert.That(calibrated.Position.z, Is.LessThan(vacuum.Position.z));
        }

        [Test]
        public void ReplacementPhase1CProtocolIsEnvV1BoundAndFinalSeedsStayUntouched()
        {
            Assert.DoesNotThrow(Phase1CProtocolV0.ValidateOrThrow);
            Assert.That(
                Phase1CProtocolV0.EnvironmentDependency,
                Is.EqualTo(SimulationConfigV1.EnvironmentVersion));
            Assert.That(
                Phase1CProtocolV0.MaximumBallAngularSpeed,
                Is.GreaterThanOrEqualTo(62.831853f));
            Assert.That(
                Phase1CProtocolV0.TrainingSeeds.Overlaps(
                    Phase1CProtocolV0.FinalEvaluationSeeds),
                Is.False);
            Assert.That(
                Phase1CProtocolV0.ValidationSeeds.Overlaps(
                    Phase1CProtocolV0.FinalEvaluationSeeds),
                Is.False);
            Assert.That(
                typeof(Phase1CProtocolV0)
                    .GetMethods()
                    .Any(method => method.Name.Contains("EvaluationRequest")),
                Is.False);
            Assert.That(
                Phase1CProtocolV0.UnityTrainerPackage,
                Is.EqualTo("com.unity.ml-agents@4.0.0"));
        }
    }
}

using System;
using System.Linq;
using NUnit.Framework;
using Picklebot.Core;
using Picklebot.Simulation;
using UnityEngine;

namespace Picklebot.Tests.EditMode
{
    public sealed class Phase0CoreContractTests
    {
        private SimulationConfigV0 configuration;

        [SetUp]
        public void SetUp()
        {
            configuration = ScriptableObject.CreateInstance<SimulationConfigV0>();
        }

        [TearDown]
        public void TearDown()
        {
            UnityEngine.Object.DestroyImmediate(configuration);
        }

        [Test]
        public void CanonicalGeometryMatchesAcceptedSpec()
        {
            Assert.That(CourtGeometryV0.CourtLength, Is.EqualTo(13.4112f));
            Assert.That(CourtGeometryV0.CourtWidth, Is.EqualTo(6.0960f));
            Assert.That(CourtGeometryV0.NonVolleyZoneDepth, Is.EqualTo(2.1336f));
            Assert.That(CourtGeometryV0.NetSidelineHeight, Is.EqualTo(0.9144f));
            Assert.That(CourtGeometryV0.NetCenterHeight, Is.EqualTo(0.8636f));
            Assert.That(CourtGeometryV0.BallMass, Is.EqualTo(0.024f));
            Assert.That(CourtGeometryV0.BallDiameter, Is.EqualTo(0.074f));
            Assert.That(
                CourtGeometryV0.NetSegmentAverageHeight,
                Is.EqualTo(0.889f).Within(0.000001f));
            Assert.That(
                CourtGeometryV0.NetSegmentSlopeDegrees,
                Is.EqualTo(0.95484f).Within(0.0001f));
        }

        [TestCase(-3.048f, -6.7056f, ZoneClassificationV0.NearCourtIn)]
        [TestCase(3.048f, 6.7056f, ZoneClassificationV0.FarCourtIn)]
        [TestCase(0f, -2.1336f, ZoneClassificationV0.NearNonVolleyZone)]
        [TestCase(0f, 2.1336f, ZoneClassificationV0.FarNonVolleyZone)]
        [TestCase(3.049f, 0f, ZoneClassificationV0.Out)]
        [TestCase(0f, 6.706f, ZoneClassificationV0.Out)]
        public void CourtLinesAreClosedRegions(
            float x,
            float z,
            ZoneClassificationV0 expected)
        {
            Assert.That(
                CourtGeometryV0.ClassifyFloorContact(new Vector3(x, 0f, z)),
                Is.EqualTo(expected));
        }

        [Test]
        public void InvalidFloorPositionIsUnknown()
        {
            Assert.That(
                CourtGeometryV0.ClassifyFloorContact(
                    new Vector3(float.NaN, 0f, 0f)),
                Is.EqualTo(ZoneClassificationV0.Unknown));
        }

        [Test]
        public void Pcg32MatchesCommittedReferenceVector()
        {
            var random = new Pcg32Random(42UL, 54UL);
            Assert.That(
                new[]
                {
                    random.NextUInt(),
                    random.NextUInt(),
                    random.NextUInt(),
                    random.NextUInt()
                },
                Is.EqualTo(new uint[]
                {
                    2707161783U,
                    2068313097U,
                    3122475824U,
                    2211639955U
                }));
        }

        [Test]
        public void NamedRandomStreamsAreIndependent()
        {
            const ulong seed = 987654321UL;
            var launcher = new Pcg32Random(
                seed,
                Pcg32Random.DeriveStream(seed, "launcher"));
            var paddleA = new Pcg32Random(
                seed,
                Pcg32Random.DeriveStream(seed, "paddle_start"));
            launcher.NextUInt();
            launcher.NextUInt();
            launcher.NextUInt();

            var paddleB = new Pcg32Random(
                seed,
                Pcg32Random.DeriveStream(seed, "paddle_start"));
            Assert.That(paddleA.NextUInt(), Is.EqualTo(paddleB.NextUInt()));
        }

        [Test]
        public void SameSeedProducesBitIdenticalScenarioManifestParameters()
        {
            var request = new ResetRequestV0(
                1234UL,
                ScenarioCatalogV0.LaunchRally,
                "hard");
            var first = ScenarioCatalogV0.Generate(request, configuration);
            var second = ScenarioCatalogV0.Generate(request, configuration);

            Assert.That(first.CanonicalText(), Is.EqualTo(second.CanonicalText()));
        }

        [Test]
        public void ContactScenariosKeepBallAndPaddleInOneSeededLane()
        {
            var contactScenarios = new[]
            {
                ScenarioCatalogV0.ContactFrontOn,
                ScenarioCatalogV0.StabilityHighSpeed
            };
            foreach (var scenario in contactScenarios)
            {
                for (ulong seed = 0; seed < 256UL; seed++)
                {
                    var generated = ScenarioCatalogV0.Generate(
                        new ResetRequestV0(seed, scenario),
                        configuration);
                    Assert.That(
                        generated.BallPosition.x,
                        Is.EqualTo(generated.PaddlePosition.x),
                        $"{scenario} seed {seed}");
                    Assert.That(
                        generated.BallLinearVelocity.x,
                        Is.Zero,
                        $"{scenario} seed {seed}");
                }
            }
        }

        [Test]
        public void ScenarioCatalogContainsNineUniqueGeneratableFamilies()
        {
            Assert.That(ScenarioCatalogV0.ScenarioIds.Count, Is.EqualTo(9));
            Assert.That(
                ScenarioCatalogV0.ScenarioIds.Distinct(StringComparer.Ordinal).Count(),
                Is.EqualTo(ScenarioCatalogV0.ScenarioIds.Count));
            foreach (var scenarioId in ScenarioCatalogV0.ScenarioIds)
            {
                Assert.DoesNotThrow(() =>
                    ScenarioCatalogV0.Generate(
                        new ResetRequestV0(123UL, scenarioId),
                        configuration));
            }
        }

        [Test]
        public void OverridesAreCanonicalizedByKeyAndApplied()
        {
            var request = new ResetRequestV0(
                10UL,
                ScenarioCatalogV0.BoundaryCourt,
                overrides: new[]
                {
                    new ResetOverrideV0("ball.position.z", 1.25f),
                    new ResetOverrideV0("ball.position.x", -0.5f)
                });
            var generated = ScenarioCatalogV0.Generate(request, configuration);

            Assert.That(generated.BallPosition.x, Is.EqualTo(-0.5f));
            Assert.That(generated.BallPosition.z, Is.EqualTo(1.25f));
            Assert.That(
                ScenarioCatalogV0.CanonicalizeOverrides(request.Overrides),
                Is.EqualTo("ball.position.x=-0.5;ball.position.z=1.25"));
        }

        [Test]
        public void ActionProcessorRejectsNonFiniteActions()
        {
            var processed = ActionProcessorV0.Process(
                new PaddleActionV0(
                    new Vector3(float.NaN, 0f, 0f),
                    Vector3.zero),
                configuration);

            Assert.That(processed.IsValid, Is.False);
            Assert.That(processed.WasClamped, Is.False);
        }

        [Test]
        public void ActionProcessorClampsAndScalesFiniteActions()
        {
            var processed = ActionProcessorV0.Process(
                new PaddleActionV0(
                    new Vector3(2f, -0.5f, -3f),
                    new Vector3(0f, 4f, 0.25f)),
                configuration);

            Assert.That(processed.IsValid, Is.True);
            Assert.That(processed.WasClamped, Is.True);
            Assert.That(
                processed.Normalized.LinearVelocityLocal,
                Is.EqualTo(new Vector3(1f, -0.5f, -1f)));
            Assert.That(
                processed.LinearVelocityLocal,
                Is.EqualTo(
                    new Vector3(1f, -0.5f, -1f) *
                    configuration.MaxPaddleLinearSpeed));
        }

        [Test]
        public void ContactLedgerDeduplicatesWithinConfiguredSeparation()
        {
            var ledger = new ContactLedgerV0();
            Assert.That(ledger.ShouldRecord(30, 10UL, 2), Is.True);
            Assert.That(ledger.ShouldRecord(30, 11UL, 2), Is.False);
            Assert.That(ledger.ShouldRecord(30, 12UL, 2), Is.True);
            Assert.That(ledger.ShouldRecord(20, 11UL, 2), Is.True);
        }

        [Test]
        public void EventOrderingPhasesMatchContract()
        {
            Assert.That(
                EventOrderingV0.Phase(EnvironmentEventKindV0.InvalidNumericState),
                Is.LessThan(EventOrderingV0.Phase(
                    EnvironmentEventKindV0.BallPaddleContact)));
            Assert.That(
                EventOrderingV0.Phase(EnvironmentEventKindV0.BallFloorContact),
                Is.LessThan(EventOrderingV0.Phase(
                    EnvironmentEventKindV0.BallEnteredZone)));
            Assert.That(
                EventOrderingV0.Phase(EnvironmentEventKindV0.BallEnteredZone),
                Is.LessThan(EventOrderingV0.Phase(
                    EnvironmentEventKindV0.EpisodeTerminated)));
        }

        [Test]
        public void StateMachineSupportsVisibleResetAndImmutableTerminal()
        {
            var machine = new EpisodeStateMachineV0();
            machine.BeginReset();
            machine.CompleteReset();
            machine.BeginRunning();
            machine.BeginReset();
            machine.CompleteReset();
            Assert.That(machine.State, Is.EqualTo(EpisodeStateV0.Ready));

            machine.BeginRunning();
            Assert.That(
                machine.TryTerminate(TerminationReasonV0.Timeout),
                Is.True);
            Assert.That(
                machine.TryTerminate(TerminationReasonV0.FarCourtLanding),
                Is.False);
            Assert.That(
                machine.TerminationReason,
                Is.EqualTo(TerminationReasonV0.Timeout));
        }

        [Test]
        public void TerminalReasonEnumIsExhaustiveAndStable()
        {
            var reasons = Enum.GetValues(typeof(TerminationReasonV0))
                .Cast<TerminationReasonV0>()
                .ToArray();
            Assert.That(reasons.Length, Is.EqualTo(10));
            Assert.That(reasons.Distinct().Count(), Is.EqualTo(reasons.Length));
            Assert.That(reasons.Single(value => value == TerminationReasonV0.None), Is.EqualTo(TerminationReasonV0.None));
        }

        [Test]
        public void QuaternionCanonicalizationUsesOneSignConvention()
        {
            var value = Quaternion.Euler(15f, -25f, 40f);
            var positive = FiniteMath.Canonicalize(value);
            var negative = FiniteMath.Canonicalize(
                new Quaternion(-value.x, -value.y, -value.z, -value.w));
            Assert.That(Quaternion.Dot(positive, negative), Is.EqualTo(1f).Within(0.000001f));
            Assert.That(positive.w, Is.GreaterThanOrEqualTo(0f));
        }

        [Test]
        public void ConfigurationIdentityIsStableAndVersioned()
        {
            configuration.ValidateOrThrow();
            var first = configuration.ConfigurationHash;
            var second = configuration.ConfigurationHash;

            Assert.That(SimulationConfigV0.CanonicalVersion, Is.EqualTo("sim-config-v0"));
            Assert.That(first, Is.EqualTo(second));
            Assert.That(first.Length, Is.EqualTo(16));
        }

        [Test]
        public void ConfigurationSerializationPreservesIdentity()
        {
            configuration.MaxPaddleLinearSpeed = 7.25f;
            configuration.ReplayVelocityTolerance = 0.0015f;
            var expectedHash = configuration.ConfigurationHash;
            var json = JsonUtility.ToJson(configuration);
            var restored = ScriptableObject.CreateInstance<SimulationConfigV0>();
            try
            {
                JsonUtility.FromJsonOverwrite(json, restored);
                restored.ValidateOrThrow();
                Assert.That(restored.ConfigurationHash, Is.EqualTo(expectedHash));
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(restored);
            }
        }

        [Test]
        public void ObservationValidatorRejectsInvalidNumericState()
        {
            var observation = new ObservationV0
            {
                ElapsedTime = 0f,
                Ball = new KinematicSnapshotV0
                {
                    PositionWorld = new Vector3(float.NaN, 0f, 0f),
                    RotationWorld = Quaternion.identity
                },
                Paddle = new KinematicSnapshotV0
                {
                    RotationWorld = Quaternion.identity
                }
            };

            Assert.That(ObservationValidatorV0.IsFinite(observation), Is.False);
        }

        [Test]
        public void RecordedActionSourceUsesCanonicalActionBoundary()
        {
            var recording = ScriptableObject.CreateInstance<RecordedActionSequenceV0>();
            recording.Frames = new[]
            {
                new RecordedActionFrameV0
                {
                    LinearVelocityLocal = new Vector3(0.25f, 0f, -0.5f),
                    AngularVelocityLocal = new Vector3(0f, 0.75f, 0f)
                }
            };
            try
            {
                var source = new RecordedActionSourceV0(recording);
                source.Reset(123UL);
                Assert.That(source.TryGetNext(out var action), Is.True);
                Assert.That(
                    action.LinearVelocityLocal,
                    Is.EqualTo(recording.Frames[0].LinearVelocityLocal));
                Assert.That(
                    action.AngularVelocityLocal,
                    Is.EqualTo(recording.Frames[0].AngularVelocityLocal));
                Assert.That(source.TryGetNext(out _), Is.False);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(recording);
            }
        }

        [Test]
        public void CoreAssemblyHasNoTrainerDependency()
        {
            var referenceNames = typeof(IPicklebotEnvironmentV0)
                .Assembly
                .GetReferencedAssemblies()
                .Select(value => value.Name)
                .ToArray();

            Assert.That(
                referenceNames.Any(value =>
                    value.Contains("MLAgents", StringComparison.OrdinalIgnoreCase) ||
                    value.Contains("Barracuda", StringComparison.OrdinalIgnoreCase)),
                Is.False);
        }

        [Test]
        public void CanonicalTimingIsPinned()
        {
            Assert.That(EnvironmentVersion.PhysicsTicksPerSecond, Is.EqualTo(120));
            Assert.That(EnvironmentVersion.DefaultTicksPerAction, Is.EqualTo(2));
            Assert.That(
                EnvironmentVersion.PhysicsDeltaTime,
                Is.EqualTo(1f / 120f));
        }
    }
}

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using NUnit.Framework;
using Picklebot.Core;
using Picklebot.Evaluation;
using Picklebot.Simulation;
using UnityEngine;

namespace Picklebot.Tests.Phase1B.PlayMode
{
    public sealed class Phase1BEvidenceTests
    {
        [Serializable]
        private sealed class Summary
        {
            public string evidenceState;
            public bool closeEligible;
            public string environmentVersion;
            public string configurationVersion;
            public string configurationHash;
            public string physicsSettingsHash;
            public string phase1CProtocolVersion;
            public string phase1CProtocolHash;
            public string sourceCommit;
            public string unityVersion;
            public string platform;
            public string[] blockers;
        }

        [Serializable]
        private sealed class ParameterSource
        {
            public string parameter;
            public float value;
            public string unit;
            public string sourceKind;
            public string source;
            public string uncertainty;
            public string status;
        }

        [Serializable]
        private sealed class Manifest
        {
            public string profile;
            public string calibrationState;
            public string generatedAtUtc;
            public bool qualifiesForClose;
            public string limitation;
            public ParameterSource[] parameters;
        }

        [Serializable]
        private sealed class DropRecord
        {
            public string fixture;
            public string releaseDatum;
            public float releaseReferenceHeight;
            public float initialCenterHeight;
            public float gravityOnlyImpactTime;
            public float firstImpactTime;
            public float firstReboundTopHeight;
            public float horizontalDrift;
            public float preImpactMechanicalEnergy;
            public float postImpactMechanicalEnergy;
            public bool completed;
            public bool passesProvisionalInterval;
            public bool qualifiesForOfficialClose;
        }

        [Serializable]
        private sealed class FlightRecord
        {
            public string traceId;
            public string spinClass;
            public string arcClass;
            public Vector3 initialPosition;
            public Vector3 initialVelocity;
            public Vector3 initialAngularVelocity;
            public float duration;
            public int sampleCount;
            public float rmsPositionError;
            public float maximumPositionError;
            public float vacuumRmsPositionError;
            public bool integrationCheckPassed;
            public string provenanceKind;
            public string provenance;
            public bool qualifiesForEmpiricalClose;
        }

        [Serializable]
        private sealed class PaddleRecord
        {
            public float incomingNormalSpeed;
            public float paddleSpeed;
            public Vector2 impactOffset;
            public Vector3 incomingVelocity;
            public Vector3 outgoingVelocity;
            public Vector3 incomingSpin;
            public Vector3 outgoingSpin;
            public float effectiveRestitution;
            public float kineticEnergyRatio;
            public float tangentialVelocityChange;
            public float angularVelocityChange;
            public bool completed;
        }

        [Serializable]
        private sealed class ContactRecord
        {
            public string fixture;
            public string caseId;
            public Vector3 incomingVelocity;
            public Vector3 outgoingVelocity;
            public Vector3 incomingSpin;
            public Vector3 outgoingSpin;
            public float reboundTopHeight;
            public float energyRatio;
            public int logicalContacts;
            public bool contactDetected;
            public bool completed;
            public bool qualifiesForReferenceClose;
        }

        [Test]
        [Category("Evidence")]
        [Explicit("Run through scripts/phase1b-evidence.sh or by exact test name.")]
        public void GenerateProvisionalCalibrationAndReadinessEvidence()
        {
            var fixture = PicklebotEnvironmentFactoryV1.Create(
                "Phase1BProvisionalEvidence");
            try
            {
                var outputDirectory =
                    Environment.GetEnvironmentVariable(
                        "PICKLEBOT_PHASE1B_EVIDENCE_OUTPUT") ??
                    Path.GetFullPath(Path.Combine(
                        Application.dataPath,
                        "..",
                        "artifacts",
                        "phase1b",
                        "provisional"));
                Directory.CreateDirectory(outputDirectory);
                var sourceCommit =
                    Environment.GetEnvironmentVariable(
                        "PICKLEBOT_SOURCE_COMMIT") ??
                    "uncommitted";

                var readiness = Phase1BReadinessV1.Measure(
                    fixture.Environment,
                    new InterceptHeuristicPolicyV0(),
                    20000,
                    sourceCommit);
                File.WriteAllText(
                    Path.Combine(outputDirectory, "readiness.json"),
                    JsonUtility.ToJson(readiness, true));

                WriteManifest(outputDirectory, fixture.Configuration);
                WriteDrop(outputDirectory, fixture.Configuration);
                WriteFlights(
                    outputDirectory,
                    fixture.Environment,
                    fixture.Configuration);
                WritePaddle(outputDirectory, fixture.Configuration);
                WriteCourtAndNet(outputDirectory, fixture.Configuration);

                var blockers = new[]
                {
                    "No raw measured or published trajectory coordinates are committed.",
                    "No project-owned or equivalent published acrylic-court trace is committed.",
                    "The official drop release-height datum awaits a cited detailed procedure.",
                    "The calibration configuration remains provisional-unfitted.",
                    "A clean source-exact rerun and env-v1 tag do not yet exist."
                };
                File.WriteAllText(
                    Path.Combine(outputDirectory, "summary.json"),
                    JsonUtility.ToJson(
                        new Summary
                        {
                            evidenceState = "provisional-nonclosing",
                            closeEligible = false,
                            environmentVersion =
                                SimulationConfigV1.EnvironmentVersion,
                            configurationVersion =
                                SimulationConfigV1.CanonicalVersion,
                            configurationHash =
                                fixture.Configuration.ConfigurationHash,
                            physicsSettingsHash =
                                PhysicsSettingsIdentityV0.Hash(),
                            phase1CProtocolVersion =
                                Phase1CProtocolV0.Version,
                            phase1CProtocolHash =
                                Phase1CProtocolV0.Hash,
                            sourceCommit = sourceCommit,
                            unityVersion = Application.unityVersion,
                            platform = Application.platform.ToString(),
                            blockers = blockers
                        },
                        true));

                Assert.That(readiness.passed, Is.True);
                Assert.That(
                    File.Exists(Path.Combine(
                        outputDirectory,
                        "flight-traces.jsonl")),
                    Is.True);
            }
            finally
            {
                fixture.Destroy();
            }
        }

        private static void WriteManifest(
            string outputDirectory,
            SimulationConfigV1 configuration)
        {
            var parameters = new[]
            {
                Source(
                    "ballMass",
                    configuration.BallMass,
                    "kg",
                    "official-standard-nominal",
                    "USA Pickleball Equipment Standards Manual",
                    "official interval 0.0221-0.0265 kg",
                    "inside-official-range"),
                Source(
                    "ballDiameter",
                    configuration.BallDiameter,
                    "m",
                    "official-standard-nominal",
                    "USA Pickleball Equipment Standards Manual",
                    "official interval 0.0729-0.0754 m",
                    "inside-official-range"),
                Source(
                    "dragCoefficient",
                    configuration.DragCoefficient,
                    "dimensionless",
                    "peer-reviewed-fit",
                    "Steyn et al. DOI 10.1177/17479541251365200",
                    "+/-0.02",
                    "published-model-provisional"),
                Source(
                    "liftCoefficientSlope",
                    configuration.LiftCoefficientSlope,
                    "per-spin-parameter",
                    "peer-reviewed-fit",
                    "Steyn et al. DOI 10.1177/17479541251365200",
                    "source reports large spin scatter",
                    "published-model-provisional"),
                Source(
                    "graniteRestitution",
                    configuration.GraniteRestitution,
                    "unity-surrogate",
                    "project-fit",
                    "official 30-34 inch rebound interval",
                    "release datum unresolved",
                    "provisional"),
                Source(
                    "courtRestitution",
                    configuration.CourtRestitution,
                    "unity-surrogate",
                    "engineering-assumption",
                    "none",
                    "not measured",
                    "blocked-on-acrylic-trace"),
                Source(
                    "paddleRestitution",
                    configuration.PaddleRestitution,
                    "unity-surrogate",
                    "engineering-target",
                    "project target 0.40 +/- 0.03",
                    "+/-0.03",
                    "not-certification")
            };
            File.WriteAllText(
                Path.Combine(
                    outputDirectory,
                    "calibration-manifest.json"),
                JsonUtility.ToJson(
                    new Manifest
                    {
                        profile = SimulationConfigV1.ReferenceProfile,
                        calibrationState = configuration.CalibrationState,
                        generatedAtUtc =
                            DateTime.UtcNow.ToString("O"),
                        qualifiesForClose = false,
                        limitation =
                            "Kinematic paddle has no hand or arm inertia.",
                        parameters = parameters
                    },
                    true));
        }

        private static ParameterSource Source(
            string parameter,
            float value,
            string unit,
            string sourceKind,
            string source,
            string uncertainty,
            string status)
        {
            return new ParameterSource
            {
                parameter = parameter,
                value = value,
                unit = unit,
                sourceKind = sourceKind,
                source = source,
                uncertainty = uncertainty,
                status = status
            };
        }

        private static void WriteDrop(
            string outputDirectory,
            SimulationConfigV1 configuration)
        {
            var result = CalibrationFixturesV1.RunBallDrop(
                configuration,
                DropReleaseDatumV1.BallTop);
            var referenceTime = Mathf.Sqrt(
                2f *
                (
                    result.InitialCenterHeight -
                    configuration.BallDiameter / 2f) /
                configuration.Gravity.magnitude);
            var record = new DropRecord
            {
                fixture = "granite-reference-provisional",
                releaseDatum = result.ReleaseDatum.ToString(),
                releaseReferenceHeight = result.ReleaseReferenceHeight,
                initialCenterHeight = result.InitialCenterHeight,
                gravityOnlyImpactTime = referenceTime,
                firstImpactTime = result.FirstImpactTime,
                firstReboundTopHeight = result.FirstReboundTopHeight,
                horizontalDrift = result.HorizontalDrift,
                preImpactMechanicalEnergy =
                    result.PreImpactMechanicalEnergy,
                postImpactMechanicalEnergy =
                    result.PostImpactMechanicalEnergy,
                completed = result.Completed,
                passesProvisionalInterval =
                    result.Completed &&
                    Mathf.Abs(result.FirstImpactTime - referenceTime) <= 0.01f &&
                    result.FirstReboundTopHeight >=
                        CalibrationFixturesV1
                            .OfficialMinimumReboundTopHeight &&
                    result.FirstReboundTopHeight <=
                        CalibrationFixturesV1
                            .OfficialMaximumReboundTopHeight,
                qualifiesForOfficialClose = false
            };
            File.WriteAllText(
                Path.Combine(outputDirectory, "ball-drop.jsonl"),
                JsonUtility.ToJson(record) + Environment.NewLine);
        }

        private static void WriteFlights(
            string outputDirectory,
            PicklebotEnvironmentV1 environment,
            SimulationConfigV1 configuration)
        {
            var cases = FlightCases();
            using var writer = new StreamWriter(
                Path.Combine(outputDirectory, "flight-traces.jsonl"),
                false);
            foreach (var current in cases)
            {
                var initialPosition = new Vector3(2f, 5f, -4f);
                environment.Reset(new ResetRequestV0(
                    9000000UL + (ulong)current.index,
                    ScenarioCatalogV0.LaunchRally,
                    overrides: new[]
                    {
                        new ResetOverrideV0(
                            "ball.position.x",
                            initialPosition.x),
                        new ResetOverrideV0(
                            "ball.position.y",
                            initialPosition.y),
                        new ResetOverrideV0(
                            "ball.position.z",
                            initialPosition.z),
                        new ResetOverrideV0(
                            "ball.velocity.x",
                            current.velocity.x),
                        new ResetOverrideV0(
                            "ball.velocity.y",
                            current.velocity.y),
                        new ResetOverrideV0(
                            "ball.velocity.z",
                            current.velocity.z),
                        new ResetOverrideV0(
                            "ball.angular_velocity.x",
                            current.spin.x),
                        new ResetOverrideV0(
                            "ball.angular_velocity.y",
                            current.spin.y),
                        new ResetOverrideV0(
                            "ball.angular_velocity.z",
                            current.spin.z),
                        new ResetOverrideV0(
                            "paddle.position.x",
                            -2f),
                        new ResetOverrideV0(
                            "maximum_episode_seconds",
                            2f)
                    }));

                const int samples = 30;
                var squaredError = 0f;
                var squaredVacuumError = 0f;
                var maximumError = 0f;
                for (var sample = 1; sample <= samples; sample++)
                {
                    var result = environment.Step(PaddleActionV0.Zero);
                    Assert.That(result.IsTerminal, Is.False);
                    var time =
                        sample *
                        EnvironmentVersion.PhysicsDeltaTime *
                        EnvironmentVersion.DefaultTicksPerAction;
                    var reference = FlightReferenceIntegratorV1.Integrate(
                        new FlightStateV1(
                            initialPosition,
                            current.velocity,
                            current.spin),
                        time,
                        0.001f,
                        configuration.BallMass,
                        configuration.Gravity,
                        configuration.AerodynamicParameters);
                    var vacuum = FlightReferenceIntegratorV1.Integrate(
                        new FlightStateV1(
                            initialPosition,
                            current.velocity,
                            current.spin),
                        time,
                        0.001f,
                        configuration.BallMass,
                        configuration.Gravity,
                        VacuumParameters(configuration));
                    var error = Vector3.Distance(
                        result.Observation.Ball.PositionWorld,
                        reference.Position);
                    var vacuumError = Vector3.Distance(
                        vacuum.Position,
                        reference.Position);
                    squaredError += error * error;
                    squaredVacuumError += vacuumError * vacuumError;
                    maximumError = Mathf.Max(maximumError, error);
                }

                var rms = Mathf.Sqrt(squaredError / samples);
                var vacuumRms =
                    Mathf.Sqrt(squaredVacuumError / samples);
                writer.WriteLine(JsonUtility.ToJson(
                    new FlightRecord
                    {
                        traceId = $"model-check-{current.index:00}",
                        spinClass = current.spinClass,
                        arcClass = current.arcClass,
                        initialPosition = initialPosition,
                        initialVelocity = current.velocity,
                        initialAngularVelocity = current.spin,
                        duration =
                            samples *
                            EnvironmentVersion.PhysicsDeltaTime *
                            EnvironmentVersion.DefaultTicksPerAction,
                        sampleCount = samples,
                        rmsPositionError = rms,
                        maximumPositionError = maximumError,
                        vacuumRmsPositionError = vacuumRms,
                        integrationCheckPassed =
                            rms <= 0.05f &&
                            maximumError <= 0.10f &&
                            rms < vacuumRms,
                        provenanceKind =
                            "published-coefficient-model",
                        provenance =
                            "Steyn et al. Cd=0.30 and Cl=0.195*S",
                        qualifiesForEmpiricalClose = false
                    }));
            }
        }

        private static AerodynamicParametersV1 VacuumParameters(
            SimulationConfigV1 configuration)
        {
            return new AerodynamicParametersV1(
                configuration.BallDiameter / 2f,
                configuration.AirDensity,
                0f,
                0f,
                0f,
                configuration.MinimumAerodynamicSpeed,
                configuration.WindVelocity,
                0f);
        }

        private static (int index, Vector3 velocity, Vector3 spin,
            string spinClass, string arcClass)[] FlightCases()
        {
            var cases = new List<(int, Vector3, Vector3, string, string)>();
            var zeroSpeeds = new[] { 5f, 7f, 9f, 11f, 13f, 15f };
            for (var index = 0; index < zeroSpeeds.Length; index++)
            {
                var arc = index % 3;
                cases.Add((
                    index,
                    new Vector3(
                        0f,
                        arc == 0 ? 1f : arc == 1 ? 3f : 5f,
                        zeroSpeeds[index]),
                    Vector3.zero,
                    "zero",
                    arc == 0 ? "low" : arc == 1 ? "medium" : "high"));
            }

            for (var index = 0; index < 3; index++)
            {
                var speed = 7f + (index * 3f);
                var spin = index == 1 ? 62.831853f : 31.415927f;
                cases.Add((
                    6 + index,
                    new Vector3(0f, 2f + index, speed),
                    new Vector3(spin, 0f, 0f),
                    "topspin",
                    index == 0 ? "low" : index == 1 ? "medium" : "high"));
                cases.Add((
                    9 + index,
                    new Vector3(0f, 2f + index, speed),
                    new Vector3(-spin, 0f, 0f),
                    "backspin",
                    index == 0 ? "low" : index == 1 ? "medium" : "high"));
            }

            return cases.OrderBy(value => value.Item1).ToArray();
        }

        private static void WritePaddle(
            string outputDirectory,
            SimulationConfigV1 configuration)
        {
            var results = new List<PaddleImpactResultV1>();
            results.AddRange(new[] { 5f, 10f, 15f }.Select(speed =>
                CalibrationFixturesV1.RunPaddleImpact(
                    configuration,
                    speed,
                    0f)));
            results.AddRange(new[] { 0f, 2f, 4f, 6f }.Select(speed =>
                CalibrationFixturesV1.RunPaddleImpact(
                    configuration,
                    10f,
                    speed)));
            results.Add(CalibrationFixturesV1.RunPaddleImpact(
                configuration,
                10f,
                0f,
                new Vector2(-0.04f, 0f),
                0f,
                Vector3.zero));
            results.Add(CalibrationFixturesV1.RunPaddleImpact(
                configuration,
                10f,
                0f,
                new Vector2(0.04f, 0f),
                0f,
                Vector3.zero));
            results.Add(CalibrationFixturesV1.RunPaddleImpact(
                configuration,
                10f,
                0f,
                new Vector2(0f, 0.04f),
                3f,
                Vector3.zero));

            using var writer = new StreamWriter(
                Path.Combine(outputDirectory, "paddle-contact.jsonl"),
                false);
            foreach (var result in results)
            {
                writer.WriteLine(JsonUtility.ToJson(
                    new PaddleRecord
                    {
                        incomingNormalSpeed =
                            result.IncomingBallSpeed,
                        paddleSpeed = result.PaddleSpeed,
                        impactOffset = result.ImpactOffset,
                        incomingVelocity =
                            result.IncomingBallVelocity,
                        outgoingVelocity =
                            result.OutgoingBallVelocity,
                        incomingSpin =
                            result.IncomingAngularVelocity,
                        outgoingSpin =
                            result.OutgoingAngularVelocity,
                        effectiveRestitution =
                            result.EffectiveRestitution,
                        kineticEnergyRatio =
                            result.BallKineticEnergyRatio,
                        tangentialVelocityChange =
                            result.TangentialVelocityChange,
                        angularVelocityChange =
                            result.AngularVelocityChange,
                        completed = result.Completed
                    }));
            }
        }

        private static void WriteCourtAndNet(
            string outputDirectory,
            SimulationConfigV1 configuration)
        {
            var courtCases = new[]
            {
                ("vertical", new Vector3(0f, -5f, 0f), Vector3.zero),
                ("shallow", new Vector3(4f, -3f, 0f), Vector3.zero),
                (
                    "spun",
                    new Vector3(3f, -4f, 0f),
                    new Vector3(0f, 0f, 62.831853f))
            };
            using var writer = new StreamWriter(
                Path.Combine(
                    outputDirectory,
                    "court-net-contact.jsonl"),
                false);
            foreach (var current in courtCases)
            {
                var result = CalibrationFixturesV1.RunCourtImpact(
                    configuration,
                    current.Item2,
                    current.Item3);
                writer.WriteLine(JsonUtility.ToJson(
                    new ContactRecord
                    {
                        fixture = "court-provisional",
                        caseId = current.Item1,
                        incomingVelocity = result.IncomingVelocity,
                        outgoingVelocity = result.OutgoingVelocity,
                        incomingSpin =
                            result.IncomingAngularVelocity,
                        outgoingSpin =
                            result.OutgoingAngularVelocity,
                        reboundTopHeight =
                            result.FirstReboundTopHeight,
                        energyRatio =
                            result.PreImpactMechanicalEnergy <= 0f
                                ? 0f
                                : result.PostImpactMechanicalEnergy /
                                  result.PreImpactMechanicalEnergy,
                        logicalContacts =
                            result.LogicalContactCount,
                        contactDetected =
                            result.LogicalContactCount > 0,
                        completed = result.Completed,
                        qualifiesForReferenceClose = false
                    }));
            }

            var netCases = new[]
            {
                (
                    "clear",
                    0f,
                    CourtGeometryV1.NetCenterHeight +
                    CourtGeometryV1.BallRadius +
                    0.08f),
                ("tape", 0f, CourtGeometryV1.NetCenterHeight),
                ("body", 0f, 0.45f),
                (
                    "post-span",
                    CourtGeometryV1.HalfWidth + 0.15f,
                    0.45f)
            };
            foreach (var current in netCases)
            {
                var incoming = new Vector3(0f, 0f, 10f);
                var result = CalibrationFixturesV1.RunNetImpact(
                    configuration,
                    current.Item2,
                    current.Item3,
                    incoming,
                    Vector3.zero);
                writer.WriteLine(JsonUtility.ToJson(
                    new ContactRecord
                    {
                        fixture = "rigid-net",
                        caseId = current.Item1,
                        incomingVelocity = incoming,
                        outgoingVelocity = result.FinalVelocity,
                        incomingSpin = Vector3.zero,
                        outgoingSpin =
                            result.FinalAngularVelocity,
                        reboundTopHeight = 0f,
                        energyRatio =
                            result.KineticEnergyRatio,
                        logicalContacts =
                            result.ContactDetected ? 1 : 0,
                        contactDetected =
                            result.ContactDetected,
                        completed = result.ContinuedFlight,
                        qualifiesForReferenceClose = true
                    }));
            }
        }
    }
}

using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using NUnit.Framework;
using Picklebot.Core;
using Picklebot.Simulation;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;

namespace Picklebot.Tests.PlayMode
{
    public sealed class Phase0SoakTests
    {
        private const int EpisodeCount = 10000;
        private const ulong FirstSeed = 1000000UL;

        [Serializable]
        private sealed class TerminationCountRecord
        {
            public string reason;
            public int count;
        }

        [Serializable]
        private sealed class SoakSummary
        {
            public string environmentVersion;
            public string unityVersion;
            public string platform;
            public string sourceCommit;
            public string trainerVersion;
            public string configurationVersion;
            public string configurationHash;
            public string physicsSettingsHash;
            public ulong firstSeed;
            public ulong lastSeed;
            public int episodes;
            public int invalidNumericStates;
            public int unclassifiedTerminations;
            public int stateLeakFailures;
            public int terminalCount;
            public bool passed;
            public TerminationCountRecord[] terminalReasons;
        }

        [Serializable]
        private sealed class EpisodeRecord
        {
            public int episode;
            public ulong seed;
            public string scenarioId;
            public string difficulty;
            public string manifestHash;
            public string terminalReason;
            public ulong physicsTicks;
            public int actionSteps;
            public int paddleContacts;
            public int floorContacts;
        }

        [UnityTest]
        [Category("Soak")]
        [Explicit("Run through scripts/phase0-soak.sh or by exact test name.")]
        public IEnumerator TenThousandSeededEpisodesPassPhase0Gate()
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
            var environment =
                UnityEngine.Object.FindAnyObjectByType<PicklebotEnvironmentV0>();
            Assert.That(environment, Is.Not.Null);

            var outputDirectory = Path.GetFullPath(Path.Combine(
                Application.dataPath,
                "..",
                "docs",
                "evidence",
                "phase0",
                "soak"));
            Directory.CreateDirectory(outputDirectory);
            var episodePath = Path.Combine(outputDirectory, "episodes.jsonl");
            var summaryPath = Path.Combine(outputDirectory, "summary.json");
            var terminalCounts = new Dictionary<TerminationReasonV0, int>();
            var invalidNumericStates = 0;
            var unclassifiedTerminations = 0;
            var stateLeakFailures = 0;

            using (var writer = new StreamWriter(episodePath, false))
            {
                for (var episode = 0; episode < EpisodeCount; episode++)
                {
                    var seed = FirstSeed + (ulong)episode;
                    var scenarioId = ScenarioCatalogV0.ScenarioIds[
                        episode % ScenarioCatalogV0.ScenarioIds.Count];
                    var initial = environment.Reset(new ResetRequestV0(seed, scenarioId));

                    if (initial.PhysicsTick != 0UL ||
                        initial.ElapsedTime != 0f ||
                        initial.Episode.ControlledPaddleContacts != 0 ||
                        initial.Episode.BallFloorContacts != 0 ||
                        initial.Ball.PositionWorld !=
                            environment.CurrentManifest.Parameters.BallPosition ||
                        initial.Ball.LinearVelocityWorld !=
                            environment.CurrentManifest.Parameters.BallLinearVelocity)
                    {
                        stateLeakFailures++;
                    }

                    StepResultV0 result = null;
                    var actionSteps = 0;
                    while (actionSteps < 1500)
                    {
                        result = environment.Step(PaddleActionV0.Zero);
                        actionSteps++;
                        if (!ObservationValidatorV0.IsFinite(result.Observation))
                        {
                            invalidNumericStates++;
                            break;
                        }

                        if (result.IsTerminal)
                        {
                            break;
                        }
                    }

                    if (result == null ||
                        !result.IsTerminal ||
                        result.TerminationReason == TerminationReasonV0.None)
                    {
                        unclassifiedTerminations++;
                    }
                    else
                    {
                        if (result.TerminationReason ==
                            TerminationReasonV0.InvalidNumericState)
                        {
                            invalidNumericStates++;
                        }

                        terminalCounts.TryGetValue(
                            result.TerminationReason,
                            out var current);
                        terminalCounts[result.TerminationReason] = current + 1;
                    }

                    var record = new EpisodeRecord
                    {
                        episode = episode,
                        seed = seed,
                        scenarioId = scenarioId,
                        difficulty = "default",
                        manifestHash = StableHashV0.Hex(
                            environment.CurrentManifest.CanonicalText()),
                        terminalReason = result == null
                            ? "Missing"
                            : result.TerminationReason.ToString(),
                        physicsTicks = result?.Observation.PhysicsTick ?? 0UL,
                        actionSteps = actionSteps,
                        paddleContacts =
                            result?.Observation.Episode.ControlledPaddleContacts ?? 0,
                        floorContacts =
                            result?.Observation.Episode.BallFloorContacts ?? 0
                    };
                    writer.WriteLine(JsonUtility.ToJson(record));

                    if ((episode + 1) % 1000 == 0)
                    {
                        writer.Flush();
                        yield return null;
                    }
                }
            }

            var terminalCount = terminalCounts.Values.Sum();
            var passed =
                invalidNumericStates == 0 &&
                unclassifiedTerminations == 0 &&
                stateLeakFailures == 0 &&
                terminalCount == EpisodeCount &&
                !terminalCounts.ContainsKey(TerminationReasonV0.TestAbort);
            var summary = new SoakSummary
            {
                environmentVersion = EnvironmentVersion.Current,
                unityVersion = Application.unityVersion,
                platform = Application.platform.ToString(),
                sourceCommit =
                    Environment.GetEnvironmentVariable("PICKLEBOT_SOURCE_COMMIT") ??
                    "uncommitted",
                trainerVersion = "none",
                configurationVersion = SimulationConfigV0.CanonicalVersion,
                configurationHash = environment.Configuration.ConfigurationHash,
                physicsSettingsHash = PhysicsSettingsIdentityV0.Hash(),
                firstSeed = FirstSeed,
                lastSeed = FirstSeed + EpisodeCount - 1UL,
                episodes = EpisodeCount,
                invalidNumericStates = invalidNumericStates,
                unclassifiedTerminations = unclassifiedTerminations,
                stateLeakFailures = stateLeakFailures,
                terminalCount = terminalCount,
                passed = passed,
                terminalReasons = terminalCounts
                    .OrderBy(value => value.Key)
                    .Select(value => new TerminationCountRecord
                    {
                        reason = value.Key.ToString(),
                        count = value.Value
                    })
                    .ToArray()
            };
            File.WriteAllText(summaryPath, JsonUtility.ToJson(summary, true));

            Assert.That(invalidNumericStates, Is.Zero);
            Assert.That(unclassifiedTerminations, Is.Zero);
            Assert.That(stateLeakFailures, Is.Zero);
            Assert.That(terminalCount, Is.EqualTo(EpisodeCount));
            Assert.That(
                terminalCounts.ContainsKey(TerminationReasonV0.TestAbort),
                Is.False);
            Assert.That(passed, Is.True);
        }
    }
}

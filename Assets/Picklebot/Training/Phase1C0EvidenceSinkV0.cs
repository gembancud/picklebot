using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Picklebot.Core;
using Picklebot.Evaluation;
using UnityEngine;

namespace Picklebot.Training
{
    [Serializable]
    public sealed class Phase1C0RunManifestV0
    {
        public bool provisional = true;
        public string createdUtc;
        public string runId;
        public string sessionId;
        public string seedUse;
        public string policySource;
        public string unityVersion;
        public string operatingSystem;
        public string environmentVersion;
        public string protocolVersion;
        public string protocolHash;
        public string rewardVersion;
        public string rewardHash;
        public string unityTrainerPackage;
        public string pythonTrainerPackage;
        public int observationSize;
        public int continuousActionSize;
        public ulong trainingSeedFirst;
        public int trainingSeedCount;
        public ulong validationSeedFirst;
        public int validationSeedCount;
        public ulong untouchedFinalSeedFirst;
        public int untouchedFinalSeedCount;
    }

    [Serializable]
    public sealed class Phase1C0TrajectoryRecordV0
    {
        public bool provisional = true;
        public ulong seed;
        public string stageId;
        public Vector3[] points;
    }

    public sealed class Phase1C0EvidenceSinkV0
    {
        private readonly List<Phase1C0EpisodeRecordV0> episodes = new();
        private readonly Phase1C0SeedUseV0 seedUse;
        private readonly string episodesPath;
        private readonly string summaryPath;

        public Phase1C0EvidenceSinkV0(
            Phase1C0SeedUseV0 seedUse,
            string policySource,
            string requestedRunId)
        {
            this.seedUse = seedUse;
            var projectRoot = Path.GetFullPath(
                Path.Combine(Application.dataPath, ".."));
            var runId = ResolveRunId(requestedRunId);
            var sessionId = DateTime.UtcNow.ToString("yyyyMMdd-HHmmss");
            DirectoryPath = Path.Combine(
                projectRoot,
                "artifacts",
                "phase1c0",
                runId,
                "runtime",
                SafePathSegment(policySource),
                sessionId,
                seedUse.ToString().ToLowerInvariant());
            Directory.CreateDirectory(DirectoryPath);
            episodesPath = Path.Combine(DirectoryPath, "episodes.jsonl");
            summaryPath = Path.Combine(DirectoryPath, "summary.json");
            File.WriteAllText(
                Path.Combine(DirectoryPath, "manifest.json"),
                JsonUtility.ToJson(
                    CreateManifest(
                        seedUse,
                        policySource,
                        runId,
                        sessionId),
                    true));
        }

        public string DirectoryPath { get; }

        public void RecordEpisode(
            Phase1C0EpisodeRecordV0 episode,
            IReadOnlyList<Vector3> trajectory)
        {
            if (episode == null)
            {
                throw new ArgumentNullException(nameof(episode));
            }

            episodes.Add(episode);
            File.AppendAllText(
                episodesPath,
                JsonUtility.ToJson(episode) + Environment.NewLine);

            if (seedUse == Phase1C0SeedUseV0.Validation)
            {
                var trajectoryRecord = new Phase1C0TrajectoryRecordV0
                {
                    seed = episode.seed,
                    stageId = episode.stageId,
                    points = trajectory?.ToArray() ?? Array.Empty<Vector3>()
                };
                File.WriteAllText(
                    Path.Combine(
                        DirectoryPath,
                        $"trajectory-{episode.seed}.json"),
                    JsonUtility.ToJson(trajectoryRecord));
            }

            if (seedUse == Phase1C0SeedUseV0.Validation ||
                episodes.Count % 50 == 0)
            {
                File.WriteAllText(
                    summaryPath,
                    JsonUtility.ToJson(
                        Phase1C0MetricsV0.Aggregate(episodes),
                        true));
            }
        }

        private static Phase1C0RunManifestV0 CreateManifest(
            Phase1C0SeedUseV0 seedUse,
            string policySource,
            string runId,
            string sessionId)
        {
            return new Phase1C0RunManifestV0
            {
                createdUtc = DateTime.UtcNow.ToString("O"),
                runId = runId,
                sessionId = sessionId,
                seedUse = seedUse.ToString(),
                policySource = policySource,
                unityVersion = Application.unityVersion,
                operatingSystem = SystemInfo.operatingSystem,
                environmentVersion = SimulationConfigV1.EnvironmentVersion,
                protocolVersion = Phase1CProtocolV0.Version,
                protocolHash = Phase1CProtocolV0.Hash,
                rewardVersion = Phase1CProtocolV0.RewardVersion,
                rewardHash = Phase1CProtocolV0.RewardMappingHash,
                unityTrainerPackage = Phase1CProtocolV0.UnityTrainerPackage,
                pythonTrainerPackage = Phase1CProtocolV0.PythonTrainerPackage,
                observationSize = Phase1CObservationEncoderV0.Size,
                continuousActionSize = Phase1C0AgentV0.ContinuousActionSize,
                trainingSeedFirst = Phase1CProtocolV0.TrainingSeeds.First,
                trainingSeedCount = Phase1CProtocolV0.TrainingSeeds.Count,
                validationSeedFirst = Phase1CProtocolV0.ValidationSeeds.First,
                validationSeedCount = Phase1CProtocolV0.ValidationSeeds.Count,
                untouchedFinalSeedFirst =
                    Phase1CProtocolV0.FinalEvaluationSeeds.First,
                untouchedFinalSeedCount =
                    Phase1CProtocolV0.FinalEvaluationSeeds.Count
            };
        }

        private static string ResolveRunId(string requestedRunId)
        {
            const string prefix = "--picklebot-run-id=";
            var argument = Environment.GetCommandLineArgs()
                .FirstOrDefault(value =>
                    value.StartsWith(prefix, StringComparison.Ordinal));
            if (argument != null)
            {
                var requested = argument.Substring(prefix.Length);
                if (!string.IsNullOrWhiteSpace(requested) &&
                    requested.All(value =>
                        char.IsLetterOrDigit(value) ||
                        value is '-' or '_'))
                {
                    return requested;
                }
            }

            return SafePathSegment(requestedRunId);
        }

        private static string SafePathSegment(string value)
        {
            if (!string.IsNullOrWhiteSpace(value))
            {
                var safe = new string(value
                    .Where(current =>
                        char.IsLetterOrDigit(current) ||
                        current is '-' or '_')
                    .ToArray());
                if (!string.IsNullOrWhiteSpace(safe))
                {
                    return safe;
                }
            }

            return "unspecified";
        }
    }
}

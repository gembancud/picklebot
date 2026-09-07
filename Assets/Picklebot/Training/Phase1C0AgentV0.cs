using System;
using System.Collections.Generic;
using Picklebot.Core;
using Picklebot.Evaluation;
using Picklebot.Simulation;
using Unity.MLAgents;
using Unity.MLAgents.Actuators;
using Unity.MLAgents.Sensors;
using UnityEngine;

namespace Picklebot.Training
{
    [DisallowMultipleComponent]
    [RequireComponent(typeof(Unity.MLAgents.Policies.BehaviorParameters))]
    public sealed class Phase1C0AgentV0 : Agent
    {
        public const string BehaviorName = "PicklebotReturn";
        public const string CurriculumParameter = "phase1c_stage";
        public const int ContinuousActionSize = 6;

        private readonly float[] encodedObservation =
            new float[Phase1CObservationEncoderV0.Size];
        private readonly List<Phase1C0EpisodeRecordV0> completedEpisodes = new();

        private PicklebotEnvironmentV1 environment;
        private Phase1C0SeedUseV0 seedUse;
        private Phase1C0EvidenceSinkV0 evidence;
        private Phase1C0EpisodeAccumulatorV0 metrics;
        private ObservationV0 observation;
        private PaddleActionV0 previousAction;
        private float previousElapsedTime;
        private float previousInterceptDistance;
        private int seedIndex;
        private int stageIndex;
        private bool configured;

        public PicklebotEnvironmentV1 Environment => environment;
        public ObservationV0 CurrentObservation => observation;
        public PaddleActionV0 LastAction { get; private set; }
        public Phase1CRewardBreakdownV0 LastReward { get; private set; }
        public StepResultV0 LastResult { get; private set; }
        public int CurrentStageIndex => stageIndex;
        public Phase1C0SeedUseV0 SeedUse => seedUse;
        public string PolicySource { get; private set; }
        public IReadOnlyList<Phase1C0EpisodeRecordV0> CompletedEpisodeRecords =>
            completedEpisodes;
        public string EvidenceDirectory => evidence?.DirectoryPath ?? string.Empty;

        public void Configure(
            PicklebotEnvironmentV1 configuredEnvironment,
            Phase1C0SeedUseV0 configuredSeedUse,
            bool writeEvidence,
            string policySource = "remote-trainer",
            string runId = "phase1c0-local-001")
        {
            environment = configuredEnvironment ??
                throw new ArgumentNullException(nameof(configuredEnvironment));
            seedUse = configuredSeedUse;
            PolicySource = string.IsNullOrWhiteSpace(policySource)
                ? "unspecified"
                : policySource;
            evidence = writeEvidence
                ? new Phase1C0EvidenceSinkV0(
                    configuredSeedUse,
                    PolicySource,
                    runId)
                : null;
            configured = true;
        }

        public override void Initialize()
        {
            base.Initialize();
            MaxStep = Phase1CProtocolV0.MaximumActionSteps;
            environment ??= GetComponent<PicklebotEnvironmentV1>();
        }

        public override void OnEpisodeBegin()
        {
            EnsureConfigured();
            stageIndex = ResolveStageIndex();
            var request = seedUse == Phase1C0SeedUseV0.Training
                ? Phase1CProtocolV0.TrainingRequest(stageIndex, seedIndex)
                : Phase1CProtocolV0.ValidationRequest(stageIndex, seedIndex);
            var seedCount = seedUse == Phase1C0SeedUseV0.Training
                ? Phase1CProtocolV0.TrainingSeeds.Count
                : Phase1CProtocolV0.ValidationSeeds.Count;
            seedIndex = (seedIndex + 1) % seedCount;

            observation = environment.Reset(request);
            previousAction = PaddleActionV0.Zero;
            LastAction = PaddleActionV0.Zero;
            LastResult = null;
            LastReward = default;
            previousElapsedTime = observation.ElapsedTime;
            previousInterceptDistance =
                observation.BallPositionFromPaddle.magnitude;
            metrics = new Phase1C0EpisodeAccumulatorV0(
                seedUse,
                stageIndex,
                environment.CurrentManifest);
        }

        public override void CollectObservations(VectorSensor sensor)
        {
            EnsureConfigured();
            Phase1CObservationEncoderV0.Encode(
                observation,
                encodedObservation);
            sensor.AddObservation(encodedObservation);
        }

        public override void OnActionReceived(ActionBuffers actions)
        {
            EnsureConfigured();
            var action = DecodeAction(actions.ContinuousActions);
            var result = environment.Step(action);
            var currentInterceptDistance =
                result.Observation.BallPositionFromPaddle.magnitude;
            var reward = Phase1CRewardV0.Evaluate(
                result.RewardFeatures,
                new Phase1CRewardStateV0(
                    previousElapsedTime,
                    previousInterceptDistance,
                    currentInterceptDistance,
                    result.Observation.Episode.ControlledPaddleContacts > 0,
                    previousAction,
                    action));

            AddReward(reward.Total);
            metrics.Observe(result, action, reward.Total);

            LastAction = action;
            LastResult = result;
            LastReward = reward;
            observation = result.Observation;
            previousAction = action;
            previousElapsedTime = observation.ElapsedTime;
            previousInterceptDistance = currentInterceptDistance;

            if (!result.IsTerminal)
            {
                return;
            }

            var record = metrics.Complete();
            completedEpisodes.Add(record);
            evidence?.RecordEpisode(record, environment.Trajectory);
            EndEpisode();
        }

        public override void Heuristic(in ActionBuffers actionsOut)
        {
            // The only manual fallback is explicitly zero action. There is no
            // scripted interception or correction path in the training adapter.
            actionsOut.ContinuousActions.Clear();
            actionsOut.DiscreteActions.Clear();
        }

        public static PaddleActionV0 DecodeAction(
            ActionSegment<float> continuousActions)
        {
            if (continuousActions.Length != ContinuousActionSize)
            {
                throw new ArgumentException(
                    $"Phase 1C0 requires exactly {ContinuousActionSize} continuous actions.",
                    nameof(continuousActions));
            }

            return new PaddleActionV0(
                new Vector3(
                    continuousActions[0],
                    continuousActions[1],
                    continuousActions[2]),
                new Vector3(
                    continuousActions[3],
                    continuousActions[4],
                    continuousActions[5]));
        }

        private int ResolveStageIndex()
        {
            if (seedUse == Phase1C0SeedUseV0.Validation)
            {
                return seedIndex % Phase1CProtocolV0.CurriculumStages.Count;
            }

            var requested = Academy.Instance.EnvironmentParameters.GetWithDefault(
                CurriculumParameter,
                0f);
            return Mathf.Clamp(
                Mathf.RoundToInt(requested),
                0,
                Phase1CProtocolV0.CurriculumStages.Count - 1);
        }

        private void EnsureConfigured()
        {
            if (!configured || environment == null)
            {
                throw new InvalidOperationException(
                    "Phase1C0AgentV0 must be configured with env-v1 before use.");
            }

            Phase1CProtocolV0.ValidateOrThrow();
        }
    }
}

using Picklebot.Evaluation;
using Picklebot.Simulation;
using Unity.InferenceEngine;
using Unity.MLAgents;
using Unity.MLAgents.Actuators;
using Unity.MLAgents.Policies;
using UnityEngine;

namespace Picklebot.Training
{
    [DisallowMultipleComponent]
    public sealed class Phase1C0TrainingBootstrapV0 : MonoBehaviour
    {
        [SerializeField] private bool validationMode;
        [SerializeField] private bool writeEvidence = true;
        [SerializeField] private string runId = "phase1c0-local-001";
        [SerializeField] private ModelAsset inferenceModel;

        private PicklebotEnvironmentFixtureV1 fixture;

        public Phase1C0AgentV0 Agent { get; private set; }
        public PicklebotEnvironmentV1 Environment => fixture?.Environment;

        private void Start()
        {
            fixture = PicklebotEnvironmentFactoryV1.Create(
                "Phase1C0LearningEnvironment");
            fixture.Root.transform.SetParent(transform, worldPositionStays: true);
            ApplyDiagnosticColors();

            var behavior = fixture.Root.AddComponent<BehaviorParameters>();
            var brain = behavior.BrainParameters;
            brain.VectorObservationSize = Phase1CObservationEncoderV0.Size;
            brain.NumStackedVectorObservations = 1;
            brain.ActionSpec = ActionSpec.MakeContinuous(
                Phase1C0AgentV0.ContinuousActionSize);
            behavior.BehaviorName = Phase1C0AgentV0.BehaviorName;
            var policySource = "remote-trainer";
            if (validationMode)
            {
                if (inferenceModel != null)
                {
                    behavior.Model = inferenceModel;
                    behavior.BehaviorType = BehaviorType.InferenceOnly;
                    behavior.DeterministicInference = true;
                    policySource = inferenceModel.name;
                }
                else
                {
                    behavior.BehaviorType = BehaviorType.HeuristicOnly;
                    policySource = "zero-action-baseline";
                }
            }
            else
            {
                behavior.BehaviorType = BehaviorType.Default;
            }

            Agent = fixture.Root.AddComponent<Phase1C0AgentV0>();
            Agent.Configure(
                fixture.Environment,
                validationMode
                    ? Phase1C0SeedUseV0.Validation
                    : Phase1C0SeedUseV0.Training,
                writeEvidence,
                policySource,
                runId);

            var decisions = fixture.Root.AddComponent<DecisionRequester>();
            decisions.DecisionPeriod = 1;
            decisions.DecisionStep = 0;
            decisions.TakeActionsBetweenDecisions = true;

            var overlay = gameObject.AddComponent<Phase1C0TrainingOverlayV0>();
            overlay.Configure(Agent);
        }

        private void OnDestroy()
        {
            fixture?.Destroy();
            fixture = null;
        }

        private void ApplyDiagnosticColors()
        {
            foreach (var current in fixture.Root
                         .GetComponentsInChildren<Renderer>())
            {
                var color = current.name switch
                {
                    "CourtSurface" => new Color(0.16f, 0.42f, 0.52f),
                    "Ball" => new Color(0.88f, 0.95f, 0.15f),
                    "RoundedHittingFace" => new Color(0.85f, 0.18f, 0.48f),
                    "NonContactHandle" => new Color(0.12f, 0.12f, 0.14f),
                    _ when current.name.StartsWith("Net") =>
                        new Color(0.12f, 0.16f, 0.18f),
                    _ => current.material.color
                };
                current.material.color = color;
            }
        }
    }
}

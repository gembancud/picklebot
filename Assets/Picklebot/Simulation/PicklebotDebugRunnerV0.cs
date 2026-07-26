using Picklebot.Core;
using UnityEngine;

namespace Picklebot.Simulation
{
    [DisallowMultipleComponent]
    public sealed class PicklebotDebugRunnerV0 : MonoBehaviour
    {
        [SerializeField] private PicklebotEnvironmentV0 environment;
        [SerializeField] private string scenarioId = ScenarioCatalogV0.LaunchRally;
        [SerializeField] private ulong seed = 1;
        [SerializeField] private bool autoReset = true;

        private readonly ZeroActionSourceV0 actionSource = new();

        private void Start()
        {
            if (environment == null)
            {
                environment = GetComponent<PicklebotEnvironmentV0>();
            }

            ResetEpisode();
        }

        private void Update()
        {
            if (environment == null)
            {
                return;
            }

            if (environment.State == EpisodeStateV0.Terminal)
            {
                if (autoReset)
                {
                    seed++;
                    ResetEpisode();
                }

                return;
            }

            if (actionSource.TryGetNext(out var action))
            {
                environment.Step(action);
            }
        }

        [ContextMenu("Reset Episode")]
        public void ResetEpisode()
        {
            actionSource.Reset(seed);
            environment.Reset(new ResetRequestV0(seed, scenarioId));
        }
    }
}

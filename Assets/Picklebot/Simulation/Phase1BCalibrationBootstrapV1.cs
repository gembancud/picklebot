using Picklebot.Core;
using UnityEngine;

namespace Picklebot.Simulation
{
    [DisallowMultipleComponent]
    public sealed class Phase1BCalibrationBootstrapV1 : MonoBehaviour
    {
        private PicklebotEnvironmentFixtureV1 fixture;

        public PicklebotEnvironmentV1 Environment =>
            fixture?.Environment;

        private void Start()
        {
            fixture = PicklebotEnvironmentFactoryV1.Create(
                "Phase1BCalibratedEnvironment");
            fixture.Root.transform.SetParent(transform, worldPositionStays: true);
            fixture.Environment.Reset(new ResetRequestV0(
                8100000UL,
                ScenarioCatalogV0.LaunchRally));
        }

        private void OnDestroy()
        {
            fixture?.Destroy();
            fixture = null;
        }
    }
}

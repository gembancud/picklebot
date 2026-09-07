using System;
using NUnit.Framework;
using Picklebot.Core;
using Picklebot.Evaluation;
using Picklebot.Simulation;
using Picklebot.Training;
using Unity.MLAgents.Actuators;
using Unity.MLAgents.Policies;

namespace Picklebot.Tests.Phase1C0.PlayMode
{
    public sealed class Phase1C0AdapterPlayModeTests
    {
        private PicklebotEnvironmentFixtureV1 fixture;

        [TearDown]
        public void TearDown()
        {
            fixture?.Destroy();
        }

        [Test]
        public void AgentCallbackAdvancesEnvV1ExactlyOneControlBoundary()
        {
            fixture = PicklebotEnvironmentFactoryV1.Create(
                "Phase1C0AdapterPlayMode");
            var behavior = fixture.Root.AddComponent<BehaviorParameters>();
            behavior.BrainParameters.VectorObservationSize =
                Phase1CObservationEncoderV0.Size;
            behavior.BrainParameters.ActionSpec =
                ActionSpec.MakeContinuous(Phase1C0AgentV0.ContinuousActionSize);
            behavior.BehaviorName = Phase1C0AgentV0.BehaviorName;

            var agent = fixture.Root.AddComponent<Phase1C0AgentV0>();
            agent.Configure(
                fixture.Environment,
                Phase1C0SeedUseV0.Training,
                writeEvidence: false);
            agent.OnEpisodeBegin();

            var actionValues = new[] { 0.1f, -0.2f, 0.3f, -0.4f, 0.5f, -0.6f };
            agent.OnActionReceived(
                new ActionBuffers(actionValues, Array.Empty<int>()));

            Assert.That(agent.LastResult, Is.Not.Null);
            Assert.That(agent.LastResult.IsTerminal, Is.False);
            Assert.That(
                agent.LastResult.Observation.EnvironmentVersion,
                Is.EqualTo(SimulationConfigV1.EnvironmentVersion));
            Assert.That(
                agent.LastResult.Observation.PhysicsTick,
                Is.EqualTo((ulong)EnvironmentVersion.DefaultTicksPerAction));
            Assert.That(
                agent.LastAction.LinearVelocityLocal.x,
                Is.EqualTo(actionValues[0]));
            Assert.That(
                agent.LastAction.AngularVelocityLocal.z,
                Is.EqualTo(actionValues[5]));
        }
    }
}

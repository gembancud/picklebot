using System;
using NUnit.Framework;
using Picklebot.Training;
using Unity.MLAgents.Actuators;
using Unity.MLAgents.Policies;
using UnityEngine;

namespace Picklebot.Tests.Phase1C0.EditMode
{
    public sealed class Phase1C0AdapterContractTests
    {
        [Test]
        public void SixContinuousActionsMapDirectlyToThePaddleContract()
        {
            var action = Phase1C0AgentV0.DecodeAction(
                new ActionSegment<float>(new[]
                {
                    -1f, -0.5f, 0.25f, 0.5f, 0.75f, 1f
                }));

            Assert.That(
                action.LinearVelocityLocal,
                Is.EqualTo(new Vector3(-1f, -0.5f, 0.25f)));
            Assert.That(
                action.AngularVelocityLocal,
                Is.EqualTo(new Vector3(0.5f, 0.75f, 1f)));
        }

        [Test]
        public void ActionDecoderRejectsAnyShapeOtherThanSix()
        {
            Assert.Throws<ArgumentException>(() =>
                Phase1C0AgentV0.DecodeAction(
                    new ActionSegment<float>(new float[5])));
            Assert.Throws<ArgumentException>(() =>
                Phase1C0AgentV0.DecodeAction(
                    new ActionSegment<float>(new float[7])));
        }

        [Test]
        public void HeuristicIsStrictlyZeroOnly()
        {
            var root = new GameObject("Phase1C0HeuristicContract");
            try
            {
                root.AddComponent<BehaviorParameters>();
                var agent = root.AddComponent<Phase1C0AgentV0>();
                var continuous = new[] { 1f, -1f, 0.5f, -0.5f, 0.25f, -0.25f };
                var discrete = new[] { 1, 2 };
                var actions = new ActionBuffers(continuous, discrete);

                agent.Heuristic(in actions);

                Assert.That(continuous, Is.All.Zero);
                Assert.That(discrete, Is.All.Zero);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }
    }
}

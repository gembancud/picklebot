using System;
using NUnit.Framework;

namespace Picklebot.PlayerAgents.Tests
{
    public sealed class PlayerActorTests
    {
        private static PlayerActorModel Model() => new PlayerActorModel { layers = new[] {
            new ActorLayer { inputs = 54, outputs = 2, weights = new float[108], bias = new[] { .5f, -.5f } },
            new ActorLayer { inputs = 2, outputs = 12, weights = new float[24], bias = new float[12] } } };

        [Test] public void MalformedAndNonFiniteActorTensorsAreRejected()
        {
            var model = Model(); model.Validate(); model.layers[0].weights[0] = float.NaN;
            Assert.Throws<ArgumentException>(() => model.Validate());
            model = Model(); model.layers[1].inputs = 3; Assert.Throws<ArgumentException>(() => model.Validate());
            model = Model(); model.logStd[0] = -10; Assert.Throws<ArgumentException>(() => model.Validate());
        }
        [Test] public void RowMajorWeightsUseTanhOnlyBetweenLayers()
        {
            var model = Model(); model.layers[1].weights[0] = 2; model.layers[1].weights[1] = -3;
            model.Validate(); var output = model.Forward(new float[54]);
            Assert.That(output[0], Is.EqualTo(5 * Math.Tanh(.5)).Within(.000001));
        }
        [Test] public void IndependentActorInstancesKeepSeparateTrainingTraces()
        {
            var model = Model(); var first = new PlayerActor(model, true); var second = new PlayerActor(model, true);
            var observation = new PlayerObservation { player = 0, values = new float[54] };
            first.Decide(observation, new Random(1)); var trace = first.LastSample;
            second.Decide(observation, new Random(2));
            Assert.That(first.LastSample, Is.SameAs(trace)); Assert.That(second.LastSample, Is.Not.SameAs(trace));
            Assert.That(float.IsFinite(trace.logProbability));
        }
        [Test] public void DeterministicOutputUsesOwnMovementHitAndShotHeads()
        {
            var model = Model(); model.layers[1].bias[0] = 1; model.layers[1].bias[2] = -2; model.layers[1].bias[11] = 3;
            var actor = new PlayerActor(model); var action = actor.Decide(new PlayerObservation { values = new float[54] }, new Random(1));
            Assert.That(action.moveX, Is.EqualTo(Math.Tanh(1)).Within(.000001));
            Assert.That(action.moveZ, Is.Zero); Assert.That(action.attempt, Is.False); Assert.That(action.shot, Is.EqualTo(8));
        }
    }
}

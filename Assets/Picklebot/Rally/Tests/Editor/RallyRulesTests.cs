using NUnit.Framework;
using UnityEditor;
using UnityEngine;

namespace Picklebot.Rally.Tests
{
    public sealed class RallyRulesTests
    {
        [System.Serializable] private sealed class ReferenceCase { public float[] input, output; }
        [System.Serializable] private sealed class ReferenceSet { public ReferenceCase[] cases; }

        [Test] public void UnityInferenceMatchesPyTorchExportForBothSides()
        {
            var weights = AssetDatabase.LoadAssetAtPath<TextAsset>("Assets/Picklebot/Rally/Models/rally-policy.json");
            var reference = AssetDatabase.LoadAssetAtPath<TextAsset>("Assets/Picklebot/Rally/Models/rally-policy.reference.json");
            Assert.That(weights, Is.Not.Null);
            Assert.That(reference, Is.Not.Null);
            var cases = JsonUtility.FromJson<ReferenceSet>(reference.text).cases;
            Assert.That(cases.Length, Is.EqualTo(32));
            var policy = new RallyNeuralPolicy(weights);
            foreach (var sample in cases)
                foreach (int side in new[] { -1, 1 })
                {
                    float mirror = -side;
                    var p = new Vector3(sample.input[0]*mirror, sample.input[1], sample.input[2]*mirror);
                    var v = new Vector3(sample.input[3]*mirror, sample.input[4], sample.input[5]*mirror);
                    var actual = policy.Decide(p, v, side);
                    for (int i = 0; i < 4; i++) Assert.That(actual[i], Is.EqualTo(sample.output[i]).Within(.00001f));
                }
        }

        private RallyRules Receiving()
        {
            var rules = new RallyRules();
            rules.Reset(1);
            rules.Bounce(1);
            rules.Bounce(-1);
            return rules;
        }

        [Test] public void ServeMustBounceOnServerThenReceiver()
        {
            var rules = new RallyRules(); rules.Reset(1); rules.Bounce(-1);
            Assert.That(rules.Finished, Is.True);
            Assert.That(rules.Winner, Is.EqualTo(-1));
            var good = Receiving();
            Assert.That(good.ReadyToHit, Is.True);
            Assert.That(good.Returns, Is.Zero);
        }

        [Test] public void ReturnCountsOnlyWhenItLandsAcrossNet()
        {
            var rules = Receiving(); rules.Hit(-1);
            Assert.That(rules.Returns, Is.Zero);
            rules.Bounce(1);
            Assert.That(rules.Returns, Is.EqualTo(1));
            rules.Hit(1); rules.Bounce(-1);
            Assert.That(rules.Returns, Is.EqualTo(2));
            Assert.That(rules.Finished, Is.False);
        }

        [Test] public void SecondBounceLosesPoint()
        {
            var rules = Receiving(); rules.Bounce(-1);
            Assert.That(rules.Result, Is.EqualTo("Second bounce"));
            Assert.That(rules.Winner, Is.EqualTo(1));
        }

        [Test] public void VolleyLosesPoint()
        {
            var rules = Receiving(); rules.Hit(-1); rules.Hit(1);
            Assert.That(rules.Winner, Is.EqualTo(-1));
            Assert.That(rules.Result, Is.EqualTo("Volley or wrong paddle"));
        }

        [Test] public void WrongSideLandingAndNetLoseForHitter()
        {
            var rules = Receiving(); rules.Hit(-1); rules.Bounce(-1);
            Assert.That(rules.Winner, Is.EqualTo(1));
            rules = Receiving(); rules.Hit(-1); rules.Lost("Net contact");
            Assert.That(rules.Winner, Is.EqualTo(1));
        }

        [Test] public void OutAfterBounceLosesForReceiverAndTerminalIsImmutable()
        {
            var rules = Receiving(); rules.Lost("Miss or out");
            Assert.That(rules.Winner, Is.EqualTo(1));
            rules.Hit(-1); rules.Bounce(1);
            Assert.That(rules.Returns, Is.Zero);
            rules.Reset(-1);
            Assert.That(rules.Finished, Is.False);
            Assert.That(rules.Contacts, Is.Zero);
            Assert.That(rules.Receiver, Is.EqualTo(1));
        }
    }
}

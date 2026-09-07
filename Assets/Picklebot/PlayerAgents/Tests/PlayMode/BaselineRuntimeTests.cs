using System;
using System.IO;
using NUnit.Framework;
using Picklebot.Doubles;
using UnityEngine;

namespace Picklebot.PlayerAgents.Tests
{
    public sealed class BaselineRuntimeTests
    {
        private sealed class UnusedPolicy : IPlayerPolicy
        {
            public string Name => "unused baseline seat";
            public PlayerAction Decide(PlayerObservation observation, System.Random random) => throw new InvalidOperationException("Baseline seat invoked an actor.");
        }
        private static ContactModel Contact() => ContactModel.Load(File.ReadAllText(Path.Combine(Application.dataPath, "Picklebot/Doubles/Models/contact.json")));
        private static DoublesModels Models() => DoublesModels.Load(File.ReadAllText(Path.Combine(Application.dataPath, "Picklebot/Doubles/Models/teams.json")));
        private static IPlayerPolicy[] Unused() => new IPlayerPolicy[] { new UnusedPolicy(), new UnusedPolicy(), new UnusedPolicy(), new UnusedPolicy() };

        [TestCase(false)] [TestCase(true)]
        public void AdapterMatchesOriginalPhysicalControllerForEightRallies(bool sampled)
        {
            const int seed = 1100600;
            using var original = new DoublesMatch(false, seed) { CentreOnly = false, AutoNext = false, SampleActions = sampled, ContactModel = Contact(), Models = Models() };
            var adapter = new BaselineControl(3, Models(), Contact(), seed, sampled);
            using var adapted = new PlayerMatch(false, Unused(), Contact(), seed, adapter) { AutoNext = false };
            original.ServeJitter = adapted.ServeJitter = new Vector2(.13f, -.27f);
            int previous = 0;
            for (int tick = 0; tick < 65000 && original.CompletedRallies < 8; tick++)
            {
                original.Step(); adapted.Step();
                Assert.That(adapted.World.Rules.Phase, Is.EqualTo(original.World.Rules.Phase), $"tick {tick}");
                Assert.That(adapted.World.Rules.Hits, Is.EqualTo(original.World.Rules.Hits));
                Assert.That(adapted.World.Rules.LastFault, Is.EqualTo(original.World.Rules.LastFault));
                Assert.That(Vector3.Distance(adapted.World.Ball.position, original.World.Ball.position), Is.LessThan(.0001f), $"ball tick {tick}");
                Assert.That(Vector3.Distance(adapted.World.Ball.linearVelocity, original.World.Ball.linearVelocity), Is.LessThan(.0001f));
                for (int i = 0; i < 4; i++)
                {
                    Assert.That(Vector3.Distance(adapted.World.Players[i].Position, original.World.Players[i].Position), Is.LessThan(.0001f), $"body {i}, tick {tick}");
                    Assert.That(Vector3.Distance(adapted.World.Players[i].Paddle.position, original.World.Players[i].Paddle.position), Is.LessThan(.0001f), $"paddle {i}, tick {tick}");
                    Assert.That(Quaternion.Angle(adapted.World.Players[i].Paddle.rotation, original.World.Players[i].Paddle.rotation), Is.LessThan(.06f));
                }
                Assert.That(adapted.CompletedRallies, Is.EqualTo(original.CompletedRallies));
                if (original.CompletedRallies != previous)
                {
                    previous = original.CompletedRallies;
                    Assert.That(adapted.World.Rules.Score, Is.EqualTo(original.World.Rules.Score));
                    Assert.That(adapted.World.Rules.Server, Is.EqualTo(original.World.Rules.Server));
                    if (previous < 8) { original.Next(); adapted.Next(); }
                }
            }
            Assert.That(original.CompletedRallies, Is.EqualTo(8), "Probe safety cap reached.");
            Assert.That(adapted.Actors.Decisions, Is.Zero);
        }

        [TestCase(1)] [TestCase(2)]
        public void OpponentCannotMoveOrInvokePolicyForUnownedSeats(int teamMask)
        {
            var baseline = new BaselineControl(teamMask, Models(), Contact(), 1100620, true);
            using var w = new DoublesWorld(false);
            var before = new Vector3[4]; for (int i = 0; i < 4; i++) before[i] = w.Players[i].Position;
            baseline.Prepare(w, Vector2.zero);
            for (int i = 0; i < 4; i++)
            {
                Assert.That(w.Players[i].Position, Is.EqualTo(before[i]), "Prepare must not move a body.");
                if (!baseline.Controls(i)) Assert.Throws<InvalidOperationException>(() => baseline.StepPlayer(w, i));
            }
            var policies = Unused(); int calls = 0;
            for (int i = 0; i < 4; i++) if (!baseline.Controls(i)) policies[i] = new ConstantPlayerPolicy(default);
            var loop = new PlayerDecisionLoop(policies, 1100620, 15 & ~baseline.PlayerMask);
            loop.Decided += decision => { calls++; Assert.That(baseline.Controls(decision.player), Is.False); };
            for (int tick = 0; tick <= 6; tick++) loop.Step(w, tick);
            Assert.That(calls, Is.EqualTo(2));
        }
    }
}

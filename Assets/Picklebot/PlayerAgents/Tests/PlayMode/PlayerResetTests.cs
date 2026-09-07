using System.IO;
using System.Linq;
using NUnit.Framework;
using Picklebot.Doubles;
using UnityEngine;

namespace Picklebot.PlayerAgents.Tests
{
    public sealed class PlayerResetTests
    {
        [TestCase(0, false)] [TestCase(2, false)]
        [TestCase(0, true)] [TestCase(2, true)]
        [TestCase(1, false)] [TestCase(3, false)]
        [TestCase(1, true)] [TestCase(3, true)]
        public void StationaryKitchenMomentumFaultCanFinishWithoutChangingWinner(int player, bool baselineSeat)
        {
            var contact = ContactModel.Load(File.ReadAllText(Path.Combine(Application.dataPath, "Picklebot/Doubles/Models/contact.json")));
            var models = DoublesModels.Load(File.ReadAllText(Path.Combine(Application.dataPath, "Picklebot/Doubles/Models/teams.json")));
            var baseline = baselineSeat ? new BaselineControl(1 << (player / 2), models, contact, 1101300, true) : null;
            var policies = Enumerable.Range(0, 4).Select(i => (IPlayerPolicy)new ConstantPlayerPolicy(default)).ToArray();
            using var match = new PlayerMatch(false, policies, contact, 1101300, baseline) { AutoNext = false };
            var r = match.World.Rules;
            // Rule-state fixture: two legal bounces, then a legal volley.
            // Foot support and all subsequent motion use the real player body.
            r.Serve(0, true, true, true, true, false, false, false, 0);
            r.Bounce(new Vector3(r.ServiceX(r.DesignatedReceiver), 0, 4), .1f);
            r.Hit(2, .2f); r.Bounce(new Vector3(1, 0, -4), .3f);
            r.Hit(0, .4f); r.Hit(player >= 2 ? player : 2, .5f);
            if (player < 2) r.Hit(player, .6f);
            Assert.That(r.Dead, Is.False);
            match.World.Players[player].Reset(new Vector3(-1, 0, DoublesRules.Side(player / 2) * 1.5f));
            match.World.Simulate();
            Assert.That(r.LastFault, Is.EqualTo(Fault.KitchenMomentum));
            int winner = 1 - player / 2;
            Assert.That(r.Winner, Is.EqualTo(winner));
            Assert.That(r.ResolveRally(), Is.False, "The fault must first be settled using real feet.");
            for (int tick = 0; tick < 2400 && match.CompletedRallies == 0; tick++) match.Step();
            Assert.That(match.CompletedRallies, Is.EqualTo(1), "A stationary player inside the kitchen never leaves during the dead-ball reset.");
            Assert.That(r.Winner, Is.EqualTo(winner));
            Assert.That(r.LastFault, Is.EqualTo(Fault.KitchenMomentum));
            Assert.That(match.World.Players[player].BothFeetOutside);
            Assert.That(match.Actors.Decisions, Is.Zero, "Reset movement must not be recorded as an actor decision.");
            Assert.That(match.Metrics.deadBallClearanceSteps, Is.GreaterThan(0));
            Assert.That(match.Metrics.playerMaxSpeed[player], Is.LessThanOrEqualTo(3.801f));
            Assert.That(match.Metrics.playerMaxAcceleration[player], Is.LessThan(14.05f));
            Assert.That(r.Score[0] + r.Score[1], Is.EqualTo(winner == 0 ? 1 : 0));
            Assert.That(r.ResolveRally(), Is.False, "Scoring is idempotent.");
        }

        [Test]
        public void ClearanceNeedsRecordedDeadBallFaultAndSettledMomentum()
        {
            using var world = new DoublesWorld(false);
            var reset = new PlayerDeadBallReset();
            world.Players[0].Reset(new Vector3(-1, 0, -1.5f));
            Assert.That(reset.TryAction(world, 0, 10, out _), Is.False, "No scripted movement before a fault.");
            world.Rules.Fail(0, Fault.KitchenMomentum, 0, default, 0);
            Assert.That(reset.TryAction(world, 0, .9f, out _), Is.False, "Let momentum settle first.");
            Assert.That(reset.TryAction(world, 1, 2, out _), Is.False, "Do not move a non-faulted teammate.");
            Assert.That(reset.TryAction(world, 0, 2, out var action), Is.True);
            Assert.That(action.attempt, Is.False);
            Assert.That(action.WorldVelocity(0).z, Is.EqualTo(-1).Within(.0001));
            world.Players[0].Reset(new Vector3(-1, 0, -4));
            Assert.That(reset.TryAction(world, 0, 2, out _), Is.False, "Stop when real feet are outside.");
            Assert.That(world.Rules.ResolveRally(), Is.True);
            world.ResetRally(); reset.Reset();
            world.Players[0].Reset(new Vector3(-1, 0, -1.5f));
            world.Rules.Fail(0, Fault.Out, 0, default, 0);
            Assert.That(reset.TryAction(world, 0, 2, out _), Is.False, "Do not leak the previous fault into the next rally.");
        }
    }
}

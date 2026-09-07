using NUnit.Framework;
using System.IO;
using System.Linq;
using Picklebot.Doubles;
using UnityEngine;

namespace Picklebot.PlayerAgents.Tests
{
    public sealed class PlayerRuntimeTests
    {
        [TestCase(0)]
        [TestCase(2)]
        public void BouncedKitchenBallHasAReachableLowContactPlan(int player)
        {
            using var world = new DoublesWorld(false);
            for (int tick = 0; tick < 480 && !world.ServeBounced; tick++) world.Simulate();
            Assert.That(world.ServeBounced, Is.True);
            var rules = world.Rules;
            rules.Serve(0, true, true, true, true, false, false, false, world.Time);
            rules.Bounce(new Vector3(rules.ServiceX(rules.DesignatedReceiver), 0, 4), world.Time);
            rules.Hit(2, world.Time); rules.Bounce(new Vector3(1, 0, -4), world.Time); rules.Hit(0, world.Time);
            if (player == 0) rules.Hit(2, world.Time);
            Vector3 W(Vector3 p) => PlayerObservation.ToWorld(p, player);
            var body = world.Players[player];
            body.Reset(W(new Vector3(.82f, 0, -2.1f)));
            world.Players[player ^ 1].Reset(W(new Vector3(-1.55f, 0, -6)));
            world.Ball.position = W(new Vector3(1.2f, 1.2f, .4f));
            world.Ball.transform.position = world.Ball.position;
            world.Ball.linearVelocity = W(new Vector3(0, 1.2f, -3));
            world.Ball.angularVelocity = Vector3.zero; world.Ball.WakeUp();
            Physics.SyncTransforms(); rules.Events.Clear(); world.Contacts.Clear();
            for (int tick = 0; tick < 480 && !rules.Bounced && !rules.Dead; tick++) world.Simulate();
            Assert.That(rules.Dead, Is.False, rules.LastFault.ToString());
            Assert.That(rules.Bounced, Is.True);
            Assert.That(Mathf.Abs(world.Ball.position.z), Is.LessThan(DoublesRules.Kitchen));
            var feet = body.Position;
            var plan = new PlayerContactPlan();
            Assert.That(plan.Plan(world, player, new Vector2(0, 3.4f)), Is.True);
            Assert.That(plan.LowContact, Is.True);
            Assert.That(plan.Impact.z * body.Side, Is.LessThan(DoublesRules.Kitchen),
                "A bounced ball must not be forced outside the kitchen contact region.");
            Assert.That(body.Position, Is.EqualTo(feet), "Planning must not move the player.");
        }

        [TestCase(0, 0)]
        [TestCase(0, 4)]
        [TestCase(0, 8)]
        [TestCase(2, 0)]
        [TestCase(2, 4)]
        [TestCase(2, 8)]
        public void StationaryKitchenGroundstrokeMakesALegalPhysicalReturn(int player, int shot)
        {
            using var world = new DoublesWorld(false);
            for (int tick = 0; tick < 480 && !world.ServeBounced; tick++) world.Simulate();
            Assert.That(world.ServeBounced, Is.True);
            var rules = world.Rules;
            rules.Serve(0, true, true, true, true, false, false, false, world.Time);
            rules.Bounce(new Vector3(rules.ServiceX(rules.DesignatedReceiver), 0, 4), world.Time);
            rules.Hit(2, world.Time); rules.Bounce(new Vector3(1, 0, -4), world.Time); rules.Hit(0, world.Time);
            if (player == 0) rules.Hit(2, world.Time);
            Vector3 W(Vector3 p) => PlayerObservation.ToWorld(p, player);
            var body = world.Players[player];
            body.Reset(W(new Vector3(.82f, 0, -2.1f)));
            world.Players[player ^ 1].Reset(W(new Vector3(-1.55f, 0, -6)));
            world.Ball.position = W(new Vector3(1.2f, 1.2f, .4f));
            world.Ball.transform.position = world.Ball.position;
            world.Ball.linearVelocity = W(new Vector3(0, 1.2f, -3));
            world.Ball.angularVelocity = Vector3.zero; world.Ball.WakeUp();
            Physics.SyncTransforms(); rules.Events.Clear(); world.Contacts.Clear();
            var startFeet = body.Position;
            var swing = new PlayerSwing();
            var model = ContactModel.Load(File.ReadAllText("Assets/Picklebot/Doubles/Models/contact.json"));
            bool hit = false, landed = false;
            for (int tick = 0; tick < 1920 && !rules.Dead && !landed; tick++)
            {
                var previous = body.PaddleVelocity;
                // No movement action. Keep the real colliders after contact.
                swing.Step(world, player, new PlayerAction { attempt = !hit, shot = shot }, model);
                Assert.That(swing.PaddleStepFeasible, Is.True);
                Assert.That(body.PaddleVelocity.magnitude, Is.LessThanOrEqualTo(12.01f));
                Assert.That((body.PaddleVelocity - previous).magnitude / DoublesWorld.Dt, Is.LessThanOrEqualTo(100.1f));
                Assert.That(Vector3.Distance(body.Hand, body.Shoulder), Is.LessThanOrEqualTo(.6201f));
                Assert.That(body.AngularVelocity.magnitude, Is.LessThanOrEqualTo(12.01f));
                Assert.That(Vector3.Distance(body.Position, startFeet), Is.LessThan(.0001f));
                world.Simulate();
                int hitIndex = rules.Events.FindIndex(e => e.kind == "hit" && e.player == player);
                if (!hit && hitIndex >= 0)
                {
                    hit = true;
                    Assert.That(body.FeetInKitchen, Is.True);
                    Assert.That(rules.Events.Take(hitIndex).Any(e => e.kind == "bounce"), Is.True);
                    Assert.That(world.Contacts.Any(c => c.player == player && c.surface == "RoundedHittingFace"), Is.True);
                }
                if (hit)
                {
                    var bounce = rules.Events.Skip(hitIndex + 1).FirstOrDefault(e => e.kind == "bounce");
                    if (bounce != null)
                    {
                        landed = true;
                        Assert.That(bounce.position.z * body.Side, Is.LessThan(0));
                        Assert.That(Mathf.Abs(bounce.position.z), Is.LessThanOrEqualTo(DoublesRules.HalfLength));
                        Assert.That(Mathf.Abs(bounce.position.x), Is.LessThanOrEqualTo(DoublesRules.HalfWidth));
                    }
                }
            }
            Assert.That(rules.Dead, Is.False, rules.LastFault.ToString());
            Assert.That(hit, Is.True, "A physical kitchen groundstroke is required.");
            Assert.That(landed, Is.True, "The return must bounce inside the opposite court.");
        }

        private sealed class IdentityProbePolicy : IPlayerPolicy
        {
            public string Name => "identity test only";
            public readonly System.Collections.Generic.List<int> Draws = new System.Collections.Generic.List<int>();
            public int ObservationPlayer;
            public PlayerAction Decide(PlayerObservation observation, System.Random random)
            { ObservationPlayer = observation.player; Draws.Add(random.Next()); return default; }
        }

        [Test] public void DefaultIdentitiesKeepTheExistingRandomStreams()
        {
            using var world = new DoublesWorld(false);
            var policies = Enumerable.Range(0, 4).Select(_ => new IdentityProbePolicy()).ToArray();
            var loop = new PlayerDecisionLoop(policies, 1126000);
            loop.Step(world, 0);
            for (int i = 0; i < 4; i++)
            {
                Assert.That(loop.IdentityFor(i), Is.EqualTo(i));
                Assert.That(policies[i].Draws[0], Is.EqualTo(new System.Random(unchecked(1126000 * 397 + i * 7919)).Next()));
                Assert.That(policies[i].ObservationPlayer, Is.EqualTo(i));
            }
        }

        [Test] public void PartnerSwapMovesPolicyStateAndRandomStreamButNotObservationOwnership()
        {
            using var world = new DoublesWorld(false);
            var normalPolicies = Enumerable.Range(0, 4).Select(_ => new IdentityProbePolicy()).ToArray();
            var swappedPolicies = Enumerable.Range(0, 4).Select(_ => new IdentityProbePolicy()).ToArray();
            int[] identities = { 1, 0, 2, 3 };
            var normal = new PlayerDecisionLoop(normalPolicies, 1126001);
            var swapped = new PlayerDecisionLoop(identities.Select(i => (IPlayerPolicy)swappedPolicies[i]).ToArray(), 1126001, 15, identities);
            normal.Step(world, 0); swapped.Step(world, 0);
            normal.Reset(); swapped.Reset();
            normal.Step(world, 0); swapped.Step(world, 0);
            for (int identity = 0; identity < 4; identity++)
            {
                Assert.That(swappedPolicies[identity].Draws, Is.EqualTo(normalPolicies[identity].Draws));
                Assert.That(swappedPolicies[identity].Draws.Count, Is.EqualTo(2));
                Assert.That(swappedPolicies[identity].ObservationPlayer, Is.EqualTo(System.Array.IndexOf(identities, identity)));
            }
            Assert.That(swappedPolicies[0].Draws[0], Is.Not.EqualTo(swappedPolicies[1].Draws[0]));
        }

        [Test] public void IdentityAssignmentIsCopiedAndRejectsInvalidOrCrossTeamMaps()
        {
            int[] identities = { 1, 0, 3, 2 };
            var loop = new PlayerDecisionLoop(Policies(), 1126002, 15, identities);
            identities[0] = 0;
            Assert.That(loop.IdentityFor(0), Is.EqualTo(1));
            foreach (var invalid in new[] { new[] { 0, 0, 2, 3 }, new[] { 2, 1, 0, 3 }, new[] { 0, 1, 2 }, new[] { -1, 1, 2, 3 } })
                Assert.Throws<System.ArgumentException>(() => new PlayerDecisionLoop(Policies(), 1126002, 15, invalid));
        }

        private static IPlayerPolicy[] Policies() => new IPlayerPolicy[] {
            new ConstantPlayerPolicy(new PlayerAction { moveX = 1, attempt = true, shot = 3 }),
            new ConstantPlayerPolicy(new PlayerAction { moveX = -1, shot = 4 }),
            new ConstantPlayerPolicy(new PlayerAction { moveZ = 1, attempt = true, shot = 5 }),
            new ConstantPlayerPolicy(new PlayerAction { moveZ = -1, shot = 8 }) };

        [Test] public void EveryObservationHasSeparateOwnedValues()
        {
            using var w = new DoublesWorld(false);
            var a = PlayerObservation.Capture(w, 0, 42); var b = PlayerObservation.Capture(w, 1, 42);
            Assert.That(a.values.Length, Is.EqualTo(54)); Assert.That(a.player, Is.Zero); Assert.That(b.player, Is.EqualTo(1));
            Assert.That(a.values, Is.Not.SameAs(b.values)); Assert.That(a.values[0], Is.Not.EqualTo(b.values[0]));
            float before = w.Players[0].Position.x; a.values[0] = 999;
            Assert.That(w.Players[0].Position.x, Is.EqualTo(before)); Assert.That(b.values[0], Is.Not.EqualTo(999));
        }

        [Test] public void ActionsApplyTogetherOnlyAfterTheirLatency()
        {
            using var w = new DoublesWorld(false); var loop = new PlayerDecisionLoop(Policies(), 1000001);
            int recorded = 0; loop.Decided += d => { recorded++; Assert.That(d.observationTick, Is.Zero); Assert.That(d.applyTick, Is.EqualTo(6)); };
            for (int tick = 0; tick < 6; tick++)
            { loop.Step(w, tick); for (int i = 0; i < 4; i++) Assert.That(loop.ActionFor(i).WorldVelocity(i), Is.EqualTo(Vector3.zero)); }
            Assert.That(recorded, Is.EqualTo(4)); loop.Step(w, 6);
            Assert.That(loop.ActionFor(0).moveX, Is.EqualTo(1)); Assert.That(loop.ActionFor(1).moveX, Is.EqualTo(-1));
            Assert.That(loop.ActionFor(2).moveZ, Is.EqualTo(1)); Assert.That(loop.ActionFor(3).moveZ, Is.EqualTo(-1));
            Assert.That(loop.ActionFor(0).attempt); Assert.That(loop.ActionFor(1).attempt, Is.False);
        }

        [Test] public void LeaveActionDoesNotSelectAnInterceptOrRecoveryPosition()
        {
            using var w = new DoublesWorld(false); var p = w.Players[1]; var start = p.Position;
            var swing = new PlayerSwing();
            for (int i = 0; i < 60; i++) { swing.Step(w, 1, default, null); w.Simulate(); }
            Assert.That(Vector3.Distance(start, p.Position), Is.LessThan(.0001f)); Assert.That(swing.Contact.Planned, Is.False);
        }

        [Test] public void OwnMovementCommandMovesOnlyItsAssignedBody()
        {
            using var w = new DoublesWorld(false); var initial = w.Players[1].Position;
            var own = w.Players[0].Position; var swing = new PlayerSwing();
            for (int i = 0; i < 60; i++)
            { swing.Step(w, 0, new PlayerAction { moveZ = -1 }, null); w.Simulate(); }
            Assert.That(w.Players[0].Position.z, Is.LessThan(own.z - .05f));
            Assert.That(w.Players[1].Position, Is.EqualTo(initial));
        }

        [Test] public void ResetClearsPendingAndActiveActions()
        {
            using var w = new DoublesWorld(false); var loop = new PlayerDecisionLoop(Policies(), 1000002);
            loop.Step(w, 0); loop.Reset(); loop.Step(w, 6);
            for (int i = 0; i < 4; i++) Assert.That(loop.ActionFor(i).WorldVelocity(i), Is.EqualTo(Vector3.zero));
        }

        [Test] public void DropServeStillRequiresPhysicalContact()
        {
            using var m = new PlayerMatch(false, Policies(), null) { AutoNext = false };
            Assert.That(m.World.Ball.linearVelocity, Is.EqualTo(Vector3.zero));
            for (int i = 0; i < 800 && m.World.Rules.Hits == 0 && !m.World.Rules.Dead; i++) m.Step();
            Assert.That(m.World.ServeBounced); Assert.That(m.World.Rules.Hits, Is.EqualTo(1), m.World.Rules.LastFault.ToString());
            Assert.That(m.Metrics.serves[0], Is.EqualTo(1));
            Assert.That(m.Metrics.legalHits[0], Is.Zero);
        }

        [Test] public void BrakingAvoidsHardPartnerPositionCorrections()
        {
            using var w = new DoublesWorld(false);
            w.Players[0].Reset(new Vector3(-1, 0, -4)); w.Players[1].Reset(new Vector3(1, 0, -4));
            var swings = new[] { new PlayerSwing(), new PlayerSwing() }; bool limited = false;
            for (int tick = 0; tick < 480; tick++)
            {
                for (int i = 0; i < 2; i++)
                {
                    var oldVelocity = w.Players[i].Velocity;
                    swings[i].Step(w, i, new PlayerAction { moveX = i == 0 ? 1 : -1 }, null);
                    limited |= swings[i].SafetyLimited;
                    Assert.That((w.Players[i].Velocity - oldVelocity).magnitude / DoublesWorld.Dt, Is.LessThan(14.05f));
                }
                w.Simulate(); Assert.That(Vector3.Distance(w.Players[0].Position, w.Players[1].Position), Is.GreaterThan(.56f));
            }
            Assert.That(limited);
        }

        [Test] public void FinalContactWindowKeepsShotButStillAllowsMovementAndCancel()
        {
            var policies = Enumerable.Range(0, 4).Select(i => (IPlayerPolicy)new ConstantPlayerPolicy(new PlayerAction { attempt = true })).ToArray();
            using var match = new PlayerMatch(false, policies, null) { AutoNext = false };
            // Test swing commitment on a fixed incoming ball. A stationary
            // actor's ability to reach a particular serve is a separate skill.
            var world = match.World; var rules = world.Rules;
            for (int tick = 0; tick < 480 && !world.ServeBounced; tick++) world.Simulate();
            rules.Serve(0, true, true, true, true, false, false, false, world.Time);
            rules.Bounce(new Vector3(rules.ServiceX(rules.DesignatedReceiver), 0, 4), world.Time);
            rules.Hit(2, world.Time); rules.Bounce(new Vector3(1, 0, -4), world.Time); rules.Hit(0, world.Time); rules.Hit(2, world.Time);
            world.Players[0].Reset(new Vector3(.82f, 0, -5.5f));
            world.Players[1].Reset(new Vector3(-1.55f, 0, -6));
            world.Ball.position = new Vector3(1.2f, 1.2f, .4f); world.Ball.transform.position = world.Ball.position;
            world.Ball.linearVelocity = new Vector3(0, 1.2f, -8); world.Ball.angularVelocity = Vector3.zero;
            Physics.SyncTransforms();
            int selectedPlayer = -1;
            for (int tick = 0; tick < 1800 && selectedPlayer < 0 && !match.World.Rules.Dead; tick++)
            {
                match.Step();
                for (int i = 0; i < 4; i++)
                {
                    var plan = match.Swings[i].Contact;
                    if (plan.Planned && plan.ImpactAt - match.World.Time > 0 && plan.ImpactAt - match.World.Time < .12f) { selectedPlayer = i; break; }
                }
            }
            Assert.That(selectedPlayer, Is.GreaterThanOrEqualTo(0), "No physical contact plan reached its commitment window.");
            var swing = match.Swings[selectedPlayer]; var normal = swing.Contact.Normal; float impactAt = swing.Contact.ImpactAt;
            swing.Step(match.World, selectedPlayer, new PlayerAction { attempt = true, shot = 5, moveX = .3f }, null);
            Assert.That(swing.RequestedShot, Is.EqualTo(5)); Assert.That(swing.SelectedShot, Is.Zero); Assert.That(swing.ShotCommitted);
            Assert.That(swing.Contact.ImpactAt, Is.EqualTo(impactAt)); Assert.That(swing.Contact.Normal, Is.EqualTo(normal));
            Assert.That(swing.RequestedVelocity.magnitude, Is.EqualTo(.3f * PlayerBody.Speed).Within(.0001f));
            swing.Step(match.World, selectedPlayer, new PlayerAction { attempt = false, shot = 5 }, null);
            Assert.That(swing.Contact.Planned, Is.False); Assert.That(swing.ShotCommitted, Is.False);
            Assert.That(swing.SelectedShot, Is.EqualTo(5));
        }

        [TestCase(0, -.3f, .4f)] [TestCase(0, 0, 0)] [TestCase(0, .3f, -.4f)]
        [TestCase(1, -.3f, .4f)] [TestCase(1, 0, 0)] [TestCase(1, .3f, -.4f)]
        [TestCase(2, -.3f, .4f)] [TestCase(2, 0, 0)] [TestCase(2, .3f, -.4f)]
        [TestCase(3, -.3f, .4f)] [TestCase(3, 0, 0)] [TestCase(3, .3f, -.4f)]
        [TestCase(0, -.3f, .4f, true)] [TestCase(0, 0, 0, true)] [TestCase(0, .3f, -.4f, true)]
        [TestCase(1, -.3f, .4f, true)] [TestCase(1, 0, 0, true)] [TestCase(1, .3f, -.4f, true)]
        [TestCase(2, -.3f, .4f, true)] [TestCase(2, 0, 0, true)] [TestCase(2, .3f, -.4f, true)]
        [TestCase(3, -.3f, .4f, true)] [TestCase(3, 0, 0, true)] [TestCase(3, .3f, -.4f, true)]
        public void ScriptedServeAndReleaseRespectIndependentMotorLimits(int server, float x, float depth, bool alternatePosition = false)
        {
            var policies = Enumerable.Range(0, 4).Select(_ => (IPlayerPolicy)new ConstantPlayerPolicy(default)).ToArray();
            using var match = new PlayerMatch(false, policies, null) { AutoNext = false, ServeJitter = new Vector2(x, depth) };
            var world = match.World; var rules = world.Rules;
            // Select the service seat through public side-out rules. These
            // setup faults occur before any measured physical movement.
            for (int setup = 0; rules.Server != server && setup < 8; setup++)
            { rules.Fail(rules.ServingTeam, Fault.Lost, 0); Assert.That(rules.ResolveRally()); match.Next(); }
            Assert.That(rules.Server, Is.EqualTo(server));
            if (alternatePosition)
            {
                float originalX = rules.ServiceX(server);
                rules.Fail(1 - rules.ServingTeam, Fault.Lost, 0);
                Assert.That(rules.ResolveRally()); match.Next();
                Assert.That(rules.Server, Is.EqualTo(server));
                Assert.That(rules.ServiceX(server), Is.EqualTo(-originalX));
            }
            var body = world.Players[server]; bool release = false;
            for (int tick = 0; tick < 960 && !rules.Dead; tick++)
            {
                var previous = body.PaddleVelocity; var previousFeet = body.Velocity;
                match.Step(); release |= rules.Phase == RallyPhase.ServeFlight;
                Assert.That(body.PaddleVelocity.magnitude, Is.LessThanOrEqualTo(12.01f));
                Assert.That((body.PaddleVelocity - previous).magnitude / DoublesWorld.Dt, Is.LessThanOrEqualTo(100.1f));
                Assert.That((body.Velocity - previousFeet).magnitude / DoublesWorld.Dt, Is.LessThanOrEqualTo(14.05f));
                Assert.That(body.AngularVelocity.magnitude, Is.LessThanOrEqualTo(12.01f));
                Assert.That(Vector3.Distance(body.Hand, body.Shoulder), Is.LessThanOrEqualTo(.6201f));
                if (rules.Phase == RallyPhase.ServeFlight && rules.Bounced) break;
            }
            Assert.That(release, Is.True, "A real physical serve must release to actor control.");
            Assert.That(match.Metrics.infeasiblePaddleSteps, Is.Zero);
            Assert.That(rules.Events.Any(e => e.kind == "serve" && e.player == server), Is.True);
            Assert.That(world.Contacts.Any(c => c.player == server && c.surface == "RoundedHittingFace"), Is.True);
            Assert.That(rules.Phase == RallyPhase.ServeFlight && rules.Bounced && !rules.Dead, Is.True,
                "A bounded serve must also land legally in the opposite service court. Fault: " + rules.LastFault);
        }

        [Test] public void MissedSwingExpiresAfterItsFollowThroughWithoutMovingFeet()
        {
            using var w = new DoublesWorld(false);
            var r = w.Rules;
            r.Serve(0, true, true, true, true, false, false, false, 0);
            r.Bounce(new Vector3(r.ServiceX(r.DesignatedReceiver), 0, 4), 0);
            r.Hit(2, 0); r.Bounce(new Vector3(1, 0, -4), 0); r.Hit(0, 0); r.Hit(2, 0);
            w.Players[0].Reset(new Vector3(1.55f, 0, -3.5f));
            w.Players[1].Reset(new Vector3(-1.55f, 0, -3.5f));
            w.Ball.position = new Vector3(2.6f, 1.2f, .4f); w.Ball.transform.position = w.Ball.position;
            w.Ball.linearVelocity = new Vector3(0, 1.2f, -8); w.Ball.angularVelocity = Vector3.zero;
            Physics.SyncTransforms();
            var swing = new PlayerSwing(); bool planned = false;
            var start = w.Players[0].Position;
            for (int tick = 0; tick < 240 && !r.Dead; tick++)
            {
                swing.Step(w, 0, new PlayerAction { attempt = true }, null);
                planned |= swing.Contact.Planned;
                w.Simulate();
                Assert.That(swing.Contact.Planned && w.Time > swing.Contact.ImpactAt + .06f, Is.False,
                    "An expired swing must not keep aiming at a ball position in the past.");
            }
            Assert.That(planned, Is.True, "The fixture must exercise a real contact plan.");
            Assert.That(Vector3.Distance(start, w.Players[0].Position), Is.LessThan(.0001f));
        }

        [TestCase(0, 5.5f)] [TestCase(0, 6f)] [TestCase(0, 6.5f)] [TestCase(0, 7f)]
        [TestCase(2, 5.5f)] [TestCase(2, 6f)] [TestCase(2, 6.5f)] [TestCase(2, 7f)]
        public void LowReboundCanBePlannedWithoutAutomaticFootMovement(int player, float depth)
        {
            using var w = new DoublesWorld(false);
            for (int tick = 0; tick < 480 && !w.ServeBounced; tick++) w.Simulate();
            var r = w.Rules;
            r.Serve(0, true, true, true, true, false, false, false, w.Time);
            r.Bounce(new Vector3(r.ServiceX(r.DesignatedReceiver), 0, 4), w.Time);
            r.Hit(2, w.Time); r.Bounce(new Vector3(1, 0, -4), w.Time); r.Hit(0, w.Time);
            if (player == 0) r.Hit(2, w.Time);
            Vector3 World(Vector3 p) => PlayerObservation.ToWorld(p, player);
            w.Players[player].Reset(World(new Vector3(.82f, 0, -depth)));
            w.Players[player ^ 1].Reset(World(new Vector3(-1.55f, 0, -6)));
            w.Ball.position = World(new Vector3(1.2f, 1.2f, .4f)); w.Ball.transform.position = w.Ball.position;
            w.Ball.linearVelocity = World(new Vector3(0, 1.2f, -8)); w.Ball.angularVelocity = Vector3.zero;
            Physics.SyncTransforms();
            r.Events.Clear(); w.Contacts.Clear();
            var model = ContactModel.Load(File.ReadAllText("Assets/Picklebot/Doubles/Models/contact.json"));
            var swing = new PlayerSwing(); bool lowPlan = false; var start = w.Players[player].Position;
            for (int tick = 0; tick < 900 && !r.Dead; tick++)
            {
                var previous = w.Players[player].PaddleVelocity;
                swing.Step(w, player, new PlayerAction { attempt = true }, model);
                lowPlan |= swing.Contact.Planned && swing.Contact.Impact.y < .52f;
                w.Simulate();
                Assert.That(Vector3.Distance(w.Players[player].Hand, w.Players[player].Shoulder), Is.LessThanOrEqualTo(.6201f));
                Assert.That(Vector3.Distance(start, w.Players[player].Position), Is.LessThan(.0001f));
                Assert.That(w.Players[player].PaddleVelocity.magnitude, Is.LessThanOrEqualTo(12.01f));
                Assert.That((w.Players[player].PaddleVelocity - previous).magnitude / DoublesWorld.Dt, Is.LessThanOrEqualTo(100.1f));
                Assert.That(w.Players[player].AngularVelocity.magnitude, Is.LessThanOrEqualTo(12.01f));
                if (r.Events.Any(e => e.kind == "bounce" && e.position.z * w.Players[player].Side < 0)) break;
            }
            Assert.That(lowPlan, Is.True, "A low rebound must have a reachable contact plan on both court ends.");
            Assert.That(r.Events.Any(e => e.kind == "hit" && e.player == player), Is.True, "The planned return must make real, legal contact.");
            Assert.That(w.Contacts.Any(c => c.player == player && c.surface == "RoundedHittingFace" && c.point.y < .52f), Is.True);
            if (depth <= 6)
                Assert.That(r.Events.Any(e => e.kind == "bounce" && e.position.z * w.Players[player].Side < 0), Is.True,
                    "The reachable near fixture must land legally on the other side.");
        }

        [Test] public void RecordedDiagonalPartnerApproachDoesNotTriggerHardSeparation()
        {
            string path = Path.Combine(Application.dataPath, "Picklebot/PlayerAgents/Tests/Fixtures/partner-motion-v1.csv");
            using (var hash = System.Security.Cryptography.SHA256.Create())
                Assert.That(System.BitConverter.ToString(hash.ComputeHash(File.ReadAllBytes(path))).Replace("-", "").ToLowerInvariant(),
                    Is.EqualTo("9d4d7a7bc892fcb4e2a5fa74c8651cdd9fbf0809a353f237be08b8466fe824f9"));
            var rows = File.ReadAllLines(path).Skip(1).Select(line => line.Split(',').Select(s => float.Parse(s, System.Globalization.CultureInfo.InvariantCulture)).ToArray())
                .Where(row => row[1] == 2 || row[1] == 3).ToArray();
            Assert.That(rows.Length, Is.EqualTo(240));
            using var w = new DoublesWorld(false); var swings = new[] { new PlayerSwing(), new PlayerSwing() };
            for (int i = 0; i < 2; i++)
            {
                var row = rows[i]; int id = (int)row[1];
                w.Players[id].Reset(new Vector3(row[2], 0, row[3]));
                // Restore the captured initial motor state for this regression only.
                // No running actor can set a body state through this test helper.
                typeof(PlayerBody).GetProperty("Velocity").SetValue(w.Players[id], new Vector3(row[4], 0, row[5]));
            }
            for (int n = 0; n < rows.Length; n += 2)
            {
                Assert.That(rows[n][0], Is.EqualTo(rows[n + 1][0]));
                for (int i = 0; i < 2; i++)
                {
                    var row = rows[n + i]; int id = i + 2; Assert.That(row[1], Is.EqualTo(id));
                    var local = PlayerObservation.ToLocal(new Vector3(row[6], 0, row[7]) / PlayerBody.Speed, id);
                    var before = w.Players[id].Velocity;
                    swings[i].Step(w, id, new PlayerAction { moveX = local.x, moveZ = local.z }, null);
                    Assert.That((w.Players[id].Velocity - before).magnitude / DoublesWorld.Dt, Is.LessThan(14.05f), $"recorded tick {row[0]}, player {id}");
                }
                Assert.That(Vector3.Distance(w.Players[2].Position, w.Players[3].Position), Is.GreaterThan(.64f));
                w.Simulate();
            }
        }

        [TestCase(0)] [TestCase(1)] [TestCase(2)] [TestCase(3)]
        public void VectorBrakingKeepsTurnsAndCornerChasesWithinMotorLimits(int scenario)
        {
            using var w = new DoublesWorld(false);
            var random = new System.Random(1100310 + scenario);
            w.Players[0].Reset(new Vector3(3, 0, -7));
            w.Players[1].Reset(new Vector3(scenario < 2 ? -3 : 2, 0, -6.5f));
            var swings = new[] { new PlayerSwing(), new PlayerSwing() }; var actions = new PlayerAction[2];
            for (int tick = 0; tick < 4800; tick++)
            {
                for (int i = 0; i < 2; i++)
                {
                    if (tick % 12 == 0)
                    {
                        if (scenario == 0) actions[i] = new PlayerAction { moveX = i == 0 ? 1 : -1, moveZ = tick % 240 < 120 ? -1 : 1 }.Validated();
                        else if (scenario == 1) actions[i] = new PlayerAction { moveX = (float)(random.NextDouble() * 2 - 1), moveZ = (float)(random.NextDouble() * 2 - 1) }.Validated();
                        else
                        {
                            var target = scenario == 2 ? new Vector3(4.2f, 0, -8.1f) : w.Players[i ^ 1].Position;
                            var direction = (target - w.Players[i].Position).normalized;
                            actions[i] = new PlayerAction { moveX = direction.x, moveZ = direction.z };
                        }
                    }
                    var before = w.Players[i].Velocity;
                    swings[i].Step(w, i, tick % 960 >= 720 ? default : actions[i], null);
                    Assert.That((w.Players[i].Velocity - before).magnitude / DoublesWorld.Dt, Is.LessThan(14.05f), $"scenario {scenario}, tick {tick}, player {i}");
                    Assert.That(Mathf.Abs(w.Players[i].Position.x), Is.LessThan(4.2f));
                    Assert.That(-w.Players[i].Position.z, Is.InRange(.38f, 8.1f));
                }
                Assert.That(Vector3.Distance(w.Players[0].Position, w.Players[1].Position), Is.GreaterThan(.56f));
                w.Simulate();
            }
        }

        [Test] public void BrakingAvoidsHardCourtLimitCorrections()
        {
            using var w = new DoublesWorld(false); w.Players[0].Reset(new Vector3(-2, 0, -7));
            var swing = new PlayerSwing(); bool limited = false;
            for (int tick = 0; tick < 480; tick++)
            {
                var oldVelocity = w.Players[0].Velocity;
                swing.Step(w, 0, new PlayerAction { moveZ = -1 }, null); limited |= swing.SafetyLimited;
                Assert.That((w.Players[0].Velocity - oldVelocity).magnitude / DoublesWorld.Dt, Is.LessThan(14.05f));
                w.Simulate();
            }
            Assert.That(limited); Assert.That(w.Players[0].Position.z, Is.GreaterThan(-8.1f));
        }
    }
}

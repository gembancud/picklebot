using System;
using System.Collections;
using NUnit.Framework;
using Picklebot.Doubles;
using Picklebot.PlayerControls;
using UnityEngine;
using UnityEngine.TestTools;

namespace Picklebot.PlayerControlsIntegration.Tests
{
    public sealed class PlayerServeLearningV3Tests
    {
        private sealed class Policy : IPlayerPolicyV3
        {
            public bool release;
            public PlayerActionV3 command;
            public int resets;
            public string Name => "release ownership fixture";
            public void Reset() { resets++; }
            public PlayerActionV3 Decide(PlayerObservationV3 observation, System.Random random)
            {
                var action = command.ToArray();
                if (release) action[16] = 1;
                return new PlayerActionV3(action);
            }
        }

        [UnityTest]
        public IEnumerator LowDropContactIsReachableThroughTheNormalBoundedDecisionLoop()
        {
            // Fixed feasibility fixture only. These commands are never installed
            // in a trainer or used as demonstrations. No ball writes or hit impulses.
            var command=new PlayerActionV3(new float[]{0,0,0,.5f,0,0,-.254720449f,1,1,
                -.134723678f,.24835f,-.965271354f,-.805382f,-.722499f,-.147358075f,-.447676748f,1,0});
            for(int seat=0;seat<4;seat++)
            {
                using(var drill=new PlayerContactDrillV3(1301040+seat,seat,"drop-serve"))
                {
                    var policies=new IPlayerPolicyV3[4];
                    for(int i=0;i<4;i++)policies[i]=new Policy{command=i==seat?command:default};
                    drill.Match.AttachPolicies(policies,drill.Seed);
                    while(!drill.Done)
                    {
                        drill.Step();
                        Assert.IsNull(drill.Match.Failure);
                        var body=drill.Match.World.Players[seat];
                        Assert.LessOrEqual(body.PaddleVelocity.magnitude,PlayerBody.PaddleSpeed+.01f);
                        Assert.LessOrEqual(body.AngularVelocity.magnitude,PlayerBody.AngularSpeed+.01f);
                        if(drill.Match.Tick<=6)Assert.IsTrue(drill.Match.BallHeld);
                    }
                    Assert.AreEqual(7,drill.ReleaseTick);
                    Assert.IsTrue(drill.DropBounced);Assert.IsTrue(drill.FaceContact,drill.Outcome);
                    Assert.IsTrue(drill.ServeAccepted,"Contact must follow the actual drop bounce with legal serve feet.");
                    TestContext.WriteLine("Seat "+seat+" physical low contact; landing outcome="+drill.Outcome+". This fixture is not learned behavior or proof of a successful serve landing.");
                }
                yield return null;
            }
        }

        [UnityTest]
        public IEnumerator AnySeatCanServeButOnlyItsOwnReleaseActionDropsTheBall()
        {
            for (int server = 0; server < 4; server++)
            {
                using (var match = new PlayerLearningMatchV3(false, server))
                {
                    Assert.AreEqual(server, match.World.Rules.Server);
                    Assert.AreEqual(server / 2, match.World.Rules.ServingTeam);
                    Assert.IsTrue(match.World.Rules.IsRight(server));
                    CollectionAssert.AreEqual(new[] { 0, 0 }, match.World.Rules.Score);
                    var actions = new PlayerActionV3[4];
                    var release = new float[PlayerActionV3.Count]; release[16] = 1;
                    actions[server ^ 1] = new PlayerActionV3(release);
                    Assert.IsTrue(match.Step(actions));
                    Assert.IsTrue(match.BallHeld);
                    actions[server] = new PlayerActionV3(release);
                    Assert.IsTrue(match.Step(actions));
                    Assert.IsFalse(match.BallHeld);
                    Assert.Less(match.World.Ball.linearVelocity.y, 0);
                    Assert.AreEqual(0, match.World.Ball.linearVelocity.x);
                    Assert.AreEqual(0, match.World.Ball.linearVelocity.z);
                    Assert.AreEqual(RallyPhase.AwaitServe, match.World.Rules.Phase);
                }
                yield return null;
            }
        }

        [UnityTest]
        public IEnumerator ServeDrillAllowsThePhysicalDropBounceWithoutClaimingAServe()
        {
            using (var drill = new PlayerContactDrillV3(1300300, 0, "drop-serve"))
            {
                drill.Match.AttachPolicies(new IPlayerPolicyV3[] { new Policy { release = true }, new Policy(), new Policy(), new Policy() }, drill.Seed);
                Assert.IsTrue(PlayerContactDrillV3.ActionMask(0, 0, "drop-serve")[16]);
                while (!drill.DropBounced && !drill.Done) drill.Step();
                Assert.IsTrue(drill.Released);
                Assert.IsTrue(drill.DropBounced, drill.Outcome);
                Assert.IsFalse(drill.Done, drill.Outcome);
                Assert.IsFalse(drill.ServeAccepted);
                Assert.IsFalse(drill.FaceContact);
                Assert.AreEqual(7, drill.ReleaseTick);
                Assert.AreEqual(RallyPhase.AwaitServe, drill.Match.World.Rules.Phase);
            }
            yield return null;
        }

        [UnityTest]
        public IEnumerator RallyResetRetainsScoreAndClearsPendingActionsAndBodyState()
        {
            using (var match = new PlayerLearningMatchV3())
            {
                var policies = new[] { new Policy { release = true }, new Policy(), new Policy(), new Policy() };
                match.AttachPolicies(policies, 1300301);
                Assert.IsTrue(match.StepAgents()); // Release is queued, not yet applied.
                policies[0].release = false;
                match.World.Rules.Fail(1, Fault.Out, match.World.Time); // Rule lifecycle fixture.
                Assert.IsTrue(match.TryResetRally());
                Assert.AreEqual(1, match.World.Rules.Score[0]);
                Assert.AreEqual(1, match.RallyIndex);
                Assert.AreEqual(1, match.TotalTicks);
                Assert.AreEqual(0, match.Tick);
                Assert.IsTrue(match.BallHeld);
                for (int i = 0; i < 4; i++)
                {
                    Assert.AreEqual(1, policies[i].resets);
                    Assert.AreEqual(Vector3.zero, match.Controls.StateFor(i).velocity);
                    CollectionAssert.AreEqual(new float[PlayerActionV3.Count], match.ActiveFor(i).ToArray());
                }
                for (int tick = 0; tick < 8; tick++) Assert.IsTrue(match.StepAgents());
                Assert.IsTrue(match.BallHeld, "A queued action from the old rally leaked across reset.");
                Assert.IsFalse(match.TryResetRally());
                Assert.AreEqual(1, match.World.Rules.Score[0]);
            }
            yield return null;
        }

        [UnityTest]
        public IEnumerator CompletedGameCannotBeResetOrAwardAnotherPoint()
        {
            using (var match = new PlayerLearningMatchV3())
            {
                for (int point = 0; point < 11; point++)
                {
                    match.World.Rules.Fail(1, Fault.Out, 0); // Score lifecycle fixture, not physical game acceptance.
                    Assert.AreEqual(point < 10, match.TryResetRally());
                }
                Assert.AreEqual(0, match.World.Rules.GameWinner);
                Assert.AreEqual(11, match.World.Rules.Score[0]);
                Assert.IsFalse(match.TryResetRally());
                Assert.IsFalse(match.World.Rules.ResolveRally());
                Assert.AreEqual(11, match.World.Rules.Score[0]);
            }
            yield return null;
        }
    }
}

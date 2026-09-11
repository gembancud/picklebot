using System.Collections;
using NUnit.Framework;
using Picklebot.PlayerControls;
using UnityEngine;
using UnityEngine.TestTools;

namespace Picklebot.PlayerControlsIntegration.Tests
{
    public sealed class PlayerDrillV3Tests
    {
        private sealed class Still : IPlayerPolicyV3
        {
            public string Name => "stationary physical fixture";
            public void Reset() { }
            public PlayerActionV3 Decide(PlayerObservationV3 observation, System.Random random) => default;
        }

        private static void AttachStill(PlayerContactDrillV3 drill)
        {
            drill.Match.AttachPolicies(new IPlayerPolicyV3[] { new Still(), new Still(), new Still(), new Still() }, drill.Seed);
        }

        [UnityTest]
        public IEnumerator VariedFeedsPreserveEndpointsAndEasyPhysicalTrajectories()
        {
            for(int seat=0;seat<4;seat++)
            {
                int seed=1300800+seat;
                Vector3 position,velocity;string outcome;int ticks;float total=0;
                using(var easy=new PlayerContactDrillV3(seed,seat,"easy-return"))
                {
                    position=easy.Match.World.Ball.position;velocity=easy.Match.World.Ball.linearVelocity;
                    AttachStill(easy);while(!easy.Done){easy.Step();total+=easy.Reward;}
                    outcome=easy.Outcome;ticks=easy.Match.Tick;
                }
                yield return null;
                using(var varied=new PlayerContactDrillV3(seed,seat,"varied-return",0))
                {
                    Assert.AreEqual(0,varied.FeedDifficulty);
                    Assert.AreEqual(position,varied.Match.World.Ball.position);
                    Assert.AreEqual(velocity,varied.Match.World.Ball.linearVelocity);
                    AttachStill(varied);float repeated=0;
                    while(!varied.Done){varied.Step();repeated+=varied.Reward;}
                    Assert.AreEqual(outcome,varied.Outcome);Assert.AreEqual(ticks,varied.Match.Tick);
                    Assert.AreEqual(total,repeated);Assert.IsNull(varied.Match.Failure);
                }
                yield return null;
                using(var near=new PlayerContactDrillV3(seed,seat,"near-return"))
                {position=near.Match.World.Ball.position;velocity=near.Match.World.Ball.linearVelocity;}
                yield return null;
                using(var endpoint=new PlayerLearningMatchV3(false))
                {
                    endpoint.InitializeContactDrill(seat,seed,"varied-return",1);
                    Assert.Less(Vector3.Distance(position,endpoint.World.Ball.position),.000001f);
                    Assert.Less(Vector3.Distance(velocity,endpoint.World.Ball.linearVelocity),.00001f);
                }
                yield return null;
            }
        }

        [UnityTest]
        public IEnumerator VariedFeedsAreRepeatableBoundedAndAllowReaction()
        {
            int anchors=0,intermediate=0;
            for(int index=0;index<32;index++)
            {
                int seed=1300810+index,seat=index%4;float difficulty;Vector3 position,velocity;
                using(var drill=new PlayerContactDrillV3(seed,seat,"varied-return",.5f))
                {
                    difficulty=drill.FeedDifficulty;Assert.That(difficulty,Is.InRange(0,.5f));
                    if(difficulty==0)anchors++;else intermediate++;
                    position=drill.Match.World.Ball.position;velocity=drill.Match.World.Ball.linearVelocity;
                    AttachStill(drill);
                    for(int tick=0;tick<7;tick++){drill.Step();Assert.IsFalse(drill.Done,drill.Outcome);}
                    Assert.IsFalse(drill.FaceContact);Assert.IsNull(drill.Match.Failure);
                }
                yield return null;
                using(var repeat=new PlayerContactDrillV3(seed,seat,"varied-return",.5f))
                {
                    Assert.AreEqual(difficulty,repeat.FeedDifficulty);
                    Assert.AreEqual(position,repeat.Match.World.Ball.position);
                    Assert.AreEqual(velocity,repeat.Match.World.Ball.linearVelocity);
                }
                yield return null;
            }
            Assert.Greater(anchors,0);Assert.Greater(intermediate,0);
            Assert.Throws<System.ArgumentOutOfRangeException>(()=>new PlayerContactDrillV3(1300850,0,"varied-return",float.NaN));
            Assert.Throws<System.ArgumentOutOfRangeException>(()=>new PlayerContactDrillV3(1300850,0,"varied-return",1.01f));
        }

        [UnityTest]
        public IEnumerator ReactionFeedRepeatsAndAllowsTheFirstDecisionToArrive()
        {
            foreach (string task in new[] { "reaction-contact", "reaction-return", "near-return", "easy-return" })
            for (int seat = 0; seat < 4; seat++)
            {
                Vector3 position, velocity;
                using (var drill = new PlayerContactDrillV3(1300100 + seat, seat, task))
                {
                    position = drill.Match.World.Ball.position;
                    velocity = drill.Match.World.Ball.linearVelocity;
                    Assert.Greater(position.y, .1f);
                    Assert.Greater(Vector3.Distance(position, drill.Match.World.Players[seat].Paddle.position), 1.2f);
                    AttachStill(drill);
                    for (int tick = 0; tick < 7; tick++)
                    {
                        drill.Step();
                        Assert.IsFalse(drill.Done, drill.Outcome);
                        Assert.IsNull(drill.Match.Failure);
                    }
                    Assert.IsFalse(drill.FaceContact);
                }
                yield return null;
                using (var repeat = new PlayerContactDrillV3(1300100 + seat, seat, task))
                {
                    Assert.AreEqual(position, repeat.Match.World.Ball.position);
                    Assert.AreEqual(velocity, repeat.Match.World.Ball.linearVelocity);
                }
                yield return null;
            }
        }

        [UnityTest]
        public IEnumerator MissingTheFeedAndWithholdingTheServeRemainTaskFailures()
        {
            using (var drill = new PlayerContactDrillV3(1300310, 0, "near-return"))
            {
                // Reset-only miss fixture, away from every body and paddle.
                var ball = drill.Match.World.Ball;
                ball.position = ball.transform.position = new Vector3(0, .2f, -4);
                ball.linearVelocity = Vector3.down * 2;
                AttachStill(drill);
                float total = 0;
                while (!drill.Done) { drill.Step(); total += drill.Reward; }
                Assert.AreEqual("miss", drill.Outcome);
                Assert.IsFalse(drill.FaceContact);
                Assert.Less(total, -.89f, "A miss must not become a cheap alternative to a failed contact.");
                Assert.Greater(total, -1.11f, "Bounded progress must not create another terminal loss.");
            }
            yield return null;
            using (var drill = new PlayerContactDrillV3(1300311, 1, "drop-serve"))
            {
                AttachStill(drill);
                float total = 0;
                while (!drill.Done) { drill.Step(); total += drill.Reward; }
                Assert.AreEqual("time_limit", drill.Outcome);
                Assert.IsTrue(drill.Match.BallHeld);
                Assert.IsFalse(drill.ServeAccepted);
                Assert.AreEqual(-1, total, .0001f);
                CollectionAssert.AreEqual(new[] { 0, 0 }, drill.Match.World.Rules.Score);
            }
            yield return null;
        }

        [UnityTest]
        public IEnumerator ReturnTaskContinuesAfterRealFaceContactAndRejectsShortLanding()
        {
            using (var drill = new PlayerContactDrillV3(1300110, 0, "reaction-return"))
            {
                // A reset-only physical test feed; no post-contact ball state changes.
                var paddle = drill.Match.World.Players[0].Paddle;
                var normal = paddle.rotation * Vector3.forward;
                var position = paddle.position + paddle.rotation * new Vector3(0, .0635f, 0) + normal * .25f;
                var ball = drill.Match.World.Ball;
                ball.position = ball.transform.position = position;
                ball.linearVelocity = -normal * 4;
                AttachStill(drill);
                while (!drill.FaceContact && !drill.Done) drill.Step();
                Assert.IsTrue(drill.FaceContact, drill.Outcome);
                Assert.IsFalse(drill.Done, "Face callback must not count as a completed return.");
                while (!drill.Done) drill.Step();
                Assert.AreNotEqual("legal_return", drill.Outcome);
                Assert.IsFalse(drill.NetCrossed);
                Assert.IsNull(drill.Match.Failure);
                Assert.Throws<System.InvalidOperationException>(() => drill.Step());
            }
            yield return null;
        }
    }
}

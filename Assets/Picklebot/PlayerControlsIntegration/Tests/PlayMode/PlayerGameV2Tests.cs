using System;
using System.Collections;
using System.Linq;
using NUnit.Framework;
using Picklebot.Doubles;
using UnityEngine;
using UnityEngine.TestTools;

namespace Picklebot.PlayerControlsIntegration.Tests
{
    public sealed class PlayerGameV2Tests
    {
        private sealed class Ready:IPlayerPolicyV2
        {public string Name=>"test ready hold";public int calls;public bool fail;public void Reset(){}public PlayerActionV2 Decide(PlayerObservationV2 o,System.Random r){calls++;if(fail)throw new InvalidOperationException("test inference failure");return default;}}
        private static Ready[] Policies()=>Enumerable.Range(0,4).Select(i=>new Ready()).ToArray();
        [UnityTest] public IEnumerator PhysicalDropServeScoresAndResetsWithoutRelaxingPaddleBounds()
        {
            using(var game=new PlayerGameV2(false,Policies(),1300000))
            {
                Assert.AreEqual(Vector3.zero,game.Match.World.Ball.linearVelocity);
                for(int tick=0;tick<1800&&game.Rallies.Count==0;tick++)
                {
                    var previous=Enumerable.Range(0,4).Select(i=>game.Match.Controls.PaddleFor(i)).ToArray();
                    game.Step();
                    if(game.Match.Tick!=0)
                        for(int i=0;i<4;i++)
                        {
                            var paddle=game.Match.Controls.PaddleFor(i);
                            Assert.LessOrEqual(paddle.velocity.magnitude,12.0002f);
                            Assert.LessOrEqual((paddle.velocity-previous[i].velocity).magnitude/DoublesWorld.Dt,100.03f);
                            Assert.LessOrEqual(Vector3.Distance(paddle.Hand,game.Match.Controls.PoseFor(i).Shoulder),.62001f);
                        }
                    if(tick%240==0)yield return null;
                }
                Assert.AreEqual(1,game.Rallies.Count);var rally=game.Rallies[0];
                Assert.AreEqual(0,rally.server);Assert.AreEqual(1,rally.score0);Assert.AreEqual(0,rally.score1);
                Assert.IsTrue(rally.contacts.Any(c=>c.surface=="OutCatchFloor"&&c.player<0));
                Assert.IsTrue(rally.contacts.Any(c=>c.surface=="RoundedHittingFace"&&c.player==0));
                Assert.AreNotEqual(Fault.ServeFoot,rally.fault);Assert.AreNotEqual(Fault.BodyContact,rally.fault);
                Assert.AreEqual(RallyPhase.AwaitServe,game.Match.World.Rules.Phase);Assert.AreEqual(0,game.Match.Tick);
                Assert.Greater(game.AssistedServeSteps,0);Assert.Greater(game.AssistedResetSteps,0);Assert.IsNull(game.Failure);
            }
            yield return null;
        }
        [UnityTest] public IEnumerator FullMechanicsGameCompletesAndCannotAwardAnotherPoint()
        {
            using(var game=new PlayerGameV2(false,Policies(),1300000))
            {
                for(int tick=0;tick<24000&&!game.Complete;tick++)
                {game.Step();if(tick%240==0)yield return null;}
                Assert.IsTrue(game.Complete,"Untrained hold opponents should permit a completed mechanics fixture, not an accepted agent evaluation.");
                int winner=game.Match.World.Rules.GameWinner;
                Assert.GreaterOrEqual(game.Match.World.Rules.Score[winner],11);
                Assert.GreaterOrEqual(game.Match.World.Rules.Score[winner]-game.Match.World.Rules.Score[1-winner],2);
                int steps=game.PhysicsSteps,rallies=game.Rallies.Count,score=game.Match.World.Rules.Score[winner];
                game.Step();Assert.AreEqual(steps,game.PhysicsSteps);Assert.AreEqual(rallies,game.Rallies.Count);Assert.AreEqual(score,game.Match.World.Rules.Score[winner]);
            }
            yield return null;
        }
        [UnityTest] public IEnumerator UnresolvedVolleyMomentumCannotBeResetAway()
        {
            using(var match=new PlayerControlMatch(false))
            {
                var r=match.World.Rules;r.Serve(r.Server,true,true,true,true,false,false,false,0);
                r.Bounce(new Vector3(r.ServiceX(r.DesignatedReceiver),0,4),1);r.Hit(r.DesignatedReceiver,2);
                r.Bounce(new Vector3(0,0,-4),3);r.Hit(r.Server,4);r.Hit(3,5);r.Fail(0,Fault.Out,6);
                Assert.IsTrue(r.VolleyMomentumPending(3));var ball=match.World.Ball.position;
                Assert.Throws<InvalidOperationException>(()=>match.ResetRally());
                Assert.AreEqual(ball,match.World.Ball.position);Assert.IsTrue(r.VolleyMomentumPending(3));
                r.Feet(3,true,false,false,7);Assert.AreEqual(Fault.KitchenMomentum,r.LastFault);
                r.Feet(3,false,true,true,8);Assert.IsTrue(r.ResolveRally());match.ResetRally();
                Assert.AreEqual(RallyPhase.AwaitServe,r.Phase);
            }
            yield return null;
        }
        [UnityTest] public IEnumerator PolicyFailureIsTerminalAndCannotConsumeMoreSimulationTime()
        {
            var policies=Policies();policies[3].fail=true;
            using(var game=new PlayerGameV2(false,policies,1300000))
            {
                Assert.Throws<InvalidOperationException>(()=>game.Step());Assert.IsNotNull(game.Failure);Assert.AreEqual(0,game.PhysicsSteps);
                int calls=policies[3].calls;Assert.Throws<InvalidOperationException>(()=>game.Step());
                Assert.AreEqual(calls,policies[3].calls);Assert.AreEqual(0,game.PhysicsSteps);
            }
            yield return null;
        }
    }
}

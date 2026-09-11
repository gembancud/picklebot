using System.Collections;
using System.Linq;
using NUnit.Framework;
using Picklebot.Doubles;
using Picklebot.PlayerControls;
using UnityEngine;
using UnityEngine.TestTools;
namespace Picklebot.PlayerControlsIntegration.Tests
{
    public sealed class PlayerFixedServeV3Tests
    {
        [UnityTest]
        public IEnumerator FixedServeWaitsForContactAcrossFourSeats()
        {
            for(int seat=0;seat<4;seat++)
            {
                using(var drill=new PlayerContactDrillV3(1302118+seat,seat,"stationary-serve"))
                {
                    var match=drill.Match;var ball=match.World.Ball;var start=ball.position;
                    Assert.AreEqual(seat,match.World.Rules.Server);
                    Assert.IsFalse(match.BallHeld);Assert.IsTrue(match.StationarySupportActive);
                    Assert.IsFalse(ball.isKinematic);Assert.IsTrue(ball.detectCollisions);
                    Assert.IsFalse(PlayerContactDrillV3.ActionMask(seat,seat,"stationary-serve")[16]);
                    for(int tick=0;tick<120;tick++)Assert.IsTrue(match.Step(new PlayerActionV3[4]));
                    Assert.Less(Vector3.Distance(start,ball.position),1e-6);
                    Assert.AreEqual(Vector3.zero,ball.linearVelocity);
                    Assert.AreEqual(RallyPhase.AwaitServe,match.World.Rules.Phase);
                    Assert.IsFalse(match.World.Rules.Events.Any(e=>e.kind=="serve"));
                    Assert.IsFalse(match.World.ServeBounced);
                }
                yield return null;
            }
        }
        [UnityTest]
        public IEnumerator RealCollisionStartsServeAndReleasesSupport()
        {
            for(int seat=0;seat<4;seat++)
            {
                using(var drill=new PlayerContactDrillV3(1302122+seat,seat,"stationary-serve"))
                {
                    var match=drill.Match;var ball=match.World.Ball;var paddle=match.World.Players[seat].Paddle;
                    var normal=paddle.rotation*Vector3.forward;
                    // Contact fixture only, never training input or runtime launch logic.
                    ball.position=paddle.position+paddle.rotation*PlayerStrokeAimV3.FacePoint+normal*.06f;
                    ball.transform.position=ball.position;ball.linearVelocity=-normal*3;
                    for(int tick=0;tick<30&&match.World.Contacts.Count==0;tick++)Assert.IsTrue(match.Step(new PlayerActionV3[4]));
                    Assert.IsTrue(match.World.Contacts.Any(c=>c.player==seat&&c.surface=="RoundedHittingFace"));
                    Assert.IsFalse(match.StationarySupportActive);Assert.IsFalse(match.World.ServeBounced);
                    Assert.AreEqual(RallyPhase.ServeFlight,match.World.Rules.Phase);
                    Assert.AreEqual(1,match.World.Rules.Events.Count(e=>e.kind=="serve"));
                    Assert.Less(Vector3.Distance(match.World.Contacts.Last().velocity,ball.linearVelocity),1e-6);
                    Assert.Greater(ball.linearVelocity.magnitude,.01f);
                }
                yield return null;
            }
        }
        [Test]
        public void FixedServePreservesFeetDiagonalAndDoubleBounceRules()
        {
            var feet=new DoublesRules();feet.FixedBallServe(0,false,1);Assert.AreEqual(Fault.ServeFoot,feet.LastFault);
            var wrong=new DoublesRules();wrong.FixedBallServe(1,true,1);Assert.IsTrue(wrong.Dead);
            var diagonal=new DoublesRules();diagonal.FixedBallServe(0,true,1);diagonal.Bounce(new Vector3(1,0,4),2);Assert.AreEqual(Fault.ServeLanding,diagonal.LastFault);
            var kitchen=new DoublesRules();kitchen.FixedBallServe(0,true,1);kitchen.Bounce(new Vector3(-1,0,DoublesRules.Kitchen),2);Assert.AreEqual(Fault.ServeLanding,kitchen.LastFault);
            var early=new DoublesRules();early.FixedBallServe(0,true,1);early.Hit(2,2);Assert.AreEqual(Fault.EarlyVolley,early.LastFault);
            var rally=new DoublesRules();rally.FixedBallServe(0,true,1);rally.Bounce(new Vector3(-1,0,4),2);rally.Hit(2,3);rally.Hit(0,4);Assert.AreEqual(Fault.EarlyVolley,rally.LastFault);
        }
    }
}

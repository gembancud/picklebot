using System.Collections;
using NUnit.Framework;
using Picklebot.PlayerControls;
using Picklebot.Doubles;
using UnityEngine;
using UnityEngine.TestTools;
namespace Picklebot.PlayerControlsIntegration.Tests
{
    public sealed class PlayerStationaryFlightV3Tests
    {
        private sealed class Idle:IPlayerPolicyV3
        {
            public string Name=>"Physics fixture only";public void Reset(){}
            public PlayerActionV3 Decide(PlayerObservationV3 o,System.Random r)=>default;
        }
        private static void Attach(PlayerContactDrillV3 d)=>d.Match.AttachPolicies(new IPlayerPolicyV3[]{new Idle(),new Idle(),new Idle(),new Idle()},d.Seed);
        [UnityTest] public IEnumerator DistanceCurriculumPreservesFixedBallAndBodyGeometryAcrossSeats()
        {
            for(int seat=0;seat<4;seat++)for(int level=0;level<3;level++)
            {
                float difficulty=level*.5f;
                using(var d=new PlayerContactDrillV3(1306486+seat*3+level,seat,"stationary-flight",difficulty))
                {
                    Attach(d);var m=d.Match;var body=m.World.Players[seat];float sign=seat<2?1:-1;
                    Assert.AreEqual(-Mathf.Lerp(3.2f,7.65f,difficulty),body.Position.z*sign,1e-5);
                    var expected=body.Paddle.position+body.Paddle.rotation*(PlayerStrokeAimV3.FacePoint+Vector3.forward*.25f);
                    Assert.Less(Vector3.Distance(expected,m.World.Ball.position),1e-6);
                    Assert.IsFalse(m.World.FixedBallServe);Assert.AreEqual(RallyPhase.Rally,m.World.Rules.Phase);
                    Assert.IsFalse(m.BallHeld);Assert.IsFalse(m.World.Ball.isKinematic);Assert.IsTrue(m.StationarySupportActive);
                    Assert.IsFalse(PlayerContactDrillV3.ActionMask(seat,seat,d.Task)[16]);
                    var start=m.World.Ball.position;for(int i=0;i<120;i++)d.Step();
                    Assert.IsFalse(d.Done);Assert.Less(Vector3.Distance(start,m.World.Ball.position),1e-6);
                    Assert.IsFalse(d.FaceContact);Assert.AreEqual(difficulty,d.FeedDifficulty);
                }
                yield return null;
            }
        }
        [UnityTest] public IEnumerator ContactContinuesUntilRealBounceAndCountsOnlyAsReturn()
        {
            for(int seat=0;seat<4;seat++)
            {
                using(var d=new PlayerContactDrillV3(1306498+seat,seat,"stationary-flight",0))
                {
                    Attach(d);var m=d.Match;var paddle=m.World.Players[seat].Paddle;var ball=m.World.Ball;var normal=paddle.rotation*Vector3.forward;
                    // Inject only in this isolated transition fixture, never in training.
                    ball.position=paddle.position+paddle.rotation*PlayerStrokeAimV3.FacePoint+normal*.06f;ball.transform.position=ball.position;ball.linearVelocity=-normal*3;
                    for(int i=0;i<30&&!d.FaceContact;i++)d.Step();
                    Assert.IsTrue(d.FaceContact);Assert.IsFalse(d.Done);Assert.IsFalse(m.StationarySupportActive);
                    Assert.IsFalse(d.ServeAccepted);Assert.AreEqual(-1,d.ServeLandingRewardTick);
                    // Isolate actual floor-contact/rule accounting after the physical hit.
                    ball.position=new Vector3(0,1,(seat<2?1:-1)*3);ball.transform.position=ball.position;ball.linearVelocity=Vector3.down;
                    for(int i=0;i<240&&!d.Done;i++)d.Step();
                    Assert.AreEqual("legal_return",d.Outcome);Assert.AreEqual(-1,d.ServeLandingRewardTick);
                }
                yield return null;
            }
        }
    }
}

using System.Collections;
using System.Linq;
using NUnit.Framework;
using Picklebot.PlayerControls;
using UnityEngine;
using UnityEngine.TestTools;
namespace Picklebot.PlayerControlsIntegration.Tests
{
    public sealed class PlayerStationaryContactV3Tests
    {
        [UnityTest]
        public IEnumerator SupportedBallIsDynamicAndStationaryAcrossAllSeats()
        {
            for(int seat=0;seat<4;seat++)
            {
                using(var match=new PlayerLearningMatchV3(false))
                {
                    match.InitializeContactDrill(seat,1301976+seat,"stationary-contact");
                    var ball=match.World.Ball;var start=ball.position;
                    Assert.IsFalse(ball.isKinematic);Assert.IsTrue(ball.detectCollisions);
                    Assert.IsTrue(match.StationarySupportActive);Assert.IsFalse(match.BallHeld);
                    for(int i=0;i<240;i++)match.World.Simulate(true);
                    Assert.Less(Vector3.Distance(start,ball.position),1e-6);
                    Assert.AreEqual(Vector3.zero,ball.linearVelocity);
                    Assert.AreEqual(0,match.World.Contacts.Count);
                    match.World.Simulate(false);
                    Assert.Less(ball.linearVelocity.y,-.01f,"Ordinary gravity must remain active without drill support");
                }
                yield return null;
            }
        }
        [UnityTest]
        public IEnumerator ActualFaceCollisionReleasesSupportWithoutErasingImpact()
        {
            for(int seat=0;seat<4;seat++)
            {
                using(var match=new PlayerLearningMatchV3(false))
                {
                    match.InitializeContactDrill(seat,1301980+seat,"stationary-contact");
                    var paddle=match.World.Players[seat].Paddle;var ball=match.World.Ball;
                    var normal=paddle.rotation*Vector3.forward;
                    // Physics fixture only: drive a dynamic ball into the face to
                    // test the release branch, never used as policy training data.
                    ball.position=paddle.position+paddle.rotation*PlayerStrokeAimV3.FacePoint+normal*.06f;
                    ball.transform.position=ball.position;ball.linearVelocity=-normal*3;
                    for(int i=0;i<30&&match.World.Contacts.Count==0;i++)Assert.IsTrue(match.Step(new PlayerActionV3[4]));
                    Assert.IsTrue(match.World.Contacts.Any(c=>c.player==seat&&c.surface=="RoundedHittingFace"));
                    Assert.IsFalse(match.StationarySupportActive);
                    var hit=match.World.Contacts.Last();
                    Assert.Less(Vector3.Distance(hit.velocity,ball.linearVelocity),1e-6,"Support must not overwrite impact velocity");
                    Assert.Greater(ball.linearVelocity.magnitude,.01f);
                    for(int i=0;i<5;i++){Assert.IsTrue(match.Step(new PlayerActionV3[4]));Assert.IsFalse(match.StationarySupportActive);}
                }
                yield return null;
            }
        }
        [UnityTest]
        public IEnumerator FloorCollisionAlsoReleasesSupport()
        {
            using(var match=new PlayerLearningMatchV3(false))
            {
                match.InitializeContactDrill(0,1301984,"stationary-contact");
                var ball=match.World.Ball;ball.position=new Vector3(0,.06f,-4);ball.transform.position=ball.position;ball.linearVelocity=Vector3.down*2;
                for(int i=0;i<30&&match.World.Contacts.Count==0;i++)Assert.IsTrue(match.Step(new PlayerActionV3[4]));
                Assert.IsTrue(match.World.Contacts.Any(c=>c.surface=="CourtSurface"));
                Assert.IsFalse(match.StationarySupportActive);
            }
            yield return null;
        }
    }
}

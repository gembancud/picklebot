using System.Collections;
using NUnit.Framework;
using Picklebot.Doubles;
using Picklebot.PlayerControls;
using UnityEngine;
using UnityEngine.TestTools;
namespace Picklebot.PlayerControlsIntegration.Tests
{
    public sealed class PlayerRallyContextV3Tests
    {
        [UnityTest]
        public IEnumerator GeneralizedContextsKeepPhysicalBallAndEligibleLearner()
        {
            int index=0;
            for(int server=0;server<4;server++)for(int side=0;side<2;side++)for(int learner=0;learner<4;learner++)
            {
                using(var m=new PlayerLearningMatchV3(false,server,0,side==0))
                {
                    m.InitializeContactDrill(learner,1306534+index++,"stationary-flight",0,generalizedRallyContext:true);
                    var rules=m.World.Rules;Assert.IsFalse(rules.Dead);Assert.AreEqual(RallyPhase.Rally,rules.Phase);
                    Assert.AreEqual(learner/2,rules.ExpectedTeam);Assert.AreEqual(server,rules.Server);
                    Assert.AreEqual(side==0,rules.IsRight(server));Assert.IsTrue(rules.CanVolley);Assert.IsFalse(rules.Bounced);
                    var observation=PlayerObservationV3.Capture(m,learner,0).ToArray();Assert.AreEqual(124,observation.Length);
                    Assert.AreEqual(server==learner?1:0,observation[44]);Assert.AreEqual(rules.DesignatedReceiver==learner?1:0,observation[45]);Assert.AreEqual(server/2==learner/2?1:0,observation[47]);
                    Assert.IsTrue(m.StationarySupportActive);Assert.IsFalse(m.World.Ball.isKinematic);
                    var ball=m.World.Ball.position;
                    for(int tick=0;tick<120;tick++)Assert.IsTrue(m.Step(new PlayerActionV3[4]));
                    Assert.AreEqual(ball,m.World.Ball.position);Assert.AreEqual(Vector3.zero,m.World.Ball.linearVelocity);Assert.IsFalse(rules.Dead);
                    Assert.AreEqual(0,m.World.Contacts.Count);
                }
            }
            Assert.AreEqual(32,index);yield return null;
        }
    }
}

using System.Collections;
using System.IO;
using NUnit.Framework;
using Picklebot.PlayerControls;
using Picklebot.PlayerControlsIntegration;
using UnityEngine;
using UnityEngine.TestTools;
namespace Picklebot.PlayerLearning.Tests
{
    public sealed class PlayerRootCouplingV3Tests
    {
        [UnityTest]
        public IEnumerator CapturedReturnStepRetriesMovementWithinUnchangedBounds()
        {
            var path=Path.Combine(Application.dataPath,"Picklebot/PlayerLearning/Tests/Fixtures/root-coupling-1001687.json");
            var f=JsonUtility.FromJson<MlSimulationFailureV3>(File.ReadAllText(path));
            Assert.AreEqual(282,f.physicsTick);Assert.AreEqual(1001687,f.seed);
            using(var drill=new PlayerContactDrillV3(f.seed,f.player,f.task,f.maximumReturnDifficulty,f.feedLowering,f.feedLateralOffset,f.initialHoldLift,f.serveFromLeft))
            {
                var match=drill.Match;
                for(int tick=0;tick<=f.physicsTick;tick++)
                {
                    if(tick%12==0)
                    {
                        var obs=PlayerObservationV3.Capture(match,f.player,tick).ToArray();
                        for(int j=0;j<obs.Length;j++)Assert.AreEqual(f.decisions[tick/12].observation[j],obs[j],1e-6,"Observation before failure changed");
                    }
                    var actions=new PlayerActionV3[4];
                    if(tick>=6)actions[f.player]=new PlayerActionV3(f.decisions[(tick-6)/12].physical);
                    var previous=match.Controls.UpperFor(f.player).ActualVelocity;
                    var previousRoot=match.Controls.StateFor(f.player);
                    Assert.IsTrue(match.Step(actions),"Rejected captured tick "+tick);
                    var upper=match.Controls.UpperFor(f.player);
                    var root=match.Controls.StateFor(f.player);
                    Assert.LessOrEqual((root.velocity-previousRoot.velocity).magnitude,14*PlayerJointMotorV3.Dt+1e-5f);
                    Assert.LessOrEqual(Mathf.Abs(root.crouchVelocity-previousRoot.crouchVelocity),10*PlayerJointMotorV3.Dt+1e-6f);
                    Assert.LessOrEqual(upper.ActualVelocity.magnitude,12);
                    Assert.LessOrEqual((upper.ActualVelocity-previous).magnitude,100*PlayerJointMotorV3.Dt);
                    Assert.LessOrEqual(upper.ActualAngularVelocity.magnitude,11.991f);
                }
                Assert.AreEqual(283,match.Tick);Assert.IsNull(match.Failure);
            }
            yield return null;
        }
    }
}

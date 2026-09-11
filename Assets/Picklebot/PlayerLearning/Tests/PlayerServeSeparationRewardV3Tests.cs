using System.Collections;
using System.IO;
using NUnit.Framework;
using Picklebot.PlayerControls;
using Picklebot.PlayerControlsIntegration;
using UnityEngine;
using UnityEngine.TestTools;
namespace Picklebot.PlayerLearning.Tests
{
    public sealed class PlayerServeSeparationRewardV3Tests
    {
        [System.Serializable] private sealed class Trace {public MlDecisionV3[] rows;}
        private sealed class Replay:IPlayerPolicyV3
        {
            private readonly MlDecisionV3[] rows;private readonly bool active;
            public Replay(MlDecisionV3[] rows,bool active){this.rows=rows;this.active=active;}
            public string Name=>"Detached recorded action regression";
            public void Reset(){}
            public PlayerActionV3 Decide(PlayerObservationV3 observation,System.Random random)=>active?new PlayerActionV3(rows[Mathf.Min(observation.tick/12,rows.Length-1)].physical):default;
        }
        [UnityTest] public IEnumerator DirectionRewardUsesSeparationAndPaysOnlyOnce()
        {
            var path=Path.Combine(Application.dataPath,"Picklebot/PlayerLearning/Tests/Fixtures/serve-separation-parent-left.json");
            var rows=JsonUtility.FromJson<Trace>(File.ReadAllText(path)).rows;
            using(var drill=new PlayerContactDrillV3(1101745,0,"stationary-serve",.5f,0,0,0,true))
            {
                var m=drill.Match;m.AttachPolicies(new IPlayerPolicyV3[]{new Replay(rows,true),new Replay(rows,false),new Replay(rows,false),new Replay(rows,false)},1101745);
                int awarded=0;float amount=0;bool observedTransient=false;
                while(!drill.Done)
                {
                    int tick=m.Tick;
                    if(tick%12==0&&tick/12<rows.Length){var obs=PlayerObservationV3.Capture(m,0,tick).ToArray();for(int j=0;j<124;j++)Assert.AreEqual(rows[tick/12].observation[j],obs[j],1e-6);}
                    Assert.AreEqual(-1,drill.ServeLandingRewardTick);Assert.AreEqual(0,drill.ServeLandingReward);
                    int previous=drill.ServeDirectionRewardTick;drill.Step();
                    Assert.That(drill.Outcome,Is.Not.EqualTo("infeasible").And.Not.EqualTo("exception"));
                    if(m.Tick==186){Assert.IsTrue(drill.FaceContact);Assert.IsTrue(m.World.IsPaddleContactActive(0));Assert.Less(m.World.Ball.linearVelocity.z,0);Assert.AreEqual(-1,drill.ServeDirectionRewardTick);Assert.AreEqual(0,drill.ServeDirectionReward);observedTransient=true;}
                    if(previous<0&&drill.ServeDirectionRewardTick>=0){awarded++;Assert.IsFalse(m.World.IsPaddleContactActive(0));Assert.AreEqual(191,m.Tick);Assert.Greater(m.World.Ball.linearVelocity.z,2);amount=PlayerServeDirectionV3.ContactReward(m.World.Ball.linearVelocity.z);Assert.AreEqual(amount,drill.ServeDirectionReward);Assert.Greater(amount,0);}
                    if(awarded>0){Assert.AreEqual(191,drill.ServeDirectionRewardTick);Assert.AreEqual(amount,drill.ServeDirectionReward);}
                }
                Assert.IsTrue(observedTransient);Assert.AreEqual(1,awarded);Assert.AreEqual("bad_return",drill.Outcome);
                var landing=m.World.Contacts.FindLast(c=>c.surface=="CourtSurface"||c.surface=="OutCatchFloor");
                Assert.AreEqual(m.Tick,drill.ServeLandingRewardTick);
                Assert.AreEqual(PlayerServeLandingV3.ContactReward(landing.point,0,m.World.Rules.ServiceX(m.World.Rules.DesignatedReceiver)),drill.ServeLandingReward);
                Assert.Greater(drill.ServeLandingReward,0);
                float finalReward=drill.Reward;Assert.Throws<System.InvalidOperationException>(()=>drill.Step());Assert.AreEqual(finalReward,drill.Reward,"Completed drill cannot pay landing reward twice.");
            }
            yield return null;
        }
    }
}

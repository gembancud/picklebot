using System.Collections;
using NUnit.Framework;
using Picklebot.PlayerControls;
using Picklebot.PlayerControlsIntegration;
using UnityEngine;
using UnityEngine.TestTools;
namespace Picklebot.PlayerLearning.Tests
{
    public sealed class PlayerPreparationTimingV3Tests
    {
        private sealed class Command : IPlayerPolicyV3
        {
            public PlayerActionV3 value;
            public string Name=>"Preparation timing test fixture";
            public void Reset(){}
            public PlayerActionV3 Decide(PlayerObservationV3 observation,System.Random random)=>value;
        }
        [UnityTest]
        public IEnumerator BodyCanPrepareWhileHeldThenReleaseOnChosenDecision()
        {
            for(int seat=0;seat<4;seat++)
            {
                using(var drill=new PlayerContactDrillV3(1302049+seat,seat,"drop-contact"))
                {
                    var values=new float[18];values[6]=.2f;values[10]=.2f;values[17]=.15f;
                    var learner=new Command{value=new PlayerActionV3(values)};var policies=new IPlayerPolicyV3[4];
                    for(int i=0;i<4;i++)policies[i]=i==seat?learner:new Command();
                    drill.Match.AttachPolicies(policies,drill.Seed);
                    var start=drill.Match.World.Players[seat].Paddle.position;
                    for(int tick=0;tick<120;tick++)
                    {
                        drill.Step();Assert.IsFalse(drill.Done);Assert.IsTrue(drill.Match.BallHeld);
                        Assert.IsFalse(drill.DropBounced||drill.FaceContact);Assert.AreEqual(0,drill.Reward);
                    }
                    Assert.Greater(Vector3.Distance(start,drill.Match.World.Players[seat].Paddle.position),.02f,"Arm/body must move during holding");
                    values[16]=1;learner.value=new PlayerActionV3(values);
                    for(int tick=120;tick<126;tick++){drill.Step();Assert.IsTrue(drill.Match.BallHeld);}
                    drill.Step();Assert.IsFalse(drill.Match.BallHeld);Assert.AreEqual(127,drill.ReleaseTick);
                    Assert.IsNull(drill.Match.Failure);Assert.IsFalse(drill.Match.World.Ball.isKinematic);
                }
                yield return null;
            }
        }
        [Test]
        public void RetiredFallingTasksCannotStartAnEditorTrainer()
        {
            foreach(string task in new[]{"falling-contact","falling-return"})
            {
                var root=new GameObject("Retirement guard fixture");root.SetActive(false);
                try{var run=root.AddComponent<PlayerMlDrillsV3>();run.Task=task;run.RequireTrainer=true;Assert.Throws<System.InvalidOperationException>(()=>run.InitializeRun());}
                finally{Object.DestroyImmediate(root);}
            }
        }
    }
}

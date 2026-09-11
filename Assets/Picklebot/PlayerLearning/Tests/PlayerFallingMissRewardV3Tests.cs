using System.Collections;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
using Unity.MLAgents;
namespace Picklebot.PlayerLearning.Tests
{
    public sealed class PlayerFallingMissRewardV3Tests
    {
        [UnityTest]
        public IEnumerator MissingAFallingBallIsANegativeEpisodeForEverySeat()
        {
            var root=new GameObject("Falling miss reward fixture");root.SetActive(false);
            var run=root.AddComponent<PlayerMlDrillsV3>();run.AutoRun=false;run.RequireTrainer=false;
            run.FirstSeed=1302049;run.SeedCount=4;run.ArenaCount=4;run.Task="falling-contact";run.FeedLateralOffset=.8f;
            try
            {
                root.SetActive(true);run.InitializeRun();
                for(int tick=0;tick<1500&&run.Report.status!="seed_budget_complete";tick++)run.StepOneTick();
                Assert.AreEqual("seed_budget_complete",run.Report.status);Assert.AreEqual(4,run.Episodes.Count);
                foreach(var e in run.Episodes)
                {
                    Assert.AreEqual("miss",e.outcome);Assert.IsFalse(e.faceContact);
                    Assert.That(e.reward,Is.InRange(-1f,-.5f));
                }
            }
            finally{Object.DestroyImmediate(root);if(Academy.IsInitialized)Academy.Instance.Dispose();}
            yield return null;
        }
    }
}

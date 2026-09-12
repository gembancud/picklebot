// DRAFT: copy into the existing PlayerLearning test assembly only after applying
// axes-recovery-opt-in.patch. No policies, simulation ticks, or outcomes tested.
// Eight bounded cases allow local PhysicsScene cleanup between reset batches.
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using Newtonsoft.Json.Linq;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
using UnityEngine.SceneManagement;
using Picklebot.PlayerControls;
using Picklebot.PlayerControlsIntegration;

namespace Picklebot.PlayerLearning.Tests
{
    public sealed class PlayerAxesRecoveryIntegrationV3Tests
    {
        private static string GoldenPath=>Path.Combine(Application.dataPath,"Picklebot/PlayerLearning/Tests/Fixtures/axes-recovery-golden.json");
        private const string GoldenHash="6d12adc490ad432122945f4d25dcf16a894b74be1cbcb779a0e6cc30a7225e1d";
        private HashSet<int> priorSceneHandles;
        [SetUp] public void RememberExistingScenes()
        {priorSceneHandles=new HashSet<int>(Enumerable.Range(0,SceneManager.sceneCount).Select(i=>SceneManager.GetSceneAt(i).handle));}
        [UnityTearDown] public IEnumerator AllowOwnedSceneUnloads()
        {
            // Dispose already requested unloading. Yield for only new test worlds;
            // do not close unrelated scenes or simulate their local physics.
            for(int frame=0;frame<120;frame++) {
                bool pending=Enumerable.Range(0,SceneManager.sceneCount).Select(i=>SceneManager.GetSceneAt(i))
                    .Any(scene=>!priorSceneHandles.Contains(scene.handle)&&scene.isLoaded&&scene.name.StartsWith("Doubles-",StringComparison.Ordinal));
                if(!pending)yield break;
                yield return null;
            }
            Assert.Fail("Temporary reset scenes did not finish unloading within120 Editor frames.");
        }
        private static JObject Golden()
        {
            string path=GoldenPath;
            using(var hash=SHA256.Create())Assert.AreEqual(GoldenHash,BitConverter.ToString(hash.ComputeHash(File.ReadAllBytes(path))).Replace("-","").ToLowerInvariant());
            return JObject.Parse(File.ReadAllText(path));
        }
        private static PlayerWorkerManifestV3 Manifest(string pattern)=>new PlayerWorkerManifestV3 {
            version=PlayerWorkerPlanV3.Version,mode="training",task="movement-maintenance",
            sourceIdentity=new string('a',64),buildIdentity=new string('b',64),modelHash=new string('c',64),
            evidenceRoot=Path.Combine(Path.GetFullPath(Path.Combine(Application.dataPath,"..")),"artifacts/hierarchy-v1/axes-test-unused-evidence"),basePort=5705,workerCount=8,
            firstSeed=1000000,seedsPerWorker=256,arenasPerWorker=16,ticksPerFrame=48,
            maximumReturnDifficulty=.25f,fixedServeSides="both",movementRecoveryMix=true,interleavedRecovery=true,
            movementPattern=pattern,movementRange=pattern=="axes"?.0625f:.025f,movementRehearsalRange=.1f
        };
        private static PlayerMlDrillsV3 Make(GameObject holder,string pattern,int firstSeed)
        {
            holder.SetActive(false);
            var run=holder.AddComponent<PlayerMlDrillsV3>();
            PlayerWorkerPlanV3.Create(Manifest(pattern),0).Configure(run,null);
            // Reuse recorded development resets directly. Never InitializeRun:
            // this descriptor owner is inactive and has no Academy/policy.
            run.enabled=false;run.AutoRun=false;run.RequireTrainer=false;
            run.FirstSeed=firstSeed;run.EvidenceDirectory=null;
            return run;
        }
        private static void Descriptor(PlayerMlDrillsV3 run,int index,JToken old,bool axes)
        {
            bool changed=axes&&(string)old["group"]=="focus";
            Assert.AreEqual((string)old["task"],run.TaskForEpisode(index));
            Assert.AreEqual(changed?"axes":(string)old["pattern"],run.MovementPatternForEpisode(index));
            Assert.AreEqual((float)old["range"]*(changed?2.5f:1f),run.MovementRangeForEpisode(index),1e-7);
            Assert.AreEqual((float)old["difficulty"],run.DifficultyForEpisode(index));
            Assert.AreEqual((bool)old["serveFromLeft"],run.ServeFromLeftForEpisode(index));
        }
        private static void Actual(PlayerContactDrillV3 drill,int index,JToken old,bool axes)
        {
            bool changed=axes&&(string)old["group"]=="focus";
            Assert.AreEqual((int)old["seed"],drill.Seed);Assert.AreEqual((int)old["player"],drill.Player);
            Assert.AreEqual((string)old["task"],drill.Task);
            Assert.AreEqual(changed?"axes":(string)old["pattern"],drill.MovementPattern);
            Assert.AreEqual((float)old["range"]*(changed?2.5f:1f),drill.MovementRange,1e-7);
            Assert.AreEqual((float)old["difficulty"],drill.FeedDifficulty);
            Assert.AreEqual((bool)old["serveFromLeft"],drill.ServeFromLeft);
            Assert.AreEqual(0,drill.Match.Tick);Assert.AreEqual(0,drill.Match.TotalTicks);
            Assert.AreEqual(0,drill.Match.World.Time);Assert.IsNull(drill.Match.Decisions);
            Assert.AreEqual(0,drill.Reward);Assert.IsFalse(drill.Done||drill.FaceContact||drill.Cooperative);
            Assert.AreEqual(0,drill.Match.World.Contacts.Count);
            Assert.AreEqual(0,drill.MovementTiming);Assert.AreEqual(0,drill.MovementStartVariation);
            Assert.AreEqual(0,drill.MovementPositionRewardScale);
        }

        [Test] public void OldRecordedCycleAndValidationRemainCompatible()
        {
            var golden=Golden();var rows=(JArray)golden["rows"];
            Assert.AreEqual(256,rows.Count);Assert.IsFalse(Unity.MLAgents.Academy.IsInitialized);
            var oldHolder=new GameObject("Inactive old recovery");var newHolder=new GameObject("Inactive axes recovery");
            try {
                var old=Make(oldHolder,"lateral",(int)golden["firstSeed"]);
                var axes=Make(newHolder,"axes",(int)golden["firstSeed"]);
                for(int i=0;i<256;i++) {
                    Assert.AreEqual(i,(int)rows[i]["index"]);
                    Descriptor(old,i,rows[i],false);Descriptor(axes,i,rows[i],true);
                    // Also exercise the original four-argument API/default.
                    var spec=PlayerRecoveryScheduleV3.For(i,.025f,.1f,.25f);
                    Assert.AreEqual((string)rows[i]["task"],spec.Task);Assert.AreEqual((string)rows[i]["pattern"],spec.Pattern);
                    Assert.AreEqual((float)rows[i]["range"],spec.Range);Assert.AreEqual((string)rows[i]["group"],spec.Group);
                    Assert.AreEqual(old.AllocationIndexForOrdinal(i),axes.AllocationIndexForOrdinal(i));
                }
                Assert.AreEqual(64,rows.Count(row=>(string)row["group"]=="familiar"));
                Assert.AreEqual(64,rows.Count(row=>(string)row["group"]=="prior"));
                Assert.AreEqual(128,rows.Count(row=>(string)row["group"]=="focus"));
                foreach(string bad in new[]{null,"","court","depth","lateral-left","unknown","AXES"}) {
                    Assert.Throws<ArgumentException>(()=>PlayerRecoveryScheduleV3.For(0,.0625f,.1f,.25f,bad));
                    Assert.Throws<ArgumentException>(()=>PlayerRecoveryScheduleV3.For(128,.0625f,.1f,.25f,bad));
                    Assert.Throws<ArgumentException>(()=>PlayerRecoveryScheduleV3.Validate(true,"movement-maintenance",.0625f,.1f,bad,0,0,0,256));
                    Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(Manifest(bad),0));
                }
            } finally {UnityEngine.Object.DestroyImmediate(oldHolder);UnityEngine.Object.DestroyImmediate(newHolder);}
            Assert.IsFalse(Unity.MLAgents.Academy.IsInitialized);
        }

        [TestCase(0)] [TestCase(32)] [TestCase(64)] [TestCase(96)]
        [TestCase(128)] [TestCase(160)] [TestCase(192)] [TestCase(224)]
        public void ActualResetConstructionRoutesOnlyAxesFocus(int firstIndex)
        {
            Assert.IsFalse(Unity.MLAgents.Academy.IsInitialized);
            var golden=Golden();var rows=(JArray)golden["rows"];
            var oldHolder=new GameObject("Inactive old recovery");var newHolder=new GameObject("Inactive axes recovery");
            try {
                var old=Make(oldHolder,"lateral",(int)golden["firstSeed"]);
                var axes=Make(newHolder,"axes",(int)golden["firstSeed"]);
                for(int i=firstIndex;i<firstIndex+32;i++)
                using(var a=old.CreateDrillForEpisode(i,out string[] oldRejected))
                using(var b=axes.CreateDrillForEpisode(i,out string[] newRejected)) {
                    Actual(a,i,rows[i],false);Actual(b,i,rows[i],true);
                    CollectionAssert.AreEqual(rows[i]["resetRejections"].Values<string>().ToArray(),oldRejected);
                    CollectionAssert.AreEqual(oldRejected,newRejected);
                    if((string)rows[i]["group"]!="focus") {
                        for(int seat=0;seat<4;seat++)CollectionAssert.AreEqual(PlayerObservationV3.Capture(a.Match,seat,0).ToArray(),PlayerObservationV3.Capture(b.Match,seat,0).ToArray());
                        Assert.AreEqual(a.Match.World.Ball.position,b.Match.World.Ball.position);
                    } else {
                        int region=b.Match.MovementRegion,sign=b.Player<2?1:-1;
                        CollectionAssert.Contains(new[]{1,3,5,7},region);
                        var body=b.Match.World.Players[b.Player];
                        var face=body.Paddle.position+body.Paddle.rotation*PlayerStrokeAimV3.FacePoint;
                        var delta=b.Match.MovementNominalPoint-face;delta.y=0;
                        float distance=4*b.MovementRange;
                        Assert.That(distance,Is.InRange(.0625f,.25f));
                        var expected=region==3?new Vector3(-distance,0,0):region==5?new Vector3(distance,0,0):region==1?new Vector3(0,0,distance):new Vector3(0,0,-distance);
                        Assert.Less(Vector3.Distance(delta,expected*sign),2e-5);
                        Assert.Less(Vector3.Distance(b.Match.World.Ball.position-a.Match.World.Ball.position,b.Match.MovementNominalPoint-a.Match.MovementNominalPoint),2e-5);
                    }
                    Assert.AreEqual(a.Match.World.Ball.linearVelocity,b.Match.World.Ball.linearVelocity);
                    for(int seat=0;seat<4;seat++)Assert.AreEqual(a.Match.World.Players[seat].Position,b.Match.World.Players[seat].Position);
                    Assert.IsFalse(Unity.MLAgents.Academy.IsInitialized);
                }
            } finally {UnityEngine.Object.DestroyImmediate(oldHolder);UnityEngine.Object.DestroyImmediate(newHolder);}
        }
    }
}

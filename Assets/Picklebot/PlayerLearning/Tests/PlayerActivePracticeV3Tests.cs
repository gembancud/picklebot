using System.Collections;
using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using Picklebot.PlayerControlsIntegration;
using Unity.InferenceEngine;
using Unity.MLAgents;
using Unity.MLAgents.Policies;
using UnityEngine;
using UnityEngine.TestTools;
namespace Picklebot.PlayerLearning.Tests
{
 public sealed class PlayerActivePracticeV3Tests
 {
  [Test]
  public void FrozenModelIsRequiredOnlyWhenRequestedAndNeverReplacesTrainingLearner()
  {
   var m=new PlayerWorkerManifestV3{version=PlayerWorkerPlanV3.Version,mode="training",task="stationary-serve",sourceIdentity=new string('a',64),buildIdentity=new string('b',64),backgroundModelHash=new string('c',64),evidenceRoot="F:/dev/picklebot/artifacts/player-v3/active-player-worker-fixture",basePort=5005,workerCount=1,firstSeed=1000000,seedsPerWorker=8,arenasPerWorker=1,ticksPerFrame=48};
   var root=new GameObject("Frozen worker configuration");root.SetActive(false);var model=ScriptableObject.CreateInstance<ModelAsset>();
   try{
    var run=root.AddComponent<PlayerMlDrillsV3>();var plan=PlayerWorkerPlanV3.Create(m,0);
    Assert.Throws<System.ArgumentException>(()=>plan.Configure(run,null));
    plan.Configure(run,model);Assert.AreSame(model,run.BackgroundModel);Assert.IsNull(run.InferenceModel);Assert.IsTrue(run.RequireTrainer);Assert.IsNull(run.Report);Assert.AreEqual(0,run.ActiveArenas.Count);
    m.backgroundModelHash=null;PlayerWorkerPlanV3.Create(m,0).Configure(run,null);Assert.IsNull(run.BackgroundModel);
    m.backgroundModelHash="invalid";Assert.Throws<System.ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
    m.backgroundModelHash=new string('c',64);m.task="fixed-team-match";Assert.Throws<System.ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
   }finally{Object.DestroyImmediate(root);Object.DestroyImmediate(model);}
  }
  [UnityTest]
  public IEnumerator FrozenPlayersUsePrivateObservationsAcrossLearnerRotation()
  {
   var model=UnityEditor.AssetDatabase.LoadAssetAtPath<ModelAsset>("Assets/Picklebot/PlayerLearning/Models/MatchStateRecoveryHalf01.onnx");Assert.IsNotNull(model);
   var root=new GameObject("Active practice fixture");root.SetActive(false);var run=root.AddComponent<PlayerMlDrillsV3>();
   run.AutoRun=false;run.RequireTrainer=false;run.InferenceModel=model;run.BackgroundModel=model;
   // Reuse existing development fixture seeds; not independent acceptance evidence.
   run.FirstSeed=1101741;run.SeedCount=8;run.ArenaCount=1;run.Task="stationary-serve";run.FixedServeSides="both";
   int learnerDecisions=0,frozenDecisions=0;var roles=new HashSet<int>();var movingSeats=new HashSet<int>();
   try{
    root.SetActive(true);run.InitializeRun();var arena=run.ActiveArenas.Single();
    foreach(var agent in arena.Agents)agent.Received+=(current,actions)=>{
     learnerDecisions++;roles.Add(current.Seat);Assert.AreEqual(arena.Drill.Player,current.Seat);
     Assert.AreEqual(current.Seat,current.LastObservation.player);
     CollectionAssert.AreEqual(PlayerObservationV3.Capture(arena.Drill.Match,current.Seat,current.ObservedTick).ToArray(),current.LastObservation.ToArray());
    };
    foreach(var agent in arena.BackgroundAgents){Assert.IsNotNull(agent);
     var behavior=agent.GetComponent<BehaviorParameters>();Assert.AreEqual(BehaviorType.InferenceOnly,behavior.BehaviorType);Assert.AreSame(model,behavior.Model);Assert.AreEqual("PicklebotPracticeFrozen",behavior.BehaviorName);
     agent.Received+=(current,actions)=>{
      frozenDecisions++;Assert.AreNotEqual(arena.Drill.Player,current.Seat);Assert.AreEqual(current.Seat,current.LastObservation.player);
      CollectionAssert.AreEqual(PlayerObservationV3.Capture(arena.Drill.Match,current.Seat,current.ObservedTick).ToArray(),current.LastObservation.ToArray());
      Assert.AreEqual(0,current.LastCommand.ToArray()[16]);
      if(current.LastCommand.ToArray().Any(x=>Mathf.Abs(x)>.001f))movingSeats.Add(current.Seat);
     };
    }
    for(int tick=0;tick<15000&&run.Report.status=="running";tick++)run.StepOneTick();
    Assert.AreEqual("seed_budget_complete",run.Report.status);Assert.AreEqual(8,run.Episodes.Count);Assert.AreEqual(4,roles.Count);Assert.AreEqual(4,movingSeats.Count);
    Assert.IsTrue(run.Report.activePracticePlayers);Assert.AreEqual(learnerDecisions,run.Report.decisions);Assert.AreEqual(frozenDecisions,run.Report.backgroundDecisions);
    Assert.AreEqual(learnerDecisions*3,frozenDecisions);Assert.AreEqual(learnerDecisions,run.Episodes.Sum(e=>e.decisions));Assert.AreEqual(frozenDecisions,run.Episodes.Sum(e=>e.backgroundDecisions));
    Assert.IsTrue(run.Episodes.All(e=>e.backgroundDecisions==3*e.decisions));
   }finally{Object.DestroyImmediate(root);if(Academy.IsInitialized)Academy.Instance.Dispose();}
   yield return null;
  }
 }
}

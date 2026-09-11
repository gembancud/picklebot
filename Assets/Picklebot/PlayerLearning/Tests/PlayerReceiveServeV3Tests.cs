using System.Collections;
using System.Linq;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
using Unity.InferenceEngine;
using Unity.MLAgents;
using Picklebot.Doubles;
using Picklebot.PlayerControlsIntegration;
namespace Picklebot.PlayerLearning.Tests {
public sealed class PlayerReceiveServeV3Tests {
 [Test] public void ReceiverResetUsesRealUnplayedGameAndFixedServeSupport(){
  for(int seat=0;seat<4;seat++)for(int index=0;index<16;index++){
   int seed=1101773+index;
   using(var d=new PlayerContactDrillV3(seed,seat,"receive-serve",matchContextSeed:seed)){
    var rules=d.Match.World.Rules;Assert.AreEqual(seat,rules.DesignatedReceiver);Assert.AreNotEqual(seat/2,rules.Server/2);
    Assert.AreEqual(RallyPhase.AwaitServe,rules.Phase);Assert.IsEmpty(rules.Events);Assert.IsFalse(d.IncomingServeLanded);Assert.IsFalse(d.FaceContact);
    Assert.IsTrue(d.Match.World.FixedBallServe);Assert.IsTrue(d.Match.StationarySupportActive);
    using(var reference=new PlayerLearningMatchV3(false,rules.Server,0,rules.IsRight(rules.Server),seed)){
     reference.InitializeStationaryServe();for(int player=0;player<4;player++)CollectionAssert.AreEqual(PlayerObservationV3.Capture(reference,player,0).ToArray(),PlayerObservationV3.Capture(d.Match,player,0).ToArray());
    }
   }
  }
 }
 [UnityTest] public IEnumerator LearnedServeCanBounceWithoutEndingReceiverEpisode(){
  var model=UnityEditor.AssetDatabase.LoadAssetAtPath<ModelAsset>("Assets/Picklebot/PlayerLearning/Models/AfterActivePlayers01.onnx");Assert.IsNotNull(model);
  var root=new GameObject("Receive real serve fixture");root.SetActive(false);var run=root.AddComponent<PlayerMlDrillsV3>();
  run.AutoRun=false;run.RequireTrainer=false;run.InferenceModel=model;run.BackgroundModel=model;run.FirstSeed=1101773;run.SeedCount=16;run.ArenaCount=4;run.Task="serve-receive";run.FixedServeSides="both";
  bool sawIncomingBounce=false,sawRealServe=false;int observationChecks=0;
  try{
   root.SetActive(true);run.InitializeRun();
   foreach(var arena in run.ActiveArenas){var captured=arena;foreach(var agent in arena.Agents)agent.Received+=(current,actions)=>{
    if(captured.Drill.Task!="receive-serve")return;observationChecks++;Assert.AreEqual(captured.Drill.Match.World.Rules.DesignatedReceiver,current.Seat);
    CollectionAssert.AreEqual(PlayerObservationV3.Capture(captured.Drill.Match,current.Seat,current.ObservedTick).ToArray(),current.LastObservation.ToArray());
    sawRealServe|=captured.Drill.Match.World.Rules.Events.Any(e=>e.kind=="serve"&&e.time>0);
    if(captured.Drill.IncomingServeLanded){sawIncomingBounce=true;Assert.IsFalse(captured.Drill.Done);Assert.IsTrue(captured.Drill.Match.World.Rules.Events.Any(e=>e.kind=="bounce"&&e.time>0));}
   };}
   for(int tick=0;tick<30000&&run.Report.status=="running";tick++)run.StepOneTick();
   Assert.AreEqual("seed_budget_complete",run.Report.status);Assert.AreEqual(16,run.Episodes.Count);Assert.Greater(observationChecks,0);Assert.IsTrue(sawRealServe);Assert.IsTrue(sawIncomingBounce);
   Assert.IsTrue(run.Episodes.Any(e=>e.task=="receive-serve"&&e.incomingServeLanded));Assert.IsFalse(run.Episodes.Any(e=>e.task=="stationary-serve"&&e.incomingServeLanded));Assert.AreEqual(8,run.Episodes.Count(e=>e.task=="receive-serve"));Assert.AreEqual(8,run.Episodes.Count(e=>e.task=="stationary-serve"));
   Assert.IsTrue(run.Episodes.All(e=>e.backgroundDecisions==3*e.decisions));
  }finally{Object.DestroyImmediate(root);if(Academy.IsInitialized)Academy.Instance.Dispose();}
  yield return null;
 }
}}

using System;
using System.Linq;
using NUnit.Framework;
using UnityEngine;
using Picklebot.PlayerControlsIntegration;
namespace Picklebot.PlayerLearning.Tests
{
 public sealed class PlayerInterleavedRecoveryV3Tests
 {
  private static int Group(int i){i%=256;return i<64?0:i<128?1:i<160?2:i<192?3:i<240?4:5;}
  [Test] public void DisabledOrderIsIdentityForWholeWorkerInventory()
  {for(int w=0;w<8;w++)for(int i=0;i<12288;i++)Assert.AreEqual(i,PlayerInterleavedRecoveryV3.Index(i,w,false));}
  [Test] public void InterleavingPreservesEveryOriginalSeedAcrossAllWorkerCycles()
  {for(int w=0;w<8;w++)for(int c=0;c<48;c++)CollectionAssert.AreEqual(Enumerable.Range(c*256,256),Enumerable.Range(c*256,256).Select(i=>PlayerInterleavedRecoveryV3.Index(i,w,true)).OrderBy(i=>i));}
  [Test] public void EverySlidingSixteenStartsRetainsTheExactGroupMixture()
  {for(int w=0;w<8;w++)for(int start=0;start<512;start++){var groups=Enumerable.Range(start,16).Select(i=>Group(PlayerInterleavedRecoveryV3.Index(i,w,true))).ToArray();CollectionAssert.AreEqual(new[]{4,4,2,2,3,1},Enumerable.Range(0,6).Select(g=>groups.Count(i=>i==g)));}}
  [Test] public void InitialFleetCoversEverySeatAndFamiliarSubtype()
  {
   var indices=Enumerable.Range(0,8).SelectMany(w=>Enumerable.Range(0,16).Select(i=>PlayerInterleavedRecoveryV3.Index(i,w,true))).ToArray();
   foreach(int seat in Enumerable.Range(0,4))CollectionAssert.AreEqual(new[]{8,8,4,4,6,2},Enumerable.Range(0,6).Select(g=>indices.Count(i=>i%4==seat&&Group(i)==g)));
   CollectionAssert.AreEquivalent(Enumerable.Range(0,8),indices.Where(i=>i<64).Select(i=>i/4%8).Distinct());
  }
  [Test] public void PermutationPreservesPhysicalResetsAndPrivateObservations()
  {
   var g=new GameObject("Interleave reset parity");g.SetActive(false);
   try{
    var r=g.AddComponent<PlayerMlDrillsV3>();r.AutoRun=false;r.RequireTrainer=false;r.Task="movement-maintenance";r.FixedServeSides="both";r.MovementRecoveryMix=true;r.MovementRange=.025f;r.MovementRehearsalRange=.1f;r.MovementPattern="lateral";r.MaximumReturnDifficulty=.25f;r.FirstSeed=1305000;r.SeedCount=256;r.InterleavedRecovery=true;r.SchedulerWorkerId=3;
    foreach(int i in Enumerable.Range(0,256)){
     int mapped=r.AllocationIndexForOrdinal(i);using(var a=r.CreateDrillForEpisode(mapped,out _)){
      r.InterleavedRecovery=false;using(var b=r.CreateDrillForEpisode(mapped,out _)){
       Assert.AreEqual(b.Seed,a.Seed);Assert.AreEqual(b.Player,a.Player);Assert.AreEqual(b.Task,a.Task);Assert.AreEqual(b.Match.World.Ball.position,a.Match.World.Ball.position);
       for(int p=0;p<4;p++)CollectionAssert.AreEqual(PlayerObservationV3.Capture(b.Match,p,0).ToArray(),PlayerObservationV3.Capture(a.Match,p,0).ToArray());
      }r.InterleavedRecovery=true;
     }
    }
   }finally{UnityEngine.Object.DestroyImmediate(g);}
  }
  [Test] public void InvalidOrdersAndDiagnosticContractsFailExplicitly()
  {
   Assert.Throws<ArgumentOutOfRangeException>(()=>PlayerInterleavedRecoveryV3.Index(-1,0,true));Assert.Throws<ArgumentOutOfRangeException>(()=>PlayerInterleavedRecoveryV3.Index(0,8,true));
   Assert.Throws<ArgumentException>(()=>PlayerInterleavedRecoveryV3.Validate(true,false,256,0));Assert.Throws<ArgumentException>(()=>PlayerInterleavedRecoveryV3.Validate(true,true,128,0));
   Assert.DoesNotThrow(()=>PlayerDrillDiagnosticsV3.ValidatePinnedContract());
   var probeRoot=new GameObject("Diagnostic terminal lifecycle");probeRoot.SetActive(false);
   try {
    var behavior=probeRoot.AddComponent<Unity.MLAgents.Policies.BehaviorParameters>();behavior.BehaviorType=Unity.MLAgents.Policies.BehaviorType.HeuristicOnly;
    behavior.BrainParameters.VectorObservationSize=1;behavior.BrainParameters.ActionSpec=Unity.MLAgents.Actuators.ActionSpec.MakeContinuous(1);
    var probe=probeRoot.AddComponent<DiagnosticTerminalProbeV3>();probeRoot.SetActive(true);
    Unity.MLAgents.Academy.Instance.AutomaticSteppingEnabled=false;
    probe.RequestDecision();Unity.MLAgents.Academy.Instance.EnvironmentStep();
    probe.DrillDone=true;probe.EndEpisode();
    probe.DrillDone=false;probe.RequestDecision();Unity.MLAgents.Academy.Instance.EnvironmentStep();
    probeRoot.SetActive(false);
    CollectionAssert.AreEqual(new[]{false,true,false,true},probe.Captures);
   } finally {UnityEngine.Object.DestroyImmediate(probeRoot);if(Unity.MLAgents.Academy.IsInitialized)Unity.MLAgents.Academy.Instance.Dispose();}
  }
  [Test] public void InterleavedLifecycleCompletesWholeSeedPoolWithoutChangingPrivateActions()
  {
   var g=new GameObject("Interleave lifecycle");g.SetActive(false);try{
    var r=g.AddComponent<PlayerMlDrillsV3>();r.AutoRun=false;r.RequireTrainer=false;r.Task="movement-maintenance";r.FixedServeSides="both";r.MovementRecoveryMix=true;r.MovementRange=.025f;r.MovementRehearsalRange=.1f;r.MovementPattern="lateral";r.MaximumReturnDifficulty=.25f;r.FirstSeed=1305000;r.SeedCount=256;r.ArenaCount=16;r.InterleavedRecovery=true;r.SchedulerWorkerId=5;g.SetActive(true);r.InitializeRun();
    for(int t=0;t<140000&&r.Report.status=="running";t++)r.StepOneTick();Assert.AreEqual("seed_budget_complete",r.Report.status);Assert.AreEqual(256,r.Report.nextSeedIndex);CollectionAssert.AreEqual(Enumerable.Range(r.FirstSeed,256),r.Episodes.Select(e=>e.seed).OrderBy(x=>x));
    foreach(var e in r.Episodes){Assert.AreEqual(0,e.movementPositionReward);Assert.AreEqual(0,e.backgroundDecisions);for(int p=0;p<4;p++)Assert.AreEqual(p==e.player,e.decisionsByPlayer[p]>0);}
   }finally{UnityEngine.Object.DestroyImmediate(g);if(Unity.MLAgents.Academy.IsInitialized)Unity.MLAgents.Academy.Instance.Dispose();}
  }
 }
 public sealed class DiagnosticTerminalProbeV3:Unity.MLAgents.Agent
 {
  public bool DrillDone;
  public readonly System.Collections.Generic.List<bool> Captures=new();
  public override void Initialize(){MaxStep=0;}
  public override void CollectObservations(Unity.MLAgents.Sensors.VectorSensor sensor){Captures.Add(PlayerDrillDiagnosticsV3.IsTerminal(this,DrillDone));sensor.AddObservation(0f);}
  public override void Heuristic(in Unity.MLAgents.Actuators.ActionBuffers actions){actions.ContinuousActions.Clear();actions.DiscreteActions.Clear();}
 }
}

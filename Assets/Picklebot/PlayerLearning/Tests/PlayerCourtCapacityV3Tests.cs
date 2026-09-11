using System;
using System.Linq;
using NUnit.Framework;
namespace Picklebot.PlayerLearning.Tests {
public sealed class PlayerCourtCapacityV3Tests {
 private static PlayerWorkerManifestV3 Manifest()=>new PlayerWorkerManifestV3{version=PlayerWorkerPlanV3.Version,mode="training",task="stationary-serve",sourceIdentity=new string('a',64),buildIdentity=new string('b',64),evidenceRoot="F:/dev/picklebot/artifacts/player-v3/capacity-fixture",basePort=5005,workerCount=4,firstSeed=1000000,seedsPerWorker=12288,arenasPerWorker=8,ticksPerFrame=48};
 [TestCase(4,8)][TestCase(4,16)][TestCase(8,12)][TestCase(8,16)][TestCase(4,32)][TestCase(8,24)][TestCase(8,32)]
 public void LargerFleetPreservesDistinctCompleteWorkerAllocations(int workers,int courts){
  var m=Manifest();m.workerCount=workers;m.arenasPerWorker=courts;
  var plans=Enumerable.Range(0,workers).Select(i=>PlayerWorkerPlanV3.Create(m,i)).ToArray();
  Assert.AreEqual(workers,plans.Select(p=>p.EvidenceDirectory).Distinct().Count());
  Assert.AreEqual(workers*12288,plans.SelectMany(p=>Enumerable.Range(p.FirstSeed,p.SeedCount)).Distinct().Count());
  Assert.IsTrue(plans.All(p=>p.FirstSeed>=1000000&&p.FirstSeed+p.SeedCount<=1100000));
 }
 [Test] public void RejectsOverflowAndUnsupportedPerProcessOrTotalCounts(){
  var m=Manifest();m.workerCount=8;m.arenasPerWorker=33;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
  m.workerCount=1;m.arenasPerWorker=33;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
  m.workerCount=8;m.arenasPerWorker=int.MaxValue;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
  m.workerCount=9;m.arenasPerWorker=1;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
 }
}}

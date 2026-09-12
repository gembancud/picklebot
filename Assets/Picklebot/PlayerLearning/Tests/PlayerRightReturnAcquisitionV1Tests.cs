using System;
using NUnit.Framework;
using UnityEngine;
namespace Picklebot.PlayerLearning.Tests
{
    public sealed class PlayerRightReturnAcquisitionV1Tests
    {
        [Test] public void FixedRightRangeCoversBothFeedsAndEverySeat()
        {
            var go=new GameObject("Acquisition schedule test");go.SetActive(false);
            try {
                var run=go.AddComponent<PlayerMlDrillsV3>();run.Task=PlayerRightReturnAcquisitionV1.Task;run.MovementPattern="lateral-right";run.MovementRange=.0625f;
                for(int i=0;i<64;i++){
                    Assert.AreEqual(i/4%2==0?"rally-air-feed":"rally-bounce-feed",run.TaskForEpisode(i));
                    Assert.AreEqual(.0625f,run.MovementRangeForEpisode(i));Assert.AreEqual("lateral-right",run.MovementPatternForEpisode(i));Assert.AreEqual(0,run.DifficultyForEpisode(i));
                    Assert.IsFalse(run.MovementRehearsalForEpisode(i));Assert.IsFalse(run.ServeFromLeftForEpisode(i));
                }
                Assert.AreEqual(8,PlayerWorkerPlanV3.CycleLength(run.Task));
            } finally {UnityEngine.Object.DestroyImmediate(go);}
        }
        [Test] public void ScopeRejectsMixedSchedulesAndOtherDirections()
        {
            string task=PlayerRightReturnAcquisitionV1.Task;
            Assert.DoesNotThrow(()=>PlayerRightReturnAcquisitionV1.Validate(task,.0625f,"lateral-right",false,0,false,0,0,0));
            Assert.Throws<ArgumentException>(()=>PlayerRightReturnAcquisitionV1.Validate(task,.0625f,"axes",false,0,false,0,0,0));
            Assert.Throws<ArgumentException>(()=>PlayerRightReturnAcquisitionV1.Validate(task,.0625f,"lateral-right",true,0,false,0,0,0));
            Assert.Throws<ArgumentException>(()=>PlayerRightReturnAcquisitionV1.Validate(task,0,"lateral-right",false,0,false,0,0,0));
            Assert.Throws<ArgumentException>(()=>PlayerRightReturnAcquisitionV1.Validate(task,float.NaN,"lateral-right",false,0,false,0,0,0));
            Assert.Throws<ArgumentOutOfRangeException>(()=>PlayerRightReturnAcquisitionV1.Feed(-1));
        }
        [Test] public void LegacyMovementScheduleRetainsItsSixtyFourCaseCycle()
        {
            var go=new GameObject("Legacy schedule test");go.SetActive(false);
            try {
                var run=go.AddComponent<PlayerMlDrillsV3>();run.Task="movement-maintenance";run.MovementPattern="axes";run.MovementRange=.0625f;
                for(int i=0;i<64;i++){
                    int block=i/4;Assert.AreEqual(block<2?"stationary-serve":block<4?"receive-feed":block<6||block>=8&&block<12?"rally-air-feed":"rally-bounce-feed",run.TaskForEpisode(i));
                    Assert.AreEqual(block<4?-1:block<8?0:.0625f*(1+block%4)*.25f,run.MovementRangeForEpisode(i));
                }
                Assert.AreEqual(64,PlayerWorkerPlanV3.CycleLength(run.Task));
            } finally {UnityEngine.Object.DestroyImmediate(go);}
        }
    }
}

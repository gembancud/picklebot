using System;
using NUnit.Framework;
namespace Picklebot.PlayerLearning.Tests
{
    public sealed class PlayerPrecontactScheduleV3Tests
    {
        [Test] public void DefaultOffPreservesOtherTasks()
        {Assert.DoesNotThrow(()=>PlayerMlDrillsV3.ValidatePrecontactAlignment("paired-maintenance",0,false,.95f,true,.1f));}
        [Test] public void EnabledRequiresSoloFocusAndMatchingGamma()
        {
            Assert.DoesNotThrow(()=>PlayerMlDrillsV3.ValidatePrecontactAlignment("movement-maintenance",.25f,true,.99f,false,0));
            Assert.Throws<ArgumentException>(()=>PlayerMlDrillsV3.ValidatePrecontactAlignment("paired-movement-maintenance",.25f,true,.99f,false,0));
            Assert.Throws<ArgumentException>(()=>PlayerMlDrillsV3.ValidatePrecontactAlignment("movement-maintenance",.25f,true,.95f,false,0));
            Assert.Throws<ArgumentException>(()=>PlayerMlDrillsV3.ValidatePrecontactAlignment("movement-maintenance",0,true,.99f,false,0));
        }
        [Test] public void DistinctRewardInterventionsCannotAccidentallyMix()
        {
            Assert.Throws<ArgumentException>(()=>PlayerMlDrillsV3.ValidatePrecontactAlignment("movement-maintenance",.25f,true,.99f,true,0));
            Assert.Throws<ArgumentException>(()=>PlayerMlDrillsV3.ValidatePrecontactAlignment("movement-maintenance",.25f,true,.99f,false,.1f));
        }
    }
}

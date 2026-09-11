using System;
using System.IO;
using NUnit.Framework;
using Picklebot.Doubles;
using UnityEngine;
namespace Picklebot.PlayerControlsIntegration.Tests
{
    public sealed class PlayerContactCalibrationV2Tests
    {
        private const string Hash="6698221451858f044e26a28c58a39447d391c4f1aba58a68f11370926df9cba4";
        private static string Json=>File.ReadAllText(Path.Combine(Application.dataPath,"Picklebot/Doubles/Models/contact.json"));
        [Test] public void HistoricalCalibrationMatchesEachStrokeAndOwnsItsParameters()
        {
            var calibration=PlayerContactCalibrationV2.Load(Json,Hash);var original=ContactModel.Load(Json);
            for(int i=0;i<3;i++)
            {
                var first=new StrokeController();var second=new StrokeController();calibration.Apply((StrokeKind)i,first);
                Assert.AreEqual(original.strokes[i].pitch,first.PitchBias);Assert.AreEqual(original.strokes[i].timing,first.TimingBias);
                Assert.AreEqual(original.strokes[i].speed,first.SpeedScale);Assert.AreEqual(original.strokes[i].brush,first.BrushScale);Assert.AreEqual(original.strokes[i].brushBias,first.BrushBias);
                first.PitchBias=999;calibration.Apply((StrokeKind)i,second);Assert.AreEqual(original.strokes[i].pitch,second.PitchBias);
            }
        }
        [Test] public void WrongCheckpointCalibrationFailsAndLineEndingsArePortable()
        {
            Assert.Throws<ArgumentException>(()=>PlayerContactCalibrationV2.Load(Json,new string('0',64)));
            Assert.AreEqual(Hash,PlayerContactCalibrationV2.Load(Json.Replace("\r\n","\n").Replace("\n","\r\n"),Hash).Hash);
        }
    }
}

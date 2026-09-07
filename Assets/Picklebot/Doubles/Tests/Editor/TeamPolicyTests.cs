using System;
using System.Collections.Generic;
using NUnit.Framework;
namespace Picklebot.Doubles.Tests
{
    public sealed class TeamPolicyTests
    {
        [Test] public void NewPolicyHasUniformProbabilities()
        {var p=new TeamPolicy().Probabilities(new float[12]);foreach(float v in p)Assert.That(v,Is.EqualTo(1f/9).Within(.00001));}
        [Test] public void WinIncreasesSelectedActionProbability()
        {
            var p=new TeamPolicy();var x=new float[12];x[0]=1;var before=p.Probabilities(x);
            p.Learn(new List<TeamDecision>{new(){team=0,action=2,observation=x,probabilities=before}},0,0);
            Assert.That(p.Probabilities(x)[2],Is.GreaterThan(before[2]));
        }
        [Test] public void DrawDoesNotCreateWinReward()
        {var p=new TeamPolicy();p.Learn(new List<TeamDecision>(),0,-1);Assert.That(p.weights,Is.EqualTo(new float[108]));}
        [Test] public void ModelRejectsWrongWeightCount()
        {Assert.Throws<ArgumentException>(()=>DoublesModels.Load("{\"version\":\"doubles-team-policy-v1\",\"orange\":{\"weights\":[1]}}"));}
        [Test] public void ContactModelRejectsUnknownVersion()
        {Assert.Throws<ArgumentException>(()=>ContactModel.Load("{\"version\":\"old\"}"));}
        [Test] public void TimeLimitDoesNotChangeScoreOrServer()
        {var r=new DoublesRules();r.Truncate(30);Assert.That(r.ResolveRally());Assert.That(r.ScoreCall,Is.EqualTo("0-0-2"));Assert.That(r.Winner,Is.EqualTo(-1));}
    }
}

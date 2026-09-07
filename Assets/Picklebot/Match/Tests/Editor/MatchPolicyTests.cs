using System.Collections.Generic;
using NUnit.Framework;
using UnityEngine;
namespace Picklebot.Match.Tests
{
    public sealed class MatchPolicyTests
    {
        [Test] public void WinningActionProbabilityIncreases()
        {
            var p=new ShotPolicy();var x=new[]{1f,0f,0f,0f,0f,0f};var d=p.Choose(x,-1,new System.Random(1),true);
            p.Learn(new List<ShotSample>{d},-1,-1);var after=p.Choose(x,-1,new System.Random(1),false);
            Assert.That(after.probabilities[d.action],Is.GreaterThan(d.probabilities[d.action]));
        }
        [Test] public void LosingActionProbabilityDecreases()
        {
            var p=new ShotPolicy();var x=new[]{1f,0f,0f,0f,0f,0f};var d=p.Choose(x,1,new System.Random(1),true);
            p.Learn(new List<ShotSample>{d},1,-1);Assert.That(p.Choose(x,1,new System.Random(1),false).probabilities[d.action],Is.LessThan(d.probabilities[d.action]));
        }
        [Test] public void TimeCapDoesNotRewardEitherSide()
        {
            var p=new ShotPolicy();p.Learn(new List<ShotSample>(),-1,0);Assert.That(p.updates,Is.Zero);
        }
        [Test] public void IndependentPoliciesAndModelRoundTrip()
        {
            var m=new MatchModels();m.orange.weights[0]=1;
            var loaded=MatchModels.Load(JsonUtility.ToJson(m));Assert.That(loaded.orange.weights[0],Is.EqualTo(1));Assert.That(loaded.blue.weights[0],Is.Zero);
            loaded.orange.weights=new float[1];Assert.Throws<System.ArgumentException>(()=>MatchModels.Load(JsonUtility.ToJson(loaded)));
        }
    }
}

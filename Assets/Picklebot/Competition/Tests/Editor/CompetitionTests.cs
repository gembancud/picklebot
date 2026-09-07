using System;
using System.IO;
using NUnit.Framework;
using UnityEngine;

namespace Picklebot.Competition.Tests
{
    public sealed class CompetitionTests
    {
        private static DensePolicy Stroke() => new DensePolicy(File.ReadAllText("Assets/Picklebot/Competition/Models/stroke.json"),"competitive-stroke-v1",10,6);
        [Test] public void WrongPolicyVersionIsRejected()
        {
            Assert.Throws<ArgumentException>(()=>new DensePolicy(File.ReadAllText("Assets/Picklebot/Competition/Models/stroke.json"),"wrong-version",10,6));
        }
        [Test] public void WrongObservationSizeIsRejected() => Assert.Throws<ArgumentException>(()=>Stroke().Predict(new float[9]));
        [Test] public void StrategyChangesTargetWhenOpponentChangesSide()
        {
            var policy=new DensePolicy(File.ReadAllText("Assets/Picklebot/Competition/Models/strategy.json"),"competitive-strategy-v1",8,5);
            foreach(float opponent in new[]{-.8f,.8f})
            {
                var logits=policy.Predict(new[]{0f,.4f,.79f,0f,.75f,-4f,0f,opponent});
                int action=0;for(int i=1;i<logits.Length;i++)if(logits[i]>logits[action])action=i;
                Assert.That(CompetitiveWorld.Goals[action].x*opponent,Is.LessThan(0));
            }
        }
        [Serializable] private sealed class Sample { public float[] input, output; }
        [Serializable] private sealed class Reference { public Sample[] samples; }
        [TestCase("stroke","competitive-stroke-v1",10,6)]
        [TestCase("strategy","competitive-strategy-v1",8,5)]
        public void ExportMatchesPython(string name,string version,int inputs,int outputs)
        {
            string path="Assets/Picklebot/Competition/Models/"+name;
            var policy=new DensePolicy(File.ReadAllText(path+".json"),version,inputs,outputs);
            var reference=JsonUtility.FromJson<Reference>(File.ReadAllText(path+".reference.json"));
            Assert.That(reference.samples.Length,Is.GreaterThanOrEqualTo(32));
            foreach(var sample in reference.samples)
            {
                var result=policy.Predict(sample.input);
                for(int i=0;i<outputs;i++)Assert.That(result[i],Is.EqualTo(sample.output[i]).Within(.0001f));
            }
        }
    }
}

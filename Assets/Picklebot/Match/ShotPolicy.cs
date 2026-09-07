using System;
using System.Collections.Generic;
using UnityEngine;

namespace Picklebot.Match
{
    [Serializable] public sealed class ShotSample { public float[] observation,probabilities;public int action,side; }
    [Serializable] public sealed class ShotPolicy
    {
        public const int Inputs=6,Actions=5;
        public string version="pickleball-shot-policy-v1";
        public int updates;
        public float[] weights=new float[Inputs*Actions];
        public static readonly Vector2[] Goals={new(0,2),new(-1.8f,2),new(1.8f,2),new(-1.8f,3.8f),new(1.8f,3.8f)};
        public ShotSample Choose(float[] observation,int side,System.Random rng,bool sample)
        {
            var p=new float[Actions];float max=float.NegativeInfinity,total=0;
            for(int a=0;a<Actions;a++) {for(int j=0;j<Inputs;j++)p[a]+=weights[a*Inputs+j]*observation[j];max=Mathf.Max(max,p[a]);}
            for(int a=0;a<Actions;a++) {p[a]=Mathf.Exp(p[a]-max);total+=p[a];}
            for(int a=0;a<Actions;a++)p[a]/=total;
            int action=0;
            if(sample) {float r=(float)rng.NextDouble();action=Actions-1;for(int a=0;a<Actions;a++){r-=p[a];if(r<=0){action=a;break;}}}
            else for(int a=1;a<Actions;a++)if(p[a]>p[action])action=a;
            return new ShotSample {observation=observation,probabilities=p,action=action,side=side};
        }
        public void Learn(List<ShotSample> samples,int side,int winner,float rate=.01f)
        {
            if(winner==0)return;
            float reward=winner==side?1:-1;
            for(int s=samples.Count-1;s>=0;s--)
            {
                var sample=samples[s];if(sample.side!=side)continue;
                for(int a=0;a<Actions;a++)for(int j=0;j<Inputs;j++)
                    weights[a*Inputs+j]=Mathf.Clamp(weights[a*Inputs+j]+rate*reward*((sample.action==a?1:0)-sample.probabilities[a])*sample.observation[j],-5,5);
                reward*=.97f;
            }
            updates++;
        }
    }
}

using System;
using System.Collections.Generic;
using UnityEngine;
namespace Picklebot.Doubles
{
    [Serializable] public sealed class TeamDecision
    {public int team,action,player;public float[] observation,probabilities;}
    [Serializable] public sealed class TeamPolicy
    {
        public const int Inputs=12,Actions=9;
        public float[] weights=new float[Inputs*Actions];
        public float[] Probabilities(float[] observation)
        {
            if(observation.Length!=Inputs)throw new ArgumentException("Invalid doubles observation.");
            var p=new float[Actions];float max=float.NegativeInfinity;
            for(int a=0;a<Actions;a++){for(int i=0;i<Inputs;i++)p[a]+=weights[a*Inputs+i]*observation[i];max=Mathf.Max(max,p[a]);}
            float total=0;for(int a=0;a<Actions;a++){p[a]=Mathf.Exp(p[a]-max);total+=p[a];}for(int a=0;a<Actions;a++)p[a]/=total;return p;
        }
        public TeamDecision Choose(DoublesWorld w,int team,System.Random rng,bool sample)
        {
            int side=DoublesRules.Side(team),a=team*2,b=(1-team)*2;
            var ball=w.Ball.position;var velocity=w.Ball.linearVelocity;
            var x=new[]{1f,ball.x/3,ball.z*side/7,velocity.x/15,velocity.z*side/15,w.Players[a].Position.x/3,w.Players[a+1].Position.x/3,
                w.Players[b].Position.x/3,w.Players[b+1].Position.x/3,Mathf.Abs(w.Players[b].Position.z)/7,Mathf.Abs(w.Players[b+1].Position.z)/7,w.Rules.CanVolley?1f:0f};
            var probabilities=Probabilities(x);int action=0;
            if(sample){float draw=(float)rng.NextDouble();for(int i=0;i<Actions;i++){draw-=probabilities[i];if(draw<=0){action=i;break;}}}
            else for(int i=1;i<Actions;i++)if(probabilities[i]>probabilities[action])action=i;
            return new TeamDecision{team=team,action=action,observation=x,probabilities=probabilities,player=-1};
        }
        public static Vector2 Target(int action)=>action switch
        {0=>new Vector2(0,3.4f),1=>new Vector2(-2.2f,2.8f),2=>new Vector2(2.2f,2.8f),3=>new Vector2(-2.1f,5.3f),4=>new Vector2(2.1f,5.3f),
            5=>new Vector2(-1.7f,3.8f),6=>new Vector2(1.7f,3.8f),7=>new Vector2(-1.7f,2.8f),8=>new Vector2(1.7f,2.8f),_=>throw new ArgumentOutOfRangeException(nameof(action))};
        public static StrokeKind Kind(int action)=>action<5?StrokeKind.Flat:action<7?StrokeKind.Topspin:StrokeKind.Slice;
        public void Learn(IReadOnlyList<TeamDecision> decisions,int team,int winner,float rate=.015f)
        {
            if(winner<0)return;float reward=winner==team?1:-1;
            for(int j=decisions.Count-1;j>=0;j--)
            {
                var d=decisions[j];if(d.team!=team)continue;
                for(int a=0;a<Actions;a++)for(int i=0;i<Inputs;i++)weights[a*Inputs+i]=Mathf.Clamp(weights[a*Inputs+i]+rate*reward*((a==d.action?1:0)-d.probabilities[a])*d.observation[i],-6,6);
                reward*=.98f;
            }
        }
    }
    [Serializable] public sealed class DoublesModels
    {
        public string version="doubles-team-policy-v1",method="two independent team softmax policies / terminal REINFORCE / fitted contact residuals / scripted interception and IK",sourceHash,configurationHash,contactModelHash,createdUtc;
        public int seed=910000,rallies;
        public TeamPolicy orange=new(),blue=new();
        public TeamPolicy ForTeam(int team)=>team==0?orange:blue;
        public static DoublesModels Load(string json)
        {
            var model=JsonUtility.FromJson<DoublesModels>(json);
            if(model?.version!="doubles-team-policy-v1")throw new ArgumentException("Invalid team model.");
            foreach(var p in new[]{model.orange,model.blue})if(p?.weights?.Length!=TeamPolicy.Inputs*TeamPolicy.Actions||Array.Exists(p.weights,v=>!float.IsFinite(v)))throw new ArgumentException("Invalid team policy weights.");
            return model;
        }
    }
}

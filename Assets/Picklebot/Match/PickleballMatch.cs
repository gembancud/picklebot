using System;
using System.Collections.Generic;
using Picklebot.Inspection;
using UnityEngine;

namespace Picklebot.Match
{
    public sealed class PickleballMatch:IDisposable
    {
        public const string Version="pickleball-assisted-selfplay-v1";
        public readonly InspectionWorld World;
        public readonly ScriptedStrokeMotor[] Controllers={new(),new()};
        public readonly List<ShotSample> Decisions=new();
        public readonly float[] Travel=new float[2];
        public int Seed {get;private set;}
        public bool Finished=>World.Rules.Finished||World.AtTimeLimit;
        public int Winner=>World.Rules.Finished?World.Rules.Winner:0;
        private System.Random rng;
        private int receiver,readContacts;
        private bool bounced,chosen;
        private Vector2 goal;
        public PickleballMatch(bool visible) {World=new InspectionWorld(visible);Reset(860000);}
        public void Reset(int seed)
        {
            Seed=seed;rng=new System.Random(seed);World.Reset(InspectionPreset.Serve);
            int server=seed%2==0?-1:1;float mirror=-server;
            float x=1.2f+(float)rng.NextDouble()*.6f;
            World.Rules.BeginServe(server,server<0?1:-1);
            var p=new Vector3(x*mirror,.8f,-6.9f*mirror);
            World.Ball.transform.position=p;World.Ball.position=p;
            World.Ball.linearVelocity=new Vector3(-2.7f*mirror,5.5f,12*mirror);
            for(int i=0;i<2;i++)
            {
                int side=i==0?-1:1;float px=side==server?x*mirror:-1.5f*mirror;
                World.Motors[i].Reset(new Vector3(px,0,side*6.1f),new Vector3(px,1,side*5.5f),Quaternion.LookRotation(Vector3.forward*-side));
                Controllers[i].Reset();Travel[i]=0;
            }
            receiver=World.Rules.Receiver;readContacts=0;bounced=chosen=false;Decisions.Clear();Physics.SyncTransforms();
        }
        public void Step(ShotPolicy orange,ShotPolicy blue,bool sample=false,bool stationary=false)
        {
            if(Finished)return;
            int side=World.Rules.Receiver,index=side<0?0:1;
            if(side!=receiver) {receiver=side;bounced=chosen=false;Controllers[index].Reset();Controllers[1-index].Reset();}
            if(!chosen&&World.Ball.linearVelocity.z*side>.1f)
            {
                float mirror=-side;
                var observation=new[]{1f,World.Ball.position.x*mirror/3,World.Ball.position.z*mirror/7,
                    World.Motors[index].PlayerPosition.x*mirror/3,World.Motors[1-index].PlayerPosition.x*mirror/3,
                    Mathf.Abs(World.Motors[1-index].PlayerPosition.z)/7};
                var decision=(index==0?orange:blue).Choose(observation,side,rng,sample);
                Decisions.Add(decision);goal=ShotPolicy.Goals[decision.action];goal.x*=mirror;chosen=true;
            }
            if(chosen&&!stationary)Controllers[index].Plan(World,index,bounced,goal);
            var a=World.Motors[0].PlayerPosition;var b=World.Motors[1].PlayerPosition;
            World.StepBoth(stationary?default:Controllers[0].Input(World,0),stationary?default:Controllers[1].Input(World,1));
            Travel[0]+=Vector3.Distance(a,World.Motors[0].PlayerPosition);Travel[1]+=Vector3.Distance(b,World.Motors[1].PlayerPosition);
            while(readContacts<World.Contacts.Count)
            {
                var c=World.Contacts[readContacts++];
                if(c.surface=="CourtSurface"&&c.point.z*side>0)bounced=true;
            }
        }
        public void Dispose()=>World.Dispose();
    }
}

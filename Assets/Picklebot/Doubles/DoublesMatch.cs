using System;
using System.Collections.Generic;
using UnityEngine;
namespace Picklebot.Doubles
{
    public sealed class DoublesMatch : IDisposable
    {
        public readonly DoublesWorld World;
        public readonly StrokeController[] Strokes={new(),new(),new(),new()};
        public int ActivePlayer {get;private set;}=-1;
        public int RallyNumber {get;private set;}
        public int CompletedRallies {get;private set;}
        public int[] PlayerHits=new int[4];
        public Vector2 Target {get;private set;}
        public bool CentreOnly=true;
        public bool AutoNext=true;
        public StrokeKind ForcedStroke=StrokeKind.Flat;
        public ContactModel ContactModel;
        public Vector2? TargetOverride;
        public Vector2 ServeJitter;
        public DoublesModels Models;
        public bool Learning,SampleActions;
        public readonly List<TeamDecision> Decisions=new();
        private TeamDecision currentDecision;
        public float LastDeadAt {get;private set;}=-1;
        private int previousHits=-1,previousContacts;
        private readonly System.Random random;
        public DoublesMatch(bool visible,int seed=950000) {random=new System.Random(seed);World=new DoublesWorld(visible);}
        public void Next()
        {World.ResetRally();previousHits=-1;previousContacts=0;ActivePlayer=-1;LastDeadAt=-1;RallyNumber++;Decisions.Clear();foreach(var s in Strokes)s.Reset();}
        public void Step()
        {
            var r=World.Rules;
            if(r.Dead)
            {
                if(LastDeadAt<0)LastDeadAt=World.Time;
                for(int i=0;i<4;i++){Strokes[i].Reset();Strokes[i].Step(World,i,World.Players[i].Position);}
                World.Simulate();
                if(World.Time-LastDeadAt>1&&r.ResolveRally())
                {
                    if(Learning&&Models!=null){Models.orange.Learn(Decisions,0,r.Winner);Models.blue.Learn(Decisions,1,r.Winner);Models.rallies++;}
                    CompletedRallies++;if(AutoNext&&r.GameWinner<0)Next();
                }
                return;
            }
            if(previousHits!=r.Hits)
            {
                previousHits=r.Hits;foreach(var s in Strokes)s.Reset();ActivePlayer=-1;
                Target=r.Phase==RallyPhase.AwaitServe?new Vector2(r.ServiceX(r.DesignatedReceiver),4.2f)+ServeJitter:TargetOverride??(
                    CentreOnly?new Vector2(0,3.4f):new Vector2((float)(random.NextDouble()*4.2-2.1),2.8f+(float)random.NextDouble()*2));
                currentDecision=null;
                if(r.Phase!=RallyPhase.AwaitServe&&Models!=null&&!CentreOnly)
                {
                    currentDecision=Models.ForTeam(r.ExpectedTeam).Choose(World,r.ExpectedTeam,random,SampleActions||Learning);
                    Decisions.Add(currentDecision);Target=TeamPolicy.Target(currentDecision.action);ForcedStroke=TeamPolicy.Kind(currentDecision.action);
                }
            }
            if(ActivePlayer<0)
            {
                if(r.Phase==RallyPhase.AwaitServe)ActivePlayer=r.Server;
                else if(r.Phase==RallyPhase.ServeFlight)ActivePlayer=r.DesignatedReceiver;
                else
                {
                    int a=r.ExpectedTeam*2,b=a+1;
                    bool pa=Strokes[a].Plan(World,a,Target),pb=Strokes[b].Plan(World,b,Target);
                    if(pa||pb)
                    {
                        float ca=Strokes[a].ImpactAt+.2f*Vector3.Distance(World.Players[a].Position,Strokes[a].Impact);
                        float cb=Strokes[b].ImpactAt+.2f*Vector3.Distance(World.Players[b].Position,Strokes[b].Impact);
                        ActivePlayer=!pb?a:!pa?b:ca<=cb?a:b;
                        Strokes[ActivePlayer^1].Reset();
                    }
                }
            }
            if(ActivePlayer>=0)
            {
                var stroke=Strokes[ActivePlayer];stroke.Kind=r.Phase==RallyPhase.AwaitServe?StrokeKind.Flat:ForcedStroke;
                if(r.Phase==RallyPhase.AwaitServe)new ContactParameters().Apply(stroke);
                if(ContactModel!=null&&r.Phase!=RallyPhase.AwaitServe)ContactModel.strokes[(int)stroke.Kind].Apply(stroke);
                if(currentDecision!=null&&currentDecision.player<0){currentDecision.player=ActivePlayer;stroke.Reset();}
                stroke.Plan(World,ActivePlayer,Target);
            }
            for(int i=0;i<4;i++)
            {
                int side=World.Players[i].Side;float x=(i%2==0?1.55f:-1.55f)*-side;
                if(ActivePlayer>=0&&i==(ActivePlayer^1))x=World.Players[ActivePlayer].Position.x>=0?-1.55f:1.55f;
                var recovery=new Vector3(x,0,side*(r.CanVolley?3.5f:6f));
                if(i==r.Server&&r.Phase==RallyPhase.AwaitServe)recovery=World.Players[i].Position;
                Strokes[i].Step(World,i,recovery);
            }
            World.Simulate();
            for(;previousContacts<World.Contacts.Count;previousContacts++)if(World.Contacts[previousContacts].player>=0)PlayerHits[World.Contacts[previousContacts].player]++;
        }
        public void Dispose()=>World.Dispose();
    }
}

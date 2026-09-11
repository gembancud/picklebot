using System;
using System.Collections.Generic;
using UnityEngine;

namespace Picklebot.Doubles
{
    public enum RallyPhase { AwaitServe, ServeFlight, ReturnFlight, Rally, Dead }
    public enum Fault { None, ServeFoot, ServeMotion, ServeLanding, WrongReceiver, EarlyVolley, KitchenVolley,
        KitchenMomentum, DoubleHit, SecondBounce, Out, WrongSide, BodyContact, NetTouch, Lost, Carry, ServeTimeout, PermanentObject }
    [Serializable] public sealed class RuleEvent
    {
        public float time;
        public string kind;
        public int player, winner;
        public Fault fault;
        public Vector3 position;
    }

    // Side-out doubles. Player IDs 0/1 are near; 2/3 are far.
    // Court positions are logical service positions, not movement restrictions.
    public sealed class DoublesRules
    {
        public const float HalfWidth=3.048f, HalfLength=6.7056f, Kitchen=2.1336f;
        public readonly int[] Score=new int[2];
        public readonly List<RuleEvent> Events=new();
        public RallyPhase Phase { get; private set; }
        public Fault LastFault { get; private set; }
        public int ServingTeam { get; private set; }
        public int Server { get; private set; }
        public int ServerNumber { get; private set; }
        public int DesignatedReceiver { get; private set; }
        public int ExpectedTeam { get; private set; }
        public int Winner { get; private set; }=-1;
        public int GameWinner { get; private set; }=-1;
        public int Hits { get; private set; }
        public bool Bounced { get; private set; }
        public bool CanVolley=>Phase==RallyPhase.Rally;
        public bool Dead=>Phase==RallyPhase.Dead;
        public string ScoreCall=>$"{Score[ServingTeam]}-{Score[1-ServingTeam]}-{ServerNumber}";
        private readonly int[] rightPlayer={0,2};
        private readonly bool[] kitchenOccupied=new bool[4], volleyPending=new bool[4], establishedOutside=new bool[4];
        private bool resolved;
        private int lastHitter=-1;
        public bool EstablishedOutside(int player) { Team(player);return establishedOutside[player]; }
        public bool VolleyMomentumPending(int player) { Team(player);return volleyPending[player]; }
        public static int Team(int player) { if(player<0||player>3)throw new ArgumentOutOfRangeException(nameof(player));return player/2; }
        public static int Side(int team)=>team==0?-1:1;
        public int RightPlayer(int team)=>rightPlayer[team];
        public bool IsRight(int player)=>rightPlayer[Team(player)]==player;
        public float ServiceX(int player)=>(IsRight(player)?1:-1)*-Side(Team(player))*HalfWidth*.5f;
        public DoublesRules():this(0) { }
        public DoublesRules(int initialServer,bool initialServerOnRight=true,int initialScore0=0,int initialScore1=0,int initialServerNumber=2,bool swapReceivingPlayers=false)
        {
            if(initialScore0<0||initialScore0>10||initialScore1<0||initialScore1>10||(initialServerNumber!=1&&initialServerNumber!=2))throw new ArgumentException("Practice reset requires unfinished scores 0..10 and service number 1 or 2.");
            Score[0]=initialScore0;Score[1]=initialScore1;
            ServingTeam=Team(initialServer);Server=initialServer;ServerNumber=initialServerNumber;
            if(swapReceivingPlayers)rightPlayer[1-ServingTeam]^=1;
            rightPlayer[ServingTeam]=initialServerOnRight?Server:Server^1;BeginRally();
        }
        public void BeginRally()
        {
            if(GameWinner>=0)throw new InvalidOperationException("The game is complete.");
            if(Phase==RallyPhase.Dead&&!resolved)throw new InvalidOperationException("Resolve the rally before service.");
            Phase=RallyPhase.AwaitServe;LastFault=Fault.None;Winner=-1;resolved=false;
            Hits=0;Bounced=false;lastHitter=-1;ExpectedTeam=1-ServingTeam;
            DesignatedReceiver=IsRight(Server)?rightPlayer[ExpectedTeam]:(rightPlayer[ExpectedTeam]^1);
            Events.Clear();Array.Clear(volleyPending,0,4);Array.Clear(kitchenOccupied,0,4);
            for(int i=0;i<4;i++)establishedOutside[i]=true;
        }
        private void Event(string kind,int player,float time,Vector3 p=default)=>Events.Add(new RuleEvent
            {kind=kind,player=player,time=time,position=p,winner=Winner,fault=LastFault});
        public void Fail(int losingTeam,Fault fault,float time,Vector3 p=default,int player=-1)
        {
            if(Dead)return;
            Winner=1-losingTeam;LastFault=fault;Phase=RallyPhase.Dead;Event("fault",player,time,p);
        }
        // Called with actual foot support and motion state. Do not clear a volley
        // momentum obligation because a fixed number of seconds has passed.
        public void Feet(int player,bool touchesKitchen,bool bothFeetOutside,bool balanceRecovered,float time)
        {
            Team(player);kitchenOccupied[player]=touchesKitchen;
            if(touchesKitchen)establishedOutside[player]=false;
            else if(bothFeetOutside)establishedOutside[player]=true;
            if(volleyPending[player]&&touchesKitchen&&!resolved)
            {
                if(Dead) {Winner=1-Team(player);LastFault=Fault.KitchenMomentum;Event("late volley fault",player,time);}
                else Fail(Team(player),Fault.KitchenMomentum,time,default,player);
            }
            if(bothFeetOutside&&balanceRecovered)volleyPending[player]=false;
        }
        // The caller must report measured serve facts. This supports a drop serve
        // without applying volley-serve height and upward-arc restrictions to it.
        public void Serve(int player,bool legalFeet,bool dropServe,bool legalRelease,bool bouncedBeforeHit,
            bool upwardArc,bool belowWaist,bool paddleBelowWrist,float time)
        {
            if(Phase!=RallyPhase.AwaitServe)return;
            if(player!=Server) {Fail(ServingTeam,Fault.WrongReceiver,time,default,player);return;}
            if(!legalFeet) {Fail(ServingTeam,Fault.ServeFoot,time,default,player);return;}
            if(!legalRelease||(dropServe?!bouncedBeforeHit:(!upwardArc||!belowWaist||!paddleBelowWrist)))
            {Fail(ServingTeam,Fault.ServeMotion,time,default,player);return;}
            Phase=RallyPhase.ServeFlight;lastHitter=player;Hits=1;Event("serve",player,time);
        }
        // Explicit prototype variant: stationary support replaces release/motion
        // requirements. Server identity, feet, landing and rally rules remain active.
        public void FixedBallServe(int player,bool legalFeet,float time)
        {
            if(Phase!=RallyPhase.AwaitServe)return;
            if(player!=Server){Fail(ServingTeam,Fault.WrongReceiver,time,default,player);return;}
            if(!legalFeet){Fail(ServingTeam,Fault.ServeFoot,time,default,player);return;}
            Phase=RallyPhase.ServeFlight;lastHitter=player;Hits=1;Event("serve",player,time);
        }
        public void Hit(int player,float time,Vector3 position=default,bool continuousSingleDirectionStroke=false)
        {
            if(Dead||Phase==RallyPhase.AwaitServe)return;
            int team=Team(player);
            if(player==lastHitter&&continuousSingleDirectionStroke) {Event("continuous contact",player,time,position);return;}
            if(team!=ExpectedTeam) {Fail(team,Fault.DoubleHit,time,position,player);return;}
            if(Phase==RallyPhase.ServeFlight&&player!=DesignatedReceiver)
            {Fail(team,Fault.WrongReceiver,time,position,player);return;}
            if(!Bounced&&!CanVolley) {Fail(team,Fault.EarlyVolley,time,position,player);return;}
            if(!Bounced&&(kitchenOccupied[player]||!establishedOutside[player]))
            {Fail(team,Fault.KitchenVolley,time,position,player);return;}
            if(!Bounced)volleyPending[player]=true;
            if(Phase==RallyPhase.ServeFlight)Phase=RallyPhase.ReturnFlight;
            else if(Phase==RallyPhase.ReturnFlight)Phase=RallyPhase.Rally;
            Bounced=false;lastHitter=player;ExpectedTeam=1-team;Hits++;Event("hit",player,time,position);
        }
        public void Bounce(Vector3 contact,float time)
        {
            if(Dead||Phase==RallyPhase.AwaitServe)return;
            int hitterTeam=Team(lastHitter);
            if(Mathf.Abs(contact.x)>HalfWidth||Mathf.Abs(contact.z)>HalfLength)
            {Fail(Bounced?ExpectedTeam:hitterTeam,Fault.Out,time,contact);return;}
            int landing=contact.z<0?0:1;
            if(landing!=ExpectedTeam) {Fail(Bounced?ExpectedTeam:hitterTeam,Fault.WrongSide,time,contact);return;}
            if(Bounced) {Fail(ExpectedTeam,Fault.SecondBounce,time,contact);return;}
            if(Phase==RallyPhase.ServeFlight && (Mathf.Abs(contact.z)<=Kitchen || contact.x*ServiceX(DesignatedReceiver)<0))
            {Fail(ServingTeam,Fault.ServeLanding,time,contact);return;}
            Bounced=true;Event("bounce",-1,time,contact);
        }
        public void BodyContact(int player,float time)=>Fail(Team(player),Fault.BodyContact,time,default,player);
        public void TouchNet(int player,float time)=>Fail(Team(player),Fault.NetTouch,time,default,player);
        public void Lost(float time)=>Fail(Bounced?ExpectedTeam:Team(lastHitter<0?Server:lastHitter),Fault.Lost,time);
        public void PermanentObject(float time)=>Fail(Bounced?ExpectedTeam:Team(lastHitter<0?Server:lastHitter),Fault.PermanentObject,time);
        public void Truncate(float time) {if(Dead)return;Winner=-1;LastFault=Fault.None;Phase=RallyPhase.Dead;Event("training time limit - no point",-1,time);}
        // Resolve only after volley momentum is settled. Repeated calls are safe.
        public bool ResolveRally()
        {
            if(!Dead||resolved)return false;
            for(int i=0;i<4;i++)if(volleyPending[i])return false;
            resolved=true;
            if(Winner<0)return true;
            if(Winner==ServingTeam)
            {
                Score[ServingTeam]++;rightPlayer[ServingTeam]^=1;
                if(Score[ServingTeam]>=11&&Score[ServingTeam]-Score[1-ServingTeam]>=2)GameWinner=ServingTeam;
            }
            else if(ServerNumber==1) {ServerNumber=2;Server^=1;}
            else {ServingTeam=1-ServingTeam;ServerNumber=1;Server=rightPlayer[ServingTeam];}
            return true;
        }
    }
}

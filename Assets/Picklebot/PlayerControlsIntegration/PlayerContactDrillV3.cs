using System;
using System.Collections.Generic;
using System.Linq;
using Picklebot.PlayerControls;
using UnityEngine;
namespace Picklebot.PlayerControlsIntegration
{
    public sealed class PlayerContactDrillV3:IDisposable
    {
        public const string Version="player-v3-grounded-drills-27-local-patterns";
        public readonly PlayerLearningMatchV3 Match;
        public readonly int Player,Seed;
        public readonly bool ServeFromLeft;
        public readonly bool Cooperative;
        public readonly float MovementRange,MovementTiming,MovementStartVariation;
        public bool MovementFeed=>MovementRange>=0;
        public readonly string MovementPattern;
        public readonly float MovementPositionRewardScale;
        private PlayerMovementPositionRewardV3 movementPositionReward;
        public readonly bool MovementForwardProgressRewardEnabled;
        private readonly PlayerMovementFlightRewardV3 movementForwardProgress;
        public float MovementForwardProgressReward=>movementForwardProgress?.TotalReward??0;
        public int MovementForwardProgressRewardedSteps=>movementForwardProgress?.RewardedSteps??0;
        public float MovementPositionReward=>movementPositionReward?.TotalReward??0;
        private Vector3[] initialRoots,previousRoots;
        public float[] TravelBeforeContact {get;private set;}
        public float ContactDisplacement {get;private set;}=-1;
        public float ContactDistanceFromStart {get;private set;}=-1;
        private static float PlanarDistance(Vector3 a,Vector3 b)=>Vector2.Distance(new Vector2(a.x,a.z),new Vector2(b.x,b.z));
        public int Hitter {get;private set;}=-1;
        public readonly bool RandomMatchContext;
        public readonly int? RallyServer;
        public readonly bool RallyServerOnRight;
        public readonly string Task;
        public readonly float FeedDifficulty,FeedLowering,FeedLateralOffset,InitialHoldLift;
        public float FaceContactBallHeight {get;private set;}=-1;
        public bool IncomingServeLanded {get;private set;}
        public bool FaceContact {get;private set;}
        public bool ContactWasVolley {get;private set;}
        public static bool IsRallyFeed(string task)=>task=="rally-air-feed"||task=="rally-bounce-feed";
        public bool Released=>!Match.BallHeld;
        public bool DropBounced=>Match.World.ServeBounced;
        public bool ServeAccepted {get;private set;}
        public int ReleaseTick {get;private set;}=-1;
        private int contactCursor;
        private bool bounceRewarded;
        private bool directionRewardPending;
        public float ServeDirectionReward {get;private set;}
        public int ServeDirectionRewardTick {get;private set;}=-1;
        public float ServeLandingReward {get;private set;}
        public int ServeLandingRewardTick {get;private set;}=-1;
        public float ReleaseHeight=>Match.ReleasePosition?.y??-1;
        public float ReleaseLift=>Match.ReleasePosition.HasValue?Match.ReleaseHandLift:-1;
        private float faceTime=-1;
        public static bool IsDropTask(string task)=>task=="drop-serve"||task=="drop-contact";
        public static bool IsFixedServeTask(string task)=>task=="stationary-serve"||task=="stationary-serve-contact";
        public static bool IsServeTask(string task)=>IsDropTask(task)||IsFixedServeTask(task);
        private bool FlightTask=>Task=="stationary-flight"||Task=="reaction-return"||Task=="near-return"||Task=="easy-return"||Task=="varied-return"||Task=="low-return"||IsServeTask(Task);
        public bool NetCrossed {get;private set;}
        public bool Done {get;private set;}
        public string Outcome {get;private set;}
        public float Reward {get;private set;}
        public float FaceContactTime => faceTime;
        private float distance;
        private PlayerReturnProgressV3 returnProgress;
        private PlayerDropApproachV3 dropApproach;
        private readonly HashSet<string> bodySurfaces;
        public static bool ValidTask(string task)=>IsRallyFeed(task)||(task=="receive-serve"||task=="receive-feed")||task=="stationary-flight"||IsFixedServeTask(task)||(task=="stationary-contact"||task=="falling-contact")||task=="contact"||task=="reaction-contact"||task=="reaction-return"||task=="near-return"||task=="easy-return"||task=="varied-return"||task=="low-return"||IsDropTask(task);
        public static bool[] ActionMask(int seat,int learner,string task="contact",bool cooperative=false)
        {if(!ValidTask(task))throw new ArgumentException("Unknown drill task.");var mask=new bool[PlayerActionV3.Count];if(seat==learner||cooperative&&seat/2==learner/2)for(int i=0;i<PlayerActionV3.Count;i++)mask[i]=i!=4&&(i!=16||IsDropTask(task));return mask;}
        public PlayerContactDrillV3(int seed,int player,string task="contact",float maximumReturnDifficulty=1,float feedLowering=0,float feedLateralOffset=0,float initialHoldLift=0,bool serveFromLeft=false,int? rallyServer=null,bool rallyServerOnRight=true,int? matchContextSeed=null,bool cooperative=false,float movementRange=-1,float movementTiming=0,float movementStartVariation=0,float movementPositionReward=0,string movementPattern="court",bool movementForwardProgressReward=false)
        {
            if(player<0||player>3)throw new ArgumentOutOfRangeException(nameof(player));
            if(cooperative&&!IsRallyFeed(task)&&task!="receive-feed"&&!IsFixedServeTask(task))throw new ArgumentException("Paired practice supports fixed serves, opening feeds and rally feeds.");
            Cooperative=cooperative;
            if(!float.IsFinite(movementRange)||(movementRange!=-1&&(movementRange<0||movementRange>1))||!float.IsFinite(movementTiming)||movementTiming<0||movementTiming>1||!float.IsFinite(movementStartVariation)||movementStartVariation<0||movementStartVariation>1)throw new ArgumentOutOfRangeException("Invalid movement reset fractions.");
            if(movementRange>=0&&!IsRallyFeed(task)||movementRange<0&&(movementTiming!=0||movementStartVariation!=0))throw new ArgumentException("Movement reset requires an explicit rally feed.");
            if(movementForwardProgressReward&&(cooperative||movementRange<=0||!IsRallyFeed(task)))
                throw new ArgumentException("Forward flight reward requires a solo positive-range movement rally feed.");
            MovementForwardProgressRewardEnabled=movementForwardProgressReward;
            if(movementForwardProgressReward)movementForwardProgress=new PlayerMovementFlightRewardV3();
            PlayerMovementPositionRewardV3.ValidateBudget(movementPositionReward);
            if(movementPositionReward>0&&(movementRange<=0||!IsRallyFeed(task)||cooperative))throw new ArgumentException("Position reward requires a solo movement challenge.");
            PlayerMovementPatternV3.Validate(movementPattern,movementRange,!cooperative&&IsRallyFeed(task)&&movementRange>=0);
            MovementPattern=movementPattern;MovementPositionRewardScale=movementPositionReward;
            MovementRange=movementRange;MovementTiming=movementTiming;MovementStartVariation=movementStartVariation;
            if(!((seed>=1000000&&seed<1100000)||(seed>=1100000&&seed<1200000)||(seed>=1300000&&seed<1400000)))
                throw new ArgumentException("Drills cannot consume final-evaluation seeds.");
            if(!ValidTask(task))throw new ArgumentException("Unknown drill task.");
            if(float.IsNaN(maximumReturnDifficulty)||maximumReturnDifficulty<0||maximumReturnDifficulty>1)throw new ArgumentOutOfRangeException(nameof(maximumReturnDifficulty));
            if(!float.IsFinite(feedLowering)||feedLowering<0||feedLowering>.9f)throw new ArgumentOutOfRangeException(nameof(feedLowering));
            if(!float.IsFinite(feedLateralOffset)||Mathf.Abs(feedLateralOffset)>.9f)throw new ArgumentOutOfRangeException(nameof(feedLateralOffset));
            if(!float.IsFinite(initialHoldLift)||initialHoldLift<0||initialHoldLift>140||(!IsDropTask(task)&&initialHoldLift!=0))throw new ArgumentOutOfRangeException(nameof(initialHoldLift));
            if(serveFromLeft&&!IsFixedServeTask(task))throw new ArgumentException("Left service reset requires a fixed serve task.");
            if(rallyServer.HasValue&&((task!="stationary-flight"&&task!="receive-serve"&&task!="receive-feed")||rallyServer.Value<0||rallyServer.Value>3)||!rallyServer.HasValue&&!rallyServerOnRight)throw new ArgumentException("Rally context requires stationary-flight and an explicit valid server.");
            RallyServer=rallyServer;RallyServerOnRight=rallyServerOnRight;RandomMatchContext=matchContextSeed.HasValue;
            if(matchContextSeed.HasValue&&task!="receive-serve"&&task!="receive-feed"&&!IsFixedServeTask(task)&&!(task=="stationary-flight"&&rallyServer.HasValue))throw new ArgumentException("Match-state practice requires a fixed serve or explicit rally-context flight reset.");
            ServeFromLeft=serveFromLeft;
            InitialHoldLift=initialHoldLift;
            FeedLowering=task=="low-return"||(task=="stationary-contact"||task=="falling-contact")?feedLowering:0;
            FeedLateralOffset=task=="low-return"||(task=="stationary-contact"||task=="falling-contact")?feedLateralOffset:0;
            // Independent reset RNG: preserve existing feed draws and sample all seats equally.
            var feedRandom=new System.Random(seed^0x5b72a91);
            FeedDifficulty=(task=="receive-feed"||IsRallyFeed(task))?maximumReturnDifficulty:task=="stationary-flight"?maximumReturnDifficulty:task=="easy-return"||task=="low-return"?0:task=="varied-return"?(feedRandom.NextDouble()<.25?0:(float)feedRandom.NextDouble()*maximumReturnDifficulty):1;
            int server=rallyServer??((task=="receive-serve"||task=="receive-feed")?((player^2)^((seed/8)%2)):IsServeTask(task)?player:0);
            bool serverRight=rallyServer.HasValue?rallyServerOnRight:!serveFromLeft;
            if((task=="receive-serve"||task=="receive-feed")){
                if(server/2==player/2)throw new ArgumentException("Receive practice needs an opposing server.");
                bool swapped=false;
                if(matchContextSeed.HasValue){var context=new System.Random(unchecked(matchContextSeed.Value^0x17c9b43));context.Next(11);context.Next(11);context.Next(2);swapped=context.Next(2)==1;}
                serverRight=(player%2==0)^swapped;
            }
            Player=player;Seed=seed;Task=task;Match=new PlayerLearningMatchV3(false,server,initialHoldLift,serverRight,matchContextSeed);
            try
            {
            if(IsRallyFeed(task)) {
                Match.InitializeRallyFeed(player,seed,FeedDifficulty,task=="rally-air-feed",cooperative&&!MovementFeed);
                if(MovementFeed)Match.InitializeMovementRallyFeed(player,seed,task=="rally-air-feed",cooperative,movementRange,movementTiming,movementStartVariation,movementPattern);
            }
            else if(task=="receive-feed")Match.InitializeReceiveFeed(player,seed,FeedDifficulty);
            else if(IsFixedServeTask(task)||task=="receive-serve")Match.InitializeStationaryServe();
            else if(!IsDropTask(task))Match.InitializeContactDrill(player,seed,task,FeedDifficulty,FeedLowering,FeedLateralOffset,rallyServer.HasValue);
            if((task=="receive-serve"||task=="receive-feed")&&Match.World.Rules.DesignatedReceiver!=player)throw new InvalidOperationException("Receiver reset mismatch.");
            bodySurfaces=new HashSet<string>(Match.World.Players.SelectMany(p=>p.Root.GetComponentsInChildren<Collider>()).Select(c=>c.name));distance=Distance();
            if(MovementFeed){initialRoots=Match.World.Players.Select(p=>p.Position).ToArray();previousRoots=(Vector3[])initialRoots.Clone();TravelBeforeContact=new float[4];}
            if(movementPositionReward>0){var body=Match.World.Players[Player];this.movementPositionReward=new PlayerMovementPositionRewardV3(body.Position,body.Paddle.position+body.Paddle.rotation*PlayerStrokeAimV3.FacePoint,movementPositionReward);}
            }
            catch { Match.Dispose(); throw; }
        }
        private float Distance()
        {var body=Match.World.Players[Player];return Vector3.Distance(Match.World.Ball.position,body.Paddle.position+body.Paddle.rotation*PlayerStrokeAimV3.FacePoint);}
        public void Step()
        {
            if(Done)throw new InvalidOperationException("Drill is terminal.");Reward=0;
            try{if(!Match.StepAgents()){Finish("infeasible",-1);return;}}
            catch(Exception){Finish("exception",-1);return;}
            if(MovementFeed&&!FaceContact)for(int i=0;i<4;i++){var root=Match.World.Players[i].Position;TravelBeforeContact[i]+=PlanarDistance(root,previousRoots[i]);previousRoots[i]=root;}
            if(IsRallyFeed(Task)){StepRallyFeed();return;}
            if(Task=="receive-serve"||Task=="receive-feed"){StepReceiveServe();return;}
            // These one-time curriculum bonuses encourage discovering safe drops.
            // They do not count as serve success and cannot be farmed within a rally.
            if(IsDropTask(Task)&&Released&&ReleaseTick<0){ReleaseTick=Match.Tick;Reward+=.05f;}
            if(IsDropTask(Task)&&DropBounced&&!bounceRewarded){bounceRewarded=true;Reward+=.05f;}
            float next=Distance();
            if(Task=="stationary-flight"||Task=="drop-contact"||IsFixedServeTask(Task)||(Task=="stationary-contact"||Task=="falling-contact"))
            {
                // Measured proximity only after the real drop bounce. Each new
                // closest absolute distance pays once, including the first bounce
                // sample; starting farther away cannot increase the bonus.
                if((Task=="stationary-flight"||DropBounced||IsFixedServeTask(Task)||(Task=="stationary-contact"||Task=="falling-contact"))&&!FaceContact)
                {
                    if(dropApproach==null)dropApproach=new PlayerDropApproachV3(next);
                    Reward+=dropApproach.Advance(next);
                }
            }
            else if(!FaceContact)Reward+=.05f*(Mathf.Min(distance,2)-Mathf.Min(next,2));
            distance=next;
            var contacts=Match.World.Contacts.Skip(contactCursor).ToArray();
            contactCursor=Match.World.Contacts.Count;
            if(contacts.Any(c=>bodySurfaces.Contains(c.surface)||c.surface=="NonContactHandle")){Finish("body_or_handle",-1);return;}
            if(contacts.Any(c=>c.player>=0&&c.player!=Player)){Finish("other_player",-1);return;}
            var rules=Match.World.Rules;
            if(!FaceContact&&contacts.Any(c=>c.player==Player&&c.surface=="RoundedHittingFace"))
            {
                FaceContact=true;Hitter=Player;faceTime=Match.World.Time;FaceContactBallHeight=Match.World.Ball.position.y;
                if(Task=="stationary-flight"||Task=="stationary-serve"||Task=="easy-return"||Task=="varied-return"||Task=="low-return")returnProgress=new PlayerReturnProgressV3(Match.World.Ball.position.z*(Player<2?1:-1));
                ServeAccepted=IsServeTask(Task)&&rules.Events.Any(e=>e.kind=="serve"&&e.time>0);
                if(Task=="stationary-serve-contact")
                {
                    bool accepted=ServeAccepted&&!rules.Dead;
                    Finish(accepted?"fixed_serve_contact":"rule_terminal",accepted?1:-1);return;
                }
                if(Task=="drop-contact")
                {
                    bool accepted=Released&&DropBounced&&ServeAccepted&&!rules.Dead;
                    Finish(accepted?"serve_contact":"rule_terminal",accepted?1:-1);return;
                }
                if(!FlightTask){Finish("face_contact",1);return;}
                // Keep contact learning worthwhile while the actor discovers forward flight.
                // Only measured flight earns further progress; landing still decides success.
                if(!IsServeTask(Task)||ServeAccepted)Reward+=Task=="stationary-serve"?1f:.25f;
                if(Task=="stationary-serve"&&ServeAccepted)directionRewardPending=true;
            }
            // PhysX can finish the contact impulse after its first Enter callback.
            // Sample the outgoing ball once separation is observed, not mid-contact.
            if(directionRewardPending&&!Match.World.IsPaddleContactActive(Player))
            {
                ServeDirectionReward=PlayerServeDirectionV3.ContactReward(Match.World.Ball.linearVelocity.z*(Player<2?1:-1));
                ServeDirectionRewardTick=Match.Tick;Reward+=ServeDirectionReward;directionRewardPending=false;
            }
            if(FaceContact&&Match.World.Ball.position.z*(Player<2?1:-1)>0)NetCrossed=true;
            // Bounded, non-repeatable feedback from actual post-hit flight.
            // No paddle targets or ball impulses are generated by this reward.
            if(returnProgress!=null)Reward+=returnProgress.Advance(Match.World.Ball.position.z*(Player<2?1:-1));
            // A failed flight task has the same terminal loss for a miss, bad
            // landing, rule fault or body contact. Contact/drop bonuses remain
            // bounded curriculum feedback; success still requires a legal landing.
            bool floor=contacts.Any(c=>c.surface=="CourtSurface"||c.surface=="OutCatchFloor");
            if(floor&&(!IsServeTask(Task)||FaceContact))
            {
                if(Task=="stationary-serve"&&FaceContact&&ServeAccepted)
                {
                    var landing=contacts.First(c=>c.surface=="CourtSurface"||c.surface=="OutCatchFloor");
                    ServeLandingReward=PlayerServeLandingV3.ContactReward(landing.point,Player,rules.ServiceX(rules.DesignatedReceiver));
                    ServeLandingRewardTick=Match.Tick;Reward+=ServeLandingReward;
                }
                // A real accepted bounce after the hit is required. A drop bounce,
                // or a time-zero synthetic contact-drill event, cannot count as a return.
                bool legal=FaceContact&&NetCrossed&&!rules.Dead
                    &&(!IsServeTask(Task)||ServeAccepted)
                    &&rules.Events.Any(e=>e.kind=="bounce"&&e.time>faceTime&&e.position.z*(Player<2?1:-1)>0);
                Finish(legal?(IsServeTask(Task)?"legal_serve":"legal_return"):FaceContact?"bad_return":"miss",legal?1:(FlightTask||Task=="falling-contact")?-1f:0);return;
            }
            if(rules.Dead){Finish("rule_terminal",(FlightTask||Task=="falling-contact")?-1f:0);return;}
            int limit=IsServeTask(Task)||(Task=="stationary-contact"||Task=="falling-contact")?1200:FlightTask?960:360;
            if(Match.Tick>=limit)Finish("time_limit",FlightTask||(Task=="stationary-contact"||Task=="falling-contact")?-1f:0);
        }

        private void StepRallyFeed()
        {
            var rules=Match.World.Rules;
            var contacts=Match.World.Contacts.Skip(contactCursor).ToArray();contactCursor=Match.World.Contacts.Count;
            int hitter=contacts.Where(c=>c.player>=0&&(c.player==Player||Cooperative&&c.player/2==Player/2)&&c.surface=="RoundedHittingFace").Select(c=>c.player).DefaultIfEmpty(-1).First();
            if(!FaceContact&&!rules.Dead&&rules.Phase==Picklebot.Doubles.RallyPhase.Rally&&hitter>=0) {
                FaceContact=true;Hitter=hitter;faceTime=Match.World.Time;FaceContactBallHeight=Match.World.Ball.position.y;
                if(MovementFeed){ContactDisplacement=PlanarDistance(initialRoots[hitter],Match.World.Players[hitter].Position);ContactDistanceFromStart=PlanarDistance(initialRoots[hitter],Match.World.Ball.position);}
                ContactWasVolley=!rules.Events.Any(e=>e.kind=="bounce"&&e.time>0&&e.time<=faceTime);
                Reward+=.25f;
            }
            if(FaceContact&&Match.World.Ball.position.z*(Player<2?1:-1)>0)NetCrossed=true;
            // Root-only feedback ends at the first accepted face contact or any rule fault.
            if(movementPositionReward!=null&&!FaceContact&&!rules.Dead)Reward+=movementPositionReward.Advance(Match.World.Players[Player].Position,Match.World.Ball.position);
            bool legalLanding=FaceContact&&NetCrossed&&rules.Events.Any(e=>e.kind=="bounce"&&e.time>faceTime&&e.position.z*(Player<2?1:-1)>0);
            // Reward accounting only: actual flight after an accepted face contact.
            // The first legal landing closes this signal even if volley momentum
            // keeps the physical drill alive; later faults still determine success.
            if(movementForwardProgress!=null)Reward+=movementForwardProgress.Advance(
                Match.World.Ball.position.z*(Player<2?1:-1),FaceContact,rules.Dead,Done||Match.Tick>=7200,legalLanding);
            if(rules.Dead&&rules.Winner!=Player/2){Finish("receive_fault",-1);return;}
            // A legal landing cannot erase an outstanding volley-momentum duty.
            // Continue physical stepping until balance returns or a fault occurs.
            if(legalLanding&&!Enumerable.Range(0,4).Any(i=>(i==Player||Cooperative&&i/2==Player/2)&&rules.VolleyMomentumPending(i))){Finish("legal_return",1);return;}
            if(rules.Dead&&!legalLanding){Finish("opponent_fault",0);return;}
            if(Match.Tick>=7200)Finish("time_limit",-1);
        }

        private void StepReceiveServe()
        {
            var rules=Match.World.Rules;
            var contacts=Match.World.Contacts.Skip(contactCursor).ToArray();contactCursor=Match.World.Contacts.Count;
            if(rules.Phase==Picklebot.Doubles.RallyPhase.ServeFlight&&rules.Bounced)IncomingServeLanded=true;
            if(Task!="receive-feed"&&IncomingServeLanded&&!FaceContact){float next=Distance();if(dropApproach==null)dropApproach=new PlayerDropApproachV3(next);Reward+=dropApproach.Advance(next);}
            if(!FaceContact&&contacts.Any(c=>c.player==Player&&c.surface=="RoundedHittingFace")&&!rules.Dead&&rules.Phase==Picklebot.Doubles.RallyPhase.ReturnFlight){
                FaceContact=true;Hitter=Player;faceTime=Match.World.Time;FaceContactBallHeight=Match.World.Ball.position.y;Reward+=.25f;
            }
            if(FaceContact&&Match.World.Ball.position.z*(Player<2?1:-1)>0)NetCrossed=true;
            if(FaceContact&&NetCrossed&&!rules.Dead&&rules.Events.Any(e=>e.kind=="bounce"&&e.time>faceTime&&e.position.z*(Player<2?1:-1)>0)){Finish("legal_return",1);return;}
            if(rules.Dead){bool learnerLost=rules.Winner!=Player/2;Finish(learnerLost?"receive_fault":"opponent_fault",learnerLost?-1:0);return;}
            if(Match.Tick>=7200)Finish("time_limit",-1);
        }

        private void Finish(string outcome,float reward){movementForwardProgress?.Stop();Done=true;Outcome=outcome;Reward+=reward;}
        public void Dispose()=>Match.Dispose();
    }
}

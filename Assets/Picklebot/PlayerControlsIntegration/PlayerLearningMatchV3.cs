using System;
using System.Linq;
using Picklebot.Doubles;
using Picklebot.PlayerControls;
using UnityEngine;
namespace Picklebot.PlayerControlsIntegration
{
    public sealed class StationaryResetOverlapException : ArgumentException
    {
        public string Surface { get; }
        public StationaryResetOverlapException(string surface) : base("Stationary ball reset overlaps "+surface) { Surface=surface; }
    }
    // Learning-facing physical environment. No serve skill, swing helper or ball planner.
    public sealed class PlayerLearningMatchV3:IDisposable
    {
        public readonly DoublesWorld World;
        public PlayerControlWorldV3 Controls {get;private set;}
        public int Tick {get;private set;}
        public int TotalTicks {get;private set;}
        public int RallyIndex {get;private set;}
        public bool BallHeld {get;private set;}=true;
        public bool StationarySupportActive {get;private set;}
        public string Failure {get;private set;}
        public Vector3? ReleasePosition {get;private set;}
        public float ReleaseHandLift {get;private set;}
        private readonly PlayerActionV3[] active=new PlayerActionV3[4];
        public PlayerActionV3 ActiveFor(int i)=>active[i];
        public PlayerLearningMatchV3(bool visible=false):this(visible,0) { }
        public PlayerLearningMatchV3(bool visible,int initialServer,float initialHoldLift=0,bool initialServerOnRight=true,int? matchContextSeed=null)
        {
            if(initialServer<0||initialServer>3||!float.IsFinite(initialHoldLift)||initialHoldLift<0||initialHoldLift>140)throw new ArgumentException("Bounded server reset pose required.");
            // Separate reset RNG leaves ball-feed draws unchanged. Scores and roles are
            // actual rule state, never observation-only replacements.
            var context=matchContextSeed.HasValue?new System.Random(unchecked(matchContextSeed.Value^0x17c9b43)):null;
            int score0=context?.Next(11)??0,score1=context?.Next(11)??0,number=context==null?2:1+context.Next(2);
            bool swap=context!=null&&context.Next(2)==1;
            World=new DoublesWorld(visible,initialServer,initialServerOnRight,score0,score1,number,swap);
            var handAngles=new float[4];handAngles[initialServer]=initialHoldLift;
            Controls=new PlayerControlWorldV3(World.Players.Select(p=>p.Position).ToArray(),handAngles);
            for(int i=0;i<4;i++)Apply(i,true);
            World.Ball.isKinematic=true;World.Ball.detectCollisions=false;HoldBall();
        }
        // Called only between rallies. ResolveRally retains the physical volley-
        // momentum obligation; an unsettled or completed game cannot be reset.
        public bool TryResetRally(Action onResolved=null)
        {
            if(Failure!=null)throw new InvalidOperationException("Failed episode: "+Failure);
            if(!World.Rules.Dead||World.Rules.GameWinner>=0)return false;
            if(!World.Rules.ResolveRally())return false;
            // Terminal learning snapshots include committed scores, before physical reset.
            // This callback also runs for the game-winning rally.
            onResolved?.Invoke();
            if(World.Rules.GameWinner>=0)return false;
            World.Ball.isKinematic=false;World.Ball.detectCollisions=true;
            World.ResetRally();
            Controls=new PlayerControlWorldV3(World.Players.Select(p=>p.Position).ToArray());
            Array.Clear(active,0,4);Decisions?.Reset();Tick=0;RallyIndex++;
            for(int i=0;i<4;i++)Apply(i,true);
            ReleasePosition=null;ReleaseHandLift=0;BallHeld=true;World.Ball.isKinematic=true;World.Ball.detectCollisions=false;HoldBall();
            if(World.FixedBallServe)ResetStationaryServe();
            return true;
        }
        public PlayerDecisionLoopV3 Decisions {get;private set;}
        public void AttachPolicies(IPlayerPolicyV3[] policies,int seed)
        {
            if(Tick!=0||Decisions!=null)throw new InvalidOperationException("Attach four private policies before stepping.");
            Decisions=new PlayerDecisionLoopV3(policies,seed);
        }
        public bool StepAgents()
        {
            if(Failure!=null)throw new InvalidOperationException("Failed episode: "+Failure);
            if(Decisions==null)throw new InvalidOperationException("No policies attached.");
            try
            {
                Decisions.Step((player,tick)=>PlayerObservationV3.Capture(this,player,tick),Tick);
                return Step(Enumerable.Range(0,4).Select(Decisions.ActionFor).ToArray());
            }
            catch(Exception error){Failure=error.GetType().Name+": "+error.Message;throw;}
        }
        // Curriculum reset: a feeder supplies an incoming ball before its first
        // bounce. The serve event establishes receiver eligibility, but no bounce
        // or hit is fabricated. Every subsequent trajectory/contact is physical.
        public void InitializeReceiveFeed(int player, int seed, float difficulty)
        {
            if(Tick!=0||Decisions!=null||!BallHeld||player!=World.Rules.DesignatedReceiver)
                throw new InvalidOperationException("Receive feed requires a fresh designated receiver.");
            if(!float.IsFinite(difficulty)||difficulty<0||difficulty>1)throw new ArgumentOutOfRangeException(nameof(difficulty));
            var random=new System.Random(unchecked(seed^0x2b84d91));
            var forward=player<2?Vector3.forward:Vector3.back;
            var right=player<2?Vector3.right:Vector3.left;
            var body=World.Players[player];
            var face=body.Paddle.position+body.Paddle.rotation*PlayerStrokeAimV3.FacePoint;
            float lateral=((float)random.NextDouble()*2-1)*.70f*difficulty;
            float depth=((float)random.NextDouble()*2-1)*.45f*difficulty;
            var position=face+forward*(1.15f+depth)+right*lateral;
            position.y=1.8f;
            // Keep the feed in the actual diagonal service box. This is reset
            // geometry, not a runtime movement target exposed to the policy.
            float sign=Mathf.Sign(World.Rules.ServiceX(player));
            position.x=sign*Mathf.Clamp(position.x*sign,.25f,DoublesRules.HalfWidth-.25f);
            World.Rules.FixedBallServe(World.Rules.Server,true,0);
            BallHeld=false;World.Ball.isKinematic=false;World.Ball.detectCollisions=true;
            World.Ball.position=position;World.Ball.transform.position=position;
            World.Ball.linearVelocity=-forward*(1.5f+((float)random.NextDouble()*2-1)*.35f*difficulty)+Vector3.down*6;
            World.Ball.angularVelocity=Vector3.zero;World.Ball.WakeUp();
        }

        // Reset-only rally feeds. Synthetic opening history establishes volley
        // eligibility; all incoming bounces and subsequent contacts are physical.
        public int RallyFeedLane {get;private set;}=-1;
        public void InitializeRallyFeed(int player,int seed,float difficulty,bool airborne,bool paired=false)
        {
            if(!float.IsFinite(difficulty)||difficulty<0||difficulty>1)throw new ArgumentOutOfRangeException(nameof(difficulty));
            InitializeContactDrill(player,seed,"stationary-flight",0,generalizedRallyContext:true,movePartner:paired);
            StationarySupportActive=false;
            var body=World.Players[player];
            var face=body.Paddle.position+body.Paddle.rotation*PlayerStrokeAimV3.FacePoint;
            var forward=player<2?Vector3.forward:Vector3.back;
            var right=player<2?Vector3.right:Vector3.left;
            var rng=new System.Random(unchecked(seed^0x3c17a29));
            if(paired) {RallyFeedLane=rng.Next(3);face.x=(player<2?1:-1)*(RallyFeedLane-1)*DoublesRules.HalfWidth*.5f;}
            float lateral=((float)rng.NextDouble()*2-1)*.5f*difficulty;
            float depth=((float)rng.NextDouble()*2-1)*.35f*difficulty;
            var position=face+forward*(1.15f+depth)+right*lateral;
            Vector3 velocity;
            if(airborne) {
                position.y=face.y+.2f;
                float flight=paired?.9f:.65f;
                // Ballistic reset estimate only; never used to command a player.
                var target=face+right*lateral;
                velocity=(target-position)/flight-World.Configuration.Gravity*(.5f*flight);
            } else {
                position.y=1.8f;
                velocity=-forward*(1.5f+((float)rng.NextDouble()*2-1)*.35f*difficulty)+Vector3.down*6;
            }
            position.x=Mathf.Clamp(position.x,-DoublesRules.HalfWidth+.15f,DoublesRules.HalfWidth-.15f);
            World.Ball.position=position;World.Ball.transform.position=position;
            World.Ball.linearVelocity=velocity;World.Ball.angularVelocity=Vector3.zero;World.Ball.WakeUp();
        }

        public int MovementRegion {get;private set;}=-1;
        public Vector3 MovementNominalPoint {get;private set;}
        // Feeder/reset metadata only. Neither field is included in actor observations.
        public void InitializeMovementRallyFeed(int player,int seed,bool airborne,bool paired,float range,float timing,float startVariation,string pattern="court")
        {
            if(Tick!=0||Decisions!=null||BallHeld||StationarySupportActive)throw new InvalidOperationException("Movement variation requires a freshly initialized dynamic rally feed.");
            foreach(float v in new[]{range,timing,startVariation})if(!float.IsFinite(v)||v<0||v>1)throw new ArgumentOutOfRangeException("Movement fractions must be in [0,1].");
            var rng=new System.Random(unchecked(seed^0x6d41b23));
            PlayerMovementPatternV3.Validate(pattern,range,!paired);
            MovementRegion=PlayerMovementPatternV3.Region(pattern,seed,rng.Next(9));
            var forward=player<2?Vector3.forward:Vector3.back;
            var right=player<2?Vector3.right:Vector3.left;
            var oldBody=World.Players[player];
            var oldFace=oldBody.Paddle.position+oldBody.Paddle.rotation*PlayerStrokeAimV3.FacePoint;
            var positions=World.Players.Select(p=>p.Position).ToArray();
            if(startVariation>0) {
                // Start positions vary independently of the destination region.
                var start=right*((player%2==0?1:-1)*.9f+((float)rng.NextDouble()*2-1)*.2f)-forward*(4.4f+((float)rng.NextDouble()*2-1)*.25f);
                positions[player]=Vector3.Lerp(positions[player],start,startVariation);
            }
            if(paired)positions[player^1].z=positions[player].z;
            bool parkSoloPartner=!paired&&(range>0||timing>0||startVariation>0);
            // Solo footwork isolates the receiver: the inactive teammate waits
            // behind the baseline instead of blocking a deep destination.
            // Paired practice retains an active teammate inside the working court.
            if(parkSoloPartner)positions[player^1].z=(player<2?-1:1)*8.0f;
            if(startVariation>0||paired||parkSoloPartner) {
                for(int i=0;i<4;i++)World.Players[i].Reset(positions[i]);
                Controls=new PlayerControlWorldV3(positions);
                for(int i=0;i<4;i++)Apply(i,true);
            }
            var body=World.Players[player];
            var face=body.Paddle.position+body.Paddle.rotation*PlayerStrokeAimV3.FacePoint;
            var destination=right*((MovementRegion%3-1)*2.2f)-forward*(new[]{2.65f,4.2f,5.75f}[MovementRegion/3]);
            destination.y=face.y;
            if(pattern!="court")destination=PlayerMovementPatternV3.LocalDestination(face,right,forward,MovementRegion);
            MovementNominalPoint=Vector3.Lerp(face,destination,range);
            var shift=MovementNominalPoint-oldFace;shift.y=0;
            var position=World.Ball.position+shift;
            var velocity=World.Ball.linearVelocity;
            if(timing>0) {
                if(airborne) {
                    float flight=.65f+1.05f*timing;
                    velocity=MovementFlightVelocity(position,MovementNominalPoint,flight);
                } else {
                    // Prepend a ballistic approach to the familiar bounce feed.
                    // Drag and every bounce remain physical, so the nominal point
                    // is an approximate reset design point, not a guaranteed intercept.
                    float extra=1.15f*timing;
                    int ticks=Mathf.RoundToInt(extra/DoublesWorld.Dt);
                    for(int i=0;i<ticks;i++) {
                        // Invert the same free-flight timestep to prepend time
                        // while retaining the familiar incoming bounce velocity.
                        position-=velocity*DoublesWorld.Dt;
                        var prior=velocity;
                        for(int j=0;j<8;j++)prior=velocity-MovementAcceleration(prior)*DoublesWorld.Dt;
                        velocity=prior;
                    }
                    if(position.y<.1f)throw new InvalidOperationException("Movement bounce prelude starts below the court.");
                }
            }
            World.Ball.position=position;World.Ball.transform.position=position;
            World.Ball.linearVelocity=velocity;World.Ball.angularVelocity=Vector3.zero;World.Ball.WakeUp();
        }

        private Vector3 MovementAcceleration(Vector3 velocity)=>World.Configuration.Gravity+Picklebot.Core.AerodynamicModelV1.Evaluate(velocity,Vector3.zero,World.Configuration.AerodynamicParameters).TotalForce/World.Ball.mass;
        private Vector3 MovementFlightVelocity(Vector3 start,Vector3 destination,float seconds)
        {
            // Reset-only shooting estimate. The actual ball is still stepped by
            // PhysX, and no predicted path is passed to an actor or reward.
            int ticks=Mathf.RoundToInt(seconds/DoublesWorld.Dt);float duration=ticks*DoublesWorld.Dt;
            var initial=(destination-start)/duration-World.Configuration.Gravity*(.5f*duration);
            for(int iteration=0;iteration<12;iteration++) {
                var p=start;var v=initial;
                for(int tick=0;tick<ticks;tick++){v+=MovementAcceleration(v)*DoublesWorld.Dt;p+=v*DoublesWorld.Dt;}
                var error=destination-p;if(error.sqrMagnitude<1e-8f)return initial;
                initial+=error*(1.2f/duration);
            }
            throw new InvalidOperationException("Movement feed initial-velocity solve did not converge.");
        }

        public void InitializeContactDrill(int player,int seed,string task="contact",float returnDifficulty=1,float feedLowering=0,float feedLateralOffset=0,bool generalizedRallyContext=false,bool movePartner=false)
        {
            if(Tick!=0||Decisions!=null||!BallHeld||player<0||player>3)throw new InvalidOperationException("Feed only at an unused drill reset.");
            if(task!="stationary-flight"&&task!="falling-contact"&&task!="stationary-contact"&&task!="contact"&&task!="reaction-contact"&&task!="reaction-return"&&task!="near-return"&&task!="easy-return"&&task!="varied-return"&&task!="low-return")throw new ArgumentException("Unknown drill task.");
            if(float.IsNaN(returnDifficulty)||returnDifficulty<0||returnDifficulty>1)throw new ArgumentOutOfRangeException(nameof(returnDifficulty));
            if(!float.IsFinite(feedLowering)||feedLowering<0||feedLowering>.9f)throw new ArgumentOutOfRangeException(nameof(feedLowering));
            if(!float.IsFinite(feedLateralOffset)||Mathf.Abs(feedLateralOffset)>.9f)throw new ArgumentOutOfRangeException(nameof(feedLateralOffset));
            if(task=="stationary-flight"||task=="near-return"||task=="easy-return"||task=="varied-return"||task=="low-return")
            {
                // Curriculum reset only: shorten the required return distance.
                // The same body, collision and legal-bounce rules still apply.
                var positions=World.Players.Select(p=>p.Position).ToArray();
                positions[player].z=(player<2?-1:1)*(task=="stationary-flight"?Mathf.Lerp(3.2f,7.65f,returnDifficulty):3.2f);
                if(movePartner)positions[player^1].z=positions[player].z;
                for(int i=0;i<4;i++)World.Players[i].Reset(positions[i]);
                Controls=new PlayerControlWorldV3(positions);
                for(int i=0;i<4;i++)Apply(i,true);
            }
            var random=new System.Random(seed);var body=World.Players[player];
            var point=body.Paddle.position+body.Paddle.rotation*PlayerStrokeAimV3.FacePoint;
            // Reset-only vertical translation of the easy feed. No body pose,
            // policy target, subsequent ball state or physical parameter changes.
            if(task=="low-return"||(task=="stationary-contact"||task=="falling-contact"))point-=Vector3.up*feedLowering;
            // Canonical +X is player-right; opposite ends rotate 180 degrees.
            // Translate only the initial feed geometry. Zero preserves old arithmetic.
            if((task=="low-return"||(task=="stationary-contact"||task=="falling-contact"))&&feedLateralOffset!=0)point+=Vector3.right*(player<2?feedLateralOffset:-feedLateralOffset);
            var normal=body.Paddle.rotation*Vector3.forward;
            var jitter=body.Paddle.rotation*new Vector3((float)(random.NextDouble()*2-1)*.16f,(float)(random.NextDouble()*2-1)*.12f,0);
            var p=point+normal*(.35f+(float)random.NextDouble()*.3f)+jitter;
            // Explicit drill initialization: synthetic rule history makes either team
            // eligible to hit, but supplies no physical hit, score or stroke command.
            var rules=World.Rules;
            if(generalizedRallyContext)
            {
                // Opt-in reset diagnostic: use actual rule transitions for any initial server.
                // No physical serve or stroke command is generated by this synthetic history.
                int receiver=rules.DesignatedReceiver;
                rules.FixedBallServe(rules.Server,true,0);
                rules.Bounce(new Vector3(rules.ServiceX(receiver),0,DoublesRules.Side(DoublesRules.Team(receiver))*4),0);
                rules.Hit(receiver,0);
                rules.Bounce(new Vector3(0,0,DoublesRules.Side(rules.ServingTeam)*4),0);
                rules.Hit(rules.Server,0);
                if(rules.ExpectedTeam!=DoublesRules.Team(player))rules.Hit(receiver,0);
                if(rules.Dead||rules.Phase!=RallyPhase.Rally||rules.ExpectedTeam!=DoublesRules.Team(player)||!rules.CanVolley||rules.Bounced)
                    throw new InvalidOperationException("Generalized drill history did not produce an eligible rally learner.");
            }
            else
            {
            rules.Serve(rules.Server,true,true,true,true,false,false,false,0);
            rules.Bounce(new Vector3(rules.ServiceX(rules.DesignatedReceiver),0,4),0);
            rules.Hit(rules.DesignatedReceiver,0);rules.Bounce(new Vector3(0,0,-4),0);rules.Hit(0,0);
            if(player<2)rules.Hit(2,0);
            }
            BallHeld=false;World.Ball.isKinematic=false;World.Ball.detectCollisions=true;
            World.Ball.position=p;World.Ball.transform.position=p;
            World.Ball.linearVelocity=-normal*(3+(float)random.NextDouble()*2);
            if(task!="stationary-flight"&&task!="contact"&&task!="falling-contact"&&task!="stationary-contact")
            {
                // Reset-only feed. The target is sampled around the initial reach area;
                // this estimate supplies reaction time, not a policy intercept or stroke.
                // Drag, gravity and every subsequent collision are simulated normally.
                var courtForward=player<2?Vector3.forward:Vector3.back;
                var direction=task=="reaction-return"||task=="near-return"||task=="easy-return"||task=="varied-return"||task=="low-return"?courtForward:(normal+courtForward*.4f).normalized;
                bool easy=task=="easy-return"||task=="low-return";
                // Reset distribution only. Longer flight and tighter placement
                // leave preparation to the policy; gravity/drag are unchanged.
                float flight=easy?.65f+(float)random.NextDouble()*.10f:.32f+(float)random.NextDouble()*.23f;
                var target=point+body.Paddle.rotation*new Vector3((float)(random.NextDouble()*2-1)*(easy?.06f:.28f),(float)(random.NextDouble()*2-1)*(easy?.04f:.20f),0);
                p=point+direction*(1.4f+(float)random.NextDouble()*(easy?.2f:1.0f))+Vector3.up*.2f;
                if(task=="varied-return")
                {
                    // Reuse the same feed random draws through a separate reset RNG.
                    // Endpoints reproduce easy/near feeds; no assistance after reset.
                    var feed=new System.Random(seed);
                    for(int i=0;i<4;i++)feed.NextDouble();
                    float t=(float)feed.NextDouble(),x=(float)(feed.NextDouble()*2-1),y=(float)(feed.NextDouble()*2-1),z=(float)feed.NextDouble();
                    flight=Mathf.Lerp(.65f+t*.10f,.32f+t*.23f,returnDifficulty);
                    target=point+body.Paddle.rotation*new Vector3(x*Mathf.Lerp(.06f,.28f,returnDifficulty),y*Mathf.Lerp(.04f,.20f,returnDifficulty),0);
                    p=point+direction*(1.4f+z*Mathf.Lerp(.2f,1f,returnDifficulty))+Vector3.up*.2f;
                }
                World.Ball.position=p;World.Ball.transform.position=p;
                World.Ball.linearVelocity=(target-p)/flight-World.Configuration.Gravity*(.5f*flight);
            }
            if((task=="stationary-flight"||task=="stationary-contact"||task=="falling-contact"))
            {
                // Drill support only: dynamic collision response remains enabled.
                // No per-tick repositioning or velocity overwrite after impact.
                p=point+normal*.25f;
                var ballCollider=World.Ball.GetComponent<Collider>();
                foreach(var other in World.Root.GetComponentsInChildren<Collider>())
                    if(other!=ballCollider&&other.enabled&&!other.isTrigger&&Physics.ComputePenetration(ballCollider,p,World.Ball.rotation,other,other.transform.position,other.transform.rotation,out _,out _))
                        throw new StationaryResetOverlapException(other.name);
                World.Ball.position=p;World.Ball.transform.position=p;
                World.Ball.linearVelocity=Vector3.zero;StationarySupportActive=task=="stationary-contact"||task=="stationary-flight";
            }
            World.Ball.angularVelocity=Vector3.zero;
            World.Ball.WakeUp();World.Contacts.Clear();
        }
        public void InitializeStationaryServe()
        {
            if(Tick!=0||Decisions!=null||!BallHeld)throw new InvalidOperationException("Fixed serve requires unused rally reset.");
            ResetStationaryServe();
        }
        private void ResetStationaryServe()
        {
            var body=World.Players[World.Rules.Server];
            var p=body.Paddle.position+body.Paddle.rotation*(PlayerStrokeAimV3.FacePoint+Vector3.forward*.25f);
            var ballCollider=World.Ball.GetComponent<Collider>();
            foreach(var other in World.Root.GetComponentsInChildren<Collider>())
                if(other!=ballCollider&&other.enabled&&!other.isTrigger&&Physics.ComputePenetration(ballCollider,p,World.Ball.rotation,other,other.transform.position,other.transform.rotation,out _,out _))
                    throw new StationaryResetOverlapException(other.name);
            World.FixedBallServe=true;BallHeld=false;StationarySupportActive=true;
            World.Ball.isKinematic=false;World.Ball.detectCollisions=true;
            World.Ball.position=p;World.Ball.transform.position=p;
            World.Ball.linearVelocity=World.Ball.angularVelocity=Vector3.zero;World.Ball.WakeUp();
        }
        private void HoldBall()
        {
            var hand=World.Players[World.Rules.Server].Root.transform.Find("Left hand");
            // Fixed finger-side attachment, clear of the palm/forearm as the shoulder lifts.
            var rotation=Controls.UpperFor(World.Rules.Server).Pose().rotation;
            var p=hand.position+rotation*Vector3.forward*.105f;
            World.Ball.position=p;World.Ball.transform.position=p;
        }
        public bool Step(PlayerActionV3[] actions)
        {
            if(Failure!=null)throw new InvalidOperationException("Failed episode: "+Failure);
            if(!Controls.TryStep(actions)){Failure="Infeasible body step for player "+Controls.RejectedPlayer;return false;}
            for(int i=0;i<4;i++)Apply(i,false);
            if(BallHeld)
            {
                HoldBall();
                // Initial drop-serve contract: the policy chooses release time and body
                // preparation; release is at rest, with no toss impulse or automatic hit.
                if(actions[World.Rules.Server].Release&&!World.Rules.Dead)
                {
                    ReleasePosition=World.Ball.position;ReleaseHandLift=Controls.OffHandAngleFor(World.Rules.Server);
                    BallHeld=false;World.Ball.isKinematic=false;World.Ball.detectCollisions=true;
                    World.Ball.linearVelocity=World.Ball.angularVelocity=Vector3.zero;World.Ball.WakeUp();
                }
            }
            int contactsBefore=World.Contacts.Count;
            World.Simulate(StationarySupportActive);
            if(StationarySupportActive&&World.Contacts.Count>contactsBefore)StationarySupportActive=false;
            Tick++;TotalTicks++;Array.Copy(actions,active,4);return true;
        }
        private void Apply(int i,bool initialize)
        {
            var root=Controls.StateFor(i);var legs=Controls.PoseFor(i);var upper=Controls.UpperFor(i);
            var support=new PlayerSupportState(legs.Left,legs.Right,root,i<2?-1:1,DoublesRules.HalfWidth,DoublesRules.Kitchen);
            var frame=PlayerArticulatedFrameV3.ComposeBounded(new PlayerBodyFrame{position=root.position,velocity=root.velocity,pelvis=legs.Pelvis,
                leftFoot=legs.Left.center,rightFoot=legs.Right.center,leftHip=legs.LeftHip,rightHip=legs.RightHip,leftKnee=legs.LeftKnee,rightKnee=legs.RightKnee,
                yaw=root.facingYaw,offHandLift=Controls.OffHandAngleFor(i),leftFootYaw=legs.Left.yaw,rightFootYaw=legs.Right.yaw,touchesKitchen=support.touchesKitchen,
                bothFeetOutside=support.bothFeetOutside,balanceRecovered=support.balanceRecovered},upper);
            World.Players[i].ApplyExternalFrame(frame,initialize);
        }
        public void Dispose()=>World.Dispose();
    }
}

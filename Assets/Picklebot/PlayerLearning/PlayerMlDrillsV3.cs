using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Picklebot.PlayerControlsIntegration;
using Unity.MLAgents;
using Unity.InferenceEngine;
using Unity.MLAgents.Actuators;
using Unity.MLAgents.Policies;
using UnityEngine;

namespace Picklebot.PlayerLearning
{
    [Serializable] public sealed class MlDecisionV3
    {
        public int seed, player, observationTick, release;
        public string task;
        public bool canRelease, serveFromLeft, backgroundPolicy;
        public float[] observation, continuous, physical;
    }
    [Serializable] public sealed class MlSimulationFailureV3
    {
        public string version="ml-drill-simulation-failure-v1",sourceIdentity,task,outcome,error;
        public int seed,player,rejectedPlayer,physicsTick;
        public float maximumReturnDifficulty,feedLowering,feedLateralOffset,initialHoldLift;
        public bool serveFromLeft;
        public bool randomMatchContext;
        public int rallyServer=-1;
        public bool rallyServerOnRight;
        public bool inactivePlayerCommandsAreZero=true;
        public MlDecisionV3[] decisions;
    }
    [Serializable] public sealed class MlDrillEpisodeV3
    {
        public int seed, player, physicsTicks, decisions, backgroundDecisions;
        public string[] resetRejections;
        public string task, outcome;
        public int rallyServer=-1;
        public bool rallyServerOnRight;
        public float reward, feedDifficulty, feedLowering, feedLateralOffset, faceContactBallHeight, initialHoldLift;
        public bool incomingServeLanded;
        public bool contactWasVolley;
        public string terminalFault;
        public bool cooperativePairs;
        public int hitter=-1, pairFeedLane=-1;
        public int[] decisionsByPlayer;
        public bool movementFeed;
        public int movementRegion=-1;
        public float movementRange,movementTiming,movementStartVariation,contactDisplacement,contactDistanceFromStart;
        public string movementPattern;
        public float movementPositionRewardScale,movementPositionReward;
        public bool precontactAlignmentRewardEnabled;
        public float precontactShapingReward,precontactInitialPotential;
        public double precontactDiscountedReward;
        public int precontactTransitions;
        public bool precontactSettled;
        public bool movementForwardProgressRewardEnabled;
        public float movementForwardProgressReward;
        public int movementForwardProgressRewardedSteps;
        public float[] travelBeforeContact;
        public bool faceContact, netCrossed, released, dropBounced, serveAccepted, serveFromLeft, randomMatchContext;
        public float faceContactNormalAlignment=-1;
    }
    [Serializable] public sealed class MlDrillReportV3
    {
        public string contract = PlayerMlAgentV3.ContractVersion;
        public string curriculumVersion = PlayerMlDrillsV3.CurriculumVersion;
        public string drillVersion = PlayerContactDrillV3.Version;
        public string status, failure, task, sourceIdentity, unityVersion, split;
        public string fixedServeSides;
        public int firstSeed, seedCount, arenas, completedEpisodes, decisions, physicsTicks;
        public int nextSeedIndex;
        public float maximumReturnDifficulty, stationaryFlightDifficulty, feedLowering, feedLateralOffset, initialHoldLift;
        public bool trainerConnected, alignedDecisions, randomMatchContext, movementRecoveryMix, interleavedRecovery, optimizerDiagnostics;
        public bool movementForwardProgressReward,precontactAlignmentReward;
        public float precontactGamma;
        public int schedulerWorkerId;
        public int schedulerTicks, decisionBatches, requestedDecisions, backgroundDecisions;
        public bool activePracticePlayers, cooperativePairs;
        public string movementPattern;
        public float movementRange,movementTiming,movementStartVariation,movementPositionReward,movementRehearsalRange;
    }

    public sealed class PlayerMlDrillsV3 : MonoBehaviour
    {
        public PlayerExecutionDrillsV1 ExecutionGoals { get; private set; }
        public const string CurriculumVersion = "ml-drill-curriculum-v29-stability-order";
        public string Task = "reaction-contact";
        public string FixedServeSides = "right";
        public bool RandomizeMatchContext;
        public float MaximumReturnDifficulty = 1;
        public string MovementPattern="court";
        public float MovementRange,MovementTiming,MovementStartVariation,MovementPositionReward;
        public bool MovementForwardProgressReward; // Optional focus-only measured post-contact flight feedback.
        public bool PrecontactAlignmentReward;
        public float PrecontactGamma=PlayerPrecontactPotentialV3.Gamma;
        public static void ValidatePrecontactAlignment(string task,float range,bool enabled,float gamma,bool forward,float position)
        {
            if(!enabled)return;
            if(task!="movement-maintenance"||!float.IsFinite(range)||range<=0||range>1||gamma!=PlayerPrecontactPotentialV3.Gamma||forward||position!=0)
                throw new ArgumentException("Precontact shaping requires solo movement practice, gamma0.99 and no other movement shaping.");
        }
        public float MovementRehearsalRange; // Zero preserves the existing schedule. Positive: half of challenges rehearse prior court feeds.
        public bool MovementRecoveryMix; // Opt-in256-episode25/25/50 recovery schedule.
        public bool InterleavedRecovery, OptimizerDiagnostics;
        public int SchedulerWorkerId;
        private PlayerRecoveryScheduleV3.Episode Recovery(int index)=>PlayerRecoveryScheduleV3.For(index,MovementRange,MovementRehearsalRange,MaximumReturnDifficulty,MovementPattern);
        public static void ValidateMovementPositionReward(string task,float range,float budget)
        {
            PlayerMovementPositionRewardV3.ValidateBudget(budget);
            if(budget>0&&(task!="movement-maintenance"||!float.IsFinite(range)||range<=0))throw new ArgumentException("Position reward requires solo movement practice with a positive range.");
        }
        public static void ValidateMovementForwardProgressReward(string task,float range,bool enabled)
        {
            if(enabled&&(task!="movement-maintenance"||!float.IsFinite(range)||range<=0||range>1))
                throw new ArgumentException("Forward flight reward requires solo movement practice with a positive bounded range.");
        }
        public static bool IsMovementTask(string task)=>task=="movement-maintenance"||task=="paired-movement-maintenance";
        public bool MovementPractice=>IsMovementTask(Task);
        public static void ValidateMovement(string task,float range,float timing,float starts)
        {
            foreach(float v in new[]{range,timing,starts})if(!float.IsFinite(v)||v<0||v>1)throw new ArgumentException("Movement fractions must be in [0,1].");
            if(!IsMovementTask(task)&&(range!=0||timing!=0||starts!=0))throw new ArgumentException("Movement parameters require a movement curriculum.");
        }
        // Half of starts retain fixed serves, opening returns and familiar rally
        // feeds. The other half sweep four ranges, each covering all four seats.
        public static void ValidateMovementRehearsal(string task,float range)
        {
            if(!float.IsFinite(range)||range<0||range>1||(range>0&&task!="movement-maintenance"))throw new ArgumentException("Movement rehearsal requires solo movement practice and a finite range in [0,1].");
        }
        public bool MovementRehearsalForEpisode(int index)=>MovementRecoveryMix?Recovery(index).Group=="prior":MovementChallenge(index)&&MovementRehearsalRange>0&&index/64%2==1;
        public string MovementPatternForEpisode(int index)=>MovementRecoveryMix?Recovery(index).Pattern:MovementChallenge(index)&&!MovementRehearsalForEpisode(index)?MovementPattern:"court";
        public float MovementRangeForEpisode(int index)=>MovementRecoveryMix?Recovery(index).Range:!MovementPractice||!PlayerContactDrillV3.IsRallyFeed(TaskForEpisode(index))?-1:index/4%16<8?0:(MovementRehearsalForEpisode(index)?MovementRehearsalRange:MovementRange)*(1+index/4%4)*.25f;
        private bool NewMovementChallenge(int index)=>MovementChallenge(index)&&!MovementRehearsalForEpisode(index);
        private bool MovementChallenge(int index)=>MovementPractice&&(MovementRecoveryMix?Recovery(index).Group!="familiar":index/4%16>=8);
        public float StationaryFlightDifficulty; // Mixed-task reset distance only; moving-return difficulty stays independent.
        public float FeedLowering;
        public float InitialHoldLift; // Reset only, applied to held-ball tasks. Subsequent actions remain unconstrained by this setting.
        public float FeedLateralOffset; // Canonical meters; low-return resets only.
        public int FirstSeed = 1023808, SeedCount = 8192, ArenaCount = 4, TicksPerFrame = 48;
        public bool RequireTrainer = true, AutoRun = true;
        public string EvidenceDirectory, SourceIdentity;
        public ModelAsset InferenceModel;
        public ModelAsset BackgroundModel; // Frozen, private-observation players; never optimizer participants.
        public bool RecordDecisions;
        // Opt-in scheduling only: wait between completed episodes so live courts
        // request their 20 Hz decisions together. Match time never advances while waiting.
        public bool AlignDrillDecisions;
        public readonly List<MlDrillEpisodeV3> Episodes = new();
        public MlDrillReportV3 Report { get; private set; }
        public bool CooperativePairs=>Task=="paired-maintenance"||Task=="paired-movement-maintenance";
        private readonly List<Arena> arenas = new();
        private StreamWriter evidence, decisionEvidence;
        private bool initialized, stopped;
        private int nextSeedIndex;

        public sealed class Arena : IDisposable
        {
            private readonly PlayerMlDrillsV3 owner;
            public readonly PlayerMlAgentV3[] Agents = new PlayerMlAgentV3[4];
            public readonly PlayerMlAgentV3[] BackgroundAgents = new PlayerMlAgentV3[4];
            public PlayerContactDrillV3 Drill { get; private set; }
            private float reward;
            private bool precontactEnabled;
            private PlayerPrecontactPotentialV3 precontact;
            private float CurrentPotential()=>Drill.MeasurePrecontactPotential();
            private PlayerExecutionGoalV1[] goals;
            private int firstDecision, firstBackgroundDecision;
            private readonly int[] firstByPlayer=new int[4];
            private readonly SimpleMultiAgentGroup group=new();
            public int RegisteredPlayers=>group.GetRegisteredAgents().Count;
            public int GroupId=>group.GetId();
            private bool awaitingReset;
            private string[] resetRejections;
            private readonly List<MlDecisionV3> decisionTrace = new();
            public bool Finished { get; private set; }
            public Arena(PlayerMlDrillsV3 owner)
            {
                this.owner = owner;
                NextDrill();
                for (int i = 0; i < 4; i++)
                {
                    int seat = i;
                    var go = new GameObject("Independent player " + i);
                    go.SetActive(false); go.transform.SetParent(owner.transform);
                    var behavior = go.AddComponent<BehaviorParameters>();
                    behavior.BehaviorName = owner.ExecutionGoals == null ? PlayerMlAgentV3.BehaviorName : PlayerExecutionGoalV1.BehaviorName;
                    // All seats share actor weights. Paired practice groups only
                    // this court's two teammates; it has no opposing learner team.
                    behavior.TeamId = 0;
                    behavior.BrainParameters.VectorObservationSize = owner.ExecutionGoals == null ? PlayerObservationV3.Count : PlayerExecutionGoalV1.ObservationCount;
                    behavior.BrainParameters.NumStackedVectorObservations = 1;
                    behavior.BrainParameters.ActionSpec = new ActionSpec(PlayerMlAgentV3.ContinuousCount, new[] {2});
                    behavior.Model = owner.InferenceModel;
                    behavior.DeterministicInference = true;
                    behavior.BehaviorType = owner.RequireTrainer ? BehaviorType.Default
                        : owner.InferenceModel != null ? BehaviorType.InferenceOnly : BehaviorType.HeuristicOnly;
                    var agent = go.AddComponent<PlayerMlAgentV3>();
                    agent.Bind(seat, () => { if(owner.OptimizerDiagnostics)PlayerDrillDiagnosticsV3.Record(Agents[seat],Drill.Seed-owner.FirstSeed,Drill.Done); return PlayerObservationV3.Capture(Drill.Match, seat, Drill.Match.Tick); },
                        () => PlayerContactDrillV3.IsDropTask(Drill.Task) && Drill.Match.BallHeld && Drill.Match.World.Rules.Server == seat);
                    if (owner.ExecutionGoals != null) agent.BindGoal(() => goals[seat]);
                    agent.Received += (current, actions) =>
                    {
                        var row=owner.RecordDecision(Drill,current,actions);
                        if(row!=null)decisionTrace.Add(row);
                    };
                    Agents[i] = agent;
                    go.SetActive(true);
                }
                if(owner.BackgroundModel!=null)for(int i=0;i<4;i++)
                {
                    int seat=i;var go=new GameObject("Frozen practice player "+i);go.SetActive(false);go.transform.SetParent(owner.transform);
                    var behavior=go.AddComponent<BehaviorParameters>();behavior.BehaviorName="PicklebotPracticeFrozen";
                    behavior.BrainParameters.VectorObservationSize=PlayerObservationV3.Count;behavior.BrainParameters.NumStackedVectorObservations=1;
                    behavior.BrainParameters.ActionSpec=new ActionSpec(PlayerMlAgentV3.ContinuousCount,new[]{2});
                    behavior.Model=owner.BackgroundModel;behavior.DeterministicInference=true;behavior.BehaviorType=BehaviorType.InferenceOnly;
                    var agent=go.AddComponent<PlayerMlAgentV3>();
                    agent.Bind(seat,()=>PlayerObservationV3.Capture(Drill.Match,seat,Drill.Match.Tick),()=>false);
                    agent.Received+=(current,actions)=>{var row=owner.RecordDecision(Drill,current,actions,true);if(row!=null)decisionTrace.Add(row);};
                    BackgroundAgents[i]=agent;go.SetActive(true);
                }
                Attach();
            }
            private void Attach()
            {
                goals = owner.ExecutionGoals?.Goals(Drill);
                precontact=precontactEnabled?new PlayerPrecontactPotentialV3(CurrentPotential(),owner.PrecontactGamma):null;
                foreach(var old in group.GetRegisteredAgents().ToArray())group.UnregisterAgent(old);
                foreach (var agent in Agents) { agent.ClearCommand(); agent.Learning = owner.CooperativePairs?agent.Seat/2==Drill.Player/2:agent.Seat==Drill.Player; if(owner.CooperativePairs&&agent.Learning)group.RegisterAgent(agent); firstByPlayer[agent.Seat]=agent.DecisionsReceived; }
                firstDecision = owner.CooperativePairs?Agents.Sum(p=>p.DecisionsReceived):Agents[Drill.Player].DecisionsReceived;
                foreach(var agent in BackgroundAgents)if(agent!=null){agent.ClearCommand();agent.Learning=agent.Seat!=Drill.Player;}
                firstBackgroundDecision=BackgroundAgents.Where(p=>p!=null).Sum(p=>p.DecisionsReceived);
                Drill.Match.AttachPolicies(Enumerable.Range(0,4).Select(i=>(IPlayerPolicyV3)(i==Drill.Player||BackgroundAgents[i]==null?Agents[i]:BackgroundAgents[i])).ToArray(),Drill.Seed);
            }
            private void NextDrill()
            {
                int index = owner.TakeSeedIndex();
                if (index < 0) { Finished = true; return; }
                Drill?.Dispose();decisionTrace.Clear();
                Drill = owner.CreateDrillForEpisode(index, out resetRejections);
                precontactEnabled=owner.PrecontactAlignmentReward&&owner.NewMovementChallenge(index);
                reward = 0;
            }
            public bool Request()
            {
                if (awaitingReset)
                {
                    if (owner.Report.schedulerTicks % PlayerDecisionLoopV3.DecisionTicks != 0) return false;
                    awaitingReset = false;
                    NextDrill();
                    if (!Finished) Attach();
                }
                if (Finished || Drill.Match.Tick % PlayerDecisionLoopV3.DecisionTicks != 0) return false;
                // Submit previous transition shaping before Academy sends the next decision.
                if(precontact!=null&&Drill.Match.Tick>0)
                {
                    float shaped=precontact.AtDecision(Drill.Match.Tick,CurrentPotential());
                    reward+=shaped;Agents[Drill.Player].AddReward(shaped);
                }
                foreach(var agent in Agents)if(agent.Learning)agent.RequestDecision();
                foreach(var agent in BackgroundAgents)if(agent!=null&&agent.Learning)agent.RequestDecision();
                return true;
            }
            public void Step()
            {
                if (Finished || awaitingReset) return;
                int before = Drill.Match.Tick;
                Drill.Step();
                owner.Report.physicsTicks += Drill.Match.Tick - before;
                // Software/solver failures are diagnostics, never ordinary loss
                // samples. Stop before reward submission or terminal notification.
                if (Drill.Outcome == "exception" || Drill.Outcome == "infeasible")
                {
                    owner.RecordSimulationFailure(Drill,decisionTrace);
                    throw new InvalidOperationException("Drill simulation failed: " + Drill.Outcome + "; seed="+Drill.Seed+" player="+Drill.Player+" tick="+Drill.Match.Tick+"; " + Drill.Match.Failure);
                }

                float stepReward = Drill.Reward;
                if (Drill.Done && owner.ExecutionGoals != null) stepReward += owner.ExecutionGoals.Finish(Drill,goals[Drill.Player]);
                if(Drill.Done&&precontact!=null)stepReward+=precontact.AtTerminal(Drill.Match.Tick);
                reward += stepReward;
                if(owner.CooperativePairs)group.AddGroupReward(stepReward);else Agents[Drill.Player].AddReward(stepReward);
                if (!Drill.Done) return;
                var record = new MlDrillEpisodeV3 { seed = Drill.Seed, player = Drill.Player, task = Drill.Task, serveFromLeft = Drill.ServeFromLeft, rallyServer=Drill.RallyServer??-1, rallyServerOnRight=Drill.RallyServerOnRight, randomMatchContext=Drill.RandomMatchContext,
                    resetRejections = resetRejections, initialHoldLift = Drill.InitialHoldLift, feedDifficulty = Drill.FeedDifficulty, feedLowering = Drill.FeedLowering, feedLateralOffset = Drill.FeedLateralOffset, faceContactBallHeight = Drill.FaceContactBallHeight, outcome = Drill.Outcome, physicsTicks = Drill.Match.Tick, reward = reward,
                    decisions = (owner.CooperativePairs?Agents.Sum(p=>p.DecisionsReceived):Agents[Drill.Player].DecisionsReceived)-firstDecision,
                    precontactAlignmentRewardEnabled=precontactEnabled,precontactShapingReward=precontact?.TotalReward??0,
                    precontactInitialPotential=precontact?.InitialPotential??0,precontactDiscountedReward=precontact?.DiscountedReward??0,
                    precontactTransitions=precontact?.Transitions??0,precontactSettled=precontact?.Settled??false,
                    movementPattern=Drill.MovementPattern,movementPositionRewardScale=Drill.MovementPositionRewardScale,movementPositionReward=Drill.MovementPositionReward,
                    movementForwardProgressRewardEnabled=Drill.MovementForwardProgressRewardEnabled,movementForwardProgressReward=Drill.MovementForwardProgressReward,movementForwardProgressRewardedSteps=Drill.MovementForwardProgressRewardedSteps,
                    movementFeed=Drill.MovementFeed,movementRegion=Drill.Match.MovementRegion,movementRange=Drill.MovementRange,movementTiming=Drill.MovementTiming,movementStartVariation=Drill.MovementStartVariation,travelBeforeContact=Drill.TravelBeforeContact,contactDisplacement=Drill.ContactDisplacement,contactDistanceFromStart=Drill.ContactDistanceFromStart,
                    cooperativePairs=owner.CooperativePairs,hitter=Drill.Hitter,pairFeedLane=Drill.Match.RallyFeedLane,decisionsByPlayer=Agents.Select(p=>p.DecisionsReceived-firstByPlayer[p.Seat]).ToArray(),
                    backgroundDecisions=BackgroundAgents.Where(p=>p!=null).Sum(p=>p.DecisionsReceived)-firstBackgroundDecision,
                    incomingServeLanded=Drill.IncomingServeLanded, contactWasVolley=Drill.ContactWasVolley,terminalFault=Drill.Match.World.Rules.LastFault.ToString(), faceContact = Drill.FaceContact, faceContactNormalAlignment=Drill.FaceContactNormalAlignment, netCrossed = Drill.NetCrossed, released = Drill.Released,
                    dropBounced = Drill.DropBounced, serveAccepted = Drill.ServeAccepted };
                owner.Record(record);
                // The final observation is captured by EndEpisode before this world's
                // reset. Drill deadlines are explicit task failures in the v5 contract.
                if(owner.CooperativePairs)group.EndGroupEpisode();else Agents[Drill.Player].EndEpisode();
                foreach(var agent in BackgroundAgents)if(agent!=null&&agent.Learning)agent.EndEpisode();
                if (owner.AlignDrillDecisions && owner.nextSeedIndex < owner.SeedCount)
                    awaitingReset = true;
                else
                {
                    NextDrill();
                    if (!Finished) Attach();
                }
            }
            public void Dispose()
            {
                group.Dispose();
                foreach (var agent in Agents.Concat(BackgroundAgents)) if (agent != null) DestroyImmediate(agent.gameObject);
                Drill?.Dispose();
            }
        }
        public IReadOnlyList<Arena> ActiveArenas => arenas;
        // Blocks of four cover every seat before switching task. This balances
        // episode starts, not decision counts: serve and return durations differ.
        // Seed-only reset sampling; no body state, policy action or future trajectory.
        public static Vector2 StationaryResetFractions(int seed, int attempt=0)
        {
            if(attempt<0||attempt>=64)throw new ArgumentOutOfRangeException(nameof(attempt));
            seed=unchecked(seed+(int)(0x9e3779b9U*(uint)attempt));
            uint Mix(uint x){unchecked{x^=x>>16;x*=0x7feb352dU;x^=x>>15;x*=0x846ca68bU;return x^(x>>16);}}
            return new Vector2((Mix(unchecked((uint)seed)^0x91a73b21U)>>8)/16777216f,
                (Mix(unchecked((uint)seed)^0x4d38ac67U)>>8)/16777216f);
        }
        // Rejection sampling happens before agents see a reset. Only actual geometric
        // overlap is retried; programming errors still stop the run.
        public PlayerContactDrillV3 CreateDrillForEpisode(int index, out string[] rejectedSurfaces)
        {
            var rejected=new List<string>();
            int seed=checked(FirstSeed+index);
            for(int attempt=0;attempt<64;attempt++)
            {
                float lower=FeedLoweringForEpisode(index), offset=FeedLateralOffsetForEpisode(index);
                if(IsVariedContactEpisode(index))
                {
                    var fractions=StationaryResetFractions(seed,attempt);
                    lower=FeedLowering*fractions.x;offset=FeedLateralOffset*fractions.y;
                }
                try
                {
                    var drill=new PlayerContactDrillV3(seed,index%4,TaskForEpisode(index),DifficultyForEpisode(index),lower,offset,HoldLiftForEpisode(index),ServeFromLeftForEpisode(index),RallyServerForEpisode(index),RallyServerOnRightForEpisode(index),RandomizeMatchContext&&(TaskForEpisode(index)=="receive-serve"||PlayerContactDrillV3.IsFixedServeTask(TaskForEpisode(index))||RallyServerForEpisode(index).HasValue)?(int?)seed:null,cooperative:CooperativePairs,movementRange:MovementRangeForEpisode(index),movementTiming:NewMovementChallenge(index)?MovementTiming:0,movementStartVariation:NewMovementChallenge(index)?MovementStartVariation:0,movementPositionReward:NewMovementChallenge(index)?MovementPositionReward:0,movementPattern:MovementPatternForEpisode(index),movementForwardProgressReward:NewMovementChallenge(index)&&MovementForwardProgressReward);
                    rejectedSurfaces=rejected.ToArray();return drill;
                }
                catch(StationaryResetOverlapException e) when(IsVariedContactEpisode(index)) { rejected.Add(e.Surface); }
            }
            throw new InvalidOperationException("Stationary reset exhausted 64 candidates; seed="+seed+"; rejected surfaces="+string.Join(",",rejected));
        }
        private bool IsVariedContactEpisode(int index)=>Task=="stationary-practice"||((Task=="stationary-return"||Task=="falling-return")&&index/4%2==0);
        // Four fixed serves alternate with four retained return resets. The return
        // subcycle is the existing 128-episode range/context mix; full cycle is 256.
        private bool CombinedServe(int index)=>Task=="serve-context-return"&&index/4%2==0;
        private int ContextIndex(int index)=>Task=="serve-context-return"?index/8*4+index%4:index;
        private bool ContextFlight(int index)=>(Task=="context-flight-return"||Task=="context-range-return"||Task=="serve-context-return")&&!CombinedServe(index)&&ContextIndex(index)/4%2==0;
        public int? RallyServerForEpisode(int index)
        {if(index<0)throw new ArgumentOutOfRangeException(nameof(index));return ContextFlight(index)?(int?)(ContextIndex(index)/16%4):null;}
        public bool RallyServerOnRightForEpisode(int index)
        {if(index<0)throw new ArgumentOutOfRangeException(nameof(index));return !RallyServerForEpisode(index).HasValue||ContextIndex(index)/8%2==0;}
        public float DifficultyForEpisode(int index)
        {
            if(index<0)throw new ArgumentOutOfRangeException(nameof(index));
            if(MovementRecoveryMix)return Recovery(index).Difficulty;
            if(MovementPractice)return index/4%16<2?1:index/4%16==3?MaximumReturnDifficulty:0;
            if(CooperativePairs)return index/4%8<2?1:index/4%8==2?0:index/4%8==3?MaximumReturnDifficulty:StationaryFlightDifficulty;
            if(Task=="rally-maintenance")return index/4%8<2?1:index/4%8==2?0:index/4%8<5?MaximumReturnDifficulty:StationaryFlightDifficulty;
            if(Task=="receive-varied-maintenance")return index/4%4==0?1:index/4%4==1?0:MaximumReturnDifficulty;
            if(Task=="receive-maintenance")return index/4%2==0?1:index/4%4==1?0:MaximumReturnDifficulty;
            if(Task=="receive-feed")return index/4%4==0?0:MaximumReturnDifficulty;
            if(Task=="serve-receive")return 1;
            if(Task=="serve-context-return")return CombinedServe(index)?1:ContextFlight(index)?(ContextIndex(index)/64%2==0?0:StationaryFlightDifficulty):MaximumReturnDifficulty;
            if(Task=="context-range-return"&&index/4%2==0)return index/64%2==0?0:StationaryFlightDifficulty;
            return (Task=="flight-return-mix"||Task=="context-flight-return")&&index/4%2==0?StationaryFlightDifficulty:MaximumReturnDifficulty;
        }
        public string TaskForEpisode(int index)
        {
            if(index<0)throw new ArgumentOutOfRangeException(nameof(index));
            if(MovementRecoveryMix)return Recovery(index).Task;
            if(MovementPractice){int block=index/4%16;return block<2?"stationary-serve":block<4?"receive-feed":block<6||block>=8&&block<12?"rally-air-feed":"rally-bounce-feed";}
            if(CooperativePairs)return index/4%8<2?"stationary-serve":index/4%8<4?"receive-feed":index/4%8<6?"rally-air-feed":"rally-bounce-feed";
            if(Task=="rally-maintenance")return index/4%8<2?"stationary-serve":index/4%8<5?"receive-feed":index/4%8<7?"rally-air-feed":"rally-bounce-feed";
            if(Task=="receive-varied-maintenance")return index/4%4==0?"stationary-serve":"receive-feed";
            if(Task=="receive-maintenance")return index/4%2==0?"stationary-serve":"receive-feed";
            if(Task=="serve-receive")return index/4%2==0?"stationary-serve":"receive-serve";
            if(Task=="serve-context-return")return CombinedServe(index)?"stationary-serve":ContextFlight(index)?"stationary-flight":"varied-return";
            if(Task=="context-range-return"||Task=="flight-return-mix"||Task=="context-flight-return")return index/4%2==0?"stationary-flight":"varied-return";
            if(Task=="fixed-serve-return")return index/4%2==0?"stationary-serve":"varied-return";
            if(Task=="falling-return")return index/4%2==0?"falling-contact":"varied-return";
            if(Task=="stationary-return")return index/4%2==0?"stationary-contact":"varied-return";
            if(Task=="stationary-practice")return "stationary-contact";
            if(Task=="serve-practice-return")return index/4%4==0?"drop-contact":index/4%4==2?"varied-return":"low-return";
            if(Task=="focused-lateral-return")return index/4%8==1||index/4%8==5?"varied-return":"low-return";
            return Task=="serve-return"?(index/4%2==0?"drop-serve":"varied-return")
                :Task=="contact-return"?(index/4%2==0?"drop-contact":"varied-return")
                :(Task=="low-high-return"||Task=="mixed-height-return"||Task=="lateral-practice-return")?(index/4%2==0?"low-return":"varied-return"):Task;
        }
        // Reset-only curriculum: five equally represented height levels, with
        // each level covering four seats and alternating with varied returns.
        // FeedLowering is the maximum offset for this task; old tasks retain
        // their fixed setting. No sampled command or body target is introduced.
        public float FeedLoweringForEpisode(int index)
        {
            if(index<0)throw new ArgumentOutOfRangeException(nameof(index));
            if(Task=="serve-context-return"||Task=="context-range-return"||Task=="context-flight-return"||Task=="flight-return-mix"||Task=="fixed-serve-return")return 0;
            if((Task=="stationary-return"||Task=="falling-return")&&index/4%2!=0)return 0;
            if(IsVariedContactEpisode(index))return FeedLowering*StationaryResetFractions(checked(FirstSeed+index)).x;
            if(Task=="serve-practice-return")return index/4%2==0?0:FeedLowering+(index/4%8==3?.1f:0);
            if(Task=="focused-lateral-return")return index/4%8==1||index/4%8==5?0:FeedLowering+(index/4%8==7?.1f:0);
            if(Task=="lateral-practice-return")return index/4%2!=0?0:FeedLowering+(index/8%4==3?.1f:0);
            if(Task!="mixed-height-return")return FeedLowering;
            return index/4%2==0?FeedLowering*((index/8%5)*.25f):0;
        }
        // Four low-feed conditions, each covering all seats and separated
        // by varied returns. Only reset placement changes; actions stay learned.
        public float FeedLateralOffsetForEpisode(int index)
        {
            if(index<0)throw new ArgumentOutOfRangeException(nameof(index));
            if(Task=="serve-context-return"||Task=="context-range-return"||Task=="context-flight-return"||Task=="flight-return-mix"||Task=="fixed-serve-return")return 0;
            if((Task=="stationary-return"||Task=="falling-return")&&index/4%2!=0)return 0;
            if(IsVariedContactEpisode(index))return FeedLateralOffset*StationaryResetFractions(checked(FirstSeed+index)).y;
            if(Task=="serve-practice-return")
            {
                int slot=index/4%8;
                return slot==1||slot==5?FeedLateralOffset:slot==7?FeedLateralOffset*.5f:0;
            }
            if(Task=="focused-lateral-return")
            {
                int slot=index/4%8;
                return slot%2==0?FeedLateralOffset:slot==3?FeedLateralOffset*.5f:0;
            }
            if(Task!="lateral-practice-return")return FeedLateralOffset;
            int condition=index/8%4;
            return index/4%2!=0||condition==3?0:FeedLateralOffset*(condition*.5f);
        }
        public static void ValidateStationaryFlightDifficulty(float difficulty,string task)
        {
            if(!float.IsFinite(difficulty)||difficulty<0||difficulty>1||(task!="flight-return-mix"&&task!="context-flight-return"&&task!="context-range-return"&&task!="serve-context-return"&&task!="rally-maintenance"&&task!="paired-maintenance"&&difficulty!=0))
                throw new ArgumentException("Stationary-flight distance is a finite 0..1 parameter for flight-return-mix only.");
        }
        public static void ValidateFixedServeSides(string mode,string task)
        {
            if(mode!="right"&&mode!="left"&&mode!="both")throw new ArgumentException("Unknown fixed serve side selection.");
            if(mode!="right"&&!PlayerContactDrillV3.IsFixedServeTask(task)&&task!="fixed-serve-return"&&task!="serve-context-return"&&task!="serve-receive"&&task!="receive-maintenance"&&task!="receive-varied-maintenance"&&task!="rally-maintenance"&&task!="paired-maintenance"&&!IsMovementTask(task))throw new ArgumentException("Service side selection requires fixed serve practice.");
        }
        public bool ServeFromLeftForEpisode(int index)
        {
            if(index<0)throw new ArgumentOutOfRangeException(nameof(index));
            ValidateFixedServeSides(FixedServeSides,Task);
            if(!PlayerContactDrillV3.IsFixedServeTask(TaskForEpisode(index)))return false;
            if(MovementRecoveryMix)return FixedServeSides=="left"||FixedServeSides=="both"&&Recovery(index).ServeFromLeft;
            if(MovementPractice)return FixedServeSides=="left"||FixedServeSides=="both"&&index/4%16==1;
            if(Task=="rally-maintenance"||CooperativePairs)return FixedServeSides=="left"||FixedServeSides=="both"&&index/4%8==1;
            if(Task=="receive-varied-maintenance")return FixedServeSides=="left"||FixedServeSides=="both"&&index/16%2==1;
            if(Task=="receive-maintenance")return FixedServeSides=="left"||FixedServeSides=="both"&&index/8%2==1;
            return FixedServeSides=="left" || FixedServeSides=="both" && ((Task=="fixed-serve-return"||Task=="serve-context-return"||Task=="serve-receive")?index/8:index/4)%2==1;
        }
        public float HoldLiftForEpisode(int index)
        {if(index<0)throw new ArgumentOutOfRangeException(nameof(index));return PlayerContactDrillV3.IsDropTask(TaskForEpisode(index))?InitialHoldLift:0;}
        public int AllocationIndexForOrdinal(int ordinal)=>PlayerInterleavedRecoveryV3.Index(ordinal,SchedulerWorkerId,InterleavedRecovery);
        private int TakeSeedIndex() { return nextSeedIndex < SeedCount ? AllocationIndexForOrdinal(nextSeedIndex++) : -1; }
        public void InitializeRun()
        {
            if((CooperativePairs||MovementPractice)&&BackgroundModel!=null)throw new ArgumentException("Paired practice has two learning teammates and idle opposing bodies.");
            if((Task=="receive-serve"||Task=="serve-receive")&&BackgroundModel==null)throw new InvalidOperationException("Receiving a learned serve requires background policies.");
            if(RequireTrainer&&(Task=="falling-contact"||Task=="falling-return"))throw new InvalidOperationException("Freely falling drills are retired from training; retained for historical evaluation only.");
            ValidateFixedServeSides(FixedServeSides,Task);
            ValidateStationaryFlightDifficulty(StationaryFlightDifficulty,Task);
            if (initialized) throw new InvalidOperationException("Already initialized.");
            if (!gameObject.activeInHierarchy) throw new InvalidOperationException("Activate the run root before initialization.");
            if (RequireTrainer && InferenceModel != null) throw new ArgumentException("Use a trainer checkpoint to initialize training; do not mix inference and training modes.");
            int seedMinimum = RequireTrainer ? 1000000 : InferenceModel != null ? 1100000 : 1300000;
            int seedMaximum = seedMinimum + 100000;
            if (!float.IsFinite(FeedLowering) || FeedLowering < 0 || FeedLowering > .9f) throw new ArgumentOutOfRangeException(nameof(FeedLowering));
            if ((Task=="lateral-practice-return"||Task=="focused-lateral-return"||Task=="serve-practice-return") && FeedLowering>.8f) throw new ArgumentOutOfRangeException(nameof(FeedLowering));
            if (!float.IsFinite(FeedLateralOffset) || Mathf.Abs(FeedLateralOffset) > .9f) throw new ArgumentOutOfRangeException(nameof(FeedLateralOffset));
            if (float.IsNaN(MaximumReturnDifficulty) || MaximumReturnDifficulty < 0 || MaximumReturnDifficulty > 1) throw new ArgumentOutOfRangeException(nameof(MaximumReturnDifficulty));
            ValidateMovement(Task,MovementRange,MovementTiming,MovementStartVariation);
            ValidateMovementPositionReward(Task,MovementRange,MovementPositionReward);
            ValidateMovementForwardProgressReward(Task,MovementRange,MovementForwardProgressReward);
            ValidatePrecontactAlignment(Task,MovementRange,PrecontactAlignmentReward,PrecontactGamma,MovementForwardProgressReward,MovementPositionReward);
            ValidateMovementRehearsal(Task,MovementRehearsalRange);
            PlayerRecoveryScheduleV3.Validate(MovementRecoveryMix,Task,MovementRange,MovementRehearsalRange,MovementPattern,MovementTiming,MovementStartVariation,MovementPositionReward,SeedCount);
            PlayerInterleavedRecoveryV3.Validate(InterleavedRecovery,MovementRecoveryMix,SeedCount,SchedulerWorkerId);
            if(OptimizerDiagnostics){if(!RequireTrainer||!MovementRecoveryMix)throw new ArgumentException("Optimizer diagnostics require recovery training.");PlayerDrillDiagnosticsV3.ValidatePinnedContract();}
            if(MovementRehearsalRange>0&&SeedCount%128!=0)throw new ArgumentException("Rehearsal allocations must cover complete 128-episode mixtures.");
            PlayerMovementPatternV3.Validate(MovementPattern,MovementRange,Task=="movement-maintenance");
            if ((!PlayerContactDrillV3.ValidTask(Task) && !MovementPractice && Task != "paired-maintenance" && Task != "rally-maintenance" && Task != "receive-varied-maintenance" && Task != "receive-maintenance" && Task != "serve-receive" && Task != "serve-context-return" && Task != "context-range-return" && Task != "context-flight-return" && Task != "flight-return-mix" && Task != "fixed-serve-return" && Task != "falling-return" && Task != "stationary-return" && Task != "stationary-practice" && Task != "serve-return" && Task != "contact-return" && Task != "low-high-return" && Task != "mixed-height-return" && Task != "lateral-practice-return" && Task != "focused-lateral-return" && Task != "serve-practice-return") || ArenaCount < 1 || ArenaCount > 32 || SeedCount < ArenaCount
                || TicksPerFrame < 1 || FirstSeed < seedMinimum || (long)FirstSeed + SeedCount > seedMaximum)
                throw new ArgumentException("Invalid or non-training drill allocation.");
            if(!float.IsFinite(InitialHoldLift)||InitialHoldLift<0||InitialHoldLift>140|| (InitialHoldLift!=0&&!PlayerContactDrillV3.IsDropTask(Task)&&Task!="serve-return"&&Task!="contact-return"&&Task!="serve-practice-return"))throw new ArgumentOutOfRangeException(nameof(InitialHoldLift));
            ExecutionGoals = GetComponent<PlayerExecutionDrillsV1>();
            if (ExecutionGoals != null && !ExecutionGoals.enabled) ExecutionGoals = null;
            ExecutionGoals?.Prepare(this);
            var academy = Academy.Instance;
            academy.AutomaticSteppingEnabled = false;
            if (!RequireTrainer && academy.IsCommunicatorOn) throw new InvalidOperationException("Evaluation cannot connect to a Python trainer.");
            if (RequireTrainer && !academy.IsCommunicatorOn) throw new InvalidOperationException("Python trainer is not connected; no heuristic fallback allowed.");
            Report = new MlDrillReportV3 { contract = ExecutionGoals == null ? PlayerMlAgentV3.ContractVersion : PlayerExecutionGoalV1.Contract, status = "running", task = Task, fixedServeSides = FixedServeSides, activePracticePlayers=BackgroundModel!=null, cooperativePairs=CooperativePairs, randomMatchContext=RandomizeMatchContext, firstSeed = FirstSeed, seedCount = SeedCount,
                arenas = ArenaCount, sourceIdentity = SourceIdentity, unityVersion = Application.unityVersion,
                interleavedRecovery=InterleavedRecovery,optimizerDiagnostics=OptimizerDiagnostics,schedulerWorkerId=SchedulerWorkerId,movementRecoveryMix=MovementRecoveryMix,movementRehearsalRange=MovementRehearsalRange,movementRange=MovementRange,movementTiming=MovementTiming,movementStartVariation=MovementStartVariation,movementPositionReward=MovementPositionReward,movementForwardProgressReward=MovementForwardProgressReward,precontactAlignmentReward=PrecontactAlignmentReward,precontactGamma=PrecontactGamma,movementPattern=MovementPattern, initialHoldLift = InitialHoldLift, stationaryFlightDifficulty = StationaryFlightDifficulty, maximumReturnDifficulty = MaximumReturnDifficulty, feedLowering = FeedLowering, feedLateralOffset = FeedLateralOffset, trainerConnected = academy.IsCommunicatorOn, alignedDecisions = AlignDrillDecisions, split = RequireTrainer ? "training" : InferenceModel != null ? "development" : "interactive" };
            if (!string.IsNullOrEmpty(EvidenceDirectory))
            {
                Directory.CreateDirectory(EvidenceDirectory);
                evidence = new StreamWriter(new FileStream(Path.Combine(EvidenceDirectory, "episodes.jsonl"), FileMode.CreateNew));
                evidence.AutoFlush = true;
                if (RecordDecisions)
                {
                    decisionEvidence = new StreamWriter(new FileStream(Path.Combine(EvidenceDirectory, "decisions.jsonl"), FileMode.CreateNew));
                    decisionEvidence.AutoFlush = true;
                }
            }
            initialized = true;
            for (int i = 0; i < ArenaCount; i++) arenas.Add(new Arena(this));
            SaveReport();
        }
        private void Start() { if (!initialized) InitializeRun(); }
        private void Update()
        {
            if (!initialized || !AutoRun || stopped) return;
            try { for (int i = 0; i < TicksPerFrame && !stopped; i++) StepOneTick(); }
            catch (Exception error)
            {
                stopped = true; Report.status = "failed"; Report.failure = error.ToString(); SaveReport(); Debug.LogException(error);
            }
        }
        public void StepOneTick()
        {
            if (!initialized || stopped) throw new InvalidOperationException("Run is not active.");
            int requested = 0;
            foreach (var arena in arenas) if (arena.Request()) requested+=CooperativePairs?2:1;
            Report.requestedDecisions += requested;
            if (requested > 0) Report.decisionBatches++;
            // All observations/decisions are exchanged before any world advances.
            Academy.Instance.EnvironmentStep();
            foreach (var arena in arenas) arena.Step();
            Report.schedulerTicks++;
            Report.nextSeedIndex = nextSeedIndex;
            Report.decisions = arenas.Sum(a => a.Agents.Sum(p => p.DecisionsReceived));
            Report.backgroundDecisions=arenas.Sum(a=>a.BackgroundAgents.Where(p=>p!=null).Sum(p=>p.DecisionsReceived));
            if (arenas.All(a => a.Finished))
            {
                stopped = true; Report.status = "seed_budget_complete";
                Academy.Instance.EnvironmentStep(); // Flush final terminal transitions.
                SaveReport();
            }
        }
        private MlDecisionV3 RecordDecision(PlayerContactDrillV3 drill, PlayerMlAgentV3 agent, ActionBuffers actions,bool background=false)
        {
            if (decisionEvidence == null && string.IsNullOrEmpty(EvidenceDirectory)) return null;
            var row = new MlDecisionV3 { backgroundPolicy=background, seed = drill.Seed, player = agent.Seat, observationTick = agent.ObservedTick, task = drill.Task, serveFromLeft = drill.ServeFromLeft,
                observation = agent.LastPolicyObservation, physical = agent.LastCommand.ToArray(),
                continuous = actions.ContinuousActions.ToArray(), release = actions.DiscreteActions[0],
                canRelease = PlayerContactDrillV3.IsDropTask(drill.Task) && drill.Match.BallHeld && drill.Match.World.Rules.Server == agent.Seat };
            decisionEvidence?.WriteLine(JsonUtility.ToJson(row));
            return row;
        }
        private void RecordSimulationFailure(PlayerContactDrillV3 drill,List<MlDecisionV3> trace)
        {
            if(string.IsNullOrEmpty(EvidenceDirectory))return;
            // Only the current episode is retained in memory. Dump on failure,
            // before reward or terminal submission; never feed this diagnostic to PPO.
            var record=new MlSimulationFailureV3{sourceIdentity=SourceIdentity,task=drill.Task,serveFromLeft=drill.ServeFromLeft,rallyServer=drill.RallyServer??-1,rallyServerOnRight=drill.RallyServerOnRight,randomMatchContext=drill.RandomMatchContext,
                seed=drill.Seed,player=drill.Player,rejectedPlayer=drill.Match.Controls.RejectedPlayer,
                physicsTick=drill.Match.Tick,outcome=drill.Outcome,error=drill.Match.Failure,inactivePlayerCommandsAreZero=BackgroundModel==null,
                maximumReturnDifficulty=DifficultyForEpisode(drill.Seed-FirstSeed),feedLowering=drill.FeedLowering,
                initialHoldLift=drill.InitialHoldLift,feedLateralOffset=drill.FeedLateralOffset,decisions=trace.ToArray()};
            using(var output=new StreamWriter(new FileStream(Path.Combine(EvidenceDirectory,"simulation-failure.json"),FileMode.CreateNew)))
                output.Write(JsonUtility.ToJson(record,true));
        }
        private void Record(MlDrillEpisodeV3 episode)
        {
            Episodes.Add(episode); Report.completedEpisodes = Episodes.Count;
            evidence?.WriteLine(JsonUtility.ToJson(episode));
            var stats = Academy.Instance.StatsRecorder;
            if(CooperativePairs&&!PlayerContactDrillV3.IsServeTask(episode.task)) { stats.Add("Picklebot/Pairs/LegalTeamReturn",episode.outcome=="legal_return"?1:0);stats.Add("Picklebot/Pairs/PartnerHit",episode.hitter>=0&&episode.hitter!=episode.player?1:0); }
            if(episode.movementFeed) {
                string movement="Picklebot/Movement/"+(episode.task=="rally-air-feed"?"Air/":"Bounce/")+(episode.movementRange==0?"Retained/":"Challenge/");
                stats.Add(movement+"Pattern/"+episode.movementPattern+"/LegalReturn",episode.outcome=="legal_return"?1:0);
                stats.Add(movement+"PositionReward",episode.movementPositionReward);
                stats.Add(movement+"ForwardProgressRewardEnabled",episode.movementForwardProgressRewardEnabled?1:0);
                stats.Add(movement+"ForwardProgressReward",episode.movementForwardProgressReward);
                stats.Add(movement+"ForwardProgressRewardedSteps",episode.movementForwardProgressRewardedSteps);
                stats.Add(movement+"LegalReturn",episode.outcome=="legal_return"?1:0);
                stats.Add(movement+"FaceContact",episode.faceContact?1:0);
                stats.Add(movement+"NetCrossed",episode.netCrossed?1:0);
                stats.Add(movement+"ReturnAfterHalfMetreMove",episode.outcome=="legal_return"&&episode.contactDisplacement>=.5f?1:0);
                if(episode.faceContact){stats.Add(movement+"ContactDisplacementMetres",episode.contactDisplacement);stats.Add(movement+"ContactFromStartMetres",episode.contactDistanceFromStart);}
                if(episode.movementRange>0)stats.Add(movement+"Region"+episode.movementRegion+"/LegalReturn",episode.outcome=="legal_return"?1:0);
            }
            stats.Add("Picklebot/Precontact/Enabled",episode.precontactAlignmentRewardEnabled?1:0);
            if(episode.precontactAlignmentRewardEnabled){stats.Add("Picklebot/Precontact/ShapingReward",episode.precontactShapingReward);stats.Add("Picklebot/Precontact/AccountingError",(float)Math.Abs(episode.precontactDiscountedReward+episode.precontactInitialPotential));}
            stats.Add("Picklebot/FaceContact", episode.faceContact ? 1 : 0);
            // Alignment is conditional on recorded accepted contact; misses are not zero-angle samples.
            stats.Add("Picklebot/ContactQuality/Measured",episode.faceContactNormalAlignment>=0?1:0);
            if(episode.faceContactNormalAlignment>=0)stats.Add("Picklebot/ContactQuality/NormalAlignment",episode.faceContactNormalAlignment);

            stats.Add("Picklebot/NetCrossed", episode.netCrossed ? 1 : 0);
            stats.Add("Picklebot/LegalReturn", episode.outcome == "legal_return" ? 1 : 0);
            stats.Add("Picklebot/LegalServe", episode.outcome == "legal_serve" ? 1 : 0);
            stats.Add("Picklebot/BodyOrHandle", episode.outcome == "body_or_handle" ? 1 : 0);
            stats.Add("Picklebot/Infeasible", episode.outcome == "infeasible" ? 1 : 0);
            // Task-specific means use that task's completed attempts as denominator.
            string prefix="Picklebot/"+episode.task+"/";
            stats.Add(prefix+"LegalReturn",episode.outcome=="legal_return"?1:0);
            stats.Add(prefix+"LegalServe",episode.outcome=="legal_serve"?1:0);
            stats.Add(prefix+"FaceContact",episode.faceContact?1:0);
            if(episode.faceContactNormalAlignment>=0)stats.Add(prefix+"ContactNormalAlignment",episode.faceContactNormalAlignment);
            stats.Add(prefix+"FeedLowering",episode.feedLowering);
            stats.Add(prefix+"FeedLateralOffset",episode.feedLateralOffset);
            if(episode.faceContact)stats.Add(prefix+"ContactBallHeight",episode.faceContactBallHeight);
            if(PlayerContactDrillV3.IsRallyFeed(episode.task))
            {
                stats.Add(prefix+"LegalVolley",episode.outcome=="legal_return"&&episode.contactWasVolley?1:0);
                stats.Add(prefix+"LegalGroundstroke",episode.outcome=="legal_return"&&!episode.contactWasVolley?1:0);
                stats.Add(prefix+"KitchenFault",episode.terminalFault=="KitchenVolley"||episode.terminalFault=="KitchenMomentum"?1:0);
                stats.Add(prefix+"NetCrossed",episode.netCrossed?1:0);
            }
            stats.Add(prefix+"EarlyVolleyFault",episode.terminalFault=="EarlyVolley"?1:0);
            if(episode.task=="receive-feed")
            {
                string feedPrefix=prefix+(episode.feedDifficulty==0?"easy/":"varied/");
                stats.Add(feedPrefix+"LegalReturn",episode.outcome=="legal_return"?1:0);
                stats.Add(feedPrefix+"FaceContact",episode.faceContact?1:0);
                stats.Add(feedPrefix+"NetCrossed",episode.netCrossed?1:0);
            }
            if(PlayerContactDrillV3.IsFixedServeTask(episode.task))
            {
                string sidePrefix=prefix+(episode.serveFromLeft?"left/":"right/");
                stats.Add(sidePrefix+"LegalServe",episode.outcome=="legal_serve"?1:0);
                stats.Add(sidePrefix+"FaceContact",episode.faceContact?1:0);
            }
            if(Task=="mixed-height-return"&&episode.task=="low-return")
            {
                string heightPrefix="Picklebot/height-"+Mathf.RoundToInt(episode.feedLowering*100)+"cm/";
                stats.Add(heightPrefix+"LegalReturn",episode.outcome=="legal_return"?1:0);
                stats.Add(heightPrefix+"FaceContact",episode.faceContact?1:0);
                stats.Add(heightPrefix+"BodyOrHandle",episode.outcome=="body_or_handle"?1:0);
            }
            if((Task=="lateral-practice-return"||Task=="focused-lateral-return"||Task=="serve-practice-return")&&episode.task=="low-return")
            {
                string placementPrefix="Picklebot/left-"+Mathf.RoundToInt(-episode.feedLateralOffset*100)+"cm-lower-"+Mathf.RoundToInt(episode.feedLowering*100)+"cm/";
                stats.Add(placementPrefix+"LegalReturn",episode.outcome=="legal_return"?1:0);
                stats.Add(placementPrefix+"FaceContact",episode.faceContact?1:0);
                stats.Add(placementPrefix+"BodyOrHandle",episode.outcome=="body_or_handle"?1:0);
            }
            if(PlayerContactDrillV3.IsDropTask(episode.task))
            {
                stats.Add(prefix+"ServeContact",episode.outcome=="serve_contact"?1:0);
                stats.Add(prefix+"Released",episode.released?1:0);
                stats.Add(prefix+"DropBounced",episode.dropBounced?1:0);
            }
            if (Episodes.Count % 32 == 0) SaveReport();
        }
        private void SaveReport()
        {
            if (!string.IsNullOrEmpty(EvidenceDirectory) && Report != null)
                File.WriteAllText(Path.Combine(EvidenceDirectory, "report.json"), JsonUtility.ToJson(Report, true));
        }
        private void OnDestroy()
        {
            foreach (var arena in arenas) arena.Dispose();
            arenas.Clear(); evidence?.Dispose(); decisionEvidence?.Dispose();
            if (Report != null && Report.status == "running") Report.status = "stopped";
            SaveReport();
            if (Academy.IsInitialized) Academy.Instance.AutomaticSteppingEnabled = true;
        }
    }
}


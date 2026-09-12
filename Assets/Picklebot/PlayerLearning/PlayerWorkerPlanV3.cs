using System;
using System.IO;
using System.Linq;
using Picklebot.PlayerControlsIntegration;
using Unity.InferenceEngine;

namespace Picklebot.PlayerLearning
{
    [Serializable]
    public sealed class PlayerWorkerManifestV3
    {
        public string version, mode, task, sourceIdentity, buildIdentity, modelHash, evidenceRoot;
        public int basePort, workerCount, firstSeed, seedsPerWorker, arenasPerWorker, ticksPerFrame;
        public int maximumRallies=300, maximumGameTicks=864000;
        public string fixedServeSides="right";
        public float maximumReturnDifficulty, stationaryFlightDifficulty, feedLowering, feedLateralOffset, initialHoldLift;
        public bool alignedDecisions, recordDecisions, randomMatchContext, movementRecoveryMix, interleavedRecovery, optimizerDiagnostics;
        public bool movementForwardProgressReward,precontactAlignmentReward;
        public float precontactGamma=PlayerPrecontactPotentialV3.Gamma;
        public string movementPattern="court";
        public float movementRange,movementTiming,movementStartVariation,movementPositionReward,movementRehearsalRange;
        public string backgroundModelHash;
        public string executionContract;
        public bool sampleShotTargets;
        public string targetLayout="random";
        public string placementRewardMode=PlayerExecutionDrillsV1.LinearReward;
        public float targetRadius=1.5f, legalTargetReward=.25f;
    }

    // Startup allocation only. No access to live balls, bodies, actions or rewards.
    public sealed class PlayerWorkerPlanV3
    {
        public const string Version="player-worker-manifest-v1";
        public readonly int WorkerId, FirstSeed, SeedCount;
        public readonly string EvidenceDirectory;
        public readonly bool RequireTrainer;
        public bool IsTeamMatch => Manifest.task=="fixed-team-match";
        public readonly PlayerWorkerManifestV3 Manifest;
        private PlayerWorkerPlanV3(PlayerWorkerManifestV3 manifest,int workerId)
        {
            Manifest=manifest;WorkerId=workerId;SeedCount=manifest.seedsPerWorker;
            FirstSeed=checked(manifest.firstSeed+workerId*SeedCount);
            RequireTrainer=manifest.mode=="training";
            EvidenceDirectory=Path.Combine(Path.GetFullPath(manifest.evidenceRoot),"worker-"+workerId.ToString("D2"));
        }
        public static bool IsHash(string s)=>s!=null&&s.Length==64&&s.All(c=>c>='0'&&c<='9'||c>='a'&&c<='f');
        public static int CycleLength(string task,string fixedServeSides="right")=>task==PlayerRightReturnAcquisitionV1.Task?8:PlayerMlDrillsV3.IsMovementTask(task)?64:task=="paired-maintenance"?32:task=="rally-maintenance"?32:task=="receive-varied-maintenance"?32:task=="receive-maintenance"?16:task=="serve-receive"?16:task=="serve-context-return"?256:task=="context-range-return"?128:task=="context-flight-return"?64:fixedServeSides=="both"&&(task=="fixed-serve-return"||PlayerContactDrillV3.IsFixedServeTask(task))?(task=="fixed-serve-return"?16:8):task=="mixed-height-return"?40:(task=="lateral-practice-return"||task=="focused-lateral-return"||task=="serve-practice-return")?32:
            task=="flight-return-mix"||task=="fixed-serve-return"||task=="falling-return"||task=="stationary-return"||task=="serve-return"||task=="contact-return"||task=="low-high-return"?8:4;
        public static PlayerWorkerPlanV3 Create(PlayerWorkerManifestV3 manifest,int workerId)
        {
            if(manifest==null||manifest.version!=Version)throw new ArgumentException("Unknown worker manifest version.");
            bool execution = !string.IsNullOrEmpty(manifest.executionContract);
            PlayerExecutionDrillsV1.ValidateLayout(manifest.targetLayout,manifest.sampleShotTargets,manifest.targetRadius);
            PlayerExecutionDrillsV1.ValidateRewardMode(manifest.placementRewardMode);
            if(manifest.placementRewardMode!=PlayerExecutionDrillsV1.LinearReward&&(!execution||!manifest.sampleShotTargets))throw new ArgumentException("Smooth placement feedback requires an active execution target contract.");
            if(!execution && manifest.targetLayout!="random")throw new ArgumentException("Target layout requires execution contract.");
            if(execution && manifest.executionContract!=PlayerExecutionGoalV1.Contract)throw new ArgumentException("Unknown execution contract.");
            if(!execution && manifest.sampleShotTargets)throw new ArgumentException("Shot targets require the execution contract.");
            if(execution && (manifest.task=="fixed-team-match" || manifest.task=="paired-maintenance" || manifest.task=="paired-movement-maintenance" || manifest.optimizerDiagnostics || !string.IsNullOrEmpty(manifest.backgroundModelHash)))throw new ArgumentException("Execution v1 currently supports solo practice only.");
            if(execution && (!float.IsFinite(manifest.targetRadius)||manifest.targetRadius<=0||manifest.targetRadius>3||!float.IsFinite(manifest.legalTargetReward)||manifest.legalTargetReward<0||manifest.legalTargetReward>.25f))throw new ArgumentException("Invalid execution target parameters.");
            if(manifest.mode!="training"&&manifest.mode!="evaluation")throw new ArgumentException("Explicit training/evaluation mode required.");
            if(manifest.mode=="training"&&(manifest.task=="falling-contact"||manifest.task=="falling-return"))throw new ArgumentException("Freely falling drills are retired from training; use stationary contact and held-ball serve practice.");
            if(manifest.task!="fixed-team-match"&&!PlayerContactDrillV3.ValidTask(manifest.task)&&!PlayerMlDrillsV3.IsMovementTask(manifest.task)&&manifest.task!="paired-maintenance"&&manifest.task!="rally-maintenance"&&manifest.task!="receive-varied-maintenance"&&manifest.task!="receive-maintenance"&&manifest.task!="serve-receive"&&manifest.task!="serve-context-return"&&manifest.task!="context-range-return"&&manifest.task!="context-flight-return"&&manifest.task!="flight-return-mix"&&manifest.task!="fixed-serve-return"&&manifest.task!="falling-return"&&manifest.task!="stationary-return"&&manifest.task!="stationary-practice"&&manifest.task!="serve-return"&&manifest.task!="contact-return"&&manifest.task!="low-high-return"&&manifest.task!="mixed-height-return"&&manifest.task!="lateral-practice-return"&&manifest.task!="focused-lateral-return"&&manifest.task!="serve-practice-return")throw new ArgumentException("Unknown task.");
            if(manifest.workerCount<1||manifest.workerCount>8||workerId<0||workerId>=manifest.workerCount||manifest.arenasPerWorker<1||manifest.arenasPerWorker>32||(long)manifest.workerCount*manifest.arenasPerWorker>256)throw new ArgumentException("Invalid worker/arena allocation.");
            if(manifest.seedsPerWorker<manifest.arenasPerWorker||manifest.seedsPerWorker%CycleLength(manifest.task,manifest.fixedServeSides)!=0||manifest.ticksPerFrame<1||manifest.ticksPerFrame>256)throw new ArgumentException("Allocation must cover complete seat/curriculum cycles.");
            int minimum=manifest.mode=="training"?1000000:1100000;
            long end=(long)manifest.firstSeed+(long)manifest.workerCount*manifest.seedsPerWorker;
            if(manifest.firstSeed<minimum||end>minimum+100000L)throw new ArgumentException("Entire worker allocation must stay in its declared seed split; final seeds are forbidden.");
            if(manifest.basePort<1024||(long)manifest.basePort+manifest.workerCount>65536)throw new ArgumentException("Invalid communicator port allocation.");
            if(!IsHash(manifest.sourceIdentity)||!IsHash(manifest.buildIdentity)||(manifest.mode=="evaluation"&&!IsHash(manifest.modelHash)))throw new ArgumentException("Pinned source/build/model identities required.");
            if(string.IsNullOrWhiteSpace(manifest.evidenceRoot)||!Path.IsPathFullyQualified(manifest.evidenceRoot))throw new ArgumentException("Absolute evidence root required.");
            string evidence=Path.GetFullPath(manifest.evidenceRoot);
            if(evidence.TrimEnd(Path.DirectorySeparatorChar,Path.AltDirectorySeparatorChar)==Path.GetPathRoot(evidence).TrimEnd(Path.DirectorySeparatorChar,Path.AltDirectorySeparatorChar))throw new ArgumentException("Evidence root cannot be a drive root.");
            if(!float.IsFinite(manifest.maximumReturnDifficulty)||manifest.maximumReturnDifficulty<0||manifest.maximumReturnDifficulty>1||!float.IsFinite(manifest.feedLowering)||manifest.feedLowering<0||manifest.feedLowering>.9f||!float.IsFinite(manifest.feedLateralOffset)||Math.Abs(manifest.feedLateralOffset)>.9f)throw new ArgumentException("Invalid feed parameters.");
            if((manifest.task=="lateral-practice-return"||manifest.task=="focused-lateral-return"||manifest.task=="serve-practice-return")&&manifest.feedLowering>.8f)throw new ArgumentException("Retained height exceeds physical reset range.");
            if(!float.IsFinite(manifest.initialHoldLift)||manifest.initialHoldLift<0||manifest.initialHoldLift>140||(manifest.initialHoldLift!=0&&!PlayerContactDrillV3.IsDropTask(manifest.task)&&manifest.task!="serve-return"&&manifest.task!="contact-return"&&manifest.task!="serve-practice-return"))throw new ArgumentException("Invalid held-ball reset angle.");
            if(!string.IsNullOrEmpty(manifest.backgroundModelHash)&&(!IsHash(manifest.backgroundModelHash)||manifest.task=="fixed-team-match"))throw new ArgumentException("Frozen practice players require a pinned model and a drill task.");
            if((manifest.task=="receive-serve"||manifest.task=="serve-receive")&&string.IsNullOrEmpty(manifest.backgroundModelHash))throw new ArgumentException("Learned server model required.");
            if((manifest.task=="paired-maintenance"||PlayerMlDrillsV3.IsMovementTask(manifest.task))&&!string.IsNullOrEmpty(manifest.backgroundModelHash))throw new ArgumentException("Paired practice cannot use frozen practice actors.");
            if(manifest.randomMatchContext&&manifest.task!="serve-context-return"&&manifest.task!="receive-serve"&&manifest.task!="serve-receive")throw new ArgumentException("Match-state randomization requires combined practice.");
            if(manifest.task=="fixed-team-match" && (manifest.arenasPerWorker>16 || manifest.maximumRallies<1 || manifest.maximumRallies>300 || manifest.maximumGameTicks<1 || manifest.maximumGameTicks>864000 || manifest.feedLowering!=0 || manifest.feedLateralOffset!=0 || manifest.initialHoldLift!=0 || manifest.maximumReturnDifficulty!=0 || manifest.recordDecisions))
                throw new ArgumentException("Team matches require explicit bounded game limits, no drill feed parameters, and no unsupported decision recording.");
            PlayerMlDrillsV3.ValidateMovement(manifest.task,manifest.movementRange,manifest.movementTiming,manifest.movementStartVariation);
            PlayerMlDrillsV3.ValidateMovementPositionReward(manifest.task,manifest.movementRange,manifest.movementPositionReward);
            PlayerMlDrillsV3.ValidateMovementForwardProgressReward(manifest.task,manifest.movementRange,manifest.movementForwardProgressReward);
            PlayerMlDrillsV3.ValidatePrecontactAlignment(manifest.task,manifest.movementRange,manifest.precontactAlignmentReward,manifest.precontactGamma,manifest.movementForwardProgressReward,manifest.movementPositionReward);
            PlayerMlDrillsV3.ValidateMovementRehearsal(manifest.task,manifest.movementRehearsalRange);
            PlayerRecoveryScheduleV3.Validate(manifest.movementRecoveryMix,manifest.task,manifest.movementRange,manifest.movementRehearsalRange,manifest.movementPattern,manifest.movementTiming,manifest.movementStartVariation,manifest.movementPositionReward,manifest.seedsPerWorker);
            PlayerInterleavedRecoveryV3.Validate(manifest.interleavedRecovery,manifest.movementRecoveryMix,manifest.seedsPerWorker,workerId);
            if(manifest.optimizerDiagnostics&&(manifest.mode!="training"||!manifest.movementRecoveryMix))throw new ArgumentException("Optimizer diagnostics require recovery training.");
            if(manifest.movementRehearsalRange>0&&manifest.seedsPerWorker%128!=0)throw new ArgumentException("Rehearsal worker allocation must cover complete 128-episode mixtures.");
            PlayerRightReturnAcquisitionV1.Validate(manifest.task,manifest.movementRange,manifest.movementPattern,manifest.movementRecoveryMix,manifest.movementRehearsalRange,manifest.interleavedRecovery,manifest.movementTiming,manifest.movementStartVariation,manifest.maximumReturnDifficulty);
            PlayerMovementPatternV3.Validate(manifest.movementPattern,manifest.movementRange,manifest.task=="movement-maintenance"||manifest.task==PlayerRightReturnAcquisitionV1.Task);
            PlayerMlDrillsV3.ValidateStationaryFlightDifficulty(manifest.stationaryFlightDifficulty,manifest.task);
            PlayerMlDrillsV3.ValidateFixedServeSides(manifest.fixedServeSides,manifest.task);
            return new PlayerWorkerPlanV3(manifest,workerId);
        }
        public static string Argument(string[] args,string name,bool required=false)
        {
            var indices=Enumerable.Range(0,args.Length).Where(i=>args[i]==name).ToArray();
            if(indices.Length>1||indices.Length==1&&(indices[0]+1>=args.Length||args[indices[0]+1].StartsWith("--")))throw new ArgumentException("Missing or duplicated "+name);
            if(indices.Length==0){if(required)throw new ArgumentException("Missing "+name);return null;}
            return args[indices[0]+1];
        }
        public static int WorkerFromArguments(PlayerWorkerManifestV3 manifest,string[] args)
        {
            string port=Argument(args,"--mlagents-port"),worker=Argument(args,"--picklebot-worker-index");
            if(manifest.mode=="training")
            {
                if(worker!=null||port==null||!int.TryParse(port,out int value))throw new ArgumentException("Training worker must be identified by its framework port.");
                return checked(value-manifest.basePort);
            }
            if(port!=null||worker==null||!int.TryParse(worker,out int index))throw new ArgumentException("Evaluation needs an explicit worker index and cannot connect to a trainer.");
            return index;
        }
        public void Configure(PlayerMlTeamsV3 run,ModelAsset model)
        {
            if(!IsTeamMatch || run==null || run.gameObject.activeInHierarchy || run.Report!=null)throw new InvalidOperationException("Configure a fresh inactive team match.");
            if(!RequireTrainer&&model==null)throw new ArgumentException("Evaluation cannot fall back to heuristic control.");
            run.FirstSeed=FirstSeed;run.SeedCount=SeedCount;run.ArenaCount=Manifest.arenasPerWorker;
            run.TicksPerFrame=Manifest.ticksPerFrame;run.RequireTrainer=RequireTrainer;
            run.InferenceModel=RequireTrainer?null:model;run.AutoRun=true;
            run.MaximumRallies=Manifest.maximumRallies;run.MaximumGameTicks=Manifest.maximumGameTicks;
            run.EvidenceDirectory=EvidenceDirectory;run.SourceIdentity=Manifest.sourceIdentity;
        }
        public void Configure(PlayerMlDrillsV3 run,ModelAsset model)
        {
            if(IsTeamMatch||run==null||run.gameObject.activeInHierarchy||run.Report!=null)throw new InvalidOperationException("Configure before enabling the drill and its agents.");
            if(!RequireTrainer&&model==null)throw new ArgumentException("Evaluation cannot fall back to heuristic control.");
            if(!string.IsNullOrEmpty(Manifest.backgroundModelHash)&&model==null)throw new ArgumentException("Frozen practice model required.");
            if(!string.IsNullOrEmpty(Manifest.executionContract))
            {
                var goals=run.gameObject.AddComponent<PlayerExecutionDrillsV1>();
                goals.RewardMode=Manifest.placementRewardMode;goals.TargetLayout=Manifest.targetLayout;goals.SampleShotTargets=Manifest.sampleShotTargets;goals.TargetRadius=Manifest.targetRadius;goals.LegalTargetReward=Manifest.legalTargetReward;
            }
            run.BackgroundModel=string.IsNullOrEmpty(Manifest.backgroundModelHash)?null:model;
            run.RandomizeMatchContext=Manifest.randomMatchContext;run.Task=Manifest.task;run.FixedServeSides=Manifest.fixedServeSides;run.FirstSeed=FirstSeed;run.SeedCount=SeedCount;
            run.ArenaCount=Manifest.arenasPerWorker;run.TicksPerFrame=Manifest.ticksPerFrame;
            run.RequireTrainer=RequireTrainer;run.InferenceModel=RequireTrainer?null:model;
            run.AutoRun=true;run.RecordDecisions=Manifest.recordDecisions;run.AlignDrillDecisions=Manifest.alignedDecisions;
            run.FeedLowering=Manifest.feedLowering;run.FeedLateralOffset=Manifest.feedLateralOffset;
            run.InterleavedRecovery=Manifest.interleavedRecovery;run.OptimizerDiagnostics=Manifest.optimizerDiagnostics;run.SchedulerWorkerId=WorkerId;run.MovementRecoveryMix=Manifest.movementRecoveryMix;run.MovementRehearsalRange=Manifest.movementRehearsalRange;run.MovementRange=Manifest.movementRange;run.MovementTiming=Manifest.movementTiming;run.MovementStartVariation=Manifest.movementStartVariation;run.MovementPositionReward=Manifest.movementPositionReward;run.MovementForwardProgressReward=Manifest.movementForwardProgressReward;run.PrecontactAlignmentReward=Manifest.precontactAlignmentReward;run.PrecontactGamma=Manifest.precontactGamma;run.MovementPattern=Manifest.movementPattern;
            run.StationaryFlightDifficulty=Manifest.stationaryFlightDifficulty;run.InitialHoldLift=Manifest.initialHoldLift;run.MaximumReturnDifficulty=Manifest.maximumReturnDifficulty;
            run.EvidenceDirectory=EvidenceDirectory;run.SourceIdentity=Manifest.sourceIdentity;
        }
    }
}

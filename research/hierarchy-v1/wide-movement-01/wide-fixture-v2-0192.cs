// Unity CLI eval-body proposal. NOT executed or compiled yet.
// The owner stays inactive: CreateDrillForEpisode constructs reset geometry only.
// Never call InitializeRun, AttachPolicies, Step, StepAgents, StepOneTick, Simulate,
// RequestDecision, or Academy.EnvironmentStep in this fixture.
// Reserve the exact development block in the ledger BEFORE executing this file.
const int FirstSeed=1109849, SeedCount=512;
const int InspectFirstOrdinal=192, InspectCount=64; // Later batches:64,128,...448.
const string ReservationRun="artifacts/hierarchy-v1/wide-movement-fixture-01";
const string ExpectedSource="5f8c4a10a777ea4c69c0a2ef01831163252a3614bddaaedfe2ab4024d04831c9";
const string Workspace="C:/Users/Admin/Documents/Codex/2026-09-07/https-unity-com-blog-meet-the-7/work/hierarchy-v1";

void Require(bool ok,string message){if(!ok)throw new System.InvalidOperationException(message);}
float[] V(UnityEngine.Vector3 value)=>new[]{value.x,value.y,value.z};
float[] Q(UnityEngine.Quaternion value)=>new[]{value.x,value.y,value.z,value.w};
string Hash(string path){using(var hash=System.Security.Cryptography.SHA256.Create())return System.BitConverter.ToString(hash.ComputeHash(System.IO.File.ReadAllBytes(path))).Replace("-","").ToLowerInvariant();}
string Direction(int region)=>region==3?"left":region==5?"right":region==1?"shallow":region==7?"deep":"not-axis-challenge";
void Increment(System.Collections.Generic.Dictionary<string,int> counts,string key){counts[key]=counts.TryGetValue(key,out int n)?n+1:1;}

Require(UnityEditor.EditorApplication.isPlaying,"Use an isolated empty Play Mode scene; no running evaluation");
Require(!UnityEditor.EditorApplication.isCompiling&&!UnityEditor.EditorApplication.isUpdating,"Editor must have completed compilation/import");
Require(!Unity.MLAgents.Academy.IsInitialized,"Close the previous evaluation Academy before this reset-only fixture");
Require(UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects().Length==0,"The active Play Mode scene must be empty");
Require(UnityEngine.Object.FindObjectsByType<Picklebot.PlayerLearning.PlayerMlDrillsV3>(UnityEngine.FindObjectsInactive.Include).Length==0,"A drill runner already exists");
Require(UnityEngine.Object.FindObjectsByType<Picklebot.Doubles.DoublesContacts>(UnityEngine.FindObjectsInactive.Include).Length==0,"An existing doubles world must be closed first");
Require(SeedCount%64==0&&InspectFirstOrdinal>=0&&InspectCount>0&&InspectCount<=64&&InspectFirstOrdinal+InspectCount<=SeedCount,"Invalid bounded inspection batch");
string repo=System.IO.Path.GetFullPath(System.IO.Path.Combine(UnityEngine.Application.dataPath,".."));
string ledgerPath=System.IO.Path.Combine(repo,"artifacts/player-v3/seed-ledger.json");
var ledger=Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(ledgerPath));
Require((string)ledger["version"]=="player-v3-seed-ledger-1","Unexpected seed ledger schema");
Require(ledger["finalSeedsConsumed"] is Newtonsoft.Json.Linq.JArray finalSeeds&&finalSeeds.Count==0,"Final seed declaration changed");
Require(FirstSeed>=1100000&&(long)FirstSeed+SeedCount<=1200000,"Only the development split is permitted");
int reservations=0;
foreach(var block in (Newtonsoft.Json.Linq.JArray)ledger["developmentBlocks"])
{
    int first=(int)block["firstSeed"],count=(int)block["count"];
    if(FirstSeed<first+count&&FirstSeed+SeedCount>first)
    {
        Require(first==FirstSeed&&count==SeedCount&&(string)block["run"]==ReservationRun,"Proposed reset range overlaps another allocation");
        reservations++;
    }
}
Require(reservations==1,"Reserve the exact proposed block before constructing any reset; this fixture never edits the ledger");

string sourcePath=System.IO.Path.Combine(repo,"artifacts/hierarchy-v1/smooth-distance-01/source-records.json");
var source=Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(sourcePath));
Require((string)source["sourceIdentity"]==ExpectedSource,"Source record identity mismatch");
foreach(var file in ((Newtonsoft.Json.Linq.JObject)source["files"]).Properties())
    Require(Hash(System.IO.Path.Combine(repo,file.Name))==(string)file.Value,"Source changed: "+file.Name);
string ledgerHash=Hash(ledgerPath),sourceRecordHash=Hash(sourcePath);
string output=System.IO.Path.Combine(Workspace,"wide-fixture-"+InspectFirstOrdinal.ToString("D4")+".json");
Require(!System.IO.File.Exists(output),"Refusing to overwrite "+output);

var holder=new UnityEngine.GameObject("Inactive wide movement fixture descriptor");holder.SetActive(false);
var rows=new System.Collections.Generic.List<object>();
var planned=new System.Collections.Generic.List<object>();
var coverage=new System.Collections.Generic.Dictionary<string,int>();
var actualCoverage=new System.Collections.Generic.Dictionary<string,int>();
var missing=new System.Collections.Generic.List<string>();
string result="";
try
{
    var run=holder.AddComponent<Picklebot.PlayerLearning.PlayerMlDrillsV3>();
    run.enabled=false;run.AutoRun=false;run.RequireTrainer=false;
    run.InferenceModel=null;run.BackgroundModel=null;run.EvidenceDirectory=null;
    run.Task="movement-maintenance";run.FirstSeed=FirstSeed;run.SeedCount=SeedCount;
    run.ArenaCount=1;run.MaximumReturnDifficulty=.25f;run.FixedServeSides="both";
    run.MovementRange=.25f;run.MovementPattern="axes";run.MovementRehearsalRange=0;
    run.MovementRecoveryMix=false;run.InterleavedRecovery=false;
    run.MovementTiming=0;run.MovementStartVariation=0;run.MovementPositionReward=0;
    run.RandomizeMatchContext=false;run.FeedLowering=0;run.FeedLateralOffset=0;
    run.InitialHoldLift=0;run.StationaryFlightDifficulty=0;
    Picklebot.PlayerLearning.PlayerMlDrillsV3.ValidateMovement(run.Task,run.MovementRange,0,0);
    Picklebot.PlayerLearning.PlayerMlDrillsV3.ValidateMovementRehearsal(run.Task,0);
    Picklebot.PlayerControlsIntegration.PlayerMovementPatternV3.Validate("axes",.25f,true);

    // Schedule-only pass over the entire reserved cohort. No physical worlds,
    // actors, critic, reward updates, or outcome-based seed selection here.
    for(int index=0;index<SeedCount;index++)
    {
        Require(run.AllocationIndexForOrdinal(index)==index,"Interleaving unexpectedly enabled");
        int seed=FirstSeed+index,player=index%4;
        string task=run.TaskForEpisode(index),pattern=run.MovementPatternForEpisode(index);
        float range=run.MovementRangeForEpisode(index);
        bool movement=range>=0,challenge=range>0;
        int region=movement?Picklebot.PlayerControlsIntegration.PlayerMovementPatternV3.Region(pattern,seed,new System.Random(unchecked(seed^0x6d41b23)).Next(9)):-1;
        string direction=challenge?Direction(region):"familiar";
        int centimetres=challenge?UnityEngine.Mathf.RoundToInt(400*range):0;
        string key=challenge?task+"/"+direction+"/"+centimetres+"cm/player-"+player:task+"/familiar/player-"+player+"/left-"+run.ServeFromLeftForEpisode(index);
        if(challenge)Require(pattern=="axes"&&System.Array.IndexOf(new[]{25,50,75,100},centimetres)>=0&&direction!="not-axis-challenge","Unexpected challenge geometry");
        Increment(coverage,key);
        planned.Add(new{index,seed,player,task,pattern,range,region,direction,centimetres,challenge,serveFromLeft=run.ServeFromLeftForEpisode(index),difficulty=run.DifficultyForEpisode(index)});
        if(index<InspectFirstOrdinal||index>=InspectFirstOrdinal+InspectCount)continue;

        // This API only constructs an episode. No Arena is created and no policy
        // is bound. Its reset geometry is exactly what later evaluation will use.
        using(var drill=run.CreateDrillForEpisode(index,out string[] rejectedSurfaces))
        {
            var match=drill.Match;var world=match.World;var body=world.Players[player];
            Require(match.Tick==0&&match.TotalTicks==0&&world.Time==0&&match.Decisions==null,"Fixture advanced time or attached a policy");
            Require(!drill.Done&&!drill.FaceContact&&drill.Reward==0&&world.Contacts.Count==0,"Fixture produced an action outcome");
            Require(drill.Seed==seed&&drill.Player==player&&drill.Task==task&&drill.MovementRange==range&&drill.MovementPattern==pattern,"Constructed reset differs from planned descriptor");
            Require(!drill.Cooperative&&drill.MovementTiming==0&&drill.MovementStartVariation==0&&drill.MovementPositionRewardScale==0,"Controller/reward fixture constraint changed");
            Require(!movement||match.MovementRegion==region,"Actual movement region differs from source-only schedule prediction");
            int sign=player<2?1:-1;
            var face=body.Paddle.position+body.Paddle.rotation*Picklebot.PlayerControls.PlayerStrokeAimV3.FacePoint;
            var nominal=match.MovementNominalPoint;
            var shift=nominal-face;shift.y=0;
            float canonicalX=shift.x*sign,canonicalZ=shift.z*sign;
            if(challenge)
            {
                float expected=centimetres/100f;
                Require(UnityEngine.Mathf.Abs(shift.magnitude-expected)<2e-5f,"Measured nominal displacement is not the requested centimetres");
                var expectedShift=region==3?new UnityEngine.Vector2(-expected,0):region==5?new UnityEngine.Vector2(expected,0):region==1?new UnityEngine.Vector2(0,expected):new UnityEngine.Vector2(0,-expected);
                Require((new UnityEngine.Vector2(canonicalX,canonicalZ)-expectedShift).sqrMagnitude<4e-10f,"Canonical direction/sign mismatch");
            }
            var observation=Picklebot.PlayerControlsIntegration.PlayerObservationV3.Capture(match,player,0);
            var physical=observation.ToArray();
            bool serve=Picklebot.PlayerControlsIntegration.PlayerContactDrillV3.IsServeTask(task);
            int serviceSign=serve?(int)UnityEngine.Mathf.Sign(world.Rules.ServiceX(world.Rules.DesignatedReceiver)*sign):0;
            var instructions=new System.Collections.Generic.List<object>();
            for(int targetRegion=0;targetRegion<2;targetRegion++)
            {
                var target=Picklebot.PlayerLearning.PlayerExecutionDrillsV1.RegionTarget(serve,serviceSign,targetRegion);
                var goal=new Picklebot.PlayerLearning.PlayerExecutionGoalV1(player,0,Picklebot.PlayerLearning.PlayerIntentV1.PlayBall,shotTarget:target,shotRadius:1f);
                var encoded=goal.Observe(observation);
                Require(encoded.Length==136&&!goal.HasMovementTarget&&goal.HasShotTarget,"Wrong supported goal contract");
                for(int k=0;k<124;k++)Require(encoded[k]==physical[k],"Goal construction modified physical observation");
                instructions.Add(new{condition=targetRegion==0?"A":"B",targetX=target.x,targetZ=target.y,radius=1f,observation136=encoded});
            }
            var overlaps=new System.Collections.Generic.List<object>();
            var ballCollider=world.Ball.GetComponent<UnityEngine.Collider>();
            foreach(var collider in world.Root.GetComponentsInChildren<UnityEngine.Collider>())
                if(collider!=ballCollider&&collider.enabled&&!collider.isTrigger&&UnityEngine.Physics.ComputePenetration(ballCollider,world.Ball.position,world.Ball.rotation,collider,collider.transform.position,collider.transform.rotation,out var separationDirection,out float penetration))
                    overlaps.Add(new{surface=collider.name,penetration,normal=V(separationDirection)});
            var players=new System.Collections.Generic.List<object>();
            for(int seat=0;seat<4;seat++)
            {
                var other=world.Players[seat];
                players.Add(new{seat,root=V(other.Position),paddlePosition=V(other.Paddle.position),paddleRotation=Q(other.Paddle.rotation)});
            }
            float halfWidth=Picklebot.Doubles.DoublesRules.HalfWidth,halfLength=Picklebot.Doubles.DoublesRules.HalfLength;
            rows.Add(new{
                index,seed,player,task,pattern,range,region,direction,centimetres,challenge,rejectedSurfaces,
                actualTicks=match.Tick,worldSeconds=world.Time,policiesAttached=false,outcomeMeasured=false,
                learnerRoot=V(body.Position),paddleFace=V(face),players,
                nominalPoint=movement?V(nominal):null,
                canonicalNominalShift=movement?new[]{canonicalX,canonicalZ}:null,
                nominalDistanceMetres=movement?(float?)shift.magnitude:null,
                nominalPointInCourt=movement?(bool?)(UnityEngine.Mathf.Abs(nominal.x)<=halfWidth&&UnityEngine.Mathf.Abs(nominal.z)<=halfLength):null,
                nominalPointInKitchen=movement?(bool?)(UnityEngine.Mathf.Abs(nominal.z)<=Picklebot.Doubles.DoublesRules.Kitchen):null,
                ballPosition=V(world.Ball.position),ballVelocity=V(world.Ball.linearVelocity),ballSpin=V(world.Ball.angularVelocity),
                ballMass=world.Ball.mass,ballDiameter=world.Configuration.BallDiameter,gravity=V(world.Configuration.Gravity),physicsDt=Picklebot.Doubles.DoublesWorld.Dt,
                ballHeld=match.BallHeld,stationarySupport=match.StationarySupportActive,overlaps,
                rule=new{phase=world.Rules.Phase.ToString(),world.Rules.Server,world.Rules.DesignatedReceiver,world.Rules.ExpectedTeam,world.Rules.Bounced,world.Rules.CanVolley},
                physicalObservation124=physical,instructions,
                configurationJson=UnityEngine.JsonUtility.ToJson(world.Configuration)
            });
            Increment(actualCoverage,key);
        }
        Require(!Unity.MLAgents.Academy.IsInitialized,"A reset unexpectedly initialized the Academy");
    }
    foreach(string task in new[]{"rally-air-feed","rally-bounce-feed"})
        foreach(string direction in new[]{"left","right","shallow","deep"})
            foreach(int centimetres in new[]{25,50,75,100})for(int player=0;player<4;player++)
            {
                string key=task+"/"+direction+"/"+centimetres+"cm/player-"+player;
                if(!coverage.ContainsKey(key))missing.Add(key);
            }
    Require(Hash(ledgerPath)==ledgerHash&&Hash(sourcePath)==sourceRecordHash,"Ledger/source manifest changed during inspection");
    var report=new{
        status="reset_fixture_only",firstSeed=FirstSeed,seedCount=SeedCount,reservation=ReservationRun,
        sourceIdentity=ExpectedSource,sourceRecordHash,ledgerHash,unityVersion=UnityEngine.Application.unityVersion,
        loadedAssembly=typeof(Picklebot.PlayerControlsIntegration.PlayerContactDrillV3).Assembly.ManifestModule.ModuleVersionId.ToString(),
        inspectFirstOrdinal=InspectFirstOrdinal,inspectCount=InspectCount,plannedCoverage=coverage,inspectedCoverage=actualCoverage,missingJointCells=missing,planned,rows,
        policyActions=0,physicsTicks=0,rewardsCollected=0,modelsLoaded=false,
        physicalReachabilityProven=false,legalReturnAbilityProven=false,promoted=false,finalSeedsConsumed=false,
        limitations=new[]{"Source-only coverage spans the whole block; measured physical records cover only this bounded batch.","Nominal feeder points are not guaranteed contact points and are never policy movement commands.","No simulation ticks means flight, bounce, timing, reachability and successful play are untested.","Kitchen location of a nominal ball point alone does not determine player volley legality.","A 25-100cm ball shift does not prove the player must move its root; arm reach may suffice.","Goal A/B stays enabled; no unfamiliar disabled-goal evaluation is introduced.","Fixed direction cells can repeat physical observations despite unused seed IDs."}
    };
    System.IO.Directory.CreateDirectory(Workspace);
    using(var stream=new System.IO.FileStream(output,System.IO.FileMode.CreateNew,System.IO.FileAccess.Write))
    using(var writer=new System.IO.StreamWriter(stream))writer.Write(Newtonsoft.Json.JsonConvert.SerializeObject(report,Newtonsoft.Json.Formatting.Indented));
    result=Newtonsoft.Json.JsonConvert.SerializeObject(new{output,inspected=rows.Count,planned=planned.Count,missingJointCells=missing.Count,policyActions=0,physicsTicks=0,reachabilityProven=false});
}
finally
{
    UnityEngine.Object.DestroyImmediate(holder);
}
return result;

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Picklebot.PlayerControls;
using UnityEditor;
using UnityEngine;
namespace Picklebot.PlayerControlsIntegration.Editor
{
    public static class PlayerDrillRolloutV3
    {
        [Serializable] public sealed class Row
        {public int episode,seed,player,observationTick,applyTick;public float[] observation;public PlayerSampleV3 sample;public float reward;public bool attempted,terminal;}
        [Serializable] public sealed class Episode
        {public int seed,player,physicsSteps,rows,attemptedRows;public string outcome,failure;public float reward,unattributedReward;public bool faceContact,netCrossed,released,dropBounced,serveAccepted;public int releaseTick;public float releaseHeight,releaseLift;}
        [Serializable] public sealed class Report
        {
            public string task,unityVersion,physicsSettingsHash,configurationHash;public bool sampled,stationary;
            public string status,split,sourceHash,actorHash,drillVersion=PlayerContactDrillV3.Version,
                observationVersion=PlayerObservationV3.Version,actionVersion=PlayerActionV3.Version,note,failure;
            public int firstSeed,requestedEpisodes,rows;public double elapsedSeconds;public List<Episode> episodes=new List<Episode>();
        }
        private static PlayerContactDrillV3 drill;private static PlayerActorModelV3 model;private static PlayerActorV3[] policies;
        private static Report report;private static string output;private static StreamWriter writer;private static List<Row> rows;
        private static System.Diagnostics.Stopwatch timer;private static float episodeReward,unattributed;
        public static bool Running=>report!=null;public static string Status{get;private set;}="idle";
        public static void Start(string actorPath,string outputDirectory,int firstSeed=1300000,int episodes=16,string split="interactive",string task="contact",bool sampled=true,bool stationary=false)
        {
            if(Running||!EditorApplication.isPlaying||EditorApplication.isCompiling||EditorUtility.scriptCompilationFailed)throw new InvalidOperationException("Idle compiled Play Mode required.");
            if(!PlayerContactDrillV3.ValidTask(task))throw new ArgumentException("Unknown drill task.");
            if(split=="training"&&(!sampled||stationary))throw new ArgumentException("Training requires sampled active policy actions.");
            int lower=split=="interactive"?1300000:split=="training"?1000000:split=="development"?1100000:-1;
            if(lower<0||episodes<1||episodes>10000||firstSeed<lower||firstSeed+episodes>lower+100000)throw new ArgumentException("Invalid non-final seed block.");
            if(Directory.Exists(outputDirectory))throw new InvalidOperationException("Choose a new rollout directory.");
            var json=File.ReadAllText(actorPath);model=PlayerActorModelV3.Load(json);
            string source=PlayerControlSource.SourceHash();if(model.SourceHash!=source)throw new InvalidOperationException("Actor/environment source mismatch.");
            Directory.CreateDirectory(outputDirectory);output=outputDirectory;writer=new StreamWriter(Path.Combine(output,"rows.jsonl"));
            report=new Report{status="running",split=split,task=task,sampled=sampled,stationary=stationary,
                unityVersion=Application.unityVersion,physicsSettingsHash=Picklebot.Simulation.PhysicsSettingsIdentityV0.Hash(),sourceHash=source,actorHash=Picklebot.Doubles.Editor.ContactTraining.Hash(json),firstSeed=firstSeed,requestedEpisodes=episodes,
                note="Drill task recorded explicitly; shared model/private actors; nonparticipants held; jump masked; release enabled only for drop-serve. Stationary control masks every action. Contact/return feeds and synthetic rule initialization occur only at reset; drop-serve starts held with actual serve rules. No prescribed stroke. Not self-play or final evaluation."};
            timer=System.Diagnostics.Stopwatch.StartNew();Status="running";EditorApplication.update+=Tick;
        }
        private static void Tick()
        {
            try
            {
                if(drill==null)
                {
                    if(report.episodes.Count==report.requestedEpisodes){Finish();return;}
                    int seed=report.firstSeed+report.episodes.Count;int player=report.episodes.Count%4;
                    drill=new PlayerContactDrillV3(seed,player,report.task);
                    string config=Picklebot.Core.StableHashV0.Hex(drill.Match.World.Configuration.CanonicalText());
                    if(report.configurationHash!=null&&report.configurationHash!=config)throw new InvalidOperationException("Drill configuration changed.");
                    report.configurationHash=config;
                    policies=Enumerable.Range(0,4).Select(i=>new PlayerActorV3(model,report.sampled,report.stationary?new bool[PlayerActionV3.Count]:PlayerContactDrillV3.ActionMask(i,player,report.task))).ToArray();
                    drill.Match.AttachPolicies(policies,seed);rows=new List<Row>();episodeReward=unattributed=0;
                    drill.Match.Decisions.Decided+=decision=>
                    {if(decision.player==player)rows.Add(new Row{episode=report.episodes.Count,seed=seed,player=player,observationTick=decision.observationTick,
                        applyTick=decision.applyTick,observation=decision.observation.ToArray(),sample=policies[player].LastSample});};
                }
                for(int i=0;i<96&&!drill.Done;i++)
                {
                    int attemptTick=drill.Match.Tick;drill.Step();episodeReward+=drill.Reward;
                    Row active=null;foreach(var row in rows)if(row.applyTick<=attemptTick){row.attempted=true;active=row;}
                    if(active!=null){active.reward+=drill.Reward;if(drill.Done)active.terminal=true;}else unattributed+=drill.Reward;
                }
                if(!drill.Done)return;
                foreach(var row in rows){writer.WriteLine(JsonUtility.ToJson(row));report.rows++;}writer.Flush();
                report.episodes.Add(new Episode{seed=drill.Seed,player=drill.Player,physicsSteps=drill.Match.Tick,rows=rows.Count,attemptedRows=rows.Count(r=>r.attempted),
                    outcome=drill.Outcome,failure=drill.Match.Failure,reward=episodeReward,unattributedReward=unattributed,faceContact=drill.FaceContact,netCrossed=drill.NetCrossed,released=drill.Released,dropBounced=drill.DropBounced,serveAccepted=drill.ServeAccepted,releaseTick=drill.ReleaseTick,releaseHeight=drill.ReleaseHeight,releaseLift=drill.ReleaseLift});
                drill.Dispose();drill=null;Status="running "+report.episodes.Count+"/"+report.requestedEpisodes;
            }
            catch(Exception e){report.failure=e.ToString();Finish();}
        }
        private static void Finish()
        {
            EditorApplication.update-=Tick;
            try
            {
                if(PlayerControlSource.SourceHash()!=report.sourceHash)report.failure="Source changed during rollout.";
                if(Picklebot.Simulation.PhysicsSettingsIdentityV0.Hash()!=report.physicsSettingsHash)report.failure="Physics settings changed during rollout.";
                report.status=report.failure==null&&report.episodes.Count==report.requestedEpisodes?"complete":"failed";
                timer.Stop();report.elapsedSeconds=timer.Elapsed.TotalSeconds;writer.Dispose();writer=null;
                File.WriteAllText(Path.Combine(output,"report.json"),JsonUtility.ToJson(report,true));Status=report.status+": "+output;
            }
            finally{drill?.Dispose();drill=null;report=null;}
        }
        [Serializable] private sealed class Parity {public float[] observation,mean;public PlayerSampleV3 sample;}
        public static void WriteParity(string actorPath,string path)
        {
            if(File.Exists(path))throw new InvalidOperationException("Parity evidence already exists.");
            var m=PlayerActorModelV3.Load(File.ReadAllText(actorPath));var x=new float[PlayerObservationV3.Count];for(int i=0;i<x.Length;i++)x[i]=Mathf.Sin(i*.37f)*.7f;
            var actor=new PlayerActorV3(m,true,PlayerContactDrillV3.ActionMask(0,0));actor.Decide(new PlayerObservationV3(0,0,x),new System.Random(1300000));
            File.WriteAllText(path,JsonUtility.ToJson(new Parity{observation=x,mean=m.Forward(x),sample=actor.LastSample},true));
        }
    }
}

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;

namespace Picklebot.Competition.Editor
{
    [Serializable] public sealed class PointRecord
    {
        public int seed, winner, returns, contacts;
        public float seconds;
        public string result;
        public float[] travel;
        public string[] events;
        public ShotDecision[] decisions;
    }
    [Serializable] public sealed class CompetitionReport
    {
        public string worldVersion, strokeSha256, strategySha256, runtimeSha256, unityVersion, createdUtc, mode;
        public List<PointRecord> points = new();
    }
    [InitializeOnLoad] public static class CompetitionEditor
    {
        public const string StrokePath = "Assets/Picklebot/Competition/Models/stroke.json";
        public const string StrategyPath = "Assets/Picklebot/Competition/Models/strategy.json";
        private static CompetitiveWorld world;
        private static DensePolicy strategy;
        private static CompetitionReport report;
        private static int firstSeed, count, goal;
        private static string output, mode;
        public static string Status { get; private set; } = "idle";
        static CompetitionEditor() => EditorApplication.playModeStateChanged += c => { if(c == PlayModeStateChange.ExitingPlayMode) Stop(); };
        public static string Hash(string path)
        {
            using var sha = SHA256.Create();
            return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-","").ToLowerInvariant();
        }
        public static string Collect(int seed=840000,int episodes=100,string label="centre",string policyPath="",string opponentMode="centre",int fixedGoal=4)
        {
            if(!EditorApplication.isPlaying) throw new InvalidOperationException("Use Play Mode for physics callbacks.");
            if(world!=null) throw new InvalidOperationException("Collection already running.");
            if(seed<830000 || seed+episodes>850000 || episodes<1 || episodes>1000) throw new ArgumentException("Use competition seed partition [830000,850000).");
            if(label.Any(c=>!char.IsLetterOrDigit(c)&&c!='-')) throw new ArgumentException("Invalid label.");
            if(!new[]{"centre","self","near","far"}.Contains(opponentMode)) throw new ArgumentException("Invalid opponent mode.");
            strategy = string.IsNullOrEmpty(policyPath)?null:new DensePolicy(File.ReadAllText(policyPath),"competitive-strategy-v1",8,5);
            using var sha = SHA256.Create();
            report = new CompetitionReport { worldVersion=CompetitiveWorld.Version, strokeSha256=Hash(StrokePath),
                strategySha256=string.IsNullOrEmpty(policyPath)?"none":Hash(policyPath),
                runtimeSha256=BitConverter.ToString(sha.ComputeHash(System.Text.Encoding.UTF8.GetBytes(string.Join("\n",
                    Directory.GetFiles("Assets/Picklebot/Competition","*.cs")
                        .Concat(new[]{"Assets/Picklebot/Rally/RallyRules.cs","Assets/Picklebot/Rally/RallyNeuralPolicy.cs"})
                        .OrderBy(p=>p,StringComparer.Ordinal).Select(p=>p+"\n"+File.ReadAllText(p)))))).Replace("-","").ToLowerInvariant(),
                unityVersion=Application.unityVersion,createdUtc=DateTime.UtcNow.ToString("O"),mode=opponentMode };
            firstSeed=seed; count=episodes; goal=fixedGoal; mode=opponentMode;
            output=Path.GetFullPath("artifacts/competition/"+label+".json"); Directory.CreateDirectory(Path.GetDirectoryName(output));
            world=new CompetitiveWorld(new DensePolicy(File.ReadAllText(StrokePath),"competitive-stroke-v1",10,6),false);
            world.Reset(firstSeed); Status="running 0/"+count; EditorApplication.update+=Tick; return Status;
        }
        private static void Tick()
        {
            if(world==null)return;
            try
            {
                for(int i=0;i<3000;i++)
                {
                    world.Step(mode=="self"||mode=="near"?strategy:null,mode=="self"||mode=="far"?strategy:null,firstSeed<840000,goal);
                    if(!world.Finished)continue;
                    report.points.Add(new PointRecord { seed=world.Seed,winner=world.Truncated?0:world.Rules.Winner,returns=world.Rules.Returns,
                        contacts=world.Rules.Contacts,seconds=world.Elapsed,result=world.Truncated?"Time cap: no point awarded":world.Rules.Result,travel=(float[])world.Travel.Clone(),
                        events=world.Events.ToArray(),decisions=world.Decisions.ToArray() });
                    Status=$"running {report.points.Count}/{count}";
                    if(report.points.Count==count)
                    {
                        File.WriteAllText(output,JsonUtility.ToJson(report,true)); Status="completed: "+output; Stop(); return;
                    }
                    world.Reset(firstSeed+report.points.Count);
                }
            }
            catch(Exception e) { Status="failed: "+e; Stop(); Debug.LogException(e); }
        }
        public static string DropMeasurement()
        {
            if(!EditorApplication.isPlaying)throw new InvalidOperationException("Use Play Mode.");
            using var test=new CompetitiveWorld(new DensePolicy(File.ReadAllText(StrokePath),"competitive-stroke-v1",10,6),false);
            test.Reset(840000); test.Ball.position=new Vector3(0,1.025f,.6f); test.Ball.linearVelocity=Vector3.zero;
            Physics.SyncTransforms(); bool rose=false; float apex=0;
            for(int i=0;i<400;i++)
            {
                test.StepFreePhysics();
                if(test.Ball.linearVelocity.y>0)rose=true;
                if(rose)apex=Mathf.Max(apex,test.Ball.position.y-CompetitiveWorld.Radius);
                if(rose&&test.Ball.linearVelocity.y<=0)break;
            }
            return $"Drop height 1 m; rebound height {apex:F4} m; restitution {CompetitiveWorld.CourtRestitution}";
        }
        private static void Stop() { EditorApplication.update-=Tick; world?.Dispose(); world=null; }
    }
}

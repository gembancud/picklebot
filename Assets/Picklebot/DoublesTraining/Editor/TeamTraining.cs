using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Picklebot.Doubles;
using Picklebot.Doubles.Editor;
using UnityEngine;
using UnityEditor;
namespace Picklebot.DoublesTraining.Editor
{
    [Serializable] public sealed class RallyResult
    {
        public int gameSeed,rally,winner,gameWinner,hits;
        public float seconds,minSeparation,maxPaddleSpeed,maxReach;
        public string fault;
        public Vector2 serveJitter;
        public int[] score,playerHits;
        public List<TeamDecision> decisions;
        public DoublesContact[] contacts;
    }
    [Serializable] public sealed class TeamReport
    {
        public string sourceHash,configurationHash,contactModelHash,teamModelHash,createdUtc,mode;
        public int seed,games;
        public List<RallyResult> rallies=new();
    }
    public static class TeamTraining
    {
        public const string ModelPath="Assets/Picklebot/Doubles/Models/teams.json";
        public static string Status {get;private set;}="idle";
        public static bool Running=>match!=null;
        private static DoublesMatch match;
        private static DoublesModels models;
        private static ContactModel contact;
        private static TeamReport report;
        private static int wanted,lastCompleted,gameIndex;
        private static bool training;
        private static System.Random rng;
        private static float minSeparation,maxPaddleSpeed,maxReach;
        public static string SourceHash()=>ContactTraining.Hash(ContactTraining.SourceHash()+string.Join("\n",Directory.GetFiles("Assets/Picklebot/DoublesTraining","*.cs",SearchOption.AllDirectories).OrderBy(ContactTraining.CanonicalPath,StringComparer.Ordinal).Select(p=>ContactTraining.CanonicalText(File.ReadAllText(p)))));
        public static void Start(int rallies=500,bool learn=true,string mode="trained")
        {
            if(!EditorApplication.isPlaying||Running||ContactTraining.Running)throw new InvalidOperationException("Start Play and finish other jobs first.");
            contact=ContactModel.Load(File.ReadAllText(ContactTraining.ModelPath));
            if(contact.sourceHash!=ContactTraining.SourceHash())throw new InvalidOperationException("Contact model source has changed.");
            training=learn;wanted=rallies;gameIndex=0;
            models=learn?new DoublesModels():DoublesModels.Load(File.ReadAllText(ModelPath));
            if(!learn&&(models.sourceHash!=SourceHash()||models.contactModelHash!=ContactTraining.Hash(File.ReadAllText(ContactTraining.ModelPath))))throw new InvalidOperationException("Team model source or contact model has changed.");
            report=new TeamReport{sourceHash=SourceHash(),contactModelHash=ContactTraining.Hash(File.ReadAllText(ContactTraining.ModelPath)),
                teamModelHash=learn?"fresh zero weights":ContactTraining.Hash(File.ReadAllText(ModelPath)),seed=learn?910000:940000,createdUtc=DateTime.UtcNow.ToString("O"),mode=learn?"training":mode};
            rng=new System.Random(report.seed);NewGame();EditorApplication.update+=Tick;
        }
        public static void Cancel(){EditorApplication.update-=Tick;match?.Dispose();match=null;Status="cancelled";}
        private static void NewGame()
        {
            match?.Dispose();match=new DoublesMatch(false,report.seed+gameIndex){AutoNext=false,CentreOnly=report.mode=="centre",Learning=training,SampleActions=report.mode=="random",Models=models,ContactModel=contact};
            report.configurationHash=match.World.Configuration.ConfigurationHash;lastCompleted=0;ResetMetrics();
        }
        private static void ResetMetrics()
        {minSeparation=100;maxPaddleSpeed=maxReach=0;match.ServeJitter=new Vector2((float)(rng.NextDouble()*.6-.3),(float)(rng.NextDouble()*.8-.4));Array.Clear(match.PlayerHits,0,4);}
        private static void Tick()
        {
            if(match==null)return;
            try
            {
                double until=EditorApplication.timeSinceStartup+.02;
                while(match!=null&&EditorApplication.timeSinceStartup<until)
                {
                    match.Step();
                    for(int i=0;i<4;i++)
                    {
                        var p=match.World.Players[i];maxPaddleSpeed=Mathf.Max(maxPaddleSpeed,p.PaddleVelocity.magnitude);
                        maxReach=Mathf.Max(maxReach,Vector3.Distance(p.Shoulder,p.Hand));
                        minSeparation=Mathf.Min(minSeparation,Vector3.Distance(p.Position,match.World.Players[i^1].Position));
                    }
                    if(match.CompletedRallies>lastCompleted)
                    {
                        var r=match.World.Rules;lastCompleted=match.CompletedRallies;
                        report.rallies.Add(new RallyResult{gameSeed=report.seed+gameIndex,rally=match.RallyNumber,winner=r.Winner,gameWinner=r.GameWinner,hits=r.Hits,seconds=match.World.Time,
                            fault=r.LastFault.ToString(),score=(int[])r.Score.Clone(),playerHits=(int[])match.PlayerHits.Clone(),decisions=new List<TeamDecision>(match.Decisions),contacts=match.World.Contacts.ToArray(),
                            minSeparation=minSeparation,maxPaddleSpeed=maxPaddleSpeed,maxReach=maxReach,serveJitter=match.ServeJitter});
                        Status=$"{report.mode}: {report.rallies.Count}/{wanted} rallies; game {gameIndex+1}; score {r.Score[0]}-{r.Score[1]}";
                        if(r.GameWinner>=0)report.games++;
                        if(report.rallies.Count>=wanted){Finish();break;}
                        if(r.GameWinner>=0){gameIndex++;NewGame();}else{match.Next();ResetMetrics();}
                    }
                }
            }
            catch(Exception e){Cancel();Status="failed: "+e;Debug.LogException(e);}
        }
        private static void Finish()
        {
            match.Dispose();match=null;EditorApplication.update-=Tick;
            if(SourceHash()!=report.sourceHash)throw new InvalidOperationException("Source changed during training.");
            if(training)
            {
                models.sourceHash=report.sourceHash;models.configurationHash=report.configurationHash;models.contactModelHash=report.contactModelHash;models.seed=report.seed;models.createdUtc=DateTime.UtcNow.ToString("O");
                Directory.CreateDirectory(Path.GetDirectoryName(ModelPath));File.WriteAllText(ModelPath,JsonUtility.ToJson(models,true));AssetDatabase.ImportAsset(ModelPath);
            }
            Directory.CreateDirectory("artifacts/doubles");File.WriteAllText("artifacts/doubles/teams-"+report.mode+".json",JsonUtility.ToJson(report,true));
            Status=$"complete: {report.rallies.Count} rallies, {report.games} complete games; report saved";
        }
    }
}

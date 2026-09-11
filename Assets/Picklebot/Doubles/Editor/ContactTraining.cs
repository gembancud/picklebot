using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using UnityEngine;
using UnityEditor;
namespace Picklebot.Doubles.Editor
{
    [Serializable] public sealed class ContactTrial
    {
        public int kind,candidate,seed;
        public ContactParameters parameters;
        public bool hit,legal,spinCorrect;
        public float error,spin,reward;
        public string fault;
        public Vector3 landing,goal,velocity,angularVelocity;
    }
    [Serializable] public sealed class ContactTrainingReport
    {
        public string sourceHash,configurationHash,createdUtc,mode,initialModelHash;
        public int candidates,samples;
        public List<ContactTrial> trials=new();
    }
    public static class ContactTraining
    {
        public static string Status {get;private set;}="idle";
        public static bool Running=>match!=null;
        public const string ModelPath="Assets/Picklebot/Doubles/Models/contact.json";
        private static DoublesMatch match;
        private static ContactTrainingReport report;
        private static ContactModel model;
        private static ContactParameters parameters,bestParameters;
        private static float bestReward,candidateReward;
        private static int kind,candidate,sample,seenContacts;
        private static bool hit,validation,resuming;
        private static int validationSeed;
        private static ContactTrial trial;
        private static System.Random random;
        private static string startHash;
        public static void Cancel()
        {EditorApplication.update-=Tick;match?.Dispose();match=null;Status="cancelled; no accepted model saved";}
        public static string Hash(string value) {using var sha=SHA256.Create();return BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(value))).Replace("-","").ToLowerInvariant();}
        // Separate runtime/contact training code from presentation and test edits.
        public static string CanonicalPath(string path) => path.Replace('\\', '/');
        public static string CanonicalText(string text) => text.Replace("\r\n", "\n").Replace("\r", "\n");
        public static string SourceRecordText(IEnumerable<KeyValuePair<string, string>> records) => string.Join("\n",
            records.Select(r => new KeyValuePair<string, string>(CanonicalPath(r.Key), CanonicalText(r.Value)))
            .OrderBy(r => r.Key, StringComparer.Ordinal).Select(r => r.Key + "\n" + r.Value));
        public static string SourceText(IEnumerable<string> paths) => SourceRecordText(paths
            .Select(p => new KeyValuePair<string, string>(p, File.ReadAllText(p))));
        public static string SourceHash() => Hash(SourceText(new[] { "Doubles", "Core", "Simulation" }
            .SelectMany(f => Directory.GetFiles("Assets/Picklebot/" + f, "*.cs", SearchOption.AllDirectories))
            .Where(p => !CanonicalPath(p).Contains("/Tests/") && Path.GetFileName(p) != "DoublesDemo.cs" && Path.GetFileName(p) != "DoublesEditor.cs")));
        public static void Start(int candidates=24,int samples=3,bool validate=false,bool resume=false,int testSeed=930000)
        {
            if(!EditorApplication.isPlaying||Running)throw new InvalidOperationException("Start Play and finish the current job first.");
            validation=validate;resuming=resume;validationSeed=testSeed;startHash=SourceHash();random=new System.Random(900000);
            model=validate||resume?ContactModel.Load(File.ReadAllText(ModelPath)):new ContactModel();
            if(validate&&model.sourceHash!=startHash)throw new InvalidOperationException("The model source hash is stale.");
            report=new ContactTrainingReport{sourceHash=startHash,initialModelHash=validate||resume?Hash(File.ReadAllText(ModelPath)):"default contact parameters",createdUtc=DateTime.UtcNow.ToString("O"),mode=validate?"held-out contact validation":"contact parameter search",candidates=validate?1:candidates,samples=samples};
            kind=candidate=sample=0;bestReward=float.NegativeInfinity;candidateReward=0;bestParameters=new ContactParameters();
            NextCandidate();BeginTrial();EditorApplication.update+=Tick;
        }
        private static void NextCandidate()
        {
            if(validation){parameters=model.strokes[kind].Copy();return;}
            parameters=candidate==0?(resuming?model.strokes[kind].Copy():new ContactParameters{brushBias=kind==0?2:kind==1?3:0}):bestParameters.Copy();
            if(candidate==0)return;
            float scale=candidate<report.candidates/2?1:.45f;
            parameters.pitch=Mathf.Clamp(parameters.pitch+(float)(random.NextDouble()*2-1)*8*scale,-18,18);
            parameters.speed=Mathf.Clamp(parameters.speed+(float)(random.NextDouble()*2-1)*.2f*scale,.6f,1.4f);
            parameters.timing=Mathf.Clamp(parameters.timing+(float)(random.NextDouble()*2-1)*.015f*scale,-.035f,.035f);
            parameters.brush=Mathf.Clamp(parameters.brush+(float)(random.NextDouble()*2-1)*.4f*scale,.3f,1.8f);
            parameters.brushBias=Mathf.Clamp(parameters.brushBias+(float)(random.NextDouble()*2-1)*1.5f*scale,-5,5);
        }
        private static void BeginTrial()
        {
            int seed=(validation?validationSeed:900000)+sample;
            var rng=new System.Random(seed);float x=(float)(rng.NextDouble()*3.6-1.8),depth=2.8f+(float)rng.NextDouble()*1.8f;
            match=new DoublesMatch(false,seed){CentreOnly=false,AutoNext=false,ForcedStroke=(StrokeKind)kind,TargetOverride=new Vector2(x,depth),ServeJitter=new Vector2((float)(rng.NextDouble()*.6-.3),(float)(rng.NextDouble()*.8-.4))};
            var trialModel=new ContactModel();trialModel.strokes[kind]=parameters;match.ContactModel=trialModel;
            report.configurationHash=match.World.Configuration.ConfigurationHash;
            trial=new ContactTrial{kind=kind,candidate=candidate,seed=seed,parameters=parameters.Copy(),goal=new Vector3(x,0,-depth),error=99,reward=-120};
            seenContacts=0;hit=false;Status=$"{report.mode}: stroke {kind+1}/3, candidate {candidate+1}/{report.candidates}, sample {sample+1}/{report.samples}";
        }
        private static void Tick()
        {
            if(match==null)return;
            try
            {
                double end=EditorApplication.timeSinceStartup+.02;
                while(match!=null&&EditorApplication.timeSinceStartup<end)
                {
                    if(!hit)match.Step();else match.World.Simulate();
                    for(;seenContacts<match.World.Contacts.Count;seenContacts++)
                    {
                        var c=match.World.Contacts[seenContacts];
                        if(!hit&&c.player==match.World.Rules.DesignatedReceiver&&match.World.Rules.Hits>=2)
                        {
                            hit=trial.hit=true;trial.velocity=c.velocity;trial.angularVelocity=c.spin;
                            var axis=Vector3.Cross(Vector3.up,c.velocity).normalized;trial.spin=Vector3.Dot(c.spin,axis);
                            trial.spinCorrect=kind==0?Mathf.Abs(trial.spin)<25:kind==1?trial.spin>5:trial.spin<-5;
                            // Measure the isolated outgoing shot. Opponent strikes
                            // cannot hide an out ball or change its landing label.
                            foreach(var p in match.World.Players)
                            {foreach(var collider in p.Paddle.GetComponentsInChildren<Collider>())collider.enabled=false;foreach(var collider in p.Root.GetComponentsInChildren<Collider>())collider.enabled=false;}
                        }
                        else if(hit&&(c.surface=="CourtSurface"||c.surface=="OutCatchFloor"))
                        {
                            trial.landing=c.point;trial.error=Vector3.Distance(new Vector3(c.point.x,0,c.point.z),trial.goal);
                            trial.legal=c.point.z<0&&Mathf.Abs(c.point.z)<=DoublesRules.HalfLength&&Mathf.Abs(c.point.x)<=DoublesRules.HalfWidth;
                            float desiredSpin=kind==0?0:kind==1?40:-30;
                            trial.reward=(trial.legal?100:-80)-trial.error*8+(trial.spinCorrect?40:-40)-Mathf.Abs(trial.spin-desiredSpin)*.4f;
                            FinishTrial();break;
                        }
                    }
                    if(match!=null&&((match.World.Rules.Dead&&!hit)||match.World.Time>8||match.World.Ball.position.y<-.5f))FinishTrial();
                }
            }
            catch(Exception e){Status="failed: "+e;match?.Dispose();match=null;EditorApplication.update-=Tick;Debug.LogException(e);}
        }
        private static void FinishTrial()
        {
            trial.fault=match.World.Rules.LastFault.ToString();report.trials.Add(trial);candidateReward+=trial.reward;match.Dispose();match=null;
            sample++;
            if(sample>=report.samples)
            {
                if(candidateReward>bestReward){bestReward=candidateReward;bestParameters=parameters.Copy();}
                sample=0;candidateReward=0;candidate++;
                if(candidate>=report.candidates)
                {if(!validation)model.strokes[kind]=bestParameters.Copy();kind++;candidate=0;bestReward=float.NegativeInfinity;bestParameters=new ContactParameters();}
                if(kind<3)NextCandidate();
            }
            if(kind<3){BeginTrial();return;}
            EditorApplication.update-=Tick;
            if(SourceHash()!=startHash)throw new InvalidOperationException("Source changed during contact fitting. Results are not accepted.");
            Directory.CreateDirectory("artifacts/doubles");File.WriteAllText(validation?"artifacts/doubles/contact-validation.json":"artifacts/doubles/contact-training.json",JsonUtility.ToJson(report,true));
            if(!validation)
            {
                model.sourceHash=startHash;model.configurationHash=report.configurationHash;model.createdUtc=DateTime.UtcNow.ToString("O");model.seed=900000;model.trials=report.trials.Count;
                Directory.CreateDirectory(Path.GetDirectoryName(ModelPath));File.WriteAllText(ModelPath,JsonUtility.ToJson(model,true));AssetDatabase.ImportAsset(ModelPath);
            }
            Status=$"complete: {report.trials.Count} contact trials; report saved";
        }
    }
}

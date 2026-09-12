from pathlib import Path
root=Path('F:/dev/picklebot')
p=root/'Assets/Picklebot/PlayerLearning/PlayerExecutionDrillsV1.cs';s=p.read_text()
assert 'SmoothDistanceReward' not in s
s=s.replace('public bool SampleShotTargets;', '''public const string LinearReward = "linear-radius";
        public const string SmoothDistanceReward = "smooth-distance-2m";
        public bool SampleShotTargets;
        public string RewardMode = LinearReward;''')
s=s.replace('public string targetLayout;', 'public string targetLayout, rewardMode;')
s=s.replace('public static void ValidateLayout(', '''public static void ValidateRewardMode(string mode)
        {
            if(mode!=LinearReward && mode!=SmoothDistanceReward)throw new ArgumentException("Unknown placement reward mode.");
        }

        public static void ValidateLayout(''')
s=s.replace('ValidateLayout(TargetLayout,SampleShotTargets,TargetRadius);', '''ValidateLayout(TargetLayout,SampleShotTargets,TargetRadius);
            ValidateRewardMode(RewardMode);
            if(RewardMode!=LinearReward&&!SampleShotTargets)throw new ArgumentException("Smooth placement feedback requires assigned targets.");''')
s=s.replace('Vector3 landing, float budget)\n        {', 'Vector3 landing, float budget, string mode = LinearReward)\n        {\n            ValidateRewardMode(mode);')
s=s.replace('return budget*Mathf.Max(0,1-distance/goal.ShotRadius);', '''// Success is still measured with ShotRadius. This optional feedback also
            // distinguishes legal misses outside that circle; it never changes physics.
            return budget*(mode==SmoothDistanceReward?Mathf.Exp(-distance/2f):Mathf.Max(0,1-distance/goal.ShotRadius));''')
s=s.replace('targetLayout=TargetLayout,assigned=', 'targetLayout=TargetLayout,rewardMode=RewardMode,assigned=')
s=s.replace('TargetBonus(goal,true,bounce.position,LegalTargetReward)', 'TargetBonus(goal,true,bounce.position,LegalTargetReward,RewardMode)')
s=s.replace('stats.Add("PicklebotExecution/TargetHitPerAttempt",row.targetHit?1:0);', 'stats.Add("PicklebotExecution/TargetHitPerAttempt",row.targetHit?1:0);\n                stats.Add("PicklebotExecution/PlacementBonus",row.bonus);')
p.write_text(s)
p=root/'Assets/Picklebot/PlayerLearning/PlayerWorkerPlanV3.cs';s=p.read_text()
s=s.replace('public string targetLayout="random";', 'public string targetLayout="random";\n        public string placementRewardMode=PlayerExecutionDrillsV1.LinearReward;')
s=s.replace('PlayerExecutionDrillsV1.ValidateLayout(manifest.targetLayout,manifest.sampleShotTargets,manifest.targetRadius);', '''PlayerExecutionDrillsV1.ValidateLayout(manifest.targetLayout,manifest.sampleShotTargets,manifest.targetRadius);
            PlayerExecutionDrillsV1.ValidateRewardMode(manifest.placementRewardMode);
            if(manifest.placementRewardMode!=PlayerExecutionDrillsV1.LinearReward&&(!execution||!manifest.sampleShotTargets))throw new ArgumentException("Smooth placement feedback requires an active execution target contract.");''')
s=s.replace('goals.TargetLayout=Manifest.targetLayout;', 'goals.RewardMode=Manifest.placementRewardMode;goals.TargetLayout=Manifest.targetLayout;')
p.write_text(s)
p=root/'Assets/Picklebot/PlayerLearning/Tests/PlayerExecutionGoalV1Tests.cs';s=p.read_text()
marker='        [Test]\n        public void LegacyBehaviorCannotSilentlyLoadNewObservations()'
test='''        [Test]
        public void SmoothBonusGradesLegalMissesWithoutChangingTheSuccessRadius()
        {
            var goal=new PlayerExecutionGoalV1(0,0,PlayerIntentV1.PlayBall,shotTarget:new Vector2(0,4),shotRadius:1);
            string mode=PlayerExecutionDrillsV1.SmoothDistanceReward;
            Assert.AreEqual(0,PlayerExecutionDrillsV1.TargetBonus(goal,false,new Vector3(0,0,4),.25f,mode));
            Assert.AreEqual(.25f,PlayerExecutionDrillsV1.TargetBonus(goal,true,new Vector3(0,0,4),.25f,mode));
            float previous=.25f;
            foreach(float distance in new[]{.5f,1f,2f,4f,8f})
            {
                float bonus=PlayerExecutionDrillsV1.TargetBonus(goal,true,new Vector3(distance,0,4),.25f,mode);
                Assert.Greater(bonus,0);Assert.Less(bonus,previous);previous=bonus;
                Assert.That(bonus,Is.EqualTo(.25f*Mathf.Exp(-distance/2)).Within(1e-7));
            }
            Assert.AreEqual(1,goal.ShotRadius);
            Assert.AreEqual(0,PlayerExecutionDrillsV1.TargetBonus(goal,true,new Vector3(2,0,4),.25f));
            Assert.AreEqual(0,PlayerExecutionDrillsV1.TargetBonus(new PlayerExecutionGoalV1(0,0,PlayerIntentV1.PlayBall),true,Vector3.zero,.25f,mode));
            Assert.Throws<ArgumentException>(()=>PlayerExecutionDrillsV1.TargetBonus(goal,true,new Vector3(float.NaN,0,4),.25f,mode));
            Assert.Throws<ArgumentException>(()=>PlayerExecutionDrillsV1.TargetBonus(goal,true,Vector3.zero,float.NaN,mode));
            Assert.Throws<ArgumentException>(()=>PlayerExecutionDrillsV1.TargetBonus(goal,true,Vector3.zero,.25f,"unknown"));
        }

'''
assert marker in s;s=s.replace(marker,test+marker)
s=s.replace('''        [UnityTest]
        public IEnumerator TwoRegionWorkerRecordsCanonicalLegalLandings()
        {''','''        private static (MlDrillEpisodeV3[] episodes,PlayerExecutionDrillsV1.Result[] records,float[] trace) RunTwoRegionWorker(string mode)
        {''')
s=s.replace('executionContract=PlayerExecutionGoalV1.Contract,sampleShotTargets=true,targetLayout="two-regions",targetRadius=1,', 'executionContract=PlayerExecutionGoalV1.Contract,sampleShotTargets=true,targetLayout="two-regions",targetRadius=1,placementRewardMode=mode,')
s=s.replace('run.AutoRun=false;root.SetActive(true);run.InitializeRun();', '''run.AutoRun=false;root.SetActive(true);run.InitializeRun();
                var trace=new List<float>();
                foreach(var arena in run.ActiveArenas)foreach(var agent in arena.Agents)
                    agent.Received+=(current,actions)=>{trace.AddRange(current.LastPolicyObservation);trace.AddRange(current.LastCommand.ToArray());};''')
s=s.replace('Assert.AreEqual("two-regions",row.targetLayout);', 'Assert.AreEqual(mode,row.rewardMode);Assert.AreEqual("two-regions",row.targetLayout);')
s=s.replace('''                CollectionAssert.AreEquivalent(new[]{"stationary-serve","receive-feed","rally-air-feed","rally-bounce-feed"},observed);
            }
            finally{Object.DestroyImmediate(root);if(Academy.IsInitialized)Academy.Instance.Dispose();}
            yield return null;
        }''','''                CollectionAssert.AreEquivalent(new[]{"stationary-serve","receive-feed","rally-air-feed","rally-bounce-feed"},observed);
                return (episodes,records,trace.ToArray());
            }
            finally{Object.DestroyImmediate(root);if(Academy.IsInitialized)Academy.Instance.Dispose();}
        }

        [UnityTest]
        public IEnumerator TwoRegionWorkerRecordsCanonicalLegalLandings()
        {
            var linear=RunTwoRegionWorker(PlayerExecutionDrillsV1.LinearReward);
            var smooth=RunTwoRegionWorker(PlayerExecutionDrillsV1.SmoothDistanceReward);
            CollectionAssert.AreEqual(linear.trace,smooth.trace);
            Assert.IsTrue(smooth.records.Any(r=>r.legalLanding&&!r.targetHit&&r.bonus>0));
            for(int i=0;i<linear.episodes.Length;i++)
            {
                linear.episodes[i].reward=0;smooth.episodes[i].reward=0;
                Assert.AreEqual(JsonUtility.ToJson(linear.episodes[i]),JsonUtility.ToJson(smooth.episodes[i]));
                linear.records[i].bonus=0;smooth.records[i].bonus=0;
                linear.records[i].rewardMode="";smooth.records[i].rewardMode="";
                Assert.AreEqual(JsonUtility.ToJson(linear.records[i]),JsonUtility.ToJson(smooth.records[i]));
            }
            yield return null;
        }''')
p.write_text(s)
print('Installed opt-in smooth legal-distance feedback and frozen-policy parity coverage')

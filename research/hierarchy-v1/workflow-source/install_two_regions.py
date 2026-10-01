from pathlib import Path
root=Path('F:/dev/picklebot')
p=root/'Assets/Picklebot/PlayerLearning/PlayerExecutionDrillsV1.cs'
s=p.read_text()
assert 'public string TargetLayout' not in s
s=s.replace('public bool SampleShotTargets;', 'public bool SampleShotTargets;\n        public string TargetLayout = "random";')
s=s.replace('public bool assigned, legalLanding, targetHit;', 'public bool assigned, legalLanding, targetHit, hasLanding;')
s=s.replace('public float targetX, targetZ, radius, distance, bonus;', 'public float targetX, targetZ, radius, distance, bonus, landingX, landingZ;\n            public string targetLayout;')
s=s.replace('public void Prepare(PlayerMlDrillsV3 run)\n        {','''public static void ValidateLayout(string layout, bool sample, float radius)
        {
            if (layout!="random" && layout!="two-regions") throw new ArgumentException("Unknown target layout.");
            if (layout=="two-regions" && (!sample || !float.IsFinite(radius) || radius<=0 || radius>1))
                throw new ArgumentException("Two-region practice requires enabled targets with radius at most one meter.");
        }

        // Geometrically legal targets, not guaranteed feasible for every body/feed state.
        public static Vector2 RegionTarget(bool serve, int serviceSign, int region)
        {
            if(region<0 || region>1 || (serve && serviceSign!=1 && serviceSign!=-1)) throw new ArgumentException("Invalid target region.");
            return serve ? new Vector2(serviceSign*1.4f,region==0?3.3f:5.4f) : new Vector2(region==0?-1.2f:1.2f,3.8f);
        }

        public void Prepare(PlayerMlDrillsV3 run)
        {
            ValidateLayout(TargetLayout,SampleShotTargets,TargetRadius);''')
s=s.replace('target = new Vector2(x,z);', '''target = new Vector2(x,z);
                if(TargetLayout=="two-regions")
                {
                    bool serve=PlayerContactDrillV3.IsServeTask(drill.Task);
                    int sign=drill.Player<2?1:-1;
                    int serviceSign=serve?(int)Mathf.Sign(drill.Match.World.Rules.ServiceX(drill.Match.World.Rules.DesignatedReceiver)*sign):0;
                    target=RegionTarget(serve,serviceSign,random.Next(2));
                }''')
s=s.replace('assigned=goal.HasShotTarget,legalLanding=legal,', 'targetLayout=TargetLayout,assigned=goal.HasShotTarget,legalLanding=legal,')
s=s.replace('if (legal && goal.HasShotTarget)\n            {', 'if (legal)\n            {')
s=s.replace('row.distance=goal.LandingDistance(bounce.position);row.targetHit=row.distance<=goal.ShotRadius;\n                row.bonus=TargetBonus(goal,true,bounce.position,LegalTargetReward);', '''row.hasLanding=true;row.landingX=bounce.position.x*sign;row.landingZ=bounce.position.z*sign;
                if(goal.HasShotTarget)
                {
                    row.distance=goal.LandingDistance(bounce.position);row.targetHit=row.distance<=goal.ShotRadius;
                    row.bonus=TargetBonus(goal,true,bounce.position,LegalTargetReward);
                }''')
p.write_text(s)
p=root/'Assets/Picklebot/PlayerLearning/PlayerWorkerPlanV3.cs';s=p.read_text()
s=s.replace('public bool sampleShotTargets;', 'public bool sampleShotTargets;\n        public string targetLayout="random";')
s=s.replace('bool execution = !string.IsNullOrEmpty(manifest.executionContract);','''bool execution = !string.IsNullOrEmpty(manifest.executionContract);
            PlayerExecutionDrillsV1.ValidateLayout(manifest.targetLayout,manifest.sampleShotTargets,manifest.targetRadius);
            if(!execution && manifest.targetLayout!="random")throw new ArgumentException("Target layout requires execution contract.");''')
s=s.replace('goals.SampleShotTargets=Manifest.sampleShotTargets;', 'goals.TargetLayout=Manifest.targetLayout;goals.SampleShotTargets=Manifest.sampleShotTargets;')
p.write_text(s)
p=root/'Assets/Picklebot/PlayerLearning/Tests/PlayerExecutionGoalV1Tests.cs';s=p.read_text()
marker='        private static (string[] episodes,float[] trace) Run('
assert marker in s
tests='''        [Test]
        public void TwoRegionsRemainSeparatedInsideTheLegalCourt()
        {
            foreach(bool serve in new[]{false,true})foreach(int sign in new[]{-1,1})
            {
                var a=PlayerExecutionDrillsV1.RegionTarget(serve,sign,0);
                var b=PlayerExecutionDrillsV1.RegionTarget(serve,sign,1);
                Assert.Greater(Vector2.Distance(a,b),2f);
                foreach(var p in new[]{a,b})
                {
                    Assert.Less(Mathf.Abs(p.x)+1,3.048f);Assert.Less(p.y+1,6.7056f);
                    Assert.Greater(p.y-1,serve?2.1336f:0);
                    if(serve)Assert.Greater(p.x*sign-1,0);
                }
            }
            Assert.Throws<ArgumentException>(()=>PlayerExecutionDrillsV1.ValidateLayout("wrong",true,1));
            Assert.Throws<ArgumentException>(()=>PlayerExecutionDrillsV1.ValidateLayout("two-regions",false,1));
            Assert.Throws<ArgumentException>(()=>PlayerExecutionDrillsV1.ValidateLayout("two-regions",true,1.5f));
        }

'''
s=s.replace(marker,tests+marker)
p.write_text(s)
print('Installed opt-in two-region sampler, canonical landing evidence and layout contract tests')

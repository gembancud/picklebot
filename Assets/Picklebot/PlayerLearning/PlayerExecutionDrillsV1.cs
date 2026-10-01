using System;
using System.IO;
using System.Linq;
using Picklebot.PlayerControlsIntegration;
using UnityEngine;

namespace Picklebot.PlayerLearning
{
    // Opt-in companion to the existing drill runner. Absent component = legacy contract.
    // This supplies practice goals only, not the eventual strategy policy.
    public sealed class PlayerExecutionDrillsV1 : MonoBehaviour
    {
        public const string LinearReward = "linear-radius";
        public const string SmoothDistanceReward = "smooth-distance-2m";
        public bool SampleShotTargets;
        public string RewardMode = LinearReward;
        public string TargetLayout = "random";
        public float TargetRadius = 1.5f;
        public float LegalTargetReward = .25f;
        private StreamWriter evidence;
        public int Completed { get; private set; }
        public int LegalLandings { get; private set; }
        public int TargetsHit { get; private set; }

        [Serializable] public sealed class Result
        {
            public string contract = PlayerExecutionGoalV1.Contract, outcome;
            public int seed, player;
            public bool assigned, legalLanding, targetHit, hasLanding;
            public float targetX, targetZ, radius, distance, bonus, landingX, landingZ;
            public string targetLayout, rewardMode;
        }

        public static void ValidateRewardMode(string mode)
        {
            if(mode!=LinearReward && mode!=SmoothDistanceReward)throw new ArgumentException("Unknown placement reward mode.");
        }

        public static void ValidateLayout(string layout, bool sample, float radius)
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
            ValidateLayout(TargetLayout,SampleShotTargets,TargetRadius);
            ValidateRewardMode(RewardMode);
            if(RewardMode!=LinearReward&&!SampleShotTargets)throw new ArgumentException("Smooth placement feedback requires assigned targets.");
            if (run.CooperativePairs || run.OptimizerDiagnostics || run.BackgroundModel != null)
                throw new ArgumentException("The first execution-goal stage supports solo drills; legacy optimizer diagnostics and teammate training need their own new contract.");
            if (!float.IsFinite(TargetRadius) || TargetRadius <= 0 || TargetRadius > 3 ||
                !float.IsFinite(LegalTargetReward) || LegalTargetReward < 0 || LegalTargetReward > .25f)
                throw new ArgumentException("Invalid target radius or reward budget.");
            if (!string.IsNullOrEmpty(run.EvidenceDirectory))
            {
                Directory.CreateDirectory(run.EvidenceDirectory);
                evidence = new StreamWriter(new FileStream(Path.Combine(run.EvidenceDirectory,"execution-goals.jsonl"),FileMode.CreateNew)) {AutoFlush=true};
            }
        }

        public PlayerExecutionGoalV1[] Goals(PlayerContactDrillV3 drill)
        {
            // Separate seed-only sampler: no changes to feed sampling or physics RNG.
            var random = new System.Random(unchecked(drill.Seed ^ 0x53c81a9));
            Vector2? target = null;
            if (SampleShotTargets)
            {
                float x = -2.3f + 4.6f*(float)random.NextDouble();
                float z = 1.0f + 4.8f*(float)random.NextDouble();
                if (PlayerContactDrillV3.IsServeTask(drill.Task))
                {
                    var rules = drill.Match.World.Rules;
                    int sign = drill.Player < 2 ? 1 : -1;
                    x = Mathf.Sign(rules.ServiceX(rules.DesignatedReceiver)*sign)*(.5f + 1.8f*(float)random.NextDouble());
                    z = 2.8f + 3.0f*(float)random.NextDouble();
                }
                target = new Vector2(x,z);
                if(TargetLayout=="two-regions")
                {
                    bool serve=PlayerContactDrillV3.IsServeTask(drill.Task);
                    int sign=drill.Player<2?1:-1;
                    int serviceSign=serve?(int)Mathf.Sign(drill.Match.World.Rules.ServiceX(drill.Match.World.Rules.DesignatedReceiver)*sign):0;
                    target=RegionTarget(serve,serviceSign,random.Next(2));
                }
            }
            return Enumerable.Range(0,4).Select(seat => new PlayerExecutionGoalV1(seat,0,
                PlayerIntentV1.PlayBall,shotTarget:seat==drill.Player?target:null,shotRadius:TargetRadius)).ToArray();
        }

        public static float TargetBonus(PlayerExecutionGoalV1 goal, bool legal, Vector3 landing, float budget, string mode = LinearReward)
        {
            ValidateRewardMode(mode);
            if (!float.IsFinite(budget) || budget < 0 || budget > .25f) throw new ArgumentException("Invalid target bonus.");
            if (!legal || !goal.HasShotTarget) return 0;
            float distance = goal.LandingDistance(landing);
            if (!float.IsFinite(distance)) throw new ArgumentException("Non-finite landing.");
            // Success is still measured with ShotRadius. This optional feedback also
            // distinguishes legal misses outside that circle; it never changes physics.
            return budget*(mode==SmoothDistanceReward?Mathf.Exp(-distance/2f):Mathf.Max(0,1-distance/goal.ShotRadius));
        }

        public float Finish(PlayerContactDrillV3 drill, PlayerExecutionGoalV1 goal)
        {
            if (!drill.Done || goal.Seat!=drill.Player) throw new InvalidOperationException("Only a settled private drill may receive target feedback.");
            bool legal = drill.Outcome=="legal_return" || drill.Outcome=="legal_serve";
            var row = new Result {seed=drill.Seed,player=drill.Player,outcome=drill.Outcome,
                targetLayout=TargetLayout,rewardMode=RewardMode,assigned=goal.HasShotTarget,legalLanding=legal,targetX=goal.ShotTarget.x,targetZ=goal.ShotTarget.y,radius=goal.ShotRadius,distance=-1};
            if (legal)
            {
                int sign = drill.Player<2?1:-1;
                var bounce = drill.Match.World.Rules.Events.FirstOrDefault(e => e.kind=="bounce" &&
                    e.time>drill.FaceContactTime && e.position.z*sign>0);
                if (bounce==null) throw new InvalidOperationException("Legal drill outcome has no accepted post-contact landing.");
                row.hasLanding=true;row.landingX=bounce.position.x*sign;row.landingZ=bounce.position.z*sign;
                if(goal.HasShotTarget)
                {
                    row.distance=goal.LandingDistance(bounce.position);row.targetHit=row.distance<=goal.ShotRadius;
                    row.bonus=TargetBonus(goal,true,bounce.position,LegalTargetReward,RewardMode);
                }
            }
            Completed++; if(legal)LegalLandings++; if(row.targetHit)TargetsHit++;
            var stats=Unity.MLAgents.Academy.Instance.StatsRecorder;
            stats.Add("PicklebotExecution/LegalLanding",legal?1:0);
            if(row.assigned)
            {
                stats.Add("PicklebotExecution/TargetHitPerAttempt",row.targetHit?1:0);
                stats.Add("PicklebotExecution/PlacementBonus",row.bonus);
                if(legal){stats.Add("PicklebotExecution/TargetHitGivenLegal",row.targetHit?1:0);stats.Add("PicklebotExecution/LandingDistanceGivenLegal",row.distance);}
            }
            evidence?.WriteLine(JsonUtility.ToJson(row));
            return row.bonus;
        }
        private void OnDestroy() { evidence?.Dispose(); }
    }
}

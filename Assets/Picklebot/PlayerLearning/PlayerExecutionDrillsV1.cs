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
        public bool SampleShotTargets;
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
            public bool assigned, legalLanding, targetHit;
            public float targetX, targetZ, radius, distance, bonus;
        }

        public void Prepare(PlayerMlDrillsV3 run)
        {
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
            }
            return Enumerable.Range(0,4).Select(seat => new PlayerExecutionGoalV1(seat,0,
                PlayerIntentV1.PlayBall,shotTarget:seat==drill.Player?target:null,shotRadius:TargetRadius)).ToArray();
        }

        public static float TargetBonus(PlayerExecutionGoalV1 goal, bool legal, Vector3 landing, float budget)
        {
            if (!float.IsFinite(budget) || budget < 0 || budget > .25f) throw new ArgumentException("Invalid target bonus.");
            if (!legal || !goal.HasShotTarget) return 0;
            float distance = goal.LandingDistance(landing);
            if (!float.IsFinite(distance)) throw new ArgumentException("Non-finite landing.");
            return budget*Mathf.Max(0,1-distance/goal.ShotRadius);
        }

        public float Finish(PlayerContactDrillV3 drill, PlayerExecutionGoalV1 goal)
        {
            if (!drill.Done || goal.Seat!=drill.Player) throw new InvalidOperationException("Only a settled private drill may receive target feedback.");
            bool legal = drill.Outcome=="legal_return" || drill.Outcome=="legal_serve";
            var row = new Result {seed=drill.Seed,player=drill.Player,outcome=drill.Outcome,
                assigned=goal.HasShotTarget,legalLanding=legal,targetX=goal.ShotTarget.x,targetZ=goal.ShotTarget.y,radius=goal.ShotRadius,distance=-1};
            if (legal && goal.HasShotTarget)
            {
                int sign = drill.Player<2?1:-1;
                var bounce = drill.Match.World.Rules.Events.FirstOrDefault(e => e.kind=="bounce" &&
                    e.time>drill.FaceContactTime && e.position.z*sign>0);
                if (bounce==null) throw new InvalidOperationException("Legal drill outcome has no accepted post-contact landing.");
                row.distance=goal.LandingDistance(bounce.position);row.targetHit=row.distance<=goal.ShotRadius;
                row.bonus=TargetBonus(goal,true,bounce.position,LegalTargetReward);
            }
            Completed++; if(legal)LegalLandings++; if(row.targetHit)TargetsHit++;
            var stats=Unity.MLAgents.Academy.Instance.StatsRecorder;
            stats.Add("PicklebotExecution/LegalLanding",legal?1:0);
            if(row.assigned)
            {
                stats.Add("PicklebotExecution/TargetHitPerAttempt",row.targetHit?1:0);
                if(legal){stats.Add("PicklebotExecution/TargetHitGivenLegal",row.targetHit?1:0);stats.Add("PicklebotExecution/LandingDistanceGivenLegal",row.distance);}
            }
            evidence?.WriteLine(JsonUtility.ToJson(row));
            return row.bonus;
        }
        private void OnDestroy() { evidence?.Dispose(); }
    }
}

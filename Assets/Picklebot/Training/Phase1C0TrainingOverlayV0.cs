using System.Text;
using Picklebot.Evaluation;
using UnityEngine;

namespace Picklebot.Training
{
    [DisallowMultipleComponent]
    public sealed class Phase1C0TrainingOverlayV0 : MonoBehaviour
    {
        private Phase1C0AgentV0 agent;
        private GUIStyle style;

        public void Configure(Phase1C0AgentV0 configuredAgent)
        {
            agent = configuredAgent;
        }

        private void OnGUI()
        {
            if (agent == null || agent.Environment == null)
            {
                return;
            }

            style ??= new GUIStyle(GUI.skin.box)
            {
                alignment = TextAnchor.UpperLeft,
                fontSize = 14,
                normal = { textColor = Color.white }
            };

            var text = new StringBuilder();
            text.AppendLine("Picklebot Phase 1C0 - PROVISIONAL");
            text.AppendLine($"seed use: {agent.SeedUse}");
            text.AppendLine($"policy: {agent.PolicySource}");
            text.AppendLine(
                $"stage: {Phase1CProtocolV0.CurriculumStages[agent.CurrentStageIndex].Id}");
            text.AppendLine(
                $"seed: {agent.Environment.CurrentManifest?.Seed.ToString() ?? "-"}");
            text.AppendLine($"episode state: {agent.Environment.State}");
            text.AppendLine($"completed: {agent.CompletedEpisodeRecords.Count}");

            if (agent.CompletedEpisodeRecords.Count > 0)
            {
                var summary = Phase1C0MetricsV0.Aggregate(
                    agent.CompletedEpisodeRecords);
                text.AppendLine($"contact: {summary.contactRate:P1}");
                text.AppendLine($"legal return: {summary.legalReturnRate:P1}");
                text.AppendLine($"target hit: {summary.targetHitRate:P1}");
                text.AppendLine($"net: {summary.netContactRate:P1}");
                text.AppendLine($"out: {summary.outRate:P1}");
                text.AppendLine($"mean return: {summary.meanEpisodeReturn:F3}");
            }

            if (agent.LastResult != null)
            {
                text.AppendLine($"last terminal: {agent.LastResult.TerminationReason}");
                text.AppendLine($"last action: L{agent.LastAction.LinearVelocityLocal:F2}");
                text.AppendLine($"             A{agent.LastAction.AngularVelocityLocal:F2}");
                text.AppendLine($"last reward: {agent.LastReward.Total:F4}");
            }

            text.AppendLine($"evidence: {agent.EvidenceDirectory}");
            GUI.Box(new Rect(12f, 12f, 570f, 350f), text.ToString(), style);
        }

        private void OnDrawGizmos()
        {
            if (agent?.Environment == null)
            {
                return;
            }

            var points = agent.Environment.Trajectory;
            Gizmos.color = Color.yellow;
            for (var index = 1; index < points.Count; index++)
            {
                Gizmos.DrawLine(points[index - 1], points[index]);
            }

            var target = agent.Environment.CurrentManifest?.Parameters.TargetPosition;
            if (target.HasValue)
            {
                Gizmos.color = Color.green;
                Gizmos.DrawWireSphere(
                    target.Value,
                    Phase1CProtocolV0.CurriculumStages[
                        agent.CurrentStageIndex].TargetRadius);
            }
        }
    }
}

using System;
using System.Reflection;
using Unity.MLAgents;
namespace Picklebot.PlayerLearning
{
    // Transport-only metadata. Never an observation, action, reward or policy input.
    public static class PlayerDrillDiagnosticsV3
    {
        public const string Prefix="__picklebot_diag/";
        private static readonly FieldInfo Id=typeof(Agent).GetField("m_EpisodeId",BindingFlags.Instance|BindingFlags.NonPublic);
        private static readonly FieldInfo Info=typeof(Agent).GetField("m_Info",BindingFlags.Instance|BindingFlags.NonPublic);
        public static void ValidatePinnedContract()
        {
            if(Id==null||Id.FieldType!=typeof(int)||Info==null||Info.FieldType!=typeof(AgentInfo))throw new InvalidOperationException("Pinned ML-Agents diagnostic ID/terminal contract changed.");
        }
        public static bool IsTerminal(Agent agent,bool drillDone)
        {
            ValidatePinnedContract();
            if(agent==null)throw new ArgumentNullException(nameof(agent));
            // m_Info.done remains true during the first decision capture after reset.
            // Only use that flag for a disabled Agent; ordinary terminals belong to the drill.
            return drillDone||(!agent.isActiveAndEnabled&&((AgentInfo)Info.GetValue(agent)).done);
        }
        public static void Record(Agent agent,int originalIndex,bool drillDone)
        {
            ValidatePinnedContract();
            if(agent==null||originalIndex<0||originalIndex>=100000)throw new ArgumentException("Invalid diagnostic identity.");
            int id=(int)Id.GetValue(agent);
            bool terminal=IsTerminal(agent,drillDone);
            Academy.Instance.StatsRecorder.Add(Prefix+id+"/"+(terminal?"T":"D"),originalIndex,StatAggregationMethod.MostRecent);
        }
    }
}

using System;
using Picklebot.PlayerControls;

namespace Picklebot.PlayerControlsIntegration
{
    public interface IPlayerPolicyV3
    {
        string Name { get; }
        PlayerActionV3 Decide(PlayerObservationV3 observation,Random random);
        void Reset();
    }
    public sealed class PlayerDecisionV3
    {
        public readonly int player,observationTick,applyTick;
        public readonly PlayerObservationV3 observation;
        public readonly PlayerActionV3 action;
        public PlayerDecisionV3(int player,int tick,PlayerObservationV3 observation,PlayerActionV3 action)
        {this.player=player;observationTick=tick;applyTick=tick+PlayerDecisionLoopV3.LatencyTicks;this.observation=observation;this.action=action;}
    }
    public sealed class PlayerDecisionLoopV3
    {
        public const int DecisionTicks=12,LatencyTicks=6;
        private readonly IPlayerPolicyV3[] policies;
        private readonly Random[] random=new Random[4];
        private readonly int[] identities;
        private readonly PlayerActionV3[] active=new PlayerActionV3[4];
        private PlayerDecisionV3[] pending;
        private int lastTick=-1;
        public event Action<PlayerDecisionV3> Decided;
        public PlayerDecisionLoopV3(IPlayerPolicyV3[] policies,int seed,int[] identityBySeat=null)
        {
            if(policies==null||policies.Length!=4||Array.Exists(policies,p=>p==null))throw new ArgumentException("Four policies required.");
            this.policies=(IPlayerPolicyV3[])policies.Clone();identities=identityBySeat==null?new[]{0,1,2,3}:(int[])identityBySeat.Clone();
            if(identities.Length!=4)throw new ArgumentException("Four identities required.");int seen=0;
            for(int i=0;i<4;i++)
            {
                int identity=identities[i];
                if(identity<0||identity>3||identity/2!=i/2||(seen&(1<<identity))!=0)throw new ArgumentException("Identities must permute within teams.");
                seen|=1<<identity;random[i]=new Random(unchecked(seed*397+identity*7919));
                for(int j=0;j<i;j++)if(ReferenceEquals(policies[i],policies[j]))throw new ArgumentException("Each player needs its own policy instance; share weights, not mutable policy state.");
            }
        }
        public PlayerActionV3 ActionFor(int player) { if(player<0||player>3)throw new ArgumentOutOfRangeException(nameof(player));return active[player]; }
        public void Reset()
        {pending=null;lastTick=-1;Array.Clear(active,0,4);foreach(var policy in policies)policy.Reset();}
        public void Step(Func<int,int,PlayerObservationV3> capture,int tick)
        {
            if(capture==null||tick!=lastTick+1)throw new ArgumentException("Decision clock must advance one physics tick at a time.");
            if(tick%DecisionTicks==0)
            {
                var observations=new PlayerObservationV3[4];
                for(int i=0;i<4;i++)
                {
                    var observation=capture(i,tick);
                    if(observation==null||observation.player!=i||observation.tick!=tick)throw new ArgumentException("Capture identity/tick mismatch.");
                    observations[i]=observation.Copy();
                }
                var next=new PlayerDecisionV3[4];
                for(int i=0;i<4;i++)
                {
                    var action=policies[i].Decide(observations[i].Copy(),random[i]);
                    next[i]=new PlayerDecisionV3(i,tick,observations[i],action);
                }
                pending=next;
                foreach(var decision in next)Decided?.Invoke(decision);
            }
            if(pending!=null&&tick>=pending[0].applyTick)
            {for(int i=0;i<4;i++){active[i]=pending[i].action;}pending=null;}
            lastTick=tick;
        }
    }
}

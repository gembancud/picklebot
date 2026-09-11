using System;

namespace Picklebot.PlayerControlsIntegration
{
    public interface IPlayerPolicyV2
    {
        string Name { get; }
        PlayerActionV2 Decide(PlayerObservationV2 observation,Random random);
        void Reset();
    }
    public sealed class PlayerDecisionV2
    {
        public readonly int player,observationTick,applyTick;
        public readonly PlayerObservationV2 observation;
        public readonly PlayerActionV2 action;
        public readonly PlayerShotIntentV2 intent;
        public PlayerDecisionV2(int player,int tick,PlayerObservationV2 observation,PlayerActionV2 action,PlayerShotIntentV2 intent=default)
        {this.player=player;observationTick=tick;applyTick=tick+PlayerDecisionLoopV2.LatencyTicks;this.observation=observation;this.action=action;this.intent=intent;}
    }
    public sealed class PlayerDecisionLoopV2
    {
        public const int DecisionTicks=12,LatencyTicks=6;
        private readonly IPlayerPolicyV2[] policies;
        private readonly Random[] random=new Random[4];
        private readonly int[] identities;
        private readonly PlayerActionV2[] active=new PlayerActionV2[4];
        private readonly PlayerShotIntentV2[] activeIntent=new PlayerShotIntentV2[4];
        private PlayerDecisionV2[] pending;
        private int lastTick=-1;
        public event Action<PlayerDecisionV2> Decided;
        public PlayerDecisionLoopV2(IPlayerPolicyV2[] policies,int seed,int[] identityBySeat=null)
        {
            if(policies==null||policies.Length!=4||Array.Exists(policies,p=>p==null))throw new ArgumentException("Four policies required.");
            this.policies=(IPlayerPolicyV2[])policies.Clone();identities=identityBySeat==null?new[]{0,1,2,3}:(int[])identityBySeat.Clone();
            if(identities.Length!=4)throw new ArgumentException("Four identities required.");int seen=0;
            for(int i=0;i<4;i++)
            {
                int identity=identities[i];
                if(identity<0||identity>3||identity/2!=i/2||(seen&(1<<identity))!=0)throw new ArgumentException("Identities must permute within teams.");
                seen|=1<<identity;random[i]=new Random(unchecked(seed*397+identity*7919));
                for(int j=0;j<i;j++)if(ReferenceEquals(policies[i],policies[j]))throw new ArgumentException("Each player needs its own policy instance; share weights, not mutable policy state.");
            }
        }
        public PlayerActionV2 ActionFor(int player) { if(player<0||player>3)throw new ArgumentOutOfRangeException(nameof(player));return active[player]; }
        public PlayerShotIntentV2 IntentFor(int player) { if(player<0||player>3)throw new ArgumentOutOfRangeException(nameof(player));return activeIntent[player]; }
        public void Reset()
        {pending=null;lastTick=-1;Array.Clear(active,0,4);Array.Clear(activeIntent,0,4);foreach(var policy in policies)policy.Reset();}
        public void Step(Func<int,int,PlayerObservationV2> capture,int tick)
        {
            if(capture==null||tick!=lastTick+1)throw new ArgumentException("Decision clock must advance one physics tick at a time.");
            if(tick%DecisionTicks==0)
            {
                var observations=new PlayerObservationV2[4];
                for(int i=0;i<4;i++)
                {
                    var observation=capture(i,tick);
                    if(observation==null||observation.player!=i||observation.tick!=tick)throw new ArgumentException("Capture identity/tick mismatch.");
                    observations[i]=observation.Copy();
                }
                var next=new PlayerDecisionV2[4];
                for(int i=0;i<4;i++)
                {
                    var action=policies[i].Decide(observations[i].Copy(),random[i]);
                    var intent=policies[i] is IPlayerIntentPolicyV2 policy?policy.LastIntent:default;
                    next[i]=new PlayerDecisionV2(i,tick,observations[i],action,intent);
                }
                pending=next;
                foreach(var decision in next)Decided?.Invoke(decision);
            }
            if(pending!=null&&tick>=pending[0].applyTick)
            {for(int i=0;i<4;i++){active[i]=pending[i].action;activeIntent[i]=pending[i].intent;}pending=null;}
            lastTick=tick;
        }
    }
}

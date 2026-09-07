using System;
using Picklebot.Doubles;

namespace Picklebot.PlayerAgents
{
    [Serializable]
    public sealed class PlayerDecision
    {
        public int player, observationTick, applyTick;
        public PlayerObservation observation;
        public PlayerAction action;
        public PlayerPolicySample trace;
    }

    // Schedule four independent decisions against one frozen physical state.
    // All observations exist before any actor is called. No hitter arbitration.
    public sealed class PlayerDecisionLoop
    {
        public const int DecisionTicks = 12; // 20 Hz, with a 240 Hz physics clock.
        public const int LatencyTicks = 6;   // 25 ms; not a calibrated human delay.
        private readonly IPlayerPolicy[] policies;
        private readonly int playerMask;
        private readonly System.Random[] random = new System.Random[4];
        private readonly int[] identities;
        private readonly PlayerAction[] active = new PlayerAction[4];
        private PlayerDecision[] pending;
        public event Action<PlayerDecision> Decided;
        public int Decisions { get; private set; }

        public PlayerDecisionLoop(IPlayerPolicy[] policies, int seed, int playerMask = 15, int[] identityBySeat = null)
        {
            if (policies == null || policies.Length != 4 || Array.Exists(policies, p => p == null))
                throw new ArgumentException("Four player policy instances are required.");
            this.policies = (IPlayerPolicy[])policies.Clone();
            if (playerMask < 0 || playerMask > 15) throw new ArgumentOutOfRangeException(nameof(playerMask));
            this.playerMask = playerMask;
            identities = identityBySeat == null ? new[] { 0, 1, 2, 3 } : (int[])identityBySeat.Clone();
            if (identities.Length != 4) throw new ArgumentException("Four seat identities are required.", nameof(identityBySeat));
            int seen = 0;
            for (int i = 0; i < 4; i++)
            {
                int identity = identities[i];
                if (identity < 0 || identity > 3 || identity / 2 != i / 2 || (seen & (1 << identity)) != 0)
                    throw new ArgumentException("Identities must be a permutation within each team.", nameof(identityBySeat));
                seen |= 1 << identity;
                random[i] = new System.Random(unchecked(seed * 397 + identity * 7919));
            }
        }

        public PlayerAction ActionFor(int player) { DoublesRules.Team(player); return active[player]; }
        // Identity is not an observation or shared policy input. It owns the
        // private random stream when a test exchanges teammates between seats.
        public int IdentityFor(int player) { DoublesRules.Team(player); return identities[player]; }
        public string NameFor(int player) { DoublesRules.Team(player); return policies[player].Name; }
        public void Reset() { pending = null; Array.Clear(active, 0, 4); }

        public void Step(DoublesWorld world, int tick)
        {
            if (playerMask == 0) return;
            if (tick % DecisionTicks == 0)
            {
                var observations = new PlayerObservation[4];
                for (int i = 0; i < 4; i++) observations[i] = PlayerObservation.Capture(world, i, tick);
                var next = new PlayerDecision[4];
                for (int i = 0; i < 4; i++)
                {
                    if ((playerMask & (1 << i)) == 0) continue;
                    // Keep the recorded input intact even if an actor modifies its copy.
                    var action = policies[i].Decide(observations[i].Copy(), random[i]).Validated();
                    next[i] = new PlayerDecision { player = i, observationTick = tick,
                        applyTick = tick + LatencyTicks, observation = observations[i], action = action,
                        trace = (policies[i] as ITracedPlayerPolicy)?.LastSample };
                }
                pending = next;
                foreach (var decision in next) if (decision != null) { Decisions++; Decided?.Invoke(decision); }
            }
            if (pending != null && tick >= Array.Find(pending, d => d != null).applyTick)
            {
                for (int i = 0; i < 4; i++) if (pending[i] != null) active[i] = pending[i].action;
                pending = null;
            }
        }
    }
}

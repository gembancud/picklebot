using System;
using Picklebot.Doubles;
using UnityEngine;

namespace Picklebot.PlayerAgents
{
    // Frozen-baseline opponent adapter. This is not part of a learned actor.
    // Prepare reads the world; StepPlayer can move only explicitly owned seats.
    public sealed class BaselineControl
    {
        public readonly int TeamMask;
        public int PlayerMask => ((TeamMask & 1) != 0 ? 3 : 0) | ((TeamMask & 2) != 0 ? 12 : 0);
        public readonly StrokeController[] Strokes = { new StrokeController(), new StrokeController(), new StrokeController(), new StrokeController() };
        public int ActivePlayer { get; private set; } = -1;
        public Vector2 Target { get; private set; }
        public int LastShot { get; private set; }
        private readonly DoublesModels models;
        private readonly ContactModel contact;
        private readonly System.Random random;
        private readonly bool sampled;
        private int previousHits = -1;
        private TeamDecision decision;

        public BaselineControl(int teamMask, DoublesModels models, ContactModel contact, int seed, bool sampled)
        {
            if (teamMask < 1 || teamMask > 3 || models == null) throw new ArgumentException("A baseline needs valid team ownership and saved policies.");
            TeamMask = teamMask; this.models = models; this.contact = contact; this.sampled = sampled; random = new System.Random(seed);
        }
        public bool Controls(int player) => (TeamMask & (1 << DoublesRules.Team(player))) != 0;
        public void Reset() { previousHits = -1; ActivePlayer = -1; decision = null; foreach (var stroke in Strokes) stroke.Reset(); }

        public void Prepare(DoublesWorld world, Vector2 serveJitter)
        {
            var rules = world.Rules;
            if (rules.Dead) { foreach (var stroke in Strokes) stroke.Reset(); return; }
            if (previousHits != rules.Hits)
            {
                previousHits = rules.Hits; foreach (var stroke in Strokes) stroke.Reset(); ActivePlayer = -1; decision = null;
                // Preserve the original random draw order, including the two
                // provisional target draws replaced by the saved team policy.
                Target = rules.Phase == RallyPhase.AwaitServe
                    ? new Vector2(rules.ServiceX(rules.DesignatedReceiver), 4.2f) + serveJitter
                    : new Vector2((float)(random.NextDouble() * 4.2 - 2.1), 2.8f + (float)random.NextDouble() * 2);
                if (rules.Phase != RallyPhase.AwaitServe)
                {
                    decision = models.ForTeam(rules.ExpectedTeam).Choose(world, rules.ExpectedTeam, random, sampled);
                    LastShot = decision.action; Target = TeamPolicy.Target(LastShot);
                }
            }
            int actingTeam = rules.Phase == RallyPhase.AwaitServe ? rules.ServingTeam : rules.ExpectedTeam;
            if ((TeamMask & (1 << actingTeam)) == 0) return;
            if (ActivePlayer < 0)
            {
                if (rules.Phase == RallyPhase.AwaitServe) ActivePlayer = rules.Server;
                else if (rules.Phase == RallyPhase.ServeFlight) ActivePlayer = rules.DesignatedReceiver;
                else
                {
                    int a = rules.ExpectedTeam * 2, b = a + 1;
                    bool pa = Strokes[a].Plan(world, a, Target), pb = Strokes[b].Plan(world, b, Target);
                    if (pa || pb)
                    {
                        float ca = Strokes[a].ImpactAt + .2f * Vector3.Distance(world.Players[a].Position, Strokes[a].Impact);
                        float cb = Strokes[b].ImpactAt + .2f * Vector3.Distance(world.Players[b].Position, Strokes[b].Impact);
                        ActivePlayer = !pb ? a : !pa ? b : ca <= cb ? a : b;
                        Strokes[ActivePlayer ^ 1].Reset();
                    }
                }
            }
            if (ActivePlayer < 0) return;
            var plan = Strokes[ActivePlayer];
            plan.Kind = rules.Phase == RallyPhase.AwaitServe ? StrokeKind.Flat : TeamPolicy.Kind(LastShot);
            if (rules.Phase == RallyPhase.AwaitServe) new ContactParameters().Apply(plan);
            else if (contact != null) contact.strokes[(int)plan.Kind].Apply(plan);
            if (decision != null && decision.player < 0) { decision.player = ActivePlayer; plan.Reset(); }
            plan.Plan(world, ActivePlayer, Target);
        }

        public void StepPlayer(DoublesWorld world, int player)
        {
            if (!Controls(player)) throw new InvalidOperationException("Baseline cannot control a learned player's body.");
            var body = world.Players[player]; var rules = world.Rules;
            if (rules.Dead) { Strokes[player].Step(world, player, body.Position); return; }
            int side = body.Side; float x = (player % 2 == 0 ? 1.55f : -1.55f) * -side;
            if (ActivePlayer >= 0 && player == (ActivePlayer ^ 1)) x = world.Players[ActivePlayer].Position.x >= 0 ? -1.55f : 1.55f;
            var recovery = new Vector3(x, 0, side * (rules.CanVolley ? 3.5f : 6f));
            if (player == rules.Server && rules.Phase == RallyPhase.AwaitServe) recovery = body.Position;
            Strokes[player].Step(world, player, recovery);
        }
    }
}

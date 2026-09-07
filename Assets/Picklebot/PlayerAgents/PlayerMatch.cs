using System;
using Picklebot.Doubles;
using UnityEngine;

namespace Picklebot.PlayerAgents
{
    public sealed class PlayerMatch : IDisposable
    {
        public readonly DoublesWorld World;
        public readonly PlayerDecisionLoop Actors;
        public readonly PlayerSwing[] Swings = { new PlayerSwing(), new PlayerSwing(), new PlayerSwing(), new PlayerSwing() };
        public readonly PlayerMetrics Metrics = new PlayerMetrics();
        public readonly ContactModel ContactModel;
        public readonly BaselineControl Baseline;
        public int Tick { get; private set; }
        public int CompletedRallies { get; private set; }
        public int RallyNumber { get; private set; } = 1;
        public bool AutoNext = true;
        public Vector2 ServeJitter;
        private readonly StrokeController serve = new StrokeController();
        private readonly PlayerDeadBallReset deadBallReset = new PlayerDeadBallReset();
        private int previousHits;
        private float deadAt = -1;

        public PlayerMatch(bool visible, IPlayerPolicy[] policies, ContactModel contact, int seed = 1300000, BaselineControl baseline = null,
            int[] identityBySeat = null)
        {
            Baseline = baseline;
            Actors = new PlayerDecisionLoop(policies, seed, 15 & ~(baseline?.PlayerMask ?? 0), identityBySeat);
            ContactModel = contact;
            World = new DoublesWorld(visible);
        }

        public static float TeamReward(int player, int winner)
        {
            int team = DoublesRules.Team(player);
            if (winner < -1 || winner > 1) throw new ArgumentOutOfRangeException(nameof(winner));
            return winner < 0 ? 0 : winner == team ? 1 : -1;
        }

        public void Next()
        {
            World.ResetRally(); Tick = 0; previousHits = 0; deadAt = -1; RallyNumber++;
            Actors.Reset(); serve.Reset(); foreach (var swing in Swings) swing.Reset(); Metrics.ResetRally();
            Baseline?.Reset();
            deadBallReset.Reset();
        }

        public void Step()
        {
            var rules = World.Rules;
            Metrics.Before(World);
            Baseline?.Prepare(World, ServeJitter);
            if (rules.Dead)
            {
                if (deadAt < 0) deadAt = World.Time;
                foreach (var swing in Swings) swing.Reset();
                for (int i = 0; i < 4; i++)
                    if (deadBallReset.TryAction(World, i, World.Time - deadAt, out var resetAction))
                    {
                        Swings[i].Step(World, i, resetAction, ContactModel);
                        Metrics.deadBallClearanceSteps++;
                    }
                    else if (Baseline != null && Baseline.Controls(i)) Baseline.StepPlayer(World, i);
                    else Swings[i].Step(World, i, default, ContactModel);
            }
            else if (rules.Phase == RallyPhase.AwaitServe)
            {
                // The shared drop-serve reset skill is explicit, not actor control.
                serve.Kind = StrokeKind.Flat;
                serve.Plan(World, rules.Server, new Vector2(rules.ServiceX(rules.DesignatedReceiver), 4.2f) + ServeJitter);
                for (int i = 0; i < 4; i++)
                    if (Baseline != null && Baseline.Controls(i)) Baseline.StepPlayer(World, i);
                    else if (i == rules.Server) StepServe(i);
                    else Swings[i].Step(World, i, default, ContactModel);
            }
            else
            {
                if (previousHits != rules.Hits)
                { previousHits = rules.Hits; foreach (var swing in Swings) swing.Reset(); }
                Actors.Step(World, Tick);
                for (int i = 0; i < 4; i++)
                    if (Baseline != null && Baseline.Controls(i)) Baseline.StepPlayer(World, i);
                    else Swings[i].Step(World, i, Actors.ActionFor(i), ContactModel);
                Metrics.Intents(World, Actors);
                for (int i = 0; i < 4; i++)
                {
                    if (Baseline != null && Baseline.Controls(i)) continue;
                    if (Swings[i].SafetyLimited) Metrics.safetyLimitedPlayerSteps++;
                    if (!Swings[i].PaddleStepFeasible) Metrics.infeasiblePaddleSteps++;
                }
            }
            World.Simulate(); Tick++; Metrics.After(World);
            if (rules.Dead && deadAt >= 0 && World.Time - deadAt > 1f && rules.ResolveRally())
            { CompletedRallies++; if (AutoNext && rules.GameWinner < 0) Next(); }
        }

        public void Dispose() => World.Dispose();

        private void StepServe(int player)
        {
            // The serve remains a disclosed scripted reset skill. Only this
            // independent-player path changes; the saved baseline is untouched.
            var body = World.Players[player]; int side = body.Side;
            var rotation = Quaternion.LookRotation(serve.Planned ? serve.Normal : Vector3.forward * -side);
            var target = serve.Planned
                ? serve.Impact - serve.Normal * (Picklebot.Core.CourtGeometryV1.BallRadius + .008f) - rotation * Vector3.up * .0635f
                : body.Position + new Vector3(-side * .19f, 1.1f, -side * .46f);
            var feet = serve.Planned ? new Vector3(serve.Impact.x + side * .38f, 0, side * Mathf.Max(7.3f, side * serve.Impact.z + .43f)) : body.Position;
            Vector3 feed = Vector3.zero;
            if (serve.Planned)
            {
                float phase = World.Time - serve.ImpactAt;
                // Transfer forward body motion into the serve while the feet
                // remain behind the baseline. The motor still bounds the hand.
                feet.z = side * (phase < -.20f ? 7.65f : 6.50f);
                var stroke = serve.Normal * serve.Swing;
                target += stroke * Mathf.Clamp(phase, -.06f, .055f);
                if (phase > -.06f && phase < .055f) feed = stroke;
            }
            var velocity = PlayerMovement.Constrain(body, World.Players[player ^ 1], Vector3.ClampMagnitude((feet - body.Position) * 4, PlayerBody.Speed));
            feet = body.Position + velocity / 4;
            if (!PlayerPaddleMotor.Constrain(body, World.Players[player ^ 1], feet, ref target, ref rotation, ref feed, DoublesWorld.Dt))
                Metrics.infeasiblePaddleSteps++;
            body.Step(feet, target, rotation, feed, World.Players[player ^ 1], DoublesWorld.Dt);
        }
    }

    [Serializable]
    public sealed class PlayerMetrics
    {
        public int physicsSteps, simultaneousChaseSteps, closePartnerSteps, safetyLimitedPlayerSteps;
        public int deadBallClearanceSteps, infeasiblePaddleSteps;
        public int[] legalHits = new int[4], serves = new int[4];
        public float minSeparation = float.MaxValue, maxSpeed, maxAcceleration, maxPaddleSpeed, maxPaddleAcceleration, maxReach;
        public float[] playerMaxSpeed = new float[4], playerMaxAcceleration = new float[4], playerMaxPaddleSpeed = new float[4], playerMaxReach = new float[4];
        public float[] playerMaxPaddleAcceleration = new float[4];
        private readonly Vector3[] velocities = new Vector3[4];
        private readonly Vector3[] paddleVelocities = new Vector3[4];
        private int seenEvents;

        public void ResetRally() { seenEvents = 0; }
        public void Before(DoublesWorld world)
        { for (int i = 0; i < 4; i++) { velocities[i] = world.Players[i].Velocity; paddleVelocities[i] = world.Players[i].PaddleVelocity; } }
        public void Intents(DoublesWorld world, PlayerDecisionLoop loop)
        {
            int a = world.Rules.ExpectedTeam * 2;
            if (loop.ActionFor(a).attempt && loop.ActionFor(a + 1).attempt) simultaneousChaseSteps++;
        }
        public void After(DoublesWorld world)
        {
            physicsSteps++;
            for (int i = 0; i < 4; i++)
            {
                var body = world.Players[i];
                playerMaxSpeed[i] = Mathf.Max(playerMaxSpeed[i], body.Velocity.magnitude);
                playerMaxAcceleration[i] = Mathf.Max(playerMaxAcceleration[i], (body.Velocity - velocities[i]).magnitude / DoublesWorld.Dt);
                playerMaxPaddleSpeed[i] = Mathf.Max(playerMaxPaddleSpeed[i], body.PaddleVelocity.magnitude);
                playerMaxPaddleAcceleration[i] = Mathf.Max(playerMaxPaddleAcceleration[i], (body.PaddleVelocity - paddleVelocities[i]).magnitude / DoublesWorld.Dt);
                playerMaxReach[i] = Mathf.Max(playerMaxReach[i], Vector3.Distance(body.Shoulder, body.Hand));
                maxSpeed = Mathf.Max(maxSpeed, body.Velocity.magnitude);
                maxAcceleration = Mathf.Max(maxAcceleration, (body.Velocity - velocities[i]).magnitude / DoublesWorld.Dt);
                maxPaddleSpeed = Mathf.Max(maxPaddleSpeed, body.PaddleVelocity.magnitude);
                maxPaddleAcceleration = Mathf.Max(maxPaddleAcceleration, playerMaxPaddleAcceleration[i]);
                maxReach = Mathf.Max(maxReach, Vector3.Distance(body.Shoulder, body.Hand));
                float separation = Vector3.Distance(body.Position, world.Players[i ^ 1].Position);
                minSeparation = Mathf.Min(minSeparation, separation);
                if ((i & 1) == 0 && separation < .85f) closePartnerSteps++;
            }
            for (; seenEvents < world.Rules.Events.Count; seenEvents++)
            {
                var e = world.Rules.Events[seenEvents];
                if (e.kind == "hit") legalHits[e.player]++;
                if (e.kind == "serve") serves[e.player]++;
            }
        }
    }
}

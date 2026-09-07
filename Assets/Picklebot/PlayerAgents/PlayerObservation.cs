using System;
using Picklebot.Doubles;
using UnityEngine;

namespace Picklebot.PlayerAgents
{
    // An actor receives values only. No world, controller, future contact or
    // teammate action is included. Each capture owns a separate array.
    [Serializable]
    public sealed class PlayerObservation
    {
        public const string Version = "player-observation-v1";
        public const int Count = 54;
        public int player, tick;
        public float[] values;

        public static readonly string[] Fields = {
            "self.x", "self.z", "self.vx", "self.vz",
            "ball.relative.x", "ball.relative.y", "ball.relative.z",
            "ball.vx", "ball.vy", "ball.vz", "ball.wx", "ball.wy", "ball.wz",
            "partner.relative.x", "partner.relative.z", "partner.vx", "partner.vz",
            "opponent0.relative.x", "opponent0.relative.z", "opponent0.vx", "opponent0.vz",
            "opponent1.relative.x", "opponent1.relative.z", "opponent1.vx", "opponent1.vz",
            "paddle.relative.x", "paddle.relative.y", "paddle.relative.z",
            "paddle.normal.x", "paddle.normal.y", "paddle.normal.z",
            "paddle.vx", "paddle.vy", "paddle.vz", "paddle.wx", "paddle.wy", "paddle.wz",
            "feet.kitchen", "feet.outside",
            "phase.serve", "phase.serveFlight", "phase.returnFlight", "phase.rally", "phase.dead",
            "role.server", "role.receiver", "team.expected", "team.serving", "ball.bounced", "serve.bounced",
            "score.own", "score.opponent", "serve.number", "role.right"
        };

        // A 180-degree rotation, not a reflection: spin uses the same transform.
        // Both teams attack toward positive canonical Z; positive X is right.
        public static Vector3 ToLocal(Vector3 value, int player)
        {
            int sign = -DoublesRules.Side(DoublesRules.Team(player));
            return new Vector3(value.x * sign, value.y, value.z * sign);
        }

        public static Vector3 ToWorld(Vector3 value, int player) => ToLocal(value, player);

        public static PlayerObservation Capture(DoublesWorld world, int player, int tick)
        {
            int team = DoublesRules.Team(player);
            var self = world.Players[player];
            var rules = world.Rules;
            var result = new PlayerObservation { player = player, tick = tick, values = new float[Count] };
            int index = 0;
            void Add(float value)
            {
                if (!float.IsFinite(value)) throw new InvalidOperationException("Non-finite player observation.");
                result.values[index++] = value;
            }
            void Ground(Vector3 value, float xScale, float zScale)
            { var local = ToLocal(value, player); Add(local.x / xScale); Add(local.z / zScale); }
            void Spatial(Vector3 value, Vector3 scale)
            { var local = ToLocal(value, player); Add(local.x / scale.x); Add(local.y / scale.y); Add(local.z / scale.z); }
            void Other(int id)
            {
                Ground(world.Players[id].Position - self.Position, 8.4f, 16.2f);
                Ground(world.Players[id].Velocity, PlayerBody.Speed, PlayerBody.Speed);
            }
            Ground(self.Position, 4.2f, 8.1f);
            Ground(self.Velocity, PlayerBody.Speed, PlayerBody.Speed);
            Spatial(world.Ball.position - self.Position, new Vector3(8.4f, 3f, 16.2f));
            Spatial(world.Ball.linearVelocity, Vector3.one * 20f);
            Spatial(world.Ball.angularVelocity, Vector3.one * 100f);
            Other(player ^ 1);
            Other((1 - team) * 2); Other((1 - team) * 2 + 1);
            Spatial(self.Paddle.position - self.Position, new Vector3(1f, 2f, 1f));
            Spatial(self.Paddle.rotation * Vector3.forward, Vector3.one);
            Spatial(self.PaddleVelocity, Vector3.one * PlayerBody.PaddleSpeed);
            Spatial(self.AngularVelocity, Vector3.one * PlayerBody.AngularSpeed);
            Add(self.FeetInKitchen ? 1 : 0); Add(self.BothFeetOutside ? 1 : 0);
            for (int phase = 0; phase < 5; phase++) Add((int)rules.Phase == phase ? 1 : 0);
            Add(rules.Server == player ? 1 : 0); Add(rules.DesignatedReceiver == player ? 1 : 0);
            Add(rules.ExpectedTeam == team ? 1 : 0); Add(rules.ServingTeam == team ? 1 : 0);
            Add(rules.Bounced ? 1 : 0); Add(world.ServeBounced ? 1 : 0);
            Add(rules.Score[team] / 11f); Add(rules.Score[1 - team] / 11f);
            Add(rules.ServerNumber / 2f); Add(rules.IsRight(player) ? 1 : 0);
            if (index != Count) throw new InvalidOperationException("Player observation schema mismatch.");
            return result;
        }

        public PlayerObservation Copy() => new PlayerObservation
        { player = player, tick = tick, values = (float[])values.Clone() };
    }
}

using System;
using Picklebot.Doubles;
using UnityEngine;

namespace Picklebot.PlayerAgents
{
    [Serializable]
    public struct PlayerAction
    {
        public float moveX, moveZ;
        public bool attempt;
        public int shot;

        public PlayerAction Validated()
        {
            if (!float.IsFinite(moveX) || !float.IsFinite(moveZ))
                throw new ArgumentException("A player action contains non-finite movement.");
            if (shot < 0 || shot >= TeamPolicy.Actions)
                throw new ArgumentOutOfRangeException(nameof(shot));
            var bounded = Vector2.ClampMagnitude(new Vector2(moveX, moveZ), 1f);
            return new PlayerAction { moveX = bounded.x, moveZ = bounded.y, attempt = attempt, shot = shot };
        }

        public Vector3 WorldVelocity(int player)
        {
            var a = Validated();
            return PlayerObservation.ToWorld(new Vector3(a.moveX, 0, a.moveZ), player) * PlayerBody.Speed;
        }

        public Vector2 WorldShotTarget(int player)
        {
            var goal = TeamPolicy.Target(Validated().shot);
            var p = PlayerObservation.ToWorld(new Vector3(goal.x, 0, goal.y), player);
            return new Vector2(p.x, Mathf.Abs(p.z));
        }
    }

    public interface IPlayerPolicy
    {
        string Name { get; }
        PlayerAction Decide(PlayerObservation observation, System.Random random);
    }

    // Test/development controller. It must never be labelled as a trained actor.
    public sealed class ConstantPlayerPolicy : IPlayerPolicy
    {
        private readonly PlayerAction action;
        public string Name => "untrained constant action";
        public ConstantPlayerPolicy(PlayerAction action) { this.action = action.Validated(); }
        public PlayerAction Decide(PlayerObservation observation, System.Random random) => action;
    }
}

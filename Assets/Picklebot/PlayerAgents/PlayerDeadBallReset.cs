using System;
using Picklebot.Doubles;

namespace Picklebot.PlayerAgents
{
    // Scripted clearance after a recorded fault only. Live-rally movement,
    // rule decisions and scoring are not changed by this reset skill.
    public sealed class PlayerDeadBallReset
    {
        private readonly bool[] faulted = new bool[4], clearing = new bool[4];
        private int seenEvents;

        public void Reset()
        {
            Array.Clear(faulted, 0, 4); Array.Clear(clearing, 0, 4); seenEvents = 0;
        }

        public bool TryAction(DoublesWorld world, int player, float deadSeconds, out PlayerAction action)
        {
            action = default;
            if (!world.Rules.Dead) return false;
            for (; seenEvents < world.Rules.Events.Count; seenEvents++)
            {
                var e = world.Rules.Events[seenEvents];
                if (e.player >= 0 && e.player < 4 && e.fault == Fault.KitchenMomentum
                    && (e.kind == "fault" || e.kind == "late volley fault")) faulted[e.player] = true;
            }
            var body = world.Players[player];
            if (!faulted[player] || body.BothFeetOutside) { clearing[player] = false; return false; }
            // First allow real momentum and foot support to settle. Never
            // replace measured feet or clear the rules' pending-volley state.
            if (!clearing[player] && deadSeconds >= 1f && body.Velocity.magnitude < .03f)
                clearing[player] = true;
            if (!clearing[player]) return false;
            action.moveZ = -1f / PlayerBody.Speed; // 1 m/s away from the net, through the normal motor.
            return true;
        }
    }
}

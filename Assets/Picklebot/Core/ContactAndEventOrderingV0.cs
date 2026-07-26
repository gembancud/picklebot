using System;
using System.Collections.Generic;

namespace Picklebot.Core
{
    public sealed class ContactLedgerV0
    {
        private readonly Dictionary<int, ulong> lastContactTicks = new();

        public bool ShouldRecord(int entityId, ulong physicsTick, int minimumSeparationTicks)
        {
            if (minimumSeparationTicks < 1)
            {
                throw new ArgumentOutOfRangeException(nameof(minimumSeparationTicks));
            }

            if (lastContactTicks.TryGetValue(entityId, out var lastTick) &&
                physicsTick - lastTick < (ulong)minimumSeparationTicks)
            {
                return false;
            }

            lastContactTicks[entityId] = physicsTick;
            return true;
        }

        public void Clear()
        {
            lastContactTicks.Clear();
        }
    }

    public static class EventOrderingV0
    {
        public static int Phase(EnvironmentEventKindV0 kind)
        {
            return kind switch
            {
                EnvironmentEventKindV0.InvalidNumericState => 0,
                EnvironmentEventKindV0.EpisodeStarted => 1,
                EnvironmentEventKindV0.BallLaunched => 1,
                EnvironmentEventKindV0.ActionClamped => 1,
                EnvironmentEventKindV0.BallPaddleContact => 2,
                EnvironmentEventKindV0.BallNetContact => 2,
                EnvironmentEventKindV0.BallFloorContact => 2,
                EnvironmentEventKindV0.BallEnteredZone => 3,
                EnvironmentEventKindV0.BallExitedPlayableVolume => 3,
                EnvironmentEventKindV0.EpisodeTerminated => 4,
                _ => throw new ArgumentOutOfRangeException(nameof(kind), kind, null)
            };
        }
    }
}

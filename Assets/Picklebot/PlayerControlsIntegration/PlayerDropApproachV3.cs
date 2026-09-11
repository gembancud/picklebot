using System;
using UnityEngine;
namespace Picklebot.PlayerControlsIntegration
{
    // Reward accounting only. Construct at the first measured drop bounce.
    public sealed class PlayerDropApproachV3
    {
        public const float MaximumReward=.5f;
        private const float Radius=2;
        private float best,paid;
        public PlayerDropApproachV3(float distance) { best=CheckedDistance(distance); }
        private static float CheckedDistance(float distance)
        {
            if(!float.IsFinite(distance)||distance<0)throw new ArgumentOutOfRangeException(nameof(distance));
            return Mathf.Min(distance,Radius);
        }
        public float Advance(float distance)
        {
            float next=CheckedDistance(distance);
            best=Mathf.Min(best,next);
            // Credit absolute closest proximity, including the first bounce
            // measurement. Starting farther away cannot increase the budget.
            float potential=MaximumReward*(1-best/Radius);
            float reward=Mathf.Max(0,potential-paid);paid=potential;return reward;
        }
    }
}

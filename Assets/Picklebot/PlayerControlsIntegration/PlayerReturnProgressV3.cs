using System;
using UnityEngine;
namespace Picklebot.PlayerControlsIntegration
{
    // Reward accounting only; inputs are measured ball positions after a real hit.
    public sealed class PlayerReturnProgressV3
    {
        private readonly float start,distance;
        private float best;
        public const float MaximumReward=.25f;
        public PlayerReturnProgressV3(float startCanonicalZ)
        {
            if(!float.IsFinite(startCanonicalZ))throw new ArgumentException("Finite hit position required.");
            start=startCanonicalZ;distance=Mathf.Max(.5f,1-start);
        }
        public float Advance(float canonicalZ)
        {
            if(!float.IsFinite(canonicalZ))throw new ArgumentException("Finite ball position required.");
            float progress=Mathf.Clamp01((canonicalZ-start)/distance);
            float reward=MaximumReward*Mathf.Max(0,progress-best);best=Mathf.Max(best,progress);return reward;
        }
    }
}

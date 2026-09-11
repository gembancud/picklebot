using System;
using UnityEngine;
namespace Picklebot.PlayerControlsIntegration
{
    // Reward only, measured once when accepted physical paddle contact separates.
    public static class PlayerServeDirectionV3
    {
        public const string Version="fixed-serve-direction-v3-separation-eight-metres-per-second";
        // Reward scale, not a physical velocity limit or target command.
        public const float SaturationSpeed=8f;
        public const float MaximumMagnitude=.5f;
        public static float ContactReward(float canonicalForwardVelocity)
        {
            if(!float.IsFinite(canonicalForwardVelocity))throw new ArgumentException("Finite measured outgoing velocity required.");
            return MaximumMagnitude*Mathf.Clamp(canonicalForwardVelocity/SaturationSpeed,-1,1);
        }
    }
}

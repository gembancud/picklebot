using System;
using UnityEngine;

namespace Picklebot.PlayerControlsIntegration
{
    // Optional curriculum feedback for root translation, not a stroke or navigation controller.
    // The ball sample is its current measured position; no reset target or future trajectory is used.
    // This bounded shaping heuristic is not claimed to preserve the optimal policy.
    public sealed class PlayerMovementPositionRewardV3
    {
        public const float MaximumBudget=.25f, ImprovementForFullReward=.75f;
        private readonly Vector2 initialRoot,initialFace;
        private readonly float budget;
        public float TotalReward {get;private set;}
        public static void ValidateBudget(float value)
        {if(!float.IsFinite(value)||value<0||value>MaximumBudget)throw new ArgumentOutOfRangeException(nameof(value));}
        private static Vector2 Horizontal(Vector3 v)
        {
            if(!float.IsFinite(v.x)||!float.IsFinite(v.y)||!float.IsFinite(v.z))throw new ArgumentException("Finite position required.");
            return new Vector2(v.x,v.z);
        }
        public PlayerMovementPositionRewardV3(Vector3 root,Vector3 face,float budget)
        {ValidateBudget(budget);initialRoot=Horizontal(root);initialFace=Horizontal(face);this.budget=budget;}
        public float Advance(Vector3 root,Vector3 ball)
        {
            var displacement=Horizontal(root)-initialRoot;var b=Horizontal(ball);
            float improvement=Vector2.Distance(b,initialFace)-Vector2.Distance(b,initialFace+displacement);
            float score=budget*Mathf.Clamp01(improvement/ImprovementForFullReward);
            float reward=Mathf.Max(0,score-TotalReward);TotalReward+=reward;return reward;
        }
    }
}

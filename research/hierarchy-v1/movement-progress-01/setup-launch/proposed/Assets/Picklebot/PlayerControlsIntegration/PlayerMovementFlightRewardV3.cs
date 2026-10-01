using System;
using UnityEngine;

namespace Picklebot.PlayerControlsIntegration
{
    // Observes measured post-contact ball positions. No physics, action or target access.
    public sealed class PlayerMovementFlightRewardV3
    {
        public const float MaximumReward=PlayerReturnProgressV3.MaximumReward;
        private PlayerReturnProgressV3 progress;
        public float TotalReward {get;private set;}
        public int RewardedSteps {get;private set;}
        public bool Started=>progress!=null;
        public bool Stopped {get;private set;}

        public float Advance(float canonicalZ,bool acceptedFaceContact,bool faulted,bool terminal,bool firstLegalLanding)
        {
            if(!float.IsFinite(canonicalZ))throw new ArgumentException("Finite measured ball position required.");
            // Stop before adding anything on a fault, deadline, or first landing.
            // In particular, a pending volley-momentum check cannot extend this signal.
            if(Stopped||faulted||terminal||firstLegalLanding){Stop();return 0;}
            if(progress==null)
            {
                if(acceptedFaceContact)progress=new PlayerReturnProgressV3(canonicalZ);
                return 0;
            }
            float reward=Mathf.Min(progress.Advance(canonicalZ),MaximumReward-TotalReward);
            if(reward>0){TotalReward+=reward;RewardedSteps++;}
            return reward;
        }
        public void Stop(){Stopped=true;}
    }
}

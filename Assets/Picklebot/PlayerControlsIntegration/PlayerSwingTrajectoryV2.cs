using System;
using UnityEngine;
namespace Picklebot.PlayerControlsIntegration
{
    // Requested trajectory; actual paddle motion still passes all motor limits.
    public static class PlayerSwingTrajectoryV2
    {
        public const float RampAcceleration=80f,FollowThrough=.055f;
        public static void Sample(Vector3 contactVelocity,float phase,out Vector3 displacement,out Vector3 feed)
        {
            if(!float.IsFinite(contactVelocity.x)||!float.IsFinite(contactVelocity.y)||!float.IsFinite(contactVelocity.z)||!float.IsFinite(phase))throw new ArgumentException("Finite swing request required.");
            float duration=contactVelocity.magnitude/RampAcceleration;
            if(duration<1e-6f){displacement=feed=Vector3.zero;return;}
            if(phase<=-duration){displacement=-.5f*contactVelocity*duration;feed=Vector3.zero;}
            else if(phase<0)
            {
                float fraction=(phase+duration)/duration;
                displacement=.5f*contactVelocity*duration*(fraction*fraction-1);
                feed=contactVelocity*fraction;
            }
            else {displacement=contactVelocity*Mathf.Min(phase,FollowThrough);feed=phase<FollowThrough?contactVelocity:Vector3.zero;}
        }
    }
}

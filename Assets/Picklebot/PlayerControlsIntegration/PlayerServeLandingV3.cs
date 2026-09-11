using System;
using Picklebot.Doubles;
using UnityEngine;
namespace Picklebot.PlayerControlsIntegration
{
    // Outcome feedback only: measured first floor contact, never a motion command.
    public static class PlayerServeLandingV3
    {
        public const string Version="fixed-serve-landing-v1-measured-diagonal-distance";
        public const float MaximumReward=.5f;
        public const float DistanceScale=4f;
        public static float ContactReward(Vector3 contact,int server,float receiverServiceX)
        {
            if(server<0||server>3)throw new ArgumentOutOfRangeException(nameof(server));
            if(!float.IsFinite(contact.x)||!float.IsFinite(contact.y)||!float.IsFinite(contact.z)||!float.IsFinite(receiverServiceX)||receiverServiceX==0)throw new ArgumentException("Finite floor contact and nonzero receiver service side required.");
            float x=contact.x*Mathf.Sign(receiverServiceX),z=contact.z*(server<2?1:-1);
            // Interior margins encourage depth and room from lines. They do not change rules.
            float dx=x-Mathf.Clamp(x,.2f,DoublesRules.HalfWidth-.2f);
            float dz=z-Mathf.Clamp(z,DoublesRules.Kitchen+.3f,DoublesRules.HalfLength-.3f);
            float distance=Mathf.Sqrt(dx*dx+dz*dz);
            return MaximumReward*Mathf.Exp(-distance/DistanceScale);
        }
    }
}

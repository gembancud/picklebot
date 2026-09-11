using System;
namespace Picklebot.PlayerControlsIntegration
{
    // Default is direct paddle control. Intent is captured and delayed with its
    // movement action, never read from mutable policy state during execution.
    public readonly struct PlayerShotIntentV2
    {
        public readonly bool enabled,attempt,legacyAutoPosture;
        public readonly int shot;
        public PlayerShotIntentV2(bool attempt,int shot,bool legacyAutoPosture=false)
        {
            if(shot<0||shot>8)throw new ArgumentOutOfRangeException(nameof(shot));
            enabled=true;this.attempt=attempt;this.shot=shot;this.legacyAutoPosture=legacyAutoPosture;
        }
    }
    public interface IPlayerIntentPolicyV2:IPlayerPolicyV2
    { PlayerShotIntentV2 LastIntent { get; } }
}

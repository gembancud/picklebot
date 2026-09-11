using System;
using UnityEngine;
namespace Picklebot.PlayerControlsIntegration
{
    // Reset distribution only. Nothing here steers an actor or modifies a live flight.
    public static class PlayerMovementPatternV3
    {
        public const float LocalExtentMetres=4;
        public static void Validate(string pattern,float range,bool soloMovement)
        {
            if(pattern!="court"&&pattern!="lateral"&&pattern!="lateral-left"&&pattern!="lateral-right"&&pattern!="depth"&&pattern!="axes"&&pattern!="local")throw new ArgumentException("Unknown movement pattern.");
            if(pattern!="court"&&(!soloMovement||!float.IsFinite(range)||range<0||range>.25f))throw new ArgumentException("Local movement patterns require solo feeds and a range from0 to.25 (up to1metre per axis).");
        }
        public static int Region(string pattern,int seed,int original)
        {
            if(pattern=="court"||pattern=="local")return original;
            var rng=new System.Random(unchecked(seed^0x329a81));
            if(pattern=="lateral-left")return 3;
            if(pattern=="lateral-right")return 5;
            if(pattern=="lateral")return rng.Next(2)==0?3:5;
            if(pattern=="depth")return rng.Next(2)==0?1:7;
            if(pattern=="axes")return new[]{3,5,1,7}[rng.Next(4)];
            throw new ArgumentException("Unknown movement pattern.");
        }
        public static Vector3 LocalDestination(Vector3 face,Vector3 right,Vector3 forward,int region)
        {
            if(region<0||region>8)throw new ArgumentOutOfRangeException(nameof(region));
            return face+LocalExtentMetres*((region%3-1)*right+(1-region/3)*forward);
        }
    }
}

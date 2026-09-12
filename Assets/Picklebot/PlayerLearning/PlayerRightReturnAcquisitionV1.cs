using System;
namespace Picklebot.PlayerLearning
{
    // Diagnostic reset distribution only; never supplies a movement or stroke command.
    public static class PlayerRightReturnAcquisitionV1
    {
        public const string Task="right-return-acquisition";
        public static string Feed(int index)
        {if(index<0)throw new ArgumentOutOfRangeException(nameof(index));return index/4%2==0?"rally-air-feed":"rally-bounce-feed";}
        public static void Validate(string task,float range,string pattern,bool recovery,float prior,bool interleaved,float timing,float starts,float difficulty)
        {
            if(task!=Task)return;
            if(!float.IsFinite(range)||range<=0||range>.25f||pattern!="lateral-right"||recovery||prior!=0||interleaved||timing!=0||starts!=0||difficulty!=0)
                throw new ArgumentException("Right-return acquisition requires fixed positive local range, right-only feeds, zero timing/start changes and no maintenance schedule.");
        }
    }
}

using System;
namespace Picklebot.PlayerLearning
{
    // Reset scheduling only. No access to policy actions, body state or live trajectories.
    public static class PlayerRecoveryScheduleV3
    {
        public const int CycleLength=256;
        public readonly struct Episode
        {
            public readonly string Task,Pattern,Group;
            public readonly float Range,Difficulty;
            public readonly bool ServeFromLeft;
            public Episode(string task,string pattern,string group,float range,float difficulty,bool left=false)
            {Task=task;Pattern=pattern;Group=group;Range=range;Difficulty=difficulty;ServeFromLeft=left;}
        }
        public static Episode For(int index,float lateralRange,float priorRange,float receiveDifficulty,string focusPattern="lateral")
        {
            if(index<0)throw new ArgumentOutOfRangeException(nameof(index));
            if(focusPattern!="lateral"&&focusPattern!="axes"&&focusPattern!="lateral-right")throw new ArgumentException("Recovery focus must be lateral, axes, or fixed lateral-right.",nameof(focusPattern));
            int block=index/4%64;
            if(block<16) {
                int basic=block%8;
                return new Episode(basic<2?"stationary-serve":basic<4?"receive-feed":basic<6?"rally-air-feed":"rally-bounce-feed",
                    "court","familiar",basic<4?-1:0,basic<2?1:basic==3?receiveDifficulty:0,basic==1);
            }
            float fraction=(1+block%4)*.25f;
            if(block<32)return new Episode(block<24?"rally-air-feed":"rally-bounce-feed","court","prior",priorRange*fraction,0);
            // New acquisition-retention arm: preserve the first128 maintenance resets;
            // focus on the same fixed rightward range that the acquisition run learned.
            if(focusPattern=="lateral-right")return new Episode(block<48?"rally-air-feed":"rally-bounce-feed","lateral-right","focus",lateralRange,0);
            bool air=block<48,left=block<40||block>=48&&block<60;
            return new Episode(air?"rally-air-feed":"rally-bounce-feed",focusPattern=="axes"?"axes":left?"lateral-left":"lateral-right","focus",lateralRange*fraction,0);
        }
        public static void Validate(bool enabled,string task,float range,float priorRange,string pattern,float timing,float starts,float bonus,int seedCount)
        {
            if(!enabled)return;
            if(task!="movement-maintenance"||(pattern!="lateral"&&pattern!="axes"&&pattern!="lateral-right")||!float.IsFinite(range)||range<=0||range>.25f||!float.IsFinite(priorRange)||priorRange<=0||priorRange>1
               ||timing!=0||starts!=0||bonus!=0||seedCount<=0||seedCount%CycleLength!=0)
                throw new ArgumentException("Recovery mix requires solo lateral, axes or fixed-right practice, positive bounded focus/prior ranges, zero timing/start/reward changes and complete256-episode cycles.");
        }
    }
}

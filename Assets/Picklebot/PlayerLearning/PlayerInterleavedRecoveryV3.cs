using System;
namespace Picklebot.PlayerLearning
{
    // Allocation order only. Returned indices retain the original seed, seat and scenario.
    public static class PlayerInterleavedRecoveryV3
    {
        public static int Index(int ordinal,int workerId,bool enabled)
        {
            if(ordinal<0||workerId<0||workerId>=8)throw new ArgumentOutOfRangeException();
            if(!enabled)return ordinal;
            int cycle=ordinal/256*256,round=(ordinal%256/16+5*workerId)%16,slot=ordinal%16;
            int original=slot switch {
                0 or 4 or 8 or 12 => 4*round+slot/4,
                1 or 5 or 9 or 13 => 64+4*round+slot/4,
                2 or 10 => 128+2*round+slot/8,
                6 or 14 => 160+2*round+slot/8,
                3 or 7 or 11 => 192+3*round+slot/4,
                15 => 240+round,
                _ => throw new InvalidOperationException()
            };
            return checked(cycle+original);
        }
        public static void Validate(bool enabled,bool recovery,int seedCount,int workerId)
        {
            if(workerId<0||workerId>=8||enabled&&(!recovery||seedCount<=0||seedCount%256!=0))
                throw new ArgumentException("Interleaving requires complete recovery cycles and a valid worker index.");
        }
    }
}

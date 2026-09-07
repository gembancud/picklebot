using System;

namespace Picklebot.Rally
{
    // Side -1 is the near end; side +1 is the far end.
    [Serializable]
    public sealed class RallyRules
    {
        public int Receiver { get; private set; }
        public int Winner { get; private set; }
        public int Returns { get; private set; }
        public int Contacts { get; private set; }
        public bool ReadyToHit { get; private set; }
        public bool Finished { get; private set; }
        public string Result { get; private set; } = "Serve";
        private int server;
        private bool firstServeBounce;
        private bool awaitingReturnLanding;

        public void Reset(int servingSide)
        {
            if (servingSide != -1 && servingSide != 1)
                throw new ArgumentOutOfRangeException(nameof(servingSide));
            server = servingSide;
            Receiver = -server;
            Winner = Returns = Contacts = 0;
            ReadyToHit = Finished = awaitingReturnLanding = false;
            firstServeBounce = true;
            Result = "Serve: own-side bounce";
        }

        public void Bounce(int side)
        {
            if (Finished) return;
            if (firstServeBounce)
            {
                if (side != server) { Fault(server, "Invalid serve"); return; }
                firstServeBounce = false;
                Result = "Serve: receiving-side bounce";
                return;
            }
            if (ReadyToHit) { Fault(Receiver, "Second bounce"); return; }
            if (side != Receiver) { Fault(-Receiver, "Wrong-side landing"); return; }
            if (awaitingReturnLanding) Returns++;
            awaitingReturnLanding = false;
            ReadyToHit = true;
            Result = "Return after one bounce";
        }

        public void Hit(int side)
        {
            if (Finished) return;
            if (firstServeBounce || !ReadyToHit || side != Receiver)
            { Fault(side, "Volley or wrong paddle"); return; }
            Contacts++;
            Receiver = -side;
            ReadyToHit = false;
            awaitingReturnLanding = true;
            Result = "Ball in flight";
        }

        public void Lost(string reason)
        {
            if (Finished) return;
            Fault(firstServeBounce ? server : ReadyToHit ? Receiver : -Receiver, reason);
        }

        public void Fault(int side, string reason)
        {
            if (Finished) return;
            Winner = -side;
            Finished = true;
            ReadyToHit = false;
            Result = reason;
        }
    }
}

using System;
using Picklebot.Core;
using UnityEngine;

namespace Picklebot.Inspection
{
    // Singles rally legality. The grounded player disc is a footwork proxy,
    // not an implementation of human feet, jumping, or official officiating.
    public sealed class InspectionRules
    {
        public int Receiver { get; private set; }
        public int Winner { get; private set; }
        public int Returns { get; private set; }
        public bool Finished { get; private set; }
        public bool CanVolley => requiredBounces == 0;
        public string Result { get; private set; }
        private int requiredBounces, server, targetX;
        private bool awaitingServe, bounced;
        private readonly bool[] volleyMomentum = new bool[2];
        private readonly float[] stillSeconds = new float[2];
        public void BeginServe(int servingSide, int servingXSign)
        {
            if(Math.Abs(servingSide)!=1||Math.Abs(servingXSign)!=1)throw new ArgumentException("Use side and service position signs -1 or +1.");
            server=servingSide;targetX=-servingXSign;Receiver=-server;
            requiredBounces=2;awaitingServe=true;bounced=Finished=false;Winner=Returns=0;
            Array.Clear(volleyMomentum,0,2);Array.Clear(stillSeconds,0,2);
            Result="Serve: diagonal receiving-court bounce required";
        }
        public void Bounce(Vector3 point)
        {
            if(Finished)return;
            int side=point.z<0?-1:1;
            if(Mathf.Abs(point.x)>CourtGeometryV1.HalfWidth+.0001f||Mathf.Abs(point.z)>CourtGeometryV1.HalfLength+.0001f)
            { Fault(bounced?Receiver:-Receiver,"Out");return; }
            if(side!=Receiver) { Fault(-Receiver,"Wrong-side landing");return; }
            if(bounced) { Fault(Receiver,"Second bounce");return; }
            if(awaitingServe && (Mathf.Abs(point.z)<=CourtGeometryV1.NonVolleyZoneDepth+.0001f || point.x*targetX<-.0001f))
            { Fault(server,"Serve outside diagonal service area");return; }
            if(!awaitingServe)Returns++;
            awaitingServe=false;bounced=true;
            if(requiredBounces>0)requiredBounces--;
            Result=CanVolley?"Live: bounce or legal volley":"Return must bounce on server side";
        }
        public void Hit(int side, bool feetInKitchen)
        {
            if(Finished)return;
            if(side!=Receiver) { Fault(side,"Double hit or wrong paddle");return; }
            if(!bounced && !CanVolley) { Fault(side,"Volley before two-bounce sequence");return; }
            bool volley=!bounced;
            if(volley&&feetInKitchen) { Fault(side,"Kitchen volley");return; }
            if(volley) { volleyMomentum[Index(side)]=true;stillSeconds[Index(side)]=0; }
            Receiver=-side;bounced=false;Result="Ball in flight";
        }
        public void ObservePlayer(int side, bool feetInKitchen, bool stationary, float dt)
        {
            int i=Index(side);if(!volleyMomentum[i])return;
            if(feetInKitchen)
            {
                // A momentum fault can follow the ball becoming dead.
                Winner=-side;Finished=true;Result="Kitchen entry after volley (ground-marker proxy)";return;
            }
            stillSeconds[i]=stationary?stillSeconds[i]+dt:0;
            if(stillSeconds[i]>=.2f)volleyMomentum[i]=false;
        }
        public void Lost() { if(!Finished)Fault(bounced?Receiver:-Receiver,"Miss or out"); }
        public void Fault(int side,string reason) { if(Finished)return;Winner=-side;Finished=true;Result=reason; }
        private static int Index(int side)=>side<0?0:1;
    }
}

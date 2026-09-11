using NUnit.Framework;
using UnityEngine;
using Picklebot.Doubles;

namespace Picklebot.PlayerControls.Tests
{
 public sealed class PlayerMomentumRecoveryV3Tests
 {
  private static PlayerControlState State(int side,Vector3 velocity,bool grounded=true,float landing=0)=>
   new PlayerControlState(new Vector3(0,grounded?0:.2f,side*3),velocity,90,0,1,landing,grounded);
  private static PlayerSupportState Support(int side,PlayerControlState state,bool leftSupported=true,bool rightSupported=true,bool kitchen=false)
  {
   float z=side*(kitchen?1:3);
   return new PlayerSupportState(new PlayerFootPose(new Vector3(-.16f,.055f,z),0,leftSupported),new PlayerFootPose(new Vector3(.16f,.055f,z),0,rightSupported),state,side,DoublesRules.HalfWidth,DoublesRules.Kitchen);
  }
  private static DoublesRules Ready(int player)
  {
   var r=new DoublesRules();r.FixedBallServe(0,true,0);
   int receiver=r.DesignatedReceiver;r.Bounce(new Vector3(r.ServiceX(receiver),0,4),.1f);r.Hit(receiver,.2f);
   r.Bounce(new Vector3(0,0,-4),.3f);r.Hit(0,.4f);
   if(player<2)r.Hit(receiver,.5f);
   for(int i=0;i<4;i++)r.Feet(i,false,true,true,.6f);
   return r;
  }
  [TestCase(-1)] [TestCase(1)]
  public void GroundedSidewaysAndAwayMovementCanRecoverWithoutFullStandstill(int side)
  {
   foreach(var velocity in new[]{new Vector3(1.5f,0,0),new Vector3(.5f,0,side*2),Vector3.zero})
    Assert.IsTrue(Support(side,State(side,velocity)).balanceRecovered);
  }
  [TestCase(-1)] [TestCase(1)]
  public void RemainingMotionTowardKitchenKeepsMomentumPending(int side)
  {
   Assert.IsFalse(Support(side,State(side,new Vector3(1.5f,0,-side*.1f))).balanceRecovered);
   Assert.IsFalse(Support(side,State(side,new Vector3(0,0,-side*.03f))).balanceRecovered);
   Assert.IsTrue(Support(side,State(side,new Vector3(0,0,-side*.019f))).balanceRecovered);
  }
  [TestCase(-1)] [TestCase(1)]
  public void AirborneLandingLockoutUnsupportedFootAndKitchenContactCannotClearMomentum(int side)
  {
   var away=new Vector3(0,0,side*2);
   Assert.IsFalse(Support(side,State(side,away,false)).balanceRecovered);
   Assert.IsFalse(Support(side,State(side,away,true,.1f)).balanceRecovered);
   Assert.IsFalse(Support(side,State(side,away),false,true).balanceRecovered);
   Assert.IsFalse(Support(side,State(side,away),true,false).balanceRecovered);
   Assert.IsFalse(Support(side,State(side,away),true,true,true).balanceRecovered);
  }
  [TestCase(-1)] [TestCase(1)]
  public void InwardVolleyMomentumStillFaultsEvenAfterOpponentLosesPoint(int side)
  {
   int player=side<0?0:2;var r=Ready(player);r.Feet(player,false,true,true,1);r.Hit(player,2);
   var s=Support(side,State(side,new Vector3(1,0,-side*.3f)));
   r.Feet(player,s.touchesKitchen,s.bothFeetOutside,s.balanceRecovered,3);
   Assert.IsTrue(r.VolleyMomentumPending(player));
   r.Fail(1-player/2,Fault.SecondBounce,4);Assert.IsFalse(r.ResolveRally());
   s=Support(side,State(side,Vector3.zero),true,true,true);
   r.Feet(player,s.touchesKitchen,s.bothFeetOutside,s.balanceRecovered,5);
   Assert.AreEqual(Fault.KitchenMomentum,r.LastFault);Assert.AreEqual(1-player/2,r.Winner);
  }
  [TestCase(-1)] [TestCase(1)]
  public void GroundedReversalSettlesPriorVolleyAndLaterIndependentEntryIsAllowed(int side)
  {
   int player=side<0?0:2;var r=Ready(player);r.Feet(player,false,true,true,1);r.Hit(player,2);
   var s=Support(side,State(side,new Vector3(1,0,side*.3f)));
   r.Feet(player,s.touchesKitchen,s.bothFeetOutside,s.balanceRecovered,3);
   Assert.IsFalse(r.VolleyMomentumPending(player));
   s=Support(side,State(side,Vector3.zero),true,true,true);
   r.Feet(player,s.touchesKitchen,s.bothFeetOutside,s.balanceRecovered,4);
   Assert.IsFalse(r.Dead);Assert.AreEqual(Fault.None,r.LastFault);
  }
 }
}

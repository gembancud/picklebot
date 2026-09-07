using NUnit.Framework;
using UnityEngine;
namespace Picklebot.Doubles.Tests
{
    public sealed class DoublesRulesTests
    {
        static void Serve(DoublesRules r)=>r.Serve(r.Server,true,true,true,true,false,false,false,0);
        static void GroundReturn(DoublesRules r)
        {
            Serve(r);int receiver=r.DesignatedReceiver;
            r.Bounce(new Vector3(r.ServiceX(receiver),0,DoublesRules.Side(1-r.ServingTeam)*4),1);
            r.Hit(receiver,2);r.Bounce(new Vector3(0,0,DoublesRules.Side(r.ServingTeam)*4),3);r.Hit(r.Server,4);
        }
        static void End(DoublesRules r,int winner)
        {r.Fail(1-winner,Fault.Out,1);Assert.That(r.ResolveRally());if(r.GameWinner<0)r.BeginRally();}
        [Test] public void OpeningScoreIsZeroZeroTwo() {var r=new DoublesRules();Assert.That(r.ScoreCall,Is.EqualTo("0-0-2"));Assert.That(r.DesignatedReceiver,Is.EqualTo(2));}
        [Test] public void FirstLossIsSideOut() {var r=new DoublesRules();End(r,1);Assert.That(r.Server,Is.EqualTo(2));Assert.That(r.ServerNumber,Is.EqualTo(1));Assert.That(r.Score,Is.EqualTo(new[]{0,0}));}
        [Test] public void TeamGetsTwoServersAfterSideOut() {var r=new DoublesRules();End(r,1);End(r,0);Assert.That(r.Server,Is.EqualTo(3));Assert.That(r.ServerNumber,Is.EqualTo(2));End(r,0);Assert.That(r.ServingTeam,Is.EqualTo(0));}
        [Test] public void ServerKeepsBallAndSwitchesCourtOnWin() {var r=new DoublesRules();End(r,0);Assert.That(r.Server,Is.EqualTo(0));Assert.That(r.IsRight(0),Is.False);Assert.That(r.DesignatedReceiver,Is.EqualTo(3));Assert.That(r.ScoreCall,Is.EqualTo("1-0-2"));}
        [Test] public void ReceivingTeamDoesNotChangeLogicalCourt() {var r=new DoublesRules();End(r,0);Assert.That(r.RightPlayer(1),Is.EqualTo(2));}
        [Test] public void ReturnToServeStartsWithRightPlayer() {var r=new DoublesRules();End(r,0);End(r,1);End(r,0);End(r,0);Assert.That(r.Server,Is.EqualTo(1));}
        [Test] public void GameRequiresElevenAndTwoPointLead() {var r=new DoublesRules();for(int i=0;i<10;i++)End(r,0);Assert.That(r.GameWinner,Is.EqualTo(-1));End(r,0);Assert.That(r.GameWinner,Is.EqualTo(0));}
        [Test] public void DuplicateResolutionDoesNotScoreTwice() {var r=new DoublesRules();r.Fail(1,Fault.Out,0);Assert.That(r.ResolveRally());Assert.That(r.ResolveRally(),Is.False);Assert.That(r.Score[0],Is.EqualTo(1));}
        [Test] public void DropServeDoesNotRequireVolleyArc() {var r=new DoublesRules();Serve(r);Assert.That(r.Phase,Is.EqualTo(RallyPhase.ServeFlight));}
        [Test] public void VolleyServeMustBeBelowWaist() {var r=new DoublesRules();r.Serve(0,true,false,true,false,true,false,true,0);Assert.That(r.LastFault,Is.EqualTo(Fault.ServeMotion));}
        [Test] public void ServeFootFault() {var r=new DoublesRules();r.Serve(0,false,true,true,true,false,false,false,0);Assert.That(r.LastFault,Is.EqualTo(Fault.ServeFoot));}
        [Test] public void ServeCannotLandOnKitchenLine() {var r=new DoublesRules();Serve(r);r.Bounce(new Vector3(-1,0,DoublesRules.Kitchen),1);Assert.That(r.LastFault,Is.EqualTo(Fault.ServeLanding));}
        [Test] public void ServeMustBeDiagonal() {var r=new DoublesRules();Serve(r);r.Bounce(new Vector3(1,0,4),1);Assert.That(r.LastFault,Is.EqualTo(Fault.ServeLanding));}
        [Test] public void ServeMayTouchCentreLine() {var r=new DoublesRules();Serve(r);r.Bounce(new Vector3(0,0,4),1);Assert.That(r.Dead,Is.False);}
        [Test] public void WrongPartnerCannotReturnServe() {var r=new DoublesRules();Serve(r);r.Bounce(new Vector3(-1,0,4),1);r.Hit(3,2);Assert.That(r.LastFault,Is.EqualTo(Fault.WrongReceiver));}
        [Test] public void ServeCannotBeVolleyed() {var r=new DoublesRules();Serve(r);r.Hit(2,1);Assert.That(r.LastFault,Is.EqualTo(Fault.EarlyVolley));}
        [Test] public void ServingTeamMustLetReturnBounce() {var r=new DoublesRules();Serve(r);r.Bounce(new Vector3(-1,0,4),1);r.Hit(2,2);r.Hit(1,3);Assert.That(r.LastFault,Is.EqualTo(Fault.EarlyVolley));}
        [Test] public void EitherPartnerMayHitAfterServeReturn() {var r=new DoublesRules();GroundReturn(r);r.Hit(3,5);Assert.That(r.Dead,Is.False);Assert.That(r.Hits,Is.EqualTo(4));}
        [Test] public void TeammateCannotMakeSecondHit() {var r=new DoublesRules();GroundReturn(r);r.Hit(1,5);Assert.That(r.LastFault,Is.EqualTo(Fault.DoubleHit));}
        [Test] public void KitchenVolleyIsFault() {var r=new DoublesRules();GroundReturn(r);r.Feet(3,true,false,false,5);r.Hit(3,6);Assert.That(r.LastFault,Is.EqualTo(Fault.KitchenVolley));}
        [Test] public void KitchenGroundstrokeIsLegal() {var r=new DoublesRules();GroundReturn(r);r.Bounce(new Vector3(1,0,1),5);r.Feet(3,true,false,false,5);r.Hit(3,6);Assert.That(r.Dead,Is.False);}
        [Test] public void BothFeetMustReestablishBeforeVolley() {var r=new DoublesRules();GroundReturn(r);r.Feet(3,true,false,false,5);r.Feet(3,false,false,false,6);r.Hit(3,7);Assert.That(r.LastFault,Is.EqualTo(Fault.KitchenVolley));}
        [Test] public void LateMomentumOverridesUnresolvedRally() {var r=new DoublesRules();GroundReturn(r);r.Hit(3,5);r.Fail(0,Fault.SecondBounce,6);Assert.That(r.ResolveRally(),Is.False);r.Feet(3,true,false,false,8);Assert.That(r.LastFault,Is.EqualTo(Fault.KitchenMomentum));Assert.That(r.Winner,Is.EqualTo(0));r.Feet(3,false,true,true,9);Assert.That(r.ResolveRally());}
        [Test] public void SecondBounceLosesForReceiver() {var r=new DoublesRules();Serve(r);r.Bounce(new Vector3(-1,0,4),1);r.Bounce(new Vector3(-1,0,5),2);Assert.That(r.Winner,Is.EqualTo(0));Assert.That(r.LastFault,Is.EqualTo(Fault.SecondBounce));}
        [Test] public void OutAfterLegalBounceStillLosesForReceiver() {var r=new DoublesRules();Serve(r);r.Bounce(new Vector3(-1,0,4),1);r.Bounce(new Vector3(-1,0,8),2);Assert.That(r.Winner,Is.EqualTo(0));}
        [Test] public void NetTouchBallIsNotAutomaticallyFault() {var r=new DoublesRules();Serve(r);r.Bounce(new Vector3(-1,0,4),2);Assert.That(r.Dead,Is.False);}
        [Test] public void BodyContactLosesEvenForAnOutwardBall() {var r=new DoublesRules();GroundReturn(r);r.BodyContact(3,5);Assert.That(r.Winner,Is.EqualTo(0));}
        [Test] public void BoundaryLinesAreIn() {var r=new DoublesRules();GroundReturn(r);r.Bounce(new Vector3(DoublesRules.HalfWidth,0,DoublesRules.HalfLength),5);Assert.That(r.Dead,Is.False);}
        [Test] public void SingleDirectionContinuousStrokeMayContactTwice() {var r=new DoublesRules();GroundReturn(r);r.Hit(0,4.01f,default,true);Assert.That(r.Dead,Is.False);Assert.That(r.Hits,Is.EqualTo(3));}
        [Test] public void ContinuousFlagCannotExcuseTeammateHit() {var r=new DoublesRules();GroundReturn(r);r.Hit(1,4.01f,default,true);Assert.That(r.LastFault,Is.EqualTo(Fault.DoubleHit));}
        [Test] public void DeuceRequiresTwoPointLead() {var r=new DoublesRules();r.Score[0]=r.Score[1]=10;End(r,0);Assert.That(r.GameWinner,Is.EqualTo(-1));End(r,0);Assert.That(r.GameWinner,Is.EqualTo(0));Assert.That(r.Score[0],Is.EqualTo(12));}
        [Test] public void PostBeforeBounceLosesForHitter() {var r=new DoublesRules();Serve(r);r.PermanentObject(1);Assert.That(r.Winner,Is.EqualTo(1));}
        [Test] public void PostAfterLegalBounceLosesForReceiver() {var r=new DoublesRules();Serve(r);r.Bounce(new Vector3(-1,0,4),1);r.PermanentObject(2);Assert.That(r.Winner,Is.EqualTo(0));}
    }
}

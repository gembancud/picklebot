using System;
using System.Collections;
using System.Linq;
using NUnit.Framework;
using Picklebot.Doubles;
using Picklebot.PlayerControls;
using UnityEngine;
using UnityEngine.TestTools;
namespace Picklebot.PlayerControlsIntegration.Tests
{
    public sealed class PlayerAimedReturnV3Tests
    {
        [UnityTest] public IEnumerator ContinuousAimedSwingReturnsIncomingBallAcrossNet()
        {
            using(var match=new PlayerControlMatch(false))
            {
                var body=match.World.Players[0];var root=match.Controls.StateFor(0);var legs=match.Controls.PoseFor(0);
                var offset=new Vector3(0,0,3.5f);var pelvis=legs.Pelvis+offset;
                body.Reset(root.position+offset);var motor=new PlayerUpperBodyBoundedV3(pelvis,Quaternion.identity);
                var reference=PlayerTorsoKinematicsV3.Evaluate(pelvis,Quaternion.identity,new Vector3(5,10,0))
                    .Arm(new PlayerArmJointsV3(new[]{-10f,20f,20f,50f,-5f,10f,0f}),PlayerGripV3.ContinentalPrototype);
                var contactPoint=reference.PaddlePoint(PlayerStrokeAimV3.FacePoint);
                var normal=new Vector3(0,.5f,1).normalized;
                var preparation=contactPoint-normal*.16f;
                string contactInfo="";bool face=false,crossed=false,landed=false;float flightStart=0;var previousBall=Vector3.zero;
                for(int tick=0;tick<780;tick++)
                {
                    float phase=(tick-300)*PlayerJointMotorV3.Dt;
                    float t=Mathf.Max(0,phase);
                    float travel=t<.12f?(.5f*4/.12f*t*t):(.24f+4*(t-.12f));
                    var target=preparation+normal*Mathf.Min(travel,.44f);
                    var aim=PlayerStrokeAimV3.Solve(pelvis,Quaternion.identity,motor.TorsoAngles,motor.ArmAngles,target,normal);
                    Assert.IsTrue(aim.Reached,"Aim tick="+tick+" p="+aim.positionError+" n="+aim.normalErrorDegrees);
                    var feed=tick>=300&&travel<.44f?normal*(t<.12f?4*t/.12f:4):Vector3.zero;
                    Assert.IsTrue(motor.TryTrack(target,normal,feed),"Bounded tracking step rejected at "+tick);
                    var frame=PlayerArticulatedFrameV3.ComposeBounded(new PlayerBodyFrame{position=root.position+offset,pelvis=pelvis,
                        leftFoot=legs.Left.center+offset,rightFoot=legs.Right.center+offset,leftHip=legs.LeftHip+offset,rightHip=legs.RightHip+offset,
                        leftKnee=legs.LeftKnee+offset,rightKnee=legs.RightKnee+offset},motor);
                    body.ApplyExternalFrame(frame,tick==0);
                    if(tick==300)
                    {
                        var start=contactPoint+Vector3.forward*.8f+Vector3.up*(.5f*9.81f*.16f*.16f);
                        match.World.Ball.position=start;match.World.Ball.transform.position=start;
                        match.World.Ball.linearVelocity=Vector3.back*5;match.World.Ball.angularVelocity=Vector3.zero;
                        match.World.Contacts.Clear();flightStart=match.World.Time;previousBall=start;
                    }
                    match.World.Simulate();
                    if(tick<300)continue;
                    Assert.IsFalse(match.World.Contacts.Any(c=>c.surface.Contains("arm")||c.surface=="NonContactHandle"||c.surface.Contains("Torso")),"Body/handle collision: "+string.Join(",",match.World.Contacts.Select(c=>c.surface)));
                    if(!face)
                    {
                        var hit=match.World.Contacts.FirstOrDefault(c=>c.player==0&&c.surface=="RoundedHittingFace");
                        if(hit!=null)contactInfo=" actualVelocity="+motor.ActualVelocity+" actualNormal="+(body.Paddle.rotation*Vector3.forward)+" localContact="+(Quaternion.Inverse(body.Paddle.rotation)*(hit.point-body.Paddle.position))+" jointRates="+string.Join(",",motor.ArmRates)+" torsoRates="+motor.TorsoRates;
                    }
                    face|=match.World.Contacts.Any(c=>c.player==0&&c.surface=="RoundedHittingFace");
                    var ball=match.World.Ball.position;
                    if(face&&previousBall.z<0&&ball.z>=0)crossed=true;
                    var floor=match.World.Contacts.FirstOrDefault(c=>c.time>=flightStart&&(c.surface=="CourtSurface"||c.surface=="OutCatchFloor"));
                    if(floor!=null)
                    {
                        Assert.IsTrue(face,"No face contact; floor="+floor.point+" target="+contactPoint);
                        Assert.IsTrue(crossed,"No net crossing; "+contactInfo+" floor="+floor.point+" motorSpeed="+motor.ActualVelocity+" face="+UnityEngine.JsonUtility.ToJson(match.World.Contacts.FirstOrDefault(c=>c.player==0&&c.surface=="RoundedHittingFace")));
                        Assert.Greater(floor.point.z,0);Assert.Less(floor.point.z,DoublesRules.HalfLength);
                        Assert.Less(Mathf.Abs(floor.point.x),DoublesRules.HalfWidth,"Landing="+floor.point);landed=true;break;
                    }
                    previousBall=ball;
                    if(tick%240==0)yield return null;
                }
                Assert.IsTrue(landed,"Require a physical opposite-court landing; contacts="+string.Join(",",match.World.Contacts.Select(c=>c.surface)));
            }
            yield return null;
        }
    }
}

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
    public sealed class PlayerArticulatedFrameV3Tests
    {
        [UnityTest] public IEnumerator MovingArticulatedPaddleSeparatesBallForAdvancingAndRetreatingSwings()
        {
            foreach(int direction in new[]{-1,1})
            using(var match=new PlayerControlMatch(false))
            {
                var body=match.World.Players[0];var root=match.Controls.StateFor(0);var legs=match.Controls.PoseFor(0);
                body.Reset(root.position);var motor=new PlayerUpperBodyMotorV3();
                var target=PlayerArmJointsV3.Ready.ToArray();target[0]=15*direction;target[3]=90-15*direction;
                var joints=new PlayerArmJointsV3(target);Vector3 launchNormal=Vector3.zero;
                bool contacted=false;float contactSpeed=0;Vector3 previous=Vector3.zero;
                for(int tick=0;tick<45;tick++)
                {
                    motor.Step(new Vector3(10*direction,0,0),joints);
                    var torso=motor.Pose(legs.Pelvis,Quaternion.Euler(0,root.facingYaw,0));
                    var arm=torso.Arm(motor.ArmAngles,PlayerGripV3.ContinentalPrototype);
                    var frame=PlayerArticulatedFrameV3.Compose(new PlayerBodyFrame{position=root.position,pelvis=legs.Pelvis,
                        leftFoot=legs.Left.center,rightFoot=legs.Right.center,leftHip=legs.LeftHip,rightHip=legs.RightHip,
                        leftKnee=legs.LeftKnee,rightKnee=legs.RightKnee},torso,arm,motor.TorsoRates,motor.ArmRates,Vector3.zero,Vector3.zero);
                    body.ApplyExternalFrame(frame,tick==0);
                    if(tick==12)
                    {
                        launchNormal=body.Paddle.rotation*Vector3.forward;
                        var face=body.Paddle.transform.Find("RoundedHittingFace");
                        var start=face.position+launchNormal*.10f;
                        match.World.Ball.position=start;match.World.Ball.transform.position=start;
                        match.World.Ball.linearVelocity=-launchNormal*4;match.World.Ball.angularVelocity=Vector3.zero;
                        match.World.Contacts.Clear();previous=body.Paddle.position;
                    }
                    match.World.Simulate();
                    if(tick>=12 && match.World.Contacts.Any(c=>c.player==0&&c.surface=="RoundedHittingFace"))
                    {
                        var contact=match.World.Contacts.First(c=>c.player==0&&c.surface=="RoundedHittingFace");
                        contactSpeed=body.ContactVelocity(contact.point).magnitude;
                        Assert.Greater(Vector3.Distance(body.Paddle.position,previous),.0001f,"Paddle must have physically moved after ball release.");
                        Assert.Less(Vector3.Dot(contact.incoming,launchNormal),0);
                        var surfaceVelocity=body.ContactVelocity(contact.point);
                        Assert.Less(Vector3.Dot(contact.incoming-surfaceVelocity,contact.normal),0,"Incoming ball must approach the moving surface.");
                        Assert.Greater(Vector3.Dot(match.World.Ball.linearVelocity-surfaceVelocity,contact.normal),0,"Outgoing ball must separate from the moving surface.");
                        if(direction==-1)
                        {
                            Assert.Greater(Vector3.Dot(surfaceVelocity,launchNormal),0,"This case must advance into the incoming ball.");
                            Assert.Greater(Vector3.Dot(match.World.Ball.linearVelocity,launchNormal),0,"Advancing stroke must return the ball outward.");
                        }
                        else Assert.Less(Vector3.Dot(surfaceVelocity,launchNormal),0,"This case must retreat from the incoming ball.");
                        contacted=true;break;
                    }
                }
                Assert.IsTrue(contacted,"Require a real PhysX face callback, not a synthetic contact event.");
                Assert.Greater(contactSpeed,.1f,"Contact must occur while the joint-driven paddle is moving.");
                TestContext.WriteLine("Articulated contact-point speed: "+contactSpeed+" m/s. This fixture does not establish legal serve or rally quality.");
            }
            yield return null;
        }
        [UnityTest] public IEnumerator BoundedPaddleSeparatesVaryingSpeedBallsWhilePelvisMoves()
        {
            foreach(float incomingSpeed in new[]{2f,4f,6f})
            foreach(int direction in new[]{-1,1})
            using(var match=new PlayerControlMatch(false))
            {
                var body=match.World.Players[0];var root=match.Controls.StateFor(0);var legs=match.Controls.PoseFor(0);
                body.Reset(root.position);var motor=new PlayerUpperBodyBoundedV3(legs.Pelvis,Quaternion.Euler(0,root.facingYaw,0));
                var target=PlayerArmJointsV3.Ready.ToArray();target[0]=15*direction;target[3]=90-15*direction;
                var joints=new PlayerArmJointsV3(target);Vector3 launchNormal=Vector3.zero;
                int firstContactTick=-1;bool contacted=false;float contactSpeed=0;Vector3 previous=Vector3.zero;
                for(int tick=0;tick<45;tick++)
                {
                    float time=tick*PlayerJointMotorV3.Dt;
                    var offset=Vector3.right*(.1f*time*time);
                    Assert.IsTrue(motor.TryStep(new Vector3(10*direction,0,0),joints,legs.Pelvis+offset,Quaternion.Euler(0,root.facingYaw,0)),"Physical fixture must not skip rejected steps.");
                    var frame=PlayerArticulatedFrameV3.ComposeBounded(new PlayerBodyFrame{position=root.position+offset,pelvis=legs.Pelvis+offset,
                        leftFoot=legs.Left.center+offset,rightFoot=legs.Right.center+offset,leftHip=legs.LeftHip+offset,rightHip=legs.RightHip+offset,
                        leftKnee=legs.LeftKnee+offset,rightKnee=legs.RightKnee+offset},motor);
                    Assert.LessOrEqual(frame.paddleVelocity.magnitude,12);
                    Assert.LessOrEqual(frame.paddleAngularVelocity.magnitude,12);
                    body.ApplyExternalFrame(frame,tick==0);
                    if(tick==12)
                    {
                        launchNormal=body.Paddle.rotation*Vector3.forward;
                        var face=body.Paddle.transform.Find("RoundedHittingFace");
                        var start=face.position+launchNormal*.10f;
                        match.World.Ball.position=start;match.World.Ball.transform.position=start;
                        match.World.Ball.linearVelocity=-launchNormal*incomingSpeed;match.World.Ball.angularVelocity=Vector3.zero;
                        match.World.Contacts.Clear();previous=body.Paddle.position;
                    }
                    match.World.Simulate();
                    if(tick>0)
                    {
                        Assert.Less(Vector3.Distance(body.Paddle.linearVelocity,motor.ActualVelocity),.001f);
                        Assert.Less(Vector3.Distance(body.Paddle.angularVelocity,motor.ActualAngularVelocity),.002f);
                    }
                    if(tick>=12 && match.World.Contacts.Any(c=>c.player==0&&c.surface=="RoundedHittingFace"))
                    {
                        var contact=match.World.Contacts.First(c=>c.player==0&&c.surface=="RoundedHittingFace");
                        contactSpeed=body.ContactVelocity(contact.point).magnitude;
                        var expectedSurface=motor.ActualVelocity+Vector3.Cross(motor.ActualAngularVelocity,contact.point-frame.paddlePosition);
                        Assert.Less(Vector3.Distance(body.ContactVelocity(contact.point),expectedSurface),.001f,"Collision velocity must use the accepted finite-step motion.");
                        Assert.Greater(Vector3.Distance(body.Paddle.position,previous),.0001f,"Paddle must have physically moved after ball release.");
                        Assert.Less(Vector3.Dot(contact.incoming,launchNormal),0);
                        var surfaceVelocity=body.ContactVelocity(contact.point);
                        Assert.Less(Vector3.Dot(contact.incoming-surfaceVelocity,contact.normal),0,"Incoming ball must approach the moving surface.");
                        if(firstContactTick<0)firstContactTick=tick;
                        Assert.IsFalse(match.World.Contacts.Any(c=>c.player!=0||c.surface!="RoundedHittingFace"),"Another collision must not supply the rebound.");
                        // A face callback can precede the resolved impulse. Measure a bounded
                        // episode, not callback arrival alone (trace: slow retreat resolves +2 ticks).
                        Assert.LessOrEqual(tick-firstContactTick,4,"Ball must separate within four physics steps of face entry.");
                        if(Vector3.Dot(match.World.Ball.linearVelocity-surfaceVelocity,contact.normal)<=0)continue;
                        Assert.Greater(Vector3.Dot(match.World.Ball.linearVelocity-surfaceVelocity,contact.normal),0,"Outgoing ball must separate from the moving surface. speed="+incomingSpeed+" direction="+direction+" tick="+tick+" incoming="+contact.incoming+" outgoing="+match.World.Ball.linearVelocity+" surface="+surfaceVelocity+" normal="+contact.normal+" contacts="+string.Join(",",match.World.Contacts.Select(c=>c.surface)));
                        if(direction==-1)
                        {
                            Assert.Greater(Vector3.Dot(surfaceVelocity,launchNormal),0,"This case must advance into the incoming ball.");
                            Assert.Greater(Vector3.Dot(match.World.Ball.linearVelocity,launchNormal),0,"Advancing stroke must return the ball outward.");
                        }
                        else Assert.Less(Vector3.Dot(surfaceVelocity,launchNormal),0,"This case must retreat from the incoming ball.");
                        contacted=true;break;
                    }
                }
                Assert.IsTrue(contacted,"Require a real face contact followed by separation within the episode deadline.");
                Assert.Greater(contactSpeed,.1f,"Contact must occur while the joint-driven paddle is moving.");
                TestContext.WriteLine("Bounded incoming speed: "+incomingSpeed+"; contact-point speed: "+contactSpeed+" m/s. This fixture does not establish legal serve or rally quality.");
            }
            yield return null;
        }
        [UnityTest] public IEnumerator PhysicalArmSegmentsFollowJointElbowAndResetRestoresUprightTorso()
        {
            using(var match=new PlayerControlMatch(false))
            {
                var body=match.World.Players[0];var root=match.Controls.StateFor(0);var legs=match.Controls.PoseFor(0);
                body.Reset(root.position);var motor=new PlayerUpperBodyMotorV3();
                for(int i=0;i<300;i++)
                {
                    motor.Step(new Vector3(40,20,-10),PlayerArmJointsV3.Ready);
                    var torso=motor.Pose(legs.Pelvis,Quaternion.Euler(0,root.facingYaw,0));
                    var arm=torso.Arm(motor.ArmAngles,PlayerGripV3.ContinentalPrototype);
                    var frame=PlayerArticulatedFrameV3.Compose(new PlayerBodyFrame{position=root.position,pelvis=legs.Pelvis,
                        leftFoot=legs.Left.center,rightFoot=legs.Right.center,leftHip=legs.LeftHip,rightHip=legs.RightHip,
                        leftKnee=legs.LeftKnee,rightKnee=legs.RightKnee},torso,arm,motor.TorsoRates,motor.ArmRates,Vector3.zero,Vector3.zero);
                    body.ApplyExternalFrame(frame,i==0);match.World.Simulate();
                    var upper=body.Root.transform.Find("Right upper arm");var forearm=body.Root.transform.Find("Right forearm");
                    Assert.Less(Vector3.Distance(upper.position,(arm.shoulder+arm.elbow)*.5f),1e-5f);
                    Assert.Less(Vector3.Distance(forearm.position,(arm.elbow+arm.wrist)*.5f),1e-5f);
                    Assert.Less(Vector3.Distance(body.Hand,arm.hand),.0001f);
                    Assert.IsNotNull(forearm.GetComponent<Collider>());
                    var point=arm.PaddlePoint(new Vector3(0,.0635f,0));
                    var expected=torso.PaddlePointVelocity(arm,point,motor.ArmRates,motor.TorsoRates,Vector3.zero,Vector3.zero);
                    Assert.Less(Vector3.Distance(body.ContactVelocity(point),expected),.0001f);
                    var invalid=frame;invalid.rightElbow+=Vector3.up;
                    Assert.Throws<ArgumentException>(()=>body.ApplyExternalFrame(invalid));
                    Assert.Less(Vector3.Distance(forearm.position,(arm.elbow+arm.wrist)*.5f),1e-5f);
                }
                Assert.Greater(Quaternion.Angle(body.Torso.transform.rotation,Quaternion.identity),10);
                body.Reset(root.position);Assert.Less(Quaternion.Angle(body.Torso.transform.rotation,Quaternion.identity),.001f);
            }
            yield return null;
        }
    }
}

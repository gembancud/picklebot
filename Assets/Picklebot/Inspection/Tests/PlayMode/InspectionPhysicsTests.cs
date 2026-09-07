using System.Linq;
using NUnit.Framework;
using Picklebot.Core;
using UnityEngine;
namespace Picklebot.Inspection.Tests
{
    public sealed class InspectionPhysicsTests
    {
        [Test] public void BothPaddlesReceiveIndependentInputsInTheSameStep()
        {
            using var w=new InspectionWorld(false);
            var a=w.Motors[0].Body.position;var b=w.Motors[1].Body.position;
            for(int i=0;i<60;i++)w.StepBoth(new PaddleInput(Vector3.right,Vector3.up,Vector2.zero),new PaddleInput(Vector3.left,Vector3.down,Vector2.zero));
            Assert.That(w.Motors[0].Body.position.x-a.x,Is.GreaterThan(.1f));
            Assert.That(w.Motors[1].Body.position.x-b.x,Is.LessThan(-.1f));
            Assert.That(w.Elapsed,Is.EqualTo(.25f).Within(.001f));
        }
        [Test] public void VisibleSceneHasPaddlesMarkersAndCourtLines()
        {
            using var w=new InspectionWorld(true);
            foreach(var motor in w.Motors)
                Assert.That(motor.Body.transform.Find("RoundedHittingFace").GetComponent<MeshRenderer>().enabled,Is.True);
            Assert.That(w.Root.transform.Find("Orange player footprint"),Is.Not.Null);
            Assert.That(w.Root.transform.Find("Blue player footprint"),Is.Not.Null);
            Assert.That(w.Root.GetComponentsInChildren<Transform>().Count(t=>t.name=="Non-contact court marking"),Is.EqualTo(10));
            Assert.That(w.Ball.GetComponent<TrailRenderer>(),Is.Not.Null);
            Assert.That(Vector3.Distance(w.Ball.transform.position,w.Ball.position),Is.LessThan(.0001f));
            foreach(var motor in w.Motors)
                Assert.That(Vector3.Distance(motor.Body.transform.position,motor.Body.position),Is.LessThan(.0001f));
        }
        [Test] public void GraniteDropUsesOnlyTheReferenceSurface()
        {
            using var w=new InspectionWorld(false);w.Reset(InspectionPreset.GraniteDrop);
            Assert.That(w.Root.transform.Find("CourtSurface").GetComponent<Collider>().enabled,Is.False);
            for(int i=0;i<480;i++)w.Step();
            Assert.That(w.Contacts.First().surface,Is.EqualTo("Granite reference slab"));
            Assert.That(w.ReboundComplete,Is.True);
            Assert.That(w.FirstReboundHeight,Is.InRange(.65f,.85f));
            w.Reset(InspectionPreset.CourtDrop);
            Assert.That(w.Root.transform.Find("CourtSurface").GetComponent<Collider>().enabled,Is.True);
        }
        [Test] public void ScriptedServeFirstBounceIsLegalAndTraceIsRecorded()
        {
            using var w=new InspectionWorld(false);w.Reset(InspectionPreset.Serve);
            for(int i=0;i<320&&w.Contacts.Count==0;i++)w.Step();
            var c=w.Contacts.First();Assert.That(c.surface,Is.EqualTo("CourtSurface"));
            Assert.That(c.point.x,Is.LessThan(0));Assert.That(c.point.z,Is.GreaterThan(CourtGeometryV1.NonVolleyZoneDepth));
            Assert.That(w.Rules.Finished,Is.False);Assert.That(c.incomingVelocity.y,Is.LessThan(0));
            Assert.That(c.velocity.y,Is.GreaterThan(0));Assert.That(w.Frames.Count,Is.GreaterThan(240));
            Assert.That(w.Frames.Last().time,Is.EqualTo(w.Elapsed));
        }
        [Test] public void FullSizeGeometryAndBall()
        {
            using var w=new InspectionWorld(false);
            Assert.That(w.Root.transform.Find("CourtSurface").localScale.x,Is.EqualTo(6.096f).Within(.0001));
            Assert.That(w.Root.transform.Find("CourtSurface").localScale.z,Is.EqualTo(13.4112f).Within(.0001));
            Assert.That(w.Ball.mass,Is.EqualTo(.024f).Within(.00001));Assert.That(w.Ball.transform.localScale.x,Is.EqualTo(.074f).Within(.00001));
            Assert.That(CourtGeometryV1.NetHeightAtX(0),Is.EqualTo(.8636f).Within(.0001));
            Assert.That(CourtGeometryV1.NetHeightAtX(3.048f),Is.EqualTo(.9144f).Within(.0001));
        }
        [Test] public void DropContinuesThroughReboundAndLosesEnergy()
        {
            using var w=new InspectionWorld(false);for(int i=0;i<480;i++)w.Step();
            Assert.That(w.ReboundComplete,Is.True);Assert.That(w.FirstReboundHeight,Is.InRange(.30f,.46f));
            Assert.That(w.Contacts.Count(c=>c.surface=="CourtSurface"),Is.GreaterThanOrEqualTo(2));Assert.That(w.Elapsed,Is.GreaterThan(1.9f));
        }
        [TestCase(0)] [TestCase(1)] [TestCase(2)]
        public void EachTranslationAxisMoves(int axis)
        {
            using var w=new InspectionWorld(false);var old=w.Motors[0].Body.position;var input=Vector3.zero;input[axis]=.4f;
            for(int i=0;i<36;i++)w.Step(0,input);Assert.That(w.Motors[0].Body.position[axis]-old[axis],Is.GreaterThan(.05f));
        }
        [TestCase(0)] [TestCase(1)] [TestCase(2)]
        public void EachRotationAxisMoves(int axis)
        {
            using var w=new InspectionWorld(false);var old=w.Motors[0].Body.rotation;var input=Vector3.zero;input[axis]=.4f;
            for(int i=0;i<36;i++)w.Step(0,rotation:input);Assert.That(Quaternion.Angle(old,w.Motors[0].Body.rotation),Is.GreaterThan(5));
        }
        [Test] public void PlayerMovementAndPaddleReachAreBounded()
        {
            using var w=new InspectionWorld(false);
            for(int i=0;i<720;i++)w.Step(0,new Vector3(1,1,0),Vector3.one,new Vector2(1,0));
            var m=w.Motors[0];var d=m.Body.position-m.PlayerPosition;d.y=0;
            Assert.That(d.magnitude,Is.LessThanOrEqualTo(PaddleMotor.Reach+.03f));
            Assert.That(m.Body.position.y,Is.LessThanOrEqualTo(PaddleMotor.MaxHeight+.001f));
            Assert.That(m.PlayerPosition.x,Is.LessThanOrEqualTo(4.5f));
        }
        [Test] public void FlatAndBrushPresetsMakePhysicalPaddleContact()
        {
            using var w=new InspectionWorld(false);
            foreach(var p in new[]{InspectionPreset.FlatContact,InspectionPreset.BrushUp,InspectionPreset.BrushDown})
            {
                w.Reset(p);for(int i=0;i<240;i++)w.Step(demonstration:true);
                Assert.That(w.Contacts.Any(c=>c.surface=="PaddleNear"),Is.True,p.ToString());
            }
        }
        [Test] public void OppositeBrushesProduceOppositeSpin()
        {
            using var w=new InspectionWorld(false);float[] spin=new float[2];int j=0;
            foreach(var p in new[]{InspectionPreset.BrushUp,InspectionPreset.BrushDown})
            {
                w.Reset(p);for(int i=0;i<240;i++)w.Step(demonstration:true);
                spin[j++]=w.Contacts.First(c=>c.surface=="PaddleNear").spin.x;
            }
            Assert.That(spin[0]*spin[1],Is.LessThan(0));Assert.That(Mathf.Abs(spin[0]),Is.GreaterThan(1));
        }
        [Test] public void ResetReproducesPhysicalTrace()
        {
            using var w=new InspectionWorld(false);w.Reset(InspectionPreset.AngledBounce);for(int i=0;i<300;i++)w.Step();var p=w.Ball.position;int n=w.Contacts.Count;
            w.Reset(InspectionPreset.AngledBounce);for(int i=0;i<300;i++)w.Step();Assert.That(Vector3.Distance(p,w.Ball.position),Is.LessThan(.001));Assert.That(w.Contacts.Count,Is.EqualTo(n));
        }
    }
}

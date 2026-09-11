using System.Collections;
using NUnit.Framework;
using Picklebot.Doubles;
using UnityEngine;
using UnityEngine.TestTools;
namespace Picklebot.PlayerControlsIntegration.Tests
{
    public sealed class PlayerFaceEventOrderTests
    {
        [UnityTest] public IEnumerator SimultaneousHandleAndFaceCallbacksHaveTheSameFinalBallState()
        {
            using(var first=new DoublesWorld(false))using(var second=new DoublesWorld(false))using(var faceOnly=new DoublesWorld(false))
            {
                var worlds=new[]{first,second,faceOnly};
                for(int i=0;i<3;i++)
                {
                    var w=worlds[i];w.Ball.linearVelocity=new Vector3(2,1,3);w.Ball.angularVelocity=new Vector3(4,5,6);
                    var face=w.Players[0].Paddle.transform.Find("RoundedHittingFace").GetComponent<Collider>();
                    var handle=w.Players[0].Paddle.transform.Find("NonContactHandle").GetComponent<Collider>();
                    var point=w.Ball.position-Vector3.forward*.037f;
                    if(i==0)w.Contact(handle,point,Vector3.forward);
                    w.Contact(face,point,Vector3.forward);
                    if(i==1)w.Contact(handle,point,Vector3.forward);
                    w.Simulate();
                }
                Assert.Less(Vector3.Distance(first.Ball.linearVelocity,second.Ball.linearVelocity),1e-5f);
                Assert.Less(Vector3.Distance(first.Ball.angularVelocity,second.Ball.angularVelocity),1e-5f);
                Assert.Less(Vector3.Distance(first.Ball.linearVelocity,faceOnly.Ball.linearVelocity),1e-5f);
                Assert.Less(Vector3.Distance(first.Ball.angularVelocity,faceOnly.Ball.angularVelocity),1e-5f);
                Assert.AreEqual(first.Rules.Phase,second.Rules.Phase);
                Assert.AreEqual(first.Rules.LastFault,second.Rules.LastFault);
            }
            yield return null;
        }
    }
}

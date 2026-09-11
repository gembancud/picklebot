using System.Collections;
using NUnit.Framework;
using Picklebot.PlayerControls;
using UnityEngine;
using UnityEngine.TestTools;
namespace Picklebot.PlayerControlsIntegration.Tests
{
    public sealed class PlayerPlanarProjectionV3Tests
    {
        [UnityTest] public IEnumerator RecordedPlanarCouplingKeepsPhysicalBoundsAndIndependentRequests()
        {
            // Captured training failure seed1026482/tick188. Commands are a
            // regression fixture only: no policy, demonstration, or learning input.
            var commands=new float[][]{
                new float[]{-1f,-0.233308479f,0.427996099f,0.108287334f,0f,0f,0.632096291f,-0.0408062749f,-0.634641528f,0.73735857f,-1f,-0.236656457f,-0.0100797815f,-0.699017286f,-0.0828496069f,0.0569065213f,0f,0f},
                new float[]{-1f,-0.0537960343f,0.438554257f,0.148849726f,0f,0f,1f,0.103594884f,-0.590340257f,0.700360179f,-1f,0.111404225f,0.46030587f,-0.633076191f,-0.645114362f,0.608977616f,0f,0.439946085f},
                new float[]{-0.247641921f,0.0246562269f,0.440458715f,0.433606565f,0f,0.099956423f,1f,0.276828229f,-0.940004289f,1f,-1f,0.504609168f,0.172649622f,-0.233784556f,-0.253788799f,0.705180407f,0f,0.345495611f},
                new float[]{0.586224735f,0.655452728f,0.250430167f,0.576270342f,0f,0.399230778f,0.72036612f,0.200659618f,-0.487362206f,1f,-1f,-0.605618f,0.540014923f,0.621232748f,-0.351782411f,1f,0f,0.518670976f},
                new float[]{-0.191196591f,0.0182801932f,-0.728959501f,0.57265687f,0f,0.291560948f,-0.0652726069f,0.673688114f,-0.159452915f,0.479365796f,-1f,-0.564252734f,-0.0838400573f,0.251874387f,-0.36033234f,0.601262391f,0f,0.607526779f},
                new float[]{0.237005085f,0.0630018711f,0.147902459f,0.392976999f,0f,0.312859565f,-0.181335777f,0.714954793f,-0.519940853f,0.423982859f,-0.759516954f,-0.0245902352f,-0.0367950611f,-0.29717955f,-0.597793341f,0.149399132f,0f,0.572540402f},
                new float[]{-0.592990994f,0.049125772f,0.0138892932f,0.36253041f,0f,0.0417046845f,-0.0920172259f,0.422799945f,0.213792711f,-0.194843292f,-0.167858645f,-0.414187402f,-0.0478895865f,0.0532038733f,-0.0642150789f,1f,0f,0.37526232f},
                new float[]{-1f,-0.463799924f,0.170432448f,0.0790662766f,0f,0.049208045f,-0.224059626f,0.182610437f,0.512393355f,-0.13045381f,-0.412676662f,-0.39398396f,0.131174549f,-0.323527277f,-0.345864266f,0.948169231f,0f,0.731608331f},
                new float[]{-0.251338214f,-0.427878559f,0.0512647629f,0f,0f,0.00425618887f,0.261063427f,0.415992349f,0.00858288072f,0.864774108f,0.271631777f,-0.689588249f,-0.619461715f,-0.491981208f,-0.302395552f,0.773023009f,0f,0.752323389f},
                new float[]{-0.489236772f,0.0109110577f,0.154312059f,0.0557855666f,0f,0.0419179201f,-0.578809738f,0.343662798f,0.802143455f,0.903279543f,0.365726054f,-0.691260517f,-0.589984059f,-0.330158383f,-0.253211379f,0.651072443f,0f,0.8908602f},
                new float[]{-0.374192089f,-0.0278926194f,0.460805595f,0.178809166f,0f,0.192169428f,0.0584339127f,0.264756113f,0.378323317f,1f,-0.0371326618f,-0.629830122f,-0.563642025f,0.177525282f,0.38390252f,0.819085002f,0f,0.765674233f},
                new float[]{-0.530488253f,0.165026918f,-0.267558813f,0f,0f,0.0822512209f,-0.190027878f,0.202325016f,0.8998878f,0.401487678f,0.626755595f,-0.36719209f,-0.649233818f,0.268121809f,-0.182139963f,0.582602501f,0f,0.693178058f},
                new float[]{-0.436915755f,-0.037769828f,-0.230843514f,0f,0f,0.299489498f,-0.728232741f,0.383825541f,0.547351003f,0.188137949f,0.57577455f,-0.599584818f,-0.84886688f,0.219827101f,-0.42236957f,0.419017255f,0f,0.659961104f},
                new float[]{-0.469705582f,0.816530883f,-1f,0f,0f,0.00801455975f,-1f,0.462003291f,0.695561588f,0.510496616f,0.532381773f,-0.770084739f,-1f,0.632350743f,0.258194536f,0.670527637f,0f,0.638761878f},
                new float[]{0.0599429421f,0.163705304f,-0.530131459f,0f,0f,0.195512831f,-0.777675629f,0.663522959f,1f,0.332866043f,0.876655757f,-1f,-1f,0.373789787f,0.40332365f,0.36944744f,0f,0.5492872f},
                new float[]{-0.450294077f,0.0736538321f,-0.41823861f,0f,0f,0.053527236f,-0.811403036f,0.0728338212f,1f,0.711166084f,1f,-0.84697789f,-0.90483129f,-0.28353259f,0.76976192f,0.201002523f,0f,0.430960745f}
            };
            using(var drill=new PlayerContactDrillV3(1026482,2,"stationary-flight",1,0,0,0,false,3,true))
            {
                var match=drill.Match;
                for(int tick=0;tick<=188;tick++)
                {
                    var before=match.Controls.UpperFor(2);var actions=new PlayerActionV3[4];
                    if(tick>=6)actions[2]=new PlayerActionV3(commands[(tick-6)/12]);
                    var rootBefore=match.Controls.StateFor(2);var requested=actions[2].ToArray();
                    Assert.IsTrue(match.Step(actions),"Rejected physics tick "+tick);
                    CollectionAssert.AreEqual(requested,actions[2].ToArray());
                    Assert.LessOrEqual((match.Controls.StateFor(2).velocity-rootBefore.velocity).magnitude/PlayerJointMotorV3.Dt,14.01f);
                    var after=match.Controls.UpperFor(2);
                    Assert.LessOrEqual(after.ActualVelocity.magnitude,12);
                    Assert.LessOrEqual((after.ActualVelocity-before.ActualVelocity).magnitude/PlayerJointMotorV3.Dt,100.01f);
                    Assert.LessOrEqual(after.ActualAngularVelocity.magnitude,12);
                    for(int j=0;j<7;j++)
                    {
                        Assert.That(after.ArmAngles[j],Is.InRange(PlayerArmJointsV3.Minimum(j),PlayerArmJointsV3.Maximum(j)));
                        Assert.LessOrEqual(Mathf.Abs(after.ArmRates[j])*Mathf.Rad2Deg,j<4?360.001f:480.001f);
                        Assert.LessOrEqual(Mathf.Abs(after.ArmRates[j]-before.ArmRates[j])*Mathf.Rad2Deg/PlayerJointMotorV3.Dt,j<4?1800.1f:2400.1f);
                    }
                    for(int j=0;j<3;j++)
                    {
                        Assert.LessOrEqual(Mathf.Abs(after.TorsoRates[j])*Mathf.Rad2Deg,j==0?180.001f:90.001f);
                        Assert.LessOrEqual(Mathf.Abs(after.TorsoRates[j]-before.TorsoRates[j])*Mathf.Rad2Deg/PlayerJointMotorV3.Dt,j==0?900.1f:450.1f);
                    }
                }
            }
            yield return null;
        }
    }
}

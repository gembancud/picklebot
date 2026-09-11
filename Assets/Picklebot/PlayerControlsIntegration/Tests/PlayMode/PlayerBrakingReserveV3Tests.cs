using System.Collections;
using NUnit.Framework;
using Picklebot.PlayerControls;
using UnityEngine;
using UnityEngine.TestTools;
namespace Picklebot.PlayerControlsIntegration.Tests
{
    public sealed class PlayerBrakingReserveV3Tests
    {
        [UnityTest] public IEnumerator RecordedCoupledBrakingCommandsRemainPhysicallyFeasible()
        {
            // Captured training failure seed1031226/tick200. Commands are a
            // regression fixture only: no policy, demonstration, or learning input.
            var commands=new float[][]{
                new float[]{-1f,-0.339685023f,0.296280235f,0.34423691f,0f,0f,0.934841037f,-0.0530639216f,-0.564354062f,0.498847187f,-0.952000618f,-0.448339403f,0.0592208728f,-0.548577666f,0.0335875079f,0.310341656f,0f,0.222884476f},
                new float[]{-1f,-0.280088305f,0.0980264395f,0.501711309f,0f,0f,1f,0.514510155f,-0.747686088f,0.29601258f,-0.992976606f,0.153190613f,0.564118564f,-0.710187793f,-0.660341859f,0.0778316259f,0f,0.122549772f},
                new float[]{0.417667478f,0.145934433f,0.676240802f,0.657227397f,0f,0.26136902f,1f,0.410300821f,-1f,1f,-1f,0.167396367f,0.504619956f,-0.801479101f,-0.851544738f,-0.131972402f,0f,0.335924387f},
                new float[]{0.482990831f,0.879361629f,0.143401742f,0.504134715f,0f,0.38115862f,0.867982507f,0.297912955f,-0.818012118f,1f,-1f,-0.286069363f,-0.0696456879f,0.264906377f,-0.118917778f,0.226308465f,0f,0.4529953f},
                new float[]{0.308663607f,-0.0515514612f,-1f,0.924797833f,0f,0.14447093f,-0.096301809f,0.441576898f,-0.68528527f,0.263305157f,-1f,-0.31297487f,0.152708024f,0.320946336f,-0.250525594f,0.412283748f,0f,0.464150399f},
                new float[]{-0.0874539465f,-0.288807452f,-0.467662334f,0.577099681f,0f,0.00325709581f,0.108647391f,0.411319375f,-0.200124472f,-0.0269393977f,-0.504576802f,-0.0248554852f,0.0969524384f,-0.186114356f,-0.484144926f,0.387729943f,0f,0.403010845f},
                new float[]{-0.557893336f,-0.223926961f,0.118650757f,0.28286162f,0f,0.15705651f,0.0132891936f,0.00983067416f,0.594609499f,0.0561687909f,-0.220645398f,-0.220460579f,0.164768606f,-0.145337552f,-0.406926155f,0.528638601f,0f,0.516175151f},
                new float[]{-0.321627468f,-0.394603491f,0.386621833f,0.0501844883f,0f,0f,0.393258065f,0.676946521f,0.325955331f,-0.17338708f,-0.102177784f,-0.337283552f,-0.0195423961f,-0.478957593f,-0.565907955f,0.112622879f,0f,0.894839406f},
                new float[]{-0.305447698f,0.0190694034f,0.100595109f,0.248253077f,0f,0f,0.0374116525f,0.74533999f,0.00150783861f,0.552629471f,0.148163825f,-0.40822053f,-0.353758186f,-0.083361499f,0.226647228f,0.503902555f,0f,0.877739251f},
                new float[]{-0.357780635f,-0.649507046f,0.562728822f,0f,0f,0f,0.200295135f,-0.00972276926f,0.73282218f,0.704817176f,0.69879663f,-0.781893432f,0.270587921f,-0.391702265f,-0.20281814f,1f,0f,0.945477068f},
                new float[]{-0.593130469f,-0.0406632833f,1f,0f,0f,0.0460502207f,0.236538351f,-0.245172545f,0.55219692f,1f,0.360369444f,-0.241831154f,0.163934588f,-0.321241587f,0.242504582f,0.967390418f,0f,0.601080656f},
                new float[]{-0.398484707f,-0.122782551f,0.341984242f,0.00145164132f,0f,0.266549528f,-0.105382949f,0.0655894503f,0.419065684f,0.742117107f,0.0623510294f,-0.401833236f,-0.380694956f,0.0875611231f,-0.241543323f,0.906564653f,0f,0.965997458f},
                new float[]{-0.580295742f,0.0461107008f,0.00775257032f,0.0539025664f,0f,0.132686287f,0.016048491f,-0.24706012f,1f,0.445328921f,0.50346756f,-0.922244549f,-0.486394495f,0.454755962f,-0.0403152108f,0.997254372f,0f,0.800634623f},
                new float[]{-0.763548851f,-0.0203013401f,-0.123817146f,0f,0f,0f,-0.605322361f,0.382287204f,1f,0.624236107f,0.924454689f,-0.503416121f,-0.746736407f,0.373284757f,0.241251886f,0.17723918f,0f,0.741589069f},
                new float[]{-0.000486890494f,0.357450098f,-0.446457565f,0f,0f,0.162670851f,-0.617850542f,0.675580204f,0.79966867f,0.562917233f,1f,-1f,-0.978396654f,0.780121803f,0.0309268832f,0.150093049f,0f,0.914559007f},
                new float[]{-0.115448892f,0.323006868f,-0.438482523f,0f,0f,0.138985157f,-0.764661014f,0.286574513f,1f,0.539243817f,1f,-1f,-1f,0.447924078f,0.241886139f,-0.170069784f,0f,0.642686963f},
                new float[]{0.396854103f,-1f,-0.220577508f,0f,0f,0f,0.216056943f,-0.666658878f,1f,1f,1f,-0.639660239f,-0.293763906f,-1f,1f,-0.207377404f,0f,0f}
            };
            using(var drill=new PlayerContactDrillV3(1031226,2,"stationary-flight",1,0,0,0,false,3,false))
            {
                var match=drill.Match;
                for(int tick=0;tick<=200;tick++)
                {
                    var before=match.Controls.UpperFor(2);var actions=new PlayerActionV3[4];
                    if(tick>=6)actions[2]=new PlayerActionV3(commands[(tick-6)/12]);
                    Assert.IsTrue(match.Step(actions),"Rejected physics tick "+tick);
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

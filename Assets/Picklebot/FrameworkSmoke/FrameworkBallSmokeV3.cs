using Unity.MLAgents;
using Unity.MLAgents.Actuators;
using Unity.MLAgents.Policies;
using UnityEngine;

namespace Picklebot.FrameworkSmoke
{
    // Procedural fixture for Unity's unchanged Ball3DAgent sample. This verifies
    // the installed trainer independently of the pickleball body and rewards.
    public sealed class FrameworkBallSmokeV3 : MonoBehaviour
    {
        private void Start()
        {
            var academy = Academy.Instance;
            if (!academy.IsCommunicatorOn)
                throw new System.InvalidOperationException("Start the Python sample trainer before Play.");
            academy.AutomaticSteppingEnabled = true;
            Physics.simulationMode = SimulationMode.FixedUpdate;
            Time.fixedDeltaTime = .02f;
            for (int i = 0; i < 16; i++)
            {
                var platform = GameObject.CreatePrimitive(PrimitiveType.Cube);
                platform.name = "3DBall platform " + i; platform.SetActive(false);
                platform.transform.SetParent(transform);
                platform.transform.position = new Vector3((i % 4) * 10, 0, (i / 4) * 10);
                platform.transform.localScale = new Vector3(5, .25f, 5);
                platform.GetComponent<Renderer>().enabled = false;
                var ball = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                ball.name = "3DBall ball " + i; ball.transform.SetParent(transform);
                ball.transform.position = platform.transform.position + Vector3.up * 4;
                ball.GetComponent<Renderer>().enabled = false;
                var body = ball.AddComponent<Rigidbody>();
                body.collisionDetectionMode = CollisionDetectionMode.ContinuousDynamic;
                var behavior = platform.AddComponent<BehaviorParameters>();
                behavior.BehaviorName = "3DBall";
                behavior.BrainParameters.VectorObservationSize = 8;
                behavior.BrainParameters.ActionSpec = ActionSpec.MakeContinuous(2);
                behavior.BehaviorType = BehaviorType.Default;
                var agent = platform.AddComponent<Ball3DAgent>();
                agent.ball = ball; agent.useVecObs = true; agent.MaxStep = 5000;
                var requester = platform.AddComponent<DecisionRequester>();
                requester.DecisionPeriod = 5; requester.TakeActionsBetweenDecisions = true;
                platform.SetActive(true);
            }
        }
    }
}

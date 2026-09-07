// Replay an isolated motor-command window. Reflection restores only the
// diagnostic initial state and recorded partner path, never a runtime action.
if (!UnityEditor.EditorApplication.isPlaying) throw new System.InvalidOperationException("Start Play.");
string path = UnityEditor.SessionState.GetString("Picklebot.MotorReplay.Path", "");
var report = Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(path));
if ((string)report["status"] != "captured" || ((string)report["split"] != "development" && (string)report["split"] != "training-diagnostic"))
    throw new System.InvalidOperationException("Use a captured diagnostic command window.");
if ((string)report["split"] == "training-diagnostic"
    && (string)report["sourceReportHash"] != Picklebot.Doubles.Editor.ContactTraining.Hash(System.IO.File.ReadAllText((string)report["sourceReportPath"])))
    throw new System.InvalidOperationException("Training diagnostic source report changed.");
var rows = (Newtonsoft.Json.Linq.JArray)report["frames"];
int player = (int)report["player"];
UnityEngine.Vector3 V(Newtonsoft.Json.Linq.JToken v) => new UnityEngine.Vector3((float)v[0], (float)v[1], (float)v[2]);
UnityEngine.Quaternion Q(Newtonsoft.Json.Linq.JToken v) => new UnityEngine.Quaternion((float)v[0], (float)v[1], (float)v[2], (float)v[3]);
void Restore(Picklebot.Doubles.PlayerBody body, Newtonsoft.Json.Linq.JToken state)
{
    body.Reset(V(state["position"]));
    var type = typeof(Picklebot.Doubles.PlayerBody);
    type.GetProperty("Velocity").SetValue(body, V(state["velocity"]));
    type.GetProperty("PaddleVelocity").SetValue(body, V(state["paddleVelocity"]));
    type.GetField("shoulderHeight", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic).SetValue(body, (float)state["shoulderHeight"]);
    var position = V(state["paddle"]); var rotation = Q(state["rotation"]);
    body.Paddle.position = position; body.Paddle.rotation = rotation;
    body.Paddle.transform.SetPositionAndRotation(position, rotation);
}
using var world = new Picklebot.Doubles.DoublesWorld(false);
foreach (var collider in world.Ball.GetComponents<UnityEngine.Collider>()) collider.enabled = false;
var body = world.Players[player]; var partner = world.Players[player ^ 1];
Restore(body, rows[0]["before"]); UnityEngine.Physics.SyncTransforms();
float positionError = 0, velocityError = 0, maxAcceleration = 0, maxSpeed = 0, maxReach = 0, maxAngular = 0;
int infeasible = 0, firstFailure = -1;
var failures = new System.Collections.Generic.List<object>();
for (int i = 0; i < rows.Count; i++)
{
    var row = rows[i]; Restore(partner, row["partner"]);
    var target = V(row["target"]); var rotation = Q(row["rotation"]); var feed = V(row["feed"]); var moveTarget = V(row["moveTarget"]);
    var previous = body.PaddleVelocity;
    bool feasible = Picklebot.PlayerAgents.PlayerPaddleMotor.Constrain(body, partner, moveTarget, ref target, ref rotation, ref feed, Picklebot.Doubles.DoublesWorld.Dt);
    body.Step(moveTarget, target, rotation, feed, partner, Picklebot.Doubles.DoublesWorld.Dt); world.Simulate();
    float acceleration = (body.PaddleVelocity - previous).magnitude / Picklebot.Doubles.DoublesWorld.Dt;
    maxAcceleration = UnityEngine.Mathf.Max(maxAcceleration, acceleration);
    maxSpeed = UnityEngine.Mathf.Max(maxSpeed, body.PaddleVelocity.magnitude);
    maxReach = UnityEngine.Mathf.Max(maxReach, UnityEngine.Vector3.Distance(body.Hand, body.Shoulder));
    maxAngular = UnityEngine.Mathf.Max(maxAngular, body.AngularVelocity.magnitude);
    positionError = UnityEngine.Mathf.Max(positionError, UnityEngine.Vector3.Distance(body.Paddle.position, V(row["after"]["paddle"])));
    velocityError = UnityEngine.Mathf.Max(velocityError, UnityEngine.Vector3.Distance(body.PaddleVelocity, V(row["after"]["paddleVelocity"])));
    if (!feasible) infeasible++;
    if (!feasible || acceleration > 100.1f)
    { if (firstFailure < 0) firstFailure = i; failures.Add(new { frame = i, tick = (int)row["tick"], feasible, acceleration }); }
}
string source = Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash();
var result = new { sourceHash = source, traceSourceHash = (string)report["sourceHash"],
    traceHash = Picklebot.Doubles.Editor.ContactTraining.Hash(System.IO.File.ReadAllText(path)), tracePath = path,
    scriptHash = Picklebot.Doubles.Editor.ContactTraining.Hash(System.IO.File.ReadAllText("scripts/player-paddle-command-replay.cs")),
    frames = rows.Count, player, positionError, velocityError, maxAcceleration, maxSpeed, maxReach, maxAngular, infeasible, firstFailure, failures,
    reconstructed = source == (string)report["sourceHash"] && positionError < .0001f && velocityError < .01f,
    boundsPassed = maxAcceleration <= 100.1f && maxSpeed <= 12.01f && maxReach <= .6201f && maxAngular <= 12.01f && infeasible == 0 };
string output = "artifacts/player-agents/paddle-replay-" + System.DateTime.UtcNow.ToString("yyyyMMdd-HHmmss") + ".json";
if (System.IO.File.Exists(output)) throw new System.IO.IOException("Output exists.");
System.IO.File.WriteAllText(output, Newtonsoft.Json.JsonConvert.SerializeObject(result, Newtonsoft.Json.Formatting.Indented));
return output;

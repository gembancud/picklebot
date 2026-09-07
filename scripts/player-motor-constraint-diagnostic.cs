// Inspect each constraint at one captured state. This does not modify the motor.
string path = UnityEditor.SessionState.GetString("Picklebot.MotorReplay.Path", "");
var report = Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(path));
var row = report["frames"].Last;
UnityEngine.Vector3 V(Newtonsoft.Json.Linq.JToken a) => new UnityEngine.Vector3((float)a[0], (float)a[1], (float)a[2]);
UnityEngine.Quaternion Q(Newtonsoft.Json.Linq.JToken a) => new UnityEngine.Quaternion((float)a[0], (float)a[1], (float)a[2], (float)a[3]);
void Restore(Picklebot.Doubles.PlayerBody b, Newtonsoft.Json.Linq.JToken s)
{
    b.Reset(V(s["position"]));
    typeof(Picklebot.Doubles.PlayerBody).GetProperty("Velocity").SetValue(b, V(s["velocity"]));
    typeof(Picklebot.Doubles.PlayerBody).GetProperty("PaddleVelocity").SetValue(b, V(s["paddleVelocity"]));
    typeof(Picklebot.Doubles.PlayerBody).GetField("shoulderHeight", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance).SetValue(b, (float)s["shoulderHeight"]);
    b.Paddle.position = V(s["paddle"]); b.Paddle.rotation = Q(s["rotation"]);
    b.Paddle.transform.SetPositionAndRotation(b.Paddle.position, b.Paddle.rotation);
}
using var world = new Picklebot.Doubles.DoublesWorld(false);
int player = (int)report["player"];
var body = world.Players[player]; var partner = world.Players[player ^ 1];
Restore(body, row["before"]); Restore(partner, row["partner"]);
float dt = Picklebot.Doubles.DoublesWorld.Dt;
var position = (UnityEngine.Vector3)typeof(Picklebot.PlayerAgents.PlayerPaddleMotor).GetMethod("PredictPosition", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static).Invoke(null, new object[] { body, partner, V(row["moveTarget"]), dt });
float height = body.Shoulder.y;
var target = V(row["target"]); var rotation = Q(row["rotation"]); var feed = V(row["feed"]);
float wantedHeight = UnityEngine.Mathf.MoveTowards(height, UnityEngine.Mathf.Clamp(target.y + .20f, .72f, 1.5f), 1.6f * dt);
var facing = UnityEngine.Quaternion.LookRotation(UnityEngine.Vector3.forward * -body.Side);
var angles = (UnityEngine.Quaternion.Inverse(facing) * rotation).eulerAngles;
angles = new UnityEngine.Vector3(UnityEngine.Mathf.Clamp(UnityEngine.Mathf.DeltaAngle(0, angles.x), -65, 65), UnityEngine.Mathf.Clamp(UnityEngine.Mathf.DeltaAngle(0, angles.y), -105, 105), UnityEngine.Mathf.Clamp(UnityEngine.Mathf.DeltaAngle(0, angles.z), -85, 85));
var wantedRotation = UnityEngine.Quaternion.RotateTowards(body.Paddle.rotation, facing * UnityEngine.Quaternion.Euler(angles), Picklebot.Doubles.PlayerBody.AngularSpeed * UnityEngine.Mathf.Rad2Deg * dt);
var handOffset = body.Hand - body.Shoulder; var radial = handOffset.normalized;
var bodyVelocity = (position - body.Position) / dt;
var trials = new System.Collections.Generic.List<object>();
int iterationLimit = UnityEditor.SessionState.GetInt("Picklebot.MotorDiagnostic.Iterations", 64);
for (int trial = 0; trial < 27; trial++)
{
    bool braking = trial < 9, innerRecovery = trial >= 18;
    int orientationTrial = trial % 9;
    float fraction = orientationTrial == 8 ? 0 : UnityEngine.Mathf.Pow(.5f, orientationTrial);
    float nextHeight = UnityEngine.Mathf.Lerp(height, wantedHeight, fraction);
    var nextRotation = UnityEngine.Quaternion.Slerp(body.Paddle.rotation, wantedRotation, fraction);
    var shoulder = position + new UnityEngine.Vector3(-body.Side * .19f, nextHeight, 0);
    var grip = Picklebot.Doubles.PlayerBody.GripLocal;
    var wantedHand = shoulder + UnityEngine.Vector3.ClampMagnitude(target + nextRotation * grip - shoulder, .62f);
    var velocity = UnityEngine.Vector3.ClampMagnitude(feed + (wantedHand - nextRotation * grip - body.Paddle.position) * 28, 12);
    var reachCenter = (shoulder - body.Paddle.position - nextRotation * grip) / dt;
    float reachRadius = .61999f / dt;
    var frameVelocity = (nextRotation * grip - body.Paddle.rotation * grip - (shoulder - body.Shoulder)) / dt;
    var postureVelocity = (nextRotation * grip - body.Paddle.rotation * grip - UnityEngine.Vector3.up * (nextHeight - height)) / dt;
    float outwardLimit = UnityEngine.Mathf.Sqrt(40f * UnityEngine.Mathf.Max(0, .60f - handOffset.magnitude)) - UnityEngine.Vector3.Dot(frameVelocity, radial);
    float stoppedLimit = UnityEngine.Mathf.Sqrt(40f * UnityEngine.Mathf.Max(0, .60f - handOffset.magnitude)) + UnityEngine.Vector3.Dot(bodyVelocity, radial);
    if (!braking) velocity = body.PaddleVelocity - radial * (100 * dt);
    if (innerRecovery) velocity = bodyVelocity;
    for (int iteration = 0; iteration < iterationLimit; iteration++)
    {
        var previous = velocity;
        velocity = UnityEngine.Vector3.ClampMagnitude(velocity, 12);
        velocity = body.PaddleVelocity + UnityEngine.Vector3.ClampMagnitude(velocity - body.PaddleVelocity, 100 * dt);
        velocity = reachCenter + UnityEngine.Vector3.ClampMagnitude(velocity - reachCenter, reachRadius);
        if (!innerRecovery)
        {
            var stopped = velocity - bodyVelocity; float speed = UnityEngine.Vector3.Dot(stopped, radial);
            velocity = bodyVelocity + radial * speed + UnityEngine.Vector3.ClampMagnitude(stopped - radial * speed, 6);
        }
        if (braking)
        {
            velocity = UnityEngine.Vector3.ClampMagnitude(velocity + frameVelocity, 6) - frameVelocity;
            velocity -= radial * UnityEngine.Mathf.Max(0, UnityEngine.Vector3.Dot(velocity, radial) - outwardLimit);
            velocity -= radial * UnityEngine.Mathf.Max(0, UnityEngine.Vector3.Dot(velocity, radial) - stoppedLimit);
        }
        if ((velocity - previous).sqrMagnitude < 1e-12f) break;
    }
    trials.Add(new { trial, fraction, skippedRadius = innerRecovery && handOffset.magnitude > .45f, skippedPosture = !braking && UnityEngine.Vector3.Dot(postureVelocity, radial) > .0001f,
        speed = velocity.magnitude, deltaVelocity = (velocity - body.PaddleVelocity).magnitude,
        tangent = UnityEngine.Vector3.ProjectOnPlane(velocity - bodyVelocity, radial).magnitude,
        handSpeed = (velocity + frameVelocity).magnitude, outward = UnityEngine.Vector3.Dot(velocity, radial), stoppedLimit,
        reach = (velocity - reachCenter).magnitude * dt, nextRadius = (handOffset + (velocity + frameVelocity) * dt).magnitude });
}
return new { player, tick = (int)row["tick"], radius = handOffset.magnitude, iterationLimit, trials };

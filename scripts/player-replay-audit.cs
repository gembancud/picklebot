// Run with Unity CLI eval_file while the independent-player demo has a replay.
// Inspect recorded private poses only for verification; runtime control does
// not use reflection. Do not modify live physics objects to show a replay.
var demo = UnityEngine.Object.FindFirstObjectByType<Picklebot.PlayerAgents.PlayerAgentsDemo>();
if (demo == null || demo.ReplayFrames == 0) throw new System.InvalidOperationException("Run the control probe through one rally first.");
demo.Paused = true;
if (demo.IsReplaying) demo.ToggleReplay();
string State()
{
    var match = demo.Match; var world = match.World;
    var values = new System.Collections.Generic.List<float>();
    void V(UnityEngine.Vector3 v) { values.Add(v.x); values.Add(v.y); values.Add(v.z); }
    void Q(UnityEngine.Quaternion q) { values.Add(q.x); values.Add(q.y); values.Add(q.z); values.Add(q.w); }
    values.Add(world.Time); values.Add(match.Tick); values.Add(match.CompletedRallies);
    values.Add(world.Contacts.Count); values.Add(world.Rules.Score[0]); values.Add(world.Rules.Score[1]);
    V(world.Ball.position); V(world.Ball.linearVelocity); V(world.Ball.angularVelocity); Q(world.Ball.rotation);
    foreach (var p in world.Players)
    { V(p.Position); V(p.Velocity); V(p.Paddle.position); Q(p.Paddle.rotation); V(p.PaddleVelocity); V(p.AngularVelocity); V(p.LeftFoot); V(p.RightFoot); }
    return string.Join(",", System.Linq.Enumerable.Select(values, v => v.ToString("R", System.Globalization.CultureInfo.InvariantCulture)));
}
string before = State(); demo.ToggleReplay();
float maxPoseError = 0;
var flags = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic;
var type = demo.GetType();
var ghosts = (UnityEngine.Transform[])type.GetField("ghosts", flags).GetValue(demo);
var recorded = (System.Collections.IList)type.GetField("lastReplay", flags).GetValue(demo);
foreach (int frame in new[] { 0, demo.ReplayFrames / 2, demo.ReplayFrames - 1 })
{
    demo.ShowReplayFrame(frame);
    var poses = (System.Array)recorded[frame];
    for (int i = 0; i < ghosts.Length; i++)
    {
        var pose = poses.GetValue(i); var t = pose.GetType();
        var position = (UnityEngine.Vector3)t.GetField("position").GetValue(pose);
        var scale = (UnityEngine.Vector3)t.GetField("scale").GetValue(pose);
        var rotation = (UnityEngine.Quaternion)t.GetField("rotation").GetValue(pose);
        var actual = ghosts[i].rotation;
        maxPoseError = UnityEngine.Mathf.Max(maxPoseError, UnityEngine.Vector3.Distance(position, ghosts[i].position),
            UnityEngine.Vector3.Distance(scale, ghosts[i].localScale),
            UnityEngine.Mathf.Abs(rotation.x - actual.x) + UnityEngine.Mathf.Abs(rotation.y - actual.y)
            + UnityEngine.Mathf.Abs(rotation.z - actual.z) + UnityEngine.Mathf.Abs(rotation.w - actual.w));
    }
    if (State() != before) throw new System.InvalidOperationException("Replay changed live physics state.");
}
demo.ToggleReplay();
bool unchanged = before == State();
var path = "artifacts/player-agents/replay-audit-" + System.DateTime.UtcNow.ToString("yyyyMMdd-HHmmss") + ".json";
string json = "{\"physicsUnchanged\":" + unchanged.ToString().ToLowerInvariant()
    + ",\"frames\":" + demo.ReplayFrames + ",\"ghostMeshes\":" + ghosts.Length
    + ",\"maxPoseError\":" + maxPoseError.ToString("R", System.Globalization.CultureInfo.InvariantCulture)
    + ",\"sourceHash\":\"" + Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash() + "\"}";
System.IO.File.WriteAllText(path, json);
if (!unchanged || maxPoseError > .00001f) throw new System.InvalidOperationException("Replay audit failed; see " + path);
return path;

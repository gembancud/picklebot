// Bounded, development-only serve delivery calibration. No ball steering.
if (!UnityEditor.EditorApplication.isPlaying || Picklebot.PlayerAgents.Editor.PlayerCompetition.Running
    || Picklebot.PlayerAgents.Editor.PlayerCurriculum.Running
    || UnityEditor.EditorApplication.update.GetInvocationList().Any(d => d.Method.Name.Contains("TickFinal")
        || d.Method.Name.Contains("TickIncoming") || d.Method.Name.Contains("TickCoverage") || d.Method.Name.Contains("TickServeDelivery")))
    throw new System.InvalidOperationException("Start Play and finish other jobs first.");
bool sweep = UnityEditor.SessionState.GetBool("Picklebot.ServeDelivery.Sweep", false);
var cases = new System.Collections.Generic.List<(int server, float x, float depth, float pitch, float timing, float speed)>();
if (sweep)
{
    foreach (float pitch in new[] { -10f, 0f, 10f, 20f })
    foreach (float timing in new[] { -.04f, 0f, .04f })
    foreach (float speed in new[] { .75f, 1f, 1.25f, 1.5f }) cases.Add((0, 0, 0, pitch, timing, speed));
}
else
    for (int server = 0; server < 4; server++)
    foreach (var jitter in new[] { new UnityEngine.Vector2(-.3f, .4f), UnityEngine.Vector2.zero, new UnityEngine.Vector2(.3f, -.4f) })
        cases.Add((server, jitter.x, jitter.y, 0, 0, 1));
string source = Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash();
string stem = "artifacts/player-agents/serve-delivery-" + System.DateTime.UtcNow.ToString("yyyyMMdd-HHmmss");
if (System.IO.File.Exists(stem + ".json")) throw new System.IO.IOException("Output exists.");
System.IO.File.Copy("scripts/player-serve-delivery-probe.cs", stem + ".collector.cs");
var rows = new System.Collections.Generic.List<object>();
Picklebot.PlayerAgents.PlayerMatch match = null;
Picklebot.Doubles.StrokeController serve = null;
int index = 0, tick = 0;
float peakAcceleration = 0, peakSpeed = 0, peakReach = 0;
object contactState = null;
var watch = System.Diagnostics.Stopwatch.StartNew();
float[] V(UnityEngine.Vector3 p) => new[] { p.x, p.y, p.z };
void NewCase()
{
    var c = cases[index];
    var policies = Enumerable.Range(0, 4).Select(_ => (Picklebot.PlayerAgents.IPlayerPolicy)new Picklebot.PlayerAgents.ConstantPlayerPolicy(default)).ToArray();
    match = new Picklebot.PlayerAgents.PlayerMatch(false, policies, null, 1132000 + index) { AutoNext = false, ServeJitter = new UnityEngine.Vector2(c.x, c.depth) };
    var r = match.World.Rules;
    for (int setup = 0; r.Server != c.server && setup < 8; setup++)
    { r.Fail(r.ServingTeam, Picklebot.Doubles.Fault.Lost, 0); if (!r.ResolveRally()) throw new System.InvalidOperationException("Service setup did not resolve"); match.Next(); }
    if (r.Server != c.server) throw new System.InvalidOperationException("Wrong service seat");
    // Diagnostic parameter search only. The game never receives this reflector.
    serve = (Picklebot.Doubles.StrokeController)typeof(Picklebot.PlayerAgents.PlayerMatch)
        .GetField("serve", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic).GetValue(match);
    serve.PitchBias = c.pitch; serve.TimingBias = c.timing; serve.SpeedScale = c.speed;
    tick = 0; peakAcceleration = peakSpeed = peakReach = 0; contactState = null;
}
void SaveCase()
{
    var c = cases[index]; var w = match.World; var r = w.Rules;
    rows.Add(new { c.server, c.x, c.depth, c.pitch, c.timing, c.speed, tick,
        legalLanding = r.Phase == Picklebot.Doubles.RallyPhase.ServeFlight && r.Bounced && !r.Dead,
        fault = r.LastFault.ToString(), hits = r.Hits, peakAcceleration, peakSpeed, peakReach,
        infeasible = match.Metrics.infeasiblePaddleSteps, contactState,
        contacts = w.Contacts.Select(z => new { z.time, z.player, z.surface, point = V(z.point), normal = V(z.normal), incoming = V(z.incoming), velocity = V(z.velocity) }).ToArray(),
        events = r.Events.Select(z => new { z.time, z.kind, z.player, fault = z.fault.ToString(), position = V(z.position) }).ToArray() });
    match.Dispose(); match = null; index++;
    UnityEditor.SessionState.SetString("Picklebot.ServeDelivery.Status", "running: " + index + "/" + cases.Count);
}
void Finish(string error = null)
{
    UnityEditor.EditorApplication.update -= TickServeDelivery;
    match?.Dispose(); match = null;
    var result = new { status = error == null ? "complete" : "failed", error, sourceHash = source, split = "development", sweep,
        collectorHash = Picklebot.Doubles.Editor.ContactTraining.Hash(System.IO.File.ReadAllText(stem + ".collector.cs")),
        collectorSnapshotPath = stem + ".collector.cs", wallSeconds = watch.Elapsed.TotalSeconds, rows };
    System.IO.File.WriteAllText(stem + ".json", Newtonsoft.Json.JsonConvert.SerializeObject(result, Newtonsoft.Json.Formatting.Indented));
    UnityEditor.SessionState.SetString("Picklebot.ServeDelivery.Status", result.status + ": " + stem + ".json");
}
void TickServeDelivery()
{
    try
    {
        if (!UnityEditor.EditorApplication.isPlaying) throw new System.InvalidOperationException("Play stopped");
        double until = UnityEditor.EditorApplication.timeSinceStartup + .02;
        while (UnityEditor.EditorApplication.timeSinceStartup < until)
        {
            if (match == null) NewCase();
            var w = match.World; var r = w.Rules; var body = w.Players[cases[index].server];
            var previous = body.PaddleVelocity; int hits = r.Hits;
            match.Step(); tick++;
            peakAcceleration = UnityEngine.Mathf.Max(peakAcceleration, (body.PaddleVelocity - previous).magnitude / Picklebot.Doubles.DoublesWorld.Dt);
            peakSpeed = UnityEngine.Mathf.Max(peakSpeed, body.PaddleVelocity.magnitude);
            peakReach = UnityEngine.Mathf.Max(peakReach, UnityEngine.Vector3.Distance(body.Hand, body.Shoulder));
            if (hits == 0 && r.Hits > 0) contactState = new { time = w.Time, ball = V(w.Ball.position), velocity = V(w.Ball.linearVelocity), paddle = V(body.Paddle.position), paddleVelocity = V(body.PaddleVelocity), normal = V(serve.Normal), swing = serve.Swing, impactAt = serve.ImpactAt };
            if (r.Dead || r.Bounced || tick >= 1440) SaveCase();
            if (index == cases.Count) { Finish(); return; }
        }
    }
    catch (System.Exception error) { Finish(error.ToString()); }
}
UnityEditor.SessionState.SetString("Picklebot.ServeDelivery.Status", "running: " + stem + ".json");
UnityEditor.EditorApplication.update += TickServeDelivery;
return stem + ".json";

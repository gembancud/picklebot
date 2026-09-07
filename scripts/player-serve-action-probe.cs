// Development-only receiver action controls. Never training data or a deployed policy.
bool IsJob(System.Delegate d) {
    string owner = d.Method.DeclaringType?.FullName ?? "";
    return (owner.StartsWith("PipelineEvaluation.") && d.Method.Name.Contains("g__Tick"))
        || (owner.StartsWith("Picklebot.") && d.Method.Name.Contains("Tick"));
}
if (!UnityEditor.EditorApplication.isPlaying || UnityEditor.EditorApplication.update.GetInvocationList().Any(IsJob))
    throw new System.InvalidOperationException("Start Play and finish other test jobs first.");
string Hash(string path) {
    using var hash = System.Security.Cryptography.SHA256.Create();
    using var input = System.IO.File.OpenRead(path);
    return System.BitConverter.ToString(hash.ComputeHash(input)).Replace("-", "").ToLowerInvariant();
}
const int Seed = 1198000, Fixtures = 12, Modes = 5;
string actorPath = UnityEditor.SessionState.GetString("Picklebot.ServeAction.ActorPath", "");
string referencePath = UnityEditor.SessionState.GetString("Picklebot.ServeAction.ReferencePath", "");
string source = Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash();
string contactPath = "Assets/Picklebot/Doubles/Models/contact.json", teamsPath = "Assets/Picklebot/Doubles/Models/teams.json";
string protocolPath = "config/player-agents/evaluation-v1.json", baselinePath = "artifacts/player-agents/baseline-manifest.json";
string collector = "scripts/player-serve-action-probe.cs";
var frozen = new[] { actorPath, contactPath, teamsPath, protocolPath, baselinePath, collector, referencePath }.ToDictionary(p => p, Hash);
var manifest = Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(baselinePath));
foreach (var file in ((Newtonsoft.Json.Linq.JObject)manifest["files"]).Properties())
    if (Hash(file.Name) != (string)file.Value) throw new System.InvalidOperationException("Frozen baseline changed.");
var model = Picklebot.PlayerAgents.PlayerActorModel.Load(System.IO.File.ReadAllText(actorPath));
var metadata = Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(actorPath));
if (model.sourceHash != source || model.trainingSteps <= 0 || model.contactModelHash != frozen[contactPath]
    || model.protocolHash != frozen[protocolPath] || (string)metadata["baselineManifestHash"] != frozen[baselinePath])
    throw new System.InvalidOperationException("Actor provenance mismatch.");
var contact = Picklebot.Doubles.ContactModel.Load(System.IO.File.ReadAllText(contactPath));
var teams = Picklebot.Doubles.DoublesModels.Load(System.IO.File.ReadAllText(teamsPath));
string stem = "artifacts/player-agents/serve-action-" + System.DateTime.UtcNow.ToString("yyyyMMdd-HHmmss");
System.IO.File.Copy(collector, stem + ".collector.cs");
var rows = new System.Collections.Generic.List<object>();
var watch = System.Diagnostics.Stopwatch.StartNew();
Picklebot.PlayerAgents.PlayerMatch match = null;
Picklebot.PlayerAgents.Editor.PlayerOracle oracle = null;
Picklebot.PlayerAgents.PlayerActor[] actors = null;
System.IO.StreamWriter trace = null;
string tracePath = "";
int index = 0, fixture = 0, mode = 0, server = 0, receiver = 0, setupSteps = 0, decisions = 0;
bool serveLanded = false, returnHit = false, returnLanded = false;
object initial = null, serveContact = null;
float[] V(Vector3 p) => new[] { p.x, p.y, p.z };
void Save(string status, string error = null) {
    trace?.Flush();
    System.IO.File.WriteAllText(stem + ".json", Newtonsoft.Json.JsonConvert.SerializeObject(new {
        version = "player-serve-action-probe-v1", status, error, sourceHash = source,
        configurationHash = model.configurationHash, actorPath, actorHash = frozen[actorPath], frozen, referencePath, referenceHash = frozen[referencePath],
        collectorSnapshotPath = stem + ".collector.cs", split = "development-diagnostic", seedBase = Seed,
        fixtures = Fixtures, modes = Modes, expectedCases = Fixtures * Modes,
        physicsHz = 240, decisionTicks = 12, actionLatencyTicks = 6, maximumSeconds = 12,
        modeSchedule = "0 deterministic actor; 1 sampled actor; 2 privileged teacher; 3 receiver teacher movement only; 4 receiver teacher shot only",
        wallSeconds = watch.Elapsed.TotalSeconds, rows,
        limitation = "One real scripted serve and its first return, not completed games. Four separate policy instances. "
            + "Teacher and component replacements are privileged diagnostic controls, never deployed policies or training data. Only the designated receiver receives component replacements; actor attempt decisions and other players remain unchanged. "
            + "Service seat is set by recorded dead-ball rule transitions before simulation. No ball steering or contact override. Physics is provisional."
    }, Newtonsoft.Json.Formatting.Indented));
    UnityEditor.SessionState.SetString("Picklebot.ServeAction.Status", status + ": " + index + " /60; " + stem + ".json");
}
void StartCase() {
    fixture = index / Modes; mode = index % Modes; server = fixture / 3;
    var jitter = new[] { new Vector2(-.3f, .4f), Vector2.zero, new Vector2(.3f, -.4f) }[fixture % 3];
    int seed = Seed + fixture;
    actors = Enumerable.Range(0, 4).Select(_ => new Picklebot.PlayerAgents.PlayerActor(model, mode == 1)).ToArray();
    oracle = mode >= 2 ? new Picklebot.PlayerAgents.Editor.PlayerOracle(contact, teams, seed, -1) : null;
    var policies = Enumerable.Range(0, 4).Select(i => mode == 2
        ? (Picklebot.PlayerAgents.IPlayerPolicy)oracle.Policies[i] : actors[i]).ToArray();
    match = new Picklebot.PlayerAgents.PlayerMatch(false, policies, contact, seed) { AutoNext = false, ServeJitter = jitter };
    var w = match.World; var r = w.Rules;
    if (w.Configuration.ConfigurationHash != model.configurationHash) throw new System.InvalidOperationException("Physics mismatch.");
    setupSteps = 0;
    while (r.Server != server && setupSteps < 8) {
        r.Fail(r.ServingTeam, Picklebot.Doubles.Fault.Lost, 0);
        if (!r.ResolveRally()) throw new System.InvalidOperationException("Service setup failed.");
        match.Next(); setupSteps++;
    }
    if (r.Server != server) throw new System.InvalidOperationException("Wrong service seat.");
    receiver = r.DesignatedReceiver; decisions = 0; serveLanded = returnHit = returnLanded = false;
    r.Events.Clear(); w.Contacts.Clear(); serveContact = null;
    initial = new { ball = V(w.Ball.position), velocity = V(w.Ball.linearVelocity), jitter = new[] { jitter.x, jitter.y },
        players = w.Players.Select(p => V(p.Position)).ToArray(), r.Server, r.DesignatedReceiver, r.ServerNumber,
        score = (int[])r.Score.Clone(), observations = Enumerable.Range(0, 4).Select(i => Picklebot.PlayerAgents.PlayerObservation.Capture(w, i, 0).values).ToArray() };
    tracePath = stem + ".case-" + index.ToString("D3") + ".jsonl";
    trace = new System.IO.StreamWriter(new System.IO.FileStream(tracePath, System.IO.FileMode.CreateNew, System.IO.FileAccess.Write));
    match.Actors.Decided += d => {
        var original = d.action;
        Picklebot.PlayerAgents.PlayerAction? teacherAction = oracle == null ? null : oracle.Policies[d.player].Action;
        if (d.player == receiver && mode == 3) {
            d.action.moveX = teacherAction.Value.moveX; d.action.moveZ = teacherAction.Value.moveZ;
        }
        if (d.player == receiver && mode == 4) d.action.shot = teacherAction.Value.shot;
        trace.WriteLine(Newtonsoft.Json.JsonConvert.SerializeObject(new { d.player, d.observationTick, d.applyTick,
            observation = d.observation.values, original, teacherAction, action = d.action,
            sample = mode == 2 ? null : actors[d.player].LastSample }));
        decisions++;
    };
}
void EndCase() {
    var w = match.World; var r = w.Rules;
    trace.Dispose(); trace = null;
    rows.Add(new { index, fixture, mode, seed = Seed + fixture, server, receiver, setupSteps, initial, serveContact,
        serveLanded, returnHit, returnLanded, fault = r.LastFault.ToString(), winner = r.Winner, hits = r.Hits,
        seconds = w.Time, ticks = match.Tick, decisions, tracePath, traceHash = Hash(tracePath),
        contacts = w.Contacts.Select(c => new { c.time, c.player, c.surface, point = V(c.point), normal = V(c.normal), incoming = V(c.incoming), velocity = V(c.velocity) }).ToArray(),
        events = r.Events.Select(e => new { e.time, e.kind, e.player, e.winner, fault = e.fault.ToString(), position = V(e.position) }).ToArray(),
        metrics = Newtonsoft.Json.Linq.JObject.Parse(UnityEngine.JsonUtility.ToJson(match.Metrics)) });
    match.Dispose(); match = null; index++; Save("running");
}
void TickServeAction() {
    try {
        if (!UnityEditor.EditorApplication.isPlaying) throw new System.InvalidOperationException("Play stopped.");
        double until = UnityEditor.EditorApplication.timeSinceStartup + .02;
        while (index < Fixtures * Modes && UnityEditor.EditorApplication.timeSinceStartup < until) {
            if (match == null) StartCase();
            oracle?.Prepare(match.World);
            var w = match.World; var r = w.Rules; int before = r.Hits;
            match.Step();
            if (before == 0 && r.Hits == 1) serveContact = new { time = w.Time, ball = V(w.Ball.position), velocity = V(w.Ball.linearVelocity) };
            serveLanded |= !r.Dead && r.Hits == 1 && r.Bounced;
            returnHit |= r.Hits >= 2;
            returnLanded |= !r.Dead && r.Hits == 2 && r.Bounced;
            if (r.Dead || returnLanded || w.Time >= 12) EndCase();
        }
        if (index == Fixtures * Modes) {
            if (source != Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash() || frozen.Any(p => Hash(p.Key) != p.Value))
                throw new System.InvalidOperationException("Probe inputs changed.");
            UnityEditor.EditorApplication.update -= TickServeAction; Save("complete");
        }
    } catch (System.Exception error) {
        UnityEditor.EditorApplication.update -= TickServeAction;
        trace?.Dispose(); trace = null; match?.Dispose(); match = null; Save("failed", error.ToString());
    }
}
Save("scheduled"); UnityEditor.EditorApplication.update += TickServeAction;
return stem + ".json";

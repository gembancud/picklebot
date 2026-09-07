// Diagnostic only. Repeat sampled teacher versus saved actor on identical shot-quality fixtures.
// No labels are added to training data. No runtime or saved asset is changed.
if (!UnityEditor.EditorApplication.isPlaying
    || Picklebot.PlayerAgents.Editor.PlayerCompetition.Running || Picklebot.PlayerAgents.Editor.PlayerCurriculum.Running
    || Picklebot.PlayerAgents.Editor.PlayerEvaluation.Running || Picklebot.PlayerAgents.Editor.PlayerTeacher.Running
    || Picklebot.PlayerAgents.Editor.PlayerControlProbe.Running || Picklebot.PlayerAgents.Editor.PlayerDiagnostics.Running
    || UnityEditor.EditorApplication.update.GetInvocationList().Any(d => d.Method.Name.StartsWith("Tick")))
    throw new System.InvalidOperationException("Start Play and finish other jobs first.");
string Hash(string path)
{
    using var algorithm = System.Security.Cryptography.SHA256.Create();
    using var input = System.IO.File.OpenRead(path);
    return System.BitConverter.ToString(algorithm.ComputeHash(input)).Replace("-", "").ToLowerInvariant();
}
const int Fixtures = 32, Modes = 2, Seed = 1199000;
string source = Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash();
string collector = "scripts/player-teacher-gap.cs";
string contactPath = "Assets/Picklebot/Doubles/Models/contact.json", teamsPath = "Assets/Picklebot/Doubles/Models/teams.json";
string protocolPath = "config/player-agents/evaluation-v1.json", baselinePath = "artifacts/player-agents/baseline-manifest.json";
string collectorHash = Hash(collector), contactHash = Hash(contactPath), teamsHash = Hash(teamsPath);
string protocolHash = Hash(protocolPath), baselineHash = Hash(baselinePath);
var manifest = Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(baselinePath));
foreach (var file in ((Newtonsoft.Json.Linq.JObject)manifest["files"]).Properties())
    if (Hash(file.Name) != (string)file.Value) throw new System.InvalidOperationException("Frozen baseline changed.");
var contact = Picklebot.Doubles.ContactModel.Load(System.IO.File.ReadAllText(contactPath));
var teams = Picklebot.Doubles.DoublesModels.Load(System.IO.File.ReadAllText(teamsPath));
string actorPath = UnityEditor.SessionState.GetString("Picklebot.TeacherGap.ActorPath",
    "artifacts/player-agents/ppo-20260907-032230/actor.json");
string actorHash = Hash(actorPath);
var actor = Picklebot.PlayerAgents.PlayerActorModel.Load(System.IO.File.ReadAllText(actorPath));
var actorMeta = Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(actorPath));
if (actor.trainingSteps <= 0 || actor.contactModelHash != contactHash || actor.protocolHash != protocolHash
    || (string)actorMeta["baselineManifestHash"] != baselineHash)
    throw new System.InvalidOperationException("Actor provenance mismatch.");
// Older runtime weights are explicitly retained as an experimental comparison.
bool historicalCandidate = actor.sourceHash != source;
string stem = "artifacts/player-agents/teacher-gap-" + System.DateTime.UtcNow.ToString("yyyyMMdd-HHmmss");
System.IO.File.Copy(collector, stem + ".collector.cs");
var watch = System.Diagnostics.Stopwatch.StartNew();
var rows = new System.Collections.Generic.List<object>();
Picklebot.PlayerAgents.PlayerMatch match = null;
Picklebot.PlayerAgents.Editor.PlayerOracle oracle = null;
System.IO.StreamWriter trace = null;
int index = 0, fixture = 0, mode = 0, team = 0, fixedShot = 0, decisions = 0;
float started = 0;
bool kitchen = false;
string tracePath = "", configurationHash = "";
Vector3 ballStart = default, velocityStart = default;
Vector3[] playerStarts = null;
float[][] initialObservations = null;
float[] V(Vector3 p) => new[] { p.x, p.y, p.z };
float[] Q(Quaternion q) => new[] { q.x, q.y, q.z, q.w };
object[] Events() => match.World.Rules.Events.Select(e => (object)new {
    e.time, e.kind, e.player, e.winner, position = V(e.position), fault = e.fault.ToString()
}).ToArray();
void Save(string status, string error = null)
{
    trace?.Flush();
    System.IO.File.WriteAllText(stem + ".json", Newtonsoft.Json.JsonConvert.SerializeObject(new {
        version = "player-teacher-gap-v1", status, error, split = "development-diagnostic",
        sourceHash = source, configurationHash, collectorHash, collectorSnapshotPath = stem + ".collector.cs",
        contactPath, contactHash, teamsPath, teamsHash, protocolPath, protocolHash, baselinePath, baselineHash,
        actorPath, actorHash, actorTrainingSourceHash = actor.sourceHash, historicalCandidate, sampledActor = false,
        fixtures = Fixtures, modes = Modes, seedBase = Seed, expectedCases = Fixtures * Modes,
        physicsHz = 240, decisionTicks = 12, actionLatencyTicks = 6, maximumSeconds = 6,
        modeSchedule = "0 sampled teacher control; 1 saved deterministic actor with diagnostic shadow labels",
        fixtureSchedule = "16 deep followed by 16 kitchen; alternating candidate team",
        wallSeconds = watch.Elapsed.TotalSeconds, rows,
        limitation = "Injected incoming fixtures, not completed games. All colliders stay enabled. "
            + "Mode zero uses privileged teacher movement and hitter selection. Mode one uses four separate "
            + "policy objects: saved actor instances for the candidate and constant leave actions for opponents. "
            + "Diagnostic shadow teacher labels never replace actor actions and are development-only, not training data. "
            + "This measures skill transfer on matched starts, not team-game-win strength."
    }, Newtonsoft.Json.Formatting.Indented));
    UnityEditor.SessionState.SetString("Picklebot.TeacherGap.Status", status + ": " + index + "/64; " + stem + ".json");
}
void StartCase()
{
    fixture = index / Modes; mode = index % Modes; team = fixture % 2; kitchen = fixture >= 16;
    int seed = Seed + fixture;
    var random = new System.Random(seed);
    float Range(float a, float b) => a + (b-a) * (float)random.NextDouble();
    fixedShot = mode == 0 ? -1 : -2;
    int worldShot = -1;
    oracle = new Picklebot.PlayerAgents.Editor.PlayerOracle(contact, teams, seed, worldShot);
    var policies = Enumerable.Range(0, 4).Select(i => i/2 == team
        ? (mode == 0 ? (Picklebot.PlayerAgents.IPlayerPolicy)oracle.Policies[i] : new Picklebot.PlayerAgents.PlayerActor(actor, false))
        : new Picklebot.PlayerAgents.ConstantPlayerPolicy(default)).ToArray();
    match = new Picklebot.PlayerAgents.PlayerMatch(false, policies, contact, seed) { AutoNext = false };
    var w = match.World; var r = w.Rules;
    configurationHash = w.Configuration.ConfigurationHash;
    if (actor.configurationHash != configurationHash) throw new System.InvalidOperationException("Actor physics mismatch.");
    for (int tick = 0; tick < 480 && !w.ServeBounced && !r.Dead; tick++) w.Simulate();
    if (!w.ServeBounced || r.Dead) throw new System.InvalidOperationException("Drop setup failed.");
    r.Serve(0, true, true, true, true, false, false, false, w.Time);
    r.Bounce(new Vector3(r.ServiceX(r.DesignatedReceiver), 0, 4), w.Time);
    r.Hit(2, w.Time); r.Bounce(new Vector3(1, 0, -4), w.Time); r.Hit(0, w.Time);
    if (team == 0) r.Hit(2, w.Time);
    if (r.Dead || r.ExpectedTeam != team || r.Phase != Picklebot.Doubles.RallyPhase.Rally)
        throw new System.InvalidOperationException("Invalid rule fixture.");
    for (int i = 0; i < 4; i++)
    {
        float x = ((i & 1) == 0 ? 1.55f : -1.55f) + (i/2 == team ? Range(-.35f, .35f) : 0);
        float depth = i/2 == team ? Range(kitchen ? 1.8f : 3.4f, kitchen ? 3.2f : 6.6f) : 6;
        w.Players[i].Reset(Picklebot.PlayerAgents.PlayerObservation.ToWorld(new Vector3(x, 0, -depth), i));
    }
    playerStarts = w.Players.Select(p => p.Position).ToArray();
    ballStart = new Vector3(Range(kitchen ? -2 : -2.7f, kitchen ? 2 : 2.7f), Range(1.1f, 1.5f), Range(.15f, .7f));
    velocityStart = new Vector3(Range(-.8f, .8f), Range(.8f, 1.8f), Range(kitchen ? -3.6f : -8.7f, kitchen ? -2.7f : -7.3f));
    w.Ball.position = Picklebot.PlayerAgents.PlayerObservation.ToWorld(ballStart, team*2);
    w.Ball.transform.position = w.Ball.position;
    w.Ball.linearVelocity = Picklebot.PlayerAgents.PlayerObservation.ToWorld(velocityStart, team*2);
    w.Ball.angularVelocity = Vector3.zero; w.Ball.WakeUp();
    UnityEngine.Physics.SyncTransforms(); r.Events.Clear(); w.Contacts.Clear(); started = w.Time;
    initialObservations = Enumerable.Range(0, 4).Select(i => Picklebot.PlayerAgents.PlayerObservation.Capture(w, i, 0).values).ToArray();
    tracePath = stem + ".case-" + index.ToString("D3") + ".jsonl";
    trace = new System.IO.StreamWriter(new System.IO.FileStream(tracePath, System.IO.FileMode.CreateNew, System.IO.FileAccess.Write));
    decisions = 0;
    match.Actors.Decided += decision => {
        trace.WriteLine(Newtonsoft.Json.JsonConvert.SerializeObject(new {
            type = "decision", decision.player, tick = decision.observationTick, decision.applyTick,
            observation = decision.observation.values,
            action = new { decision.action.moveX, decision.action.moveZ, decision.action.attempt, decision.action.shot }
        })); decisions++;
        if (mode == 1 && decision.player/2 == team)
        {
            var label = oracle.Policies[decision.player].Action.Validated();
            trace.WriteLine(Newtonsoft.Json.JsonConvert.SerializeObject(new {
                type = "shadow-teacher", decision.player, tick = decision.observationTick,
                action = new { label.moveX, label.moveZ, label.attempt, label.shot }
            }));
        }
    };
}
string Outcome()
{
    var events = match.World.Rules.Events;
    int hit = events.FindIndex(e => e.kind == "hit" && e.player/2 == team);
    if (hit < 0) return match.World.Rules.Dead ? "no hit / " + match.World.Rules.LastFault : "pending";
    foreach (var e in events.Skip(hit+1))
    {
        if (e.kind == "bounce") return (e.position.z < 0 ? 0 : 1) != team ? "legal landing" : "wrong-side bounce";
        if (e.kind == "fault" || e.kind == "late volley fault") return "fault after hit / " + e.fault;
        if (e.kind == "hit") return "intercepted before landing";
    }
    return "pending";
}
void EndCase(string outcome)
{
    var w = match.World;
    trace.Dispose(); trace = null;
    rows.Add(new {
        index, fixture, mode, fixedCanonicalShot = fixedShot, gameSeed = Seed + fixture, candidateTeam = team,
        profile = kitchen ? "kitchen" : "deep", outcome,
        legalHit = w.Rules.Events.Any(e => e.kind == "hit" && e.player/2 == team),
        legalLanding = outcome == "legal landing", fault = w.Rules.LastFault.ToString(),
        completeGame = false, seconds = w.Time-started, ticks = match.Tick, decisions,
        canonicalBall = V(ballStart), canonicalVelocity = V(velocityStart), playerStarts = playerStarts.Select(V).ToArray(),
        initialObservations, tracePath, traceHash = Hash(tracePath),
        metrics = Newtonsoft.Json.Linq.JObject.Parse(UnityEngine.JsonUtility.ToJson(match.Metrics)),
        contacts = w.Contacts.Select(c => new { c.time, c.player, c.surface, point = V(c.point), normal = V(c.normal), velocity = V(c.velocity), spin = V(c.spin) }).ToArray(),
        events = Events()
    });
    match.Dispose(); match = null; index++; Save("running");
}
void TickTeacherGap()
{
    try
    {
        if (!UnityEditor.EditorApplication.isPlaying) throw new System.InvalidOperationException("Play stopped.");
        double until = UnityEditor.EditorApplication.timeSinceStartup + .02;
        while (index < Fixtures*Modes && UnityEditor.EditorApplication.timeSinceStartup < until)
        {
            if (match == null) StartCase();
            oracle.Prepare(match.World); match.Step();
            var w = match.World;
            trace.WriteLine(Newtonsoft.Json.JsonConvert.SerializeObject(new {
                type = "step", tick = match.Tick, time = w.Time, ball = V(w.Ball.position), velocity = V(w.Ball.linearVelocity),
                spin = V(w.Ball.angularVelocity),
                players = w.Players.Select(p => new { position = V(p.Position), velocity = V(p.Velocity),
                    paddle = V(p.Paddle.position), rotation = Q(p.Paddle.rotation), paddleVelocity = V(p.PaddleVelocity),
                    angularVelocity = V(p.AngularVelocity), hand = V(p.Hand), shoulder = V(p.Shoulder) }).ToArray(), events = Events()
            }));
            string outcome = Outcome();
            if (outcome != "pending" || w.Rules.Dead || w.Time-started >= 6)
                EndCase(outcome == "pending" ? "time limit - unresolved" : outcome);
        }
        if (index == Fixtures*Modes)
        {
            if (source != Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash()
                || collectorHash != Hash(collector) || contactHash != Hash(contactPath) || teamsHash != Hash(teamsPath)
                || protocolHash != Hash(protocolPath) || baselineHash != Hash(baselinePath) || actorHash != Hash(actorPath))
                throw new System.InvalidOperationException("Diagnostic inputs changed.");
            UnityEditor.EditorApplication.update -= TickTeacherGap; Save("complete");
        }
    }
    catch (System.Exception error)
    {
        trace?.Dispose(); trace = null; match?.Dispose(); match = null;
        UnityEditor.EditorApplication.update -= TickTeacherGap; Save("failed", error.ToString());
    }
}
Save("running"); UnityEditor.EditorApplication.update += TickTeacherGap;
return stem + ".json";

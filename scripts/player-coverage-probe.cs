// Run through Unity eval_file, in Play mode, after other jobs finish.
// Set SessionState key Picklebot.Coverage.ActorPath to the model path first.
// This is a diagnostic fixture, not a learned controller or final match test.
if (!UnityEditor.EditorApplication.isPlaying
    || Picklebot.PlayerAgents.Editor.PlayerCompetition.Running
    || Picklebot.PlayerAgents.Editor.PlayerCurriculum.Running
    || Picklebot.PlayerAgents.Editor.PlayerEvaluation.Running
    || Picklebot.PlayerAgents.Editor.PlayerTeacher.Running
    || Picklebot.PlayerAgents.Editor.PlayerControlProbe.Running
    || Picklebot.PlayerAgents.Editor.PlayerDiagnostics.Running)
    throw new System.InvalidOperationException("Start Play and finish other jobs first.");
if (UnityEditor.EditorApplication.update.GetInvocationList().Any(d => d.Method.Name.Contains("TickCoverage")))
    throw new System.InvalidOperationException("A coverage callback is already active.");
string actorPath = UnityEditor.SessionState.GetString("Picklebot.Coverage.ActorPath", "");
if (string.IsNullOrEmpty(actorPath)) throw new System.ArgumentException("Set the coverage actor path first.");
var actor = Picklebot.PlayerAgents.PlayerActorModel.Load(System.IO.File.ReadAllText(actorPath));
string source = Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash();
string actorHash = Picklebot.Doubles.Editor.ContactTraining.Hash(System.IO.File.ReadAllText(actorPath));
string scriptHash = Picklebot.Doubles.Editor.ContactTraining.Hash(System.IO.File.ReadAllText("scripts/player-coverage-probe.cs"));
string contactPath = "Assets/Picklebot/Doubles/Models/contact.json";
string contactHash = Picklebot.Doubles.Editor.ContactTraining.Hash(System.IO.File.ReadAllText(contactPath));
string protocolHash = Picklebot.Doubles.Editor.ContactTraining.Hash(System.IO.File.ReadAllText("config/player-agents/evaluation-v1.json"));
if (actor.contactModelHash != contactHash || actor.protocolHash != protocolHash)
    throw new System.InvalidOperationException("Incompatible contact model or protocol.");
var contact = Picklebot.Doubles.ContactModel.Load(System.IO.File.ReadAllText(contactPath));
var teams = Picklebot.Doubles.DoublesModels.Load(System.IO.File.ReadAllText("Assets/Picklebot/Doubles/Models/teams.json"));
string output = "artifacts/player-agents/coverage-" + System.DateTime.UtcNow.ToString("yyyyMMdd-HHmmss") + ".json";
if (System.IO.File.Exists(output)) throw new System.IO.IOException("Coverage output already exists.");
float[] lanes = { -2.6f, -.2f, .2f, 2.6f }, depths = { 3.5f, 6f };
string[] modes = { "learned", "movement_disabled", "diagnostic_teacher" };
var rows = new System.Collections.Generic.List<object>();
var frames = new System.Collections.Generic.List<object>();
var decisions = new System.Collections.Generic.List<object>();
var watch = System.Diagnostics.Stopwatch.StartNew();
Picklebot.PlayerAgents.PlayerMatch match = null;
Picklebot.PlayerAgents.Editor.PlayerOracle oracle = null;
int index = 0, team = 0, mode = 0, ticks = 0;
float started = 0, lane = 0, depth = 0;
bool legalHit = false, legalLanding = false;
float[] movementDistance = new float[4];
UnityEngine.Vector3[] previousPositions = null;
string configurationHash = "";
float[] Vector(UnityEngine.Vector3 p) => new[] { p.x, p.y, p.z };

void StartCoverageCase()
{
    mode = index % 3;
    int fixture = index / 3;
    team = fixture / 8; depth = depths[(fixture / 4) % 2]; lane = lanes[fixture % 4];
    int seed = 1115000 + fixture;
    oracle = mode == 2 ? new Picklebot.PlayerAgents.Editor.PlayerOracle(contact, teams, seed, 0) : null;
    var policies = new Picklebot.PlayerAgents.IPlayerPolicy[4];
    for (int i = 0; i < 4; i++)
        policies[i] = i / 2 != team ? new Picklebot.PlayerAgents.ConstantPlayerPolicy(default)
            : mode == 2 ? oracle.Policies[i] : new Picklebot.PlayerAgents.PlayerActor(actor, false);
    match = new Picklebot.PlayerAgents.PlayerMatch(false, policies, contact, seed) { AutoNext = false };
    var w = match.World; var r = w.Rules;
    configurationHash = w.Configuration.ConfigurationHash;
    if (actor.configurationHash != configurationHash) throw new System.InvalidOperationException("Physics configuration differs.");
    // Establish the public serve-bounce observation with a real drop and floor
    // collision. Do not set private world or rules state through reflection.
    for (int tick = 0; tick < 480 && !w.ServeBounced && !r.Dead; tick++) w.Simulate();
    if (!w.ServeBounced || r.Dead) throw new System.InvalidOperationException("Drop setup failed.");
    // Explicit diagnostic rule fixture: a legal serve and two legal returns.
    r.Serve(0, true, true, true, true, false, false, false, w.Time);
    r.Bounce(new UnityEngine.Vector3(r.ServiceX(r.DesignatedReceiver), 0, 4), w.Time);
    r.Hit(2, w.Time); r.Bounce(new UnityEngine.Vector3(1, 0, -4), w.Time); r.Hit(0, w.Time);
    if (team == 0) r.Hit(2, w.Time);
    if (r.Dead || r.ExpectedTeam != team || r.Phase != Picklebot.Doubles.RallyPhase.Rally)
        throw new System.InvalidOperationException("Invalid coverage rule fixture.");
    for (int i = 0; i < 4; i++)
        w.Players[i].Reset(Picklebot.PlayerAgents.PlayerObservation.ToWorld(
            new UnityEngine.Vector3((i & 1) == 0 ? 1.55f : -1.55f, 0, -(i / 2 == team ? depth : 6f)), i));
    var ball = Picklebot.PlayerAgents.PlayerObservation.ToWorld(new UnityEngine.Vector3(lane, 1.2f, .4f), team * 2);
    w.Ball.position = ball; w.Ball.transform.position = ball;
    w.Ball.linearVelocity = Picklebot.PlayerAgents.PlayerObservation.ToWorld(new UnityEngine.Vector3(0, 1.2f, -8), team * 2);
    w.Ball.angularVelocity = UnityEngine.Vector3.zero; w.Ball.WakeUp();
    UnityEngine.Physics.SyncTransforms();
    r.Events.Clear(); w.Contacts.Clear();
    decisions.Clear();
    match.Actors.Decided += decision => {
        if (decision.player / 2 == team) decisions.Add(new {
            decision.player, decision.observationTick, decision.applyTick,
            requested = new { decision.action.moveX, decision.action.moveZ, decision.action.attempt, decision.action.shot },
            observation = decision.observation.values
        });
    };
    // This ablation changes only the action applied by the decision loop.
    // The same actor still observes its own state and selects hit and shot.
    if (mode == 1) match.Actors.Decided += decision => { decision.action.moveX = 0; decision.action.moveZ = 0; };
    ticks = 0; started = w.Time; legalHit = legalLanding = false;
    movementDistance = new float[4]; previousPositions = w.Players.Select(p => p.Position).ToArray();
    frames.Clear();
}

void SaveCoverage(string status, string error = null)
{
    var report = new {
        status, error, createdUtc = System.DateTime.UtcNow.ToString("O"), sourceHash = source,
        actorPath, actorHash, actorTrainingSourceHash = actor.sourceHash, historicalCandidate = actor.sourceHash != source,
        scriptHash, contactModelHash = contactHash, protocolHash, configurationHash,
        fixtureVersion = "coverage-development-v1", split = "development", seedBase = 1115000,
        lanes, depths, physicsHz = 240, decisionTicks = 12, actionLatencyTicks = 6,
        incomingCanonicalPosition = new[] { 0f, 1.2f, .4f }, incomingCanonicalVelocity = new[] { 0f, 1.2f, -8f },
        wallSeconds = watch.Elapsed.TotalSeconds, cases = rows.ToArray(),
        limit = "Injected incoming-ball diagnostic. Opponents stand still. The teacher is privileged and is not an exported actor. Not a final match test. Physics is provisional."
    };
    System.IO.File.WriteAllText(output, Newtonsoft.Json.JsonConvert.SerializeObject(report, Newtonsoft.Json.Formatting.Indented));
    UnityEditor.SessionState.SetString("Picklebot.Coverage.Status", status + ": " + output);
}

void EndCoverageCase()
{
    var w = match.World;
    rows.Add(new {
        mode = modes[mode], seed = 1115000 + index / 3, candidateTeam = team, lane, depth,
        legalHit, legalLanding, fault = w.Rules.LastFault.ToString(), elapsedSeconds = w.Time - started,
        actorDecisions = match.Actors.Decisions, movementDistance,
        metrics = Newtonsoft.Json.Linq.JObject.Parse(UnityEngine.JsonUtility.ToJson(match.Metrics)),
        events = w.Rules.Events.Select(e => new { e.kind, e.player, e.winner, fault = e.fault.ToString(), time = e.time - started, position = Vector(e.position) }).ToArray(),
        contacts = w.Contacts.Select(c => new { c.player, c.surface, time = c.time - started, point = Vector(c.point), incoming = Vector(c.incoming), velocity = Vector(c.velocity) }).ToArray(),
        frames = frames.ToArray(), decisions = decisions.ToArray()
    });
    match.Dispose(); match = null; index++;
    UnityEditor.SessionState.SetString("Picklebot.Coverage.Status", "running: " + index + "/48 cases; " + output);
}

void TickCoverage()
{
    try
    {
        if (!UnityEditor.EditorApplication.isPlaying) throw new System.InvalidOperationException("Play stopped during coverage.");
        double until = UnityEditor.EditorApplication.timeSinceStartup + .02;
        while (index < 48 && UnityEditor.EditorApplication.timeSinceStartup < until)
        {
            if (match == null) StartCoverageCase();
            oracle?.Prepare(match.World); match.Step(); ticks++;
            var w = match.World;
            for (int i = 0; i < 4; i++)
            { movementDistance[i] += UnityEngine.Vector3.Distance(previousPositions[i], w.Players[i].Position); previousPositions[i] = w.Players[i].Position; }
            if (ticks % 12 == 0) frames.Add(new {
                time = w.Time - started, ball = Vector(w.Ball.position), players = w.Players.Select(p => Vector(p.Position)).ToArray(),
                paddles = w.Players.Select(p => Vector(p.Paddle.position)).ToArray(),
                plans = match.Swings.Select(s => new { s.Contact.Planned, impactAt = s.Contact.ImpactAt - started, impact = Vector(s.Contact.Impact), s.SelectedShot }).ToArray()
            });
            legalHit = w.Rules.Events.Any(e => e.kind == "hit" && e.player / 2 == team);
            legalLanding = legalHit && w.Rules.Events.Any(e => e.kind == "bounce" && (e.position.z < 0 ? 0 : 1) != team);
            if (legalLanding || w.Rules.Dead || w.Time - started >= 8f) EndCoverageCase();
        }
        if (index == 48)
        {
            if (source != Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash()
                || scriptHash != Picklebot.Doubles.Editor.ContactTraining.Hash(System.IO.File.ReadAllText("scripts/player-coverage-probe.cs")))
                throw new System.InvalidOperationException("Source changed during coverage.");
            UnityEditor.EditorApplication.update -= TickCoverage; SaveCoverage("complete");
        }
    }
    catch (System.Exception error)
    { UnityEditor.EditorApplication.update -= TickCoverage; match?.Dispose(); match = null; SaveCoverage("failed", error.ToString()); }
}
UnityEditor.SessionState.SetString("Picklebot.Coverage.Status", "running: 0/48 cases; " + output);
UnityEditor.EditorApplication.update += TickCoverage;
return output;

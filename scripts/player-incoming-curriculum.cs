// Run with Unity eval_file. SessionState keys use the Picklebot.Incoming prefix.
// This collector injects initial ball states. It is not a match evaluation.
if (!UnityEditor.EditorApplication.isPlaying
    || Picklebot.PlayerAgents.Editor.PlayerCompetition.Running || Picklebot.PlayerAgents.Editor.PlayerCurriculum.Running
    || Picklebot.PlayerAgents.Editor.PlayerEvaluation.Running || Picklebot.PlayerAgents.Editor.PlayerTeacher.Running
    || Picklebot.PlayerAgents.Editor.PlayerControlProbe.Running || Picklebot.PlayerAgents.Editor.PlayerDiagnostics.Running
    || UnityEditor.EditorApplication.update.GetInvocationList().Any(d => d.Method.Name.Contains("TickIncoming") || d.Method.Name.Contains("TickCoverage")
        || d.Method.Name.Contains("TickFinal") || d.Method.Name.Contains("TickContact") || d.Method.Name.Contains("TickKitchenContact")
        || d.Method.Name.Contains("TickMixedPartner")))
    throw new System.InvalidOperationException("Start Play and finish other jobs first.");
bool development = UnityEditor.SessionState.GetBool("Picklebot.Incoming.Development", false);
int seedBase = UnityEditor.SessionState.GetInt("Picklebot.Incoming.Seed", development ? 1121000 : 1015000);
int wanted = UnityEditor.SessionState.GetInt("Picklebot.Incoming.Episodes", 320);
float teacherProbability = UnityEditor.SessionState.GetFloat("Picklebot.Incoming.TeacherProbability", 1f);
string actorPath = UnityEditor.SessionState.GetString("Picklebot.Incoming.ActorPath", "");
string skillProfile = UnityEditor.SessionState.GetString("Picklebot.Incoming.Profile", "deep");
if (skillProfile != "deep" && skillProfile != "kitchen")
    throw new System.ArgumentException("Incoming profile must be deep or kitchen.");
bool kitchen = skillProfile == "kitchen";
float laneExtent = kitchen ? 2f : 2.7f;
float minimumDepth = kitchen ? 1.8f : 3.4f, maximumDepth = kitchen ? 3.2f : 6.6f;
float minimumIncomingSpeed = kitchen ? -3.6f : -8.7f, maximumIncomingSpeed = kitchen ? -2.7f : -7.3f;
int lower = development ? 1100000 : 1000000;
if (wanted < 2 || wanted > 4096 || (wanted & 1) != 0 || seedBase < lower || seedBase + wanted >= lower + 100000
    || !float.IsFinite(teacherProbability) || teacherProbability < 0 || teacherProbability > 1)
    throw new System.ArgumentException("Invalid skill curriculum size, split, or mixture.");
var actor = string.IsNullOrEmpty(actorPath) ? null : Picklebot.PlayerAgents.PlayerActorModel.Load(System.IO.File.ReadAllText(actorPath));
if (actor == null && teacherProbability != 1) throw new System.ArgumentException("A mixture requires a saved actor.");
string Hash(string path) => Picklebot.Doubles.Editor.ContactTraining.Hash(System.IO.File.ReadAllText(path));
string source = Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash();
string contactPath = "Assets/Picklebot/Doubles/Models/contact.json", teamsPath = "Assets/Picklebot/Doubles/Models/teams.json";
string contactHash = Hash(contactPath), teamHash = Hash(teamsPath), protocolHash = Hash("config/player-agents/evaluation-v1.json");
string baselineHash = Hash("artifacts/player-agents/baseline-manifest.json");
string actorHash = actor == null ? "none" : Hash(actorPath);
if (actor != null && (actor.sourceHash != source || actor.contactModelHash != contactHash || actor.protocolHash != protocolHash))
    throw new System.InvalidOperationException("Use a current-source actor with matching contact and evaluation settings.");
var contact = Picklebot.Doubles.ContactModel.Load(System.IO.File.ReadAllText(contactPath));
var teams = Picklebot.Doubles.DoublesModels.Load(System.IO.File.ReadAllText(teamsPath));
string collectorPath = "scripts/player-incoming-curriculum.cs", collectorHash = Hash(collectorPath);
string stem = "artifacts/player-agents/incoming-" + System.DateTime.UtcNow.ToString("yyyyMMdd-HHmmss");
string output = stem + ".json", dataPath = stem + ".jsonl", collectorSnapshotPath = stem + ".collector.cs";
if (System.IO.File.Exists(output) || System.IO.File.Exists(dataPath) || System.IO.File.Exists(collectorSnapshotPath))
    throw new System.IO.IOException("Output already exists.");
System.IO.File.Copy(collectorPath, collectorSnapshotPath);
var writer = new System.IO.StreamWriter(new System.IO.FileStream(dataPath, System.IO.FileMode.CreateNew, System.IO.FileAccess.Write));
var watch = System.Diagnostics.Stopwatch.StartNew();
var results = new System.Collections.Generic.List<object>();
Picklebot.PlayerAgents.PlayerMatch match = null;
Picklebot.PlayerAgents.Editor.PlayerOracle oracle = null;
int index = 0, team = 0, rows = 0, teacherDecisions = 0, actorDecisions = 0;
float started = 0;
bool legalKitchenGroundstroke = false;
string configurationHash = "";
UnityEngine.Vector3 ballStart = default, velocityStart = default;
UnityEngine.Vector3[] playerStarts = null;
float[] V(UnityEngine.Vector3 p) => new[] { p.x, p.y, p.z };

void SaveIncoming(string status, string error = null)
{
    writer?.Flush();
    var report = new {
        status, error, createdUtc = System.DateTime.UtcNow.ToString("O"), sourceHash = source, configurationHash,
        contactModelHash = contactHash, teamModelHash = teamHash, protocolHash, baselineManifestHash = baselineHash,
        collectorHash, collectorSnapshotPath, fixtureVersion = "incoming-skill-v1", skillProfile, dataPath,
        actorHash, actorTrainingSourceHash = actor?.sourceHash ?? "none", teacherProbability, fixedShot = 0,
        split = development ? "development" : "training", seed = seedBase, rows, rallies = index, games = 0,
        requestedFixtures = wanted, teacherDecisions, actorDecisions, candidateOnly = true,
        baselineOpponent = false, initialCandidateTeam = 0, opponentMode = "stationary receivers; injected skill reset",
        physicsHz = 240, decisionTicks = 12, actionLatencyTicks = 6, maximumFixtureSeconds = 6f,
        ranges = new { lane = new[] { -laneExtent, laneExtent }, height = new[] { 1.1f, 1.5f }, ballDepth = new[] { .15f, .7f },
            velocityX = new[] { -.8f, .8f }, velocityY = new[] { .8f, 1.8f }, velocityZ = new[] { minimumIncomingSpeed, maximumIncomingSpeed },
            playerDepth = new[] { minimumDepth, maximumDepth }, playerXJitter = new[] { -.35f, .35f } },
        method = "privileged teacher labels on randomized incoming-ball skill states; optional actor mixture; no match-win reward",
        wallSeconds = watch.Elapsed.TotalSeconds, gameResults = results.ToArray(),
        limits = "Injected initial state, not a played serve or completed game. No actor sees a future intercept. Physics is provisional."
    };
    System.IO.File.WriteAllText(output, Newtonsoft.Json.JsonConvert.SerializeObject(report, Newtonsoft.Json.Formatting.Indented));
    UnityEditor.SessionState.SetString("Picklebot.Incoming.Status", status + ": " + index + "/" + wanted + "; " + output);
}

void StartIncoming()
{
    int seed = seedBase + index; team = index & 1;
    var fixtureRandom = new System.Random(seed);
    float Range(float a, float b) => a + (b - a) * (float)fixtureRandom.NextDouble();
    var mixtureRandom = Enumerable.Range(0, 4).Select(i => new System.Random(unchecked(seed * 397 + i * 7919))).ToArray();
    oracle = new Picklebot.PlayerAgents.Editor.PlayerOracle(contact, teams, seed, 0);
    var policies = Enumerable.Range(0, 4).Select(i => i / 2 != team
        ? (Picklebot.PlayerAgents.IPlayerPolicy)new Picklebot.PlayerAgents.ConstantPlayerPolicy(default)
        : actor == null ? oracle.Policies[i] : new Picklebot.PlayerAgents.PlayerActor(actor, false)).ToArray();
    match = new Picklebot.PlayerAgents.PlayerMatch(false, policies, contact, seed) { AutoNext = false };
    var w = match.World; var r = w.Rules;
    configurationHash = w.Configuration.ConfigurationHash;
    if (actor != null && actor.configurationHash != configurationHash) throw new System.InvalidOperationException("Actor physics mismatch.");
    for (int tick = 0; tick < 480 && !w.ServeBounced && !r.Dead; tick++) w.Simulate();
    if (!w.ServeBounced || r.Dead) throw new System.InvalidOperationException("Drop setup failed.");
    r.Serve(0, true, true, true, true, false, false, false, w.Time);
    r.Bounce(new UnityEngine.Vector3(r.ServiceX(r.DesignatedReceiver), 0, 4), w.Time);
    r.Hit(2, w.Time); r.Bounce(new UnityEngine.Vector3(1, 0, -4), w.Time); r.Hit(0, w.Time);
    if (team == 0) r.Hit(2, w.Time);
    if (r.Dead || r.ExpectedTeam != team || r.Phase != Picklebot.Doubles.RallyPhase.Rally)
        throw new System.InvalidOperationException("Invalid injected rule fixture.");
    for (int i = 0; i < 4; i++)
    {
        float x = ((i & 1) == 0 ? 1.55f : -1.55f) + (i / 2 == team ? Range(-.35f, .35f) : 0);
        float depth = i / 2 == team ? Range(minimumDepth, maximumDepth) : 6f;
        w.Players[i].Reset(Picklebot.PlayerAgents.PlayerObservation.ToWorld(new UnityEngine.Vector3(x, 0, -depth), i));
    }
    playerStarts = w.Players.Select(p => p.Position).ToArray();
    ballStart = new UnityEngine.Vector3(Range(-laneExtent, laneExtent), Range(1.1f, 1.5f), Range(.15f, .7f));
    velocityStart = new UnityEngine.Vector3(Range(-.8f, .8f), Range(.8f, 1.8f), Range(minimumIncomingSpeed, maximumIncomingSpeed));
    w.Ball.position = Picklebot.PlayerAgents.PlayerObservation.ToWorld(ballStart, team * 2); w.Ball.transform.position = w.Ball.position;
    w.Ball.linearVelocity = Picklebot.PlayerAgents.PlayerObservation.ToWorld(velocityStart, team * 2);
    w.Ball.angularVelocity = UnityEngine.Vector3.zero; w.Ball.WakeUp();
    UnityEngine.Physics.SyncTransforms(); r.Events.Clear(); w.Contacts.Clear(); started = w.Time;
    legalKitchenGroundstroke = false;
    match.Actors.Decided += decision => {
        if (decision.player / 2 != team) return;
        var label = oracle.Policies[decision.player].Action.Validated();
        bool teacher = actor == null || mixtureRandom[decision.player].NextDouble() < teacherProbability;
        if (teacher) { decision.action = label; teacherDecisions++; } else actorDecisions++;
        writer.WriteLine(Newtonsoft.Json.JsonConvert.SerializeObject(new {
            gameSeed = seed, rally = 0, candidateTeam = team, player = decision.player, tick = decision.observationTick,
            observation = decision.observation.values, action = new { label.moveX, label.moveZ, label.attempt, label.shot },
            appliedAction = new { decision.action.moveX, decision.action.moveZ, decision.action.attempt, decision.action.shot },
            executedBy = teacher ? "teacher" : "actor"
        })); rows++;
    };
}

void EndIncoming(bool legalHit, bool legalLanding)
{
    var w = match.World;
    results.Add(new { gameSeed = seedBase + index, candidateTeam = team, complete = false, winner = -1, rallies = 1,
        reason = "injected incoming-ball skill fixture; not a completed game", legalHit, legalLanding, legalKitchenGroundstroke,
        fault = w.Rules.LastFault.ToString(), seconds = w.Time - started, canonicalBall = V(ballStart), canonicalVelocity = V(velocityStart),
        playerStarts = playerStarts.Select(V).ToArray(),
        metrics = Newtonsoft.Json.Linq.JObject.Parse(UnityEngine.JsonUtility.ToJson(match.Metrics)),
        contacts = w.Contacts.Select(c => new { c.player, c.surface, point = V(c.point), velocity = V(c.velocity) }).ToArray(),
        events = w.Rules.Events.Select(e => new { e.kind, e.player, position = V(e.position), fault = e.fault.ToString() }).ToArray() });
    match.Dispose(); match = null; index++;
    UnityEditor.SessionState.SetString("Picklebot.Incoming.Status", "running: " + index + "/" + wanted + "; rows " + rows + "; " + output);
}

void TickIncoming()
{
    try
    {
        if (!UnityEditor.EditorApplication.isPlaying) throw new System.InvalidOperationException("Play stopped during incoming curriculum.");
        double until = UnityEditor.EditorApplication.timeSinceStartup + .02;
        while (index < wanted && UnityEditor.EditorApplication.timeSinceStartup < until)
        {
            if (match == null) StartIncoming();
            oracle.Prepare(match.World); match.Step();
            var w = match.World;
            bool hit = w.Rules.Events.Any(e => e.kind == "hit" && e.player / 2 == team);
            // Read feet at the contact step, not later at the landing step.
            foreach (var e in w.Rules.Events.Where(e => e.kind == "hit" && e.player / 2 == team && e.time == w.Time))
                legalKitchenGroundstroke |= w.Players[e.player].FeetInKitchen
                    && w.Rules.Events.TakeWhile(previous => previous != e).Any(previous => previous.kind == "bounce");
            bool landing = hit && w.Rules.Events.Any(e => e.kind == "bounce" && (e.position.z < 0 ? 0 : 1) != team);
            if (landing || w.Rules.Dead || w.Time - started >= 6f) EndIncoming(hit, landing);
        }
        if (index == wanted)
        {
            if (source != Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash() || collectorHash != Hash(collectorPath))
                throw new System.InvalidOperationException("Runtime or collector source changed during collection.");
            UnityEditor.EditorApplication.update -= TickIncoming; SaveIncoming("complete"); writer.Dispose(); writer = null;
        }
    }
    catch (System.Exception error)
    {
        UnityEditor.EditorApplication.update -= TickIncoming; match?.Dispose(); match = null;
        SaveIncoming("failed", error.ToString()); writer?.Dispose(); writer = null;
    }
}
SaveIncoming("running"); UnityEditor.EditorApplication.update += TickIncoming;
return output;

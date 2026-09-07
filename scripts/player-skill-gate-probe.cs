// Diagnostic only. Repeat sampled teacher versus a learned player-local frozen-expert selector.
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
string collector = "scripts/player-skill-gate-probe.cs";
string contactPath = "Assets/Picklebot/Doubles/Models/contact.json", teamsPath = "Assets/Picklebot/Doubles/Models/teams.json";
string protocolPath = "config/player-agents/evaluation-v1.json", baselinePath = "artifacts/player-agents/baseline-manifest.json";
string collectorHash = Hash(collector), contactHash = Hash(contactPath), teamsHash = Hash(teamsPath);
string protocolHash = Hash(protocolPath), baselineHash = Hash(baselinePath);
var manifest = Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(baselinePath));
foreach (var file in ((Newtonsoft.Json.Linq.JObject)manifest["files"]).Properties())
    if (Hash(file.Name) != (string)file.Value) throw new System.InvalidOperationException("Frozen baseline changed.");
var contact = Picklebot.Doubles.ContactModel.Load(System.IO.File.ReadAllText(contactPath));
var teams = Picklebot.Doubles.DoublesModels.Load(System.IO.File.ReadAllText(teamsPath));
string gatePath = UnityEditor.SessionState.GetString("Picklebot.SkillGate.Path", "");
if (string.IsNullOrEmpty(gatePath)) throw new System.InvalidOperationException("Select an experimental gate first.");
string gateHash = Hash(gatePath);
var gateMeta = Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(gatePath));
if ((string)gateMeta["version"] != "player-skill-gate-v1"
    || (string)gateMeta["observationVersion"] != "player-observation-v1"
    || (string)gateMeta["sourceHash"] != source || (int)gateMeta["trainingSteps"] <= 0
    || (float)gateMeta["threshold"] != 0
    || !gateMeta["maskedIndices"].ToObject<int[]>().SequenceEqual(Enumerable.Range(25, 12))
    || (string)gateMeta["contactModelHash"] != contactHash || (string)gateMeta["protocolHash"] != protocolHash
    || (string)gateMeta["baselineManifestHash"] != baselineHash)
    throw new System.InvalidOperationException("Gate schema or provenance mismatch.");
var gateLayers = gateMeta["layers"].ToObject<Picklebot.PlayerAgents.ActorLayer[]>();
if (gateLayers.Length != 2) throw new System.InvalidOperationException("Expected 54-32-1 gate.");
for (int n = 0; n < 2; n++)
{
    var l = gateLayers[n]; int ni = n == 0 ? 54 : 32, no = n == 0 ? 32 : 1;
    if (l.inputs != ni || l.outputs != no || l.weights.Length != ni*no || l.bias.Length != no
        || l.weights.Any(v => !float.IsFinite(v)) || l.bias.Any(v => !float.IsFinite(v)))
        throw new System.InvalidOperationException("Gate tensor mismatch.");
}
float GateForward(float[] observation)
{
    if (observation.Length != 54 || observation.Any(v => !float.IsFinite(v)))
        throw new System.InvalidOperationException("Gate needs this player's own finite observations.");
    var values = (float[])observation.Clone();
    for (int i = 25; i < 37; i++) values[i] = 0;
    for (int n = 0; n < 2; n++)
    {
        var l = gateLayers[n]; var next = new float[l.outputs];
        for (int o = 0; o < l.outputs; o++)
        {
            float sum = l.bias[o];
            for (int i = 0; i < l.inputs; i++) sum += l.weights[o*l.inputs+i]*values[i];
            next[o] = n == 0 ? (float)System.Math.Tanh(sum) : sum;
            if (!float.IsFinite(next[o])) throw new System.InvalidOperationException("Non-finite gate output.");
        }
        values = next;
    }
    return values[0];
}
var expertMeta = (Newtonsoft.Json.Linq.JArray)gateMeta["experts"];
if (expertMeta.Count != 2 || (string)expertMeta[0]["role"] != "older" || (string)expertMeta[1]["role"] != "short-return")
    throw new System.InvalidOperationException("Expert order mismatch.");
string actorPath = (string)expertMeta[0]["path"], shortActorPath = (string)expertMeta[1]["path"];
string shortActorHash = Hash(shortActorPath);
var shortActor = Picklebot.PlayerAgents.PlayerActorModel.Load(System.IO.File.ReadAllText(shortActorPath));
for (int e = 0; e < 2; e++)
{
    string path = (string)expertMeta[e]["path"];
    if (Hash(path) != (string)expertMeta[e]["sha256"]) throw new System.InvalidOperationException("Frozen expert changed.");
    var meta = Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(path));
    foreach (string key in new[] { "configurationHash", "contactModelHash", "protocolHash", "baselineManifestHash" })
        if ((string)meta[key] != (string)gateMeta[key]) throw new System.InvalidOperationException("Expert provenance mismatch.");
    if ((string)meta["sourceHash"] != (string)expertMeta[e]["trainingSourceHash"])
        throw new System.InvalidOperationException("Expert source mismatch.");
}
var shortPolicies = Enumerable.Range(0, 4).Select(i => new Picklebot.PlayerAgents.PlayerActor(shortActor, false)).ToArray();
var shortRandom = Enumerable.Range(0, 4).Select(i => new System.Random(Seed*397+i*7919)).ToArray();
string actorHash = Hash(actorPath);
var actor = Picklebot.PlayerAgents.PlayerActorModel.Load(System.IO.File.ReadAllText(actorPath));
var actorMeta = Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(actorPath));
if (actor.trainingSteps <= 0 || actor.contactModelHash != contactHash || actor.protocolHash != protocolHash
    || (string)actorMeta["baselineManifestHash"] != baselineHash)
    throw new System.InvalidOperationException("Actor provenance mismatch.");
// Check the cross-language gate and selected-expert output before simulating.
string parityPath = System.IO.Path.Combine(System.IO.Path.GetDirectoryName(gatePath), "parity.json");
string parityHash = Hash(parityPath);
var parity = Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(parityPath));
int parityCases = ((Newtonsoft.Json.Linq.JArray)parity["observations"]).Count;
if (parityCases != 48) throw new System.InvalidOperationException("Expected 48 parity cases.");
float parityMaxError = 0;
for (int i = 0; i < parityCases; i++)
{
    var obs = parity["observations"][i].ToObject<float[]>();
    float logit = GateForward(obs); int chosen = logit >= 0 ? 1 : 0;
    float error = Mathf.Abs(logit-(float)parity["logits"][i]);
    if (chosen != (int)parity["choices"][i]) throw new System.InvalidOperationException("Gate choice parity failed.");
    var actual = (chosen == 1 ? shortActor : actor).Forward(obs);
    var expected = parity["outputs"][i].ToObject<float[]>();
    if (actual.Length != expected.Length) throw new System.InvalidOperationException("Expert output parity shape.");
    for (int j = 0; j < actual.Length; j++) error = Mathf.Max(error, Mathf.Abs(actual[j]-expected[j]));
    if (error > .0001f) throw new System.InvalidOperationException("Selector parity failed: " + error);
    parityMaxError = Mathf.Max(parityMaxError, error);
}
// Older runtime expert weights are explicitly retained; no weights are modified.
bool historicalCandidate = actor.sourceHash != source;
string stem = "artifacts/player-agents/skill-gate-probe-" + System.DateTime.UtcNow.ToString("yyyyMMdd-HHmmss");
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
        version = "player-skill-gate-probe-v1", status, error, split = "development-diagnostic",
        sourceHash = source, configurationHash, collectorHash, collectorSnapshotPath = stem + ".collector.cs",
        contactPath, contactHash, teamsPath, teamsHash, protocolPath, protocolHash, baselinePath, baselineHash,
        actorPath, actorHash, actorTrainingSourceHash = actor.sourceHash, historicalCandidate, sampledActor = false,
        gatePath, gateHash, shortActorPath, shortActorHash, parityPath, parityHash, parityCases, parityMaxError,
        fixtures = Fixtures, modes = Modes, seedBase = Seed, expectedCases = Fixtures * Modes,
        physicsHz = 240, decisionTicks = 12, actionLatencyTicks = 6, maximumSeconds = 6,
        modeSchedule = "0 sampled teacher control; 1 own-observation learned selector over frozen deterministic experts",
        fixtureSchedule = "16 deep followed by 16 kitchen; alternating candidate team",
        wallSeconds = watch.Elapsed.TotalSeconds, rows,
        limitation = "Injected incoming fixtures, not completed games. All colliders stay enabled. "
            + "Mode zero uses privileged teacher movement and hitter selection. Mode one uses four separate "
            + "policy objects, with candidate actions selected by a learned gate from their own observations. "
            + "The actorPath field identifies only the older expert, not the complete candidate. "
            + "The selector is profile-supervised, not trained for game wins. Opponents use constant leave actions. "
            + "Diagnostic shadow teacher labels never replace actor actions and are development-only, not training data. "
            + "This measures skill transfer on matched starts, not team-game-win strength."
    }, Newtonsoft.Json.Formatting.Indented));
    UnityEditor.SessionState.SetString("Picklebot.SkillGate.Status", status + ": " + index + "/64; " + stem + ".json");
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
    if (actor.configurationHash != configurationHash || (string)gateMeta["configurationHash"] != configurationHash) throw new System.InvalidOperationException("Actor physics mismatch.");
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
        if (mode == 1 && decision.player/2 == team)
        {
            float gateLogit = GateForward(decision.observation.values);
            int selectedExpert = gateLogit >= 0 ? 1 : 0;
            if (selectedExpert == 1)
                decision.action = shortPolicies[decision.player].Decide(decision.observation.Copy(), shortRandom[decision.player]).Validated();
            decision.trace = null; // This is a composite decision, not the older expert's PPO sample.
            trace.WriteLine(Newtonsoft.Json.JsonConvert.SerializeObject(new {
                type = "decision", decision.player, tick = decision.observationTick, decision.applyTick,
                observation = decision.observation.values, gateLogit, selectedExpert,
                action = new { decision.action.moveX, decision.action.moveZ, decision.action.attempt, decision.action.shot }
            }));
        }
        else
        {
        trace.WriteLine(Newtonsoft.Json.JsonConvert.SerializeObject(new {
            type = "decision", decision.player, tick = decision.observationTick, decision.applyTick,
            observation = decision.observation.values,
            action = new { decision.action.moveX, decision.action.moveZ, decision.action.attempt, decision.action.shot }
        }));
        }
        decisions++;
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
void TickSkillGate()
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
                || protocolHash != Hash(protocolPath) || baselineHash != Hash(baselinePath) || actorHash != Hash(actorPath)
                || gateHash != Hash(gatePath) || shortActorHash != Hash(shortActorPath) || parityHash != Hash(parityPath))
                throw new System.InvalidOperationException("Diagnostic inputs changed.");
            UnityEditor.EditorApplication.update -= TickSkillGate; Save("complete");
        }
    }
    catch (System.Exception error)
    {
        trace?.Dispose(); trace = null; match?.Dispose(); match = null;
        UnityEditor.EditorApplication.update -= TickSkillGate; Save("failed", error.ToString());
    }
}
Save("running"); UnityEditor.EditorApplication.update += TickSkillGate;
return stem + ".json";

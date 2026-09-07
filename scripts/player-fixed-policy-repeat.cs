// Unity eval_file: repeat one DEVELOPMENT game with a fixed single-player policy.
// No selector, training, contact correction, or runtime asset changes.
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
const int seed = 1141000, repeats = 3;
string source = Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash();
string collectorPath = "scripts/player-fixed-policy-repeat.cs";
string actorPath = "artifacts/player-agents/ppo-20260907-032230/actor.json";
string contactPath = "Assets/Picklebot/Doubles/Models/contact.json";
string opponentPath = "Assets/Picklebot/Doubles/Models/teams.json";
string protocolPath = "config/player-agents/evaluation-v1.json";
string baselinePath = "artifacts/player-agents/baseline-manifest.json";
var paths = new[] { collectorPath, actorPath, contactPath, opponentPath, protocolPath, baselinePath };
var hashes = paths.ToDictionary(p => p, p => Hash(p));
var manifest = Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(baselinePath));
foreach (var entry in ((Newtonsoft.Json.Linq.JObject)manifest["files"]).Properties())
    if (Hash(entry.Name) != (string)entry.Value) throw new System.InvalidOperationException("Baseline changed: " + entry.Name);
var actor = Picklebot.PlayerAgents.PlayerActorModel.Load(System.IO.File.ReadAllText(actorPath));
var metadata = Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(actorPath));
var protocol = Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(protocolPath));
if (seed < 1100000 || seed >= 1200000 || actor.trainingSteps <= 0
    || actor.contactModelHash != hashes[contactPath] || actor.protocolHash != hashes[protocolPath]
    || (string)metadata["baselineManifestHash"] != hashes[baselinePath])
    throw new System.InvalidOperationException("Development seed or model provenance mismatch.");
string folder = "artifacts/player-agents/fixed-policy-repeat-" + System.DateTime.UtcNow.ToString("yyyyMMdd-HHmmss");
if (System.IO.Directory.Exists(folder)) throw new System.IO.IOException("Output already exists.");
System.IO.Directory.CreateDirectory(folder);
System.IO.File.Copy(collectorPath, folder + "/collector.cs");
var plan = new {
    version = "player-fixed-policy-repeat-v1", createdUtc = System.DateTime.UtcNow.ToString("O"),
    split = "development-diagnostic", seed, repeats, candidateTeam = 0, sampledActor = false, sampledBaseline = false,
    sourceHash = source, actorTrainingSourceHash = actor.sourceHash, hashes,
    identityBySeat = new[] { 0, 1, 2, 3 }, physicsHz = 240, decisionTicks = 12, latencyTicks = 6,
    tickBudgetSeconds = .02, rallyTimeLimitSeconds = 30, rallyResolutionLimitSeconds = 35,
    maxRallies = (int)protocol["gameSafetyMaximumRallies"], maxGameSeconds = (double)protocol["gameSafetyMaximumSimulatedSeconds"],
    limitation = "Fixed-policy repeatability diagnosis only. Same seed deliberately repeated. No selection, training, final evaluation, or promotion. Baseline retains its disclosed controller limits. Trace observes public state, not all internal PhysX state."
};
string planPath = folder + "/plan.json";
System.IO.File.WriteAllText(planPath, Newtonsoft.Json.JsonConvert.SerializeObject(plan, Newtonsoft.Json.Formatting.Indented));
string planHash = Hash(planPath);
Picklebot.PlayerAgents.PlayerMatch match = null;
System.IO.StreamWriter trace = null, decisions = null;
int run = 0, completed = 0, steps = 0, decisionCount = 0;
double gameSeconds = 0;
System.Random serveRandom = null;
var watch = System.Diagnostics.Stopwatch.StartNew();
var reports = new System.Collections.Generic.List<object>();
var rallies = new System.Collections.Generic.List<object>();
float[] V(UnityEngine.Vector3 p) => new[] { p.x, p.y, p.z };
float[] Q(UnityEngine.Quaternion p) => new[] { p.x, p.y, p.z, p.w };
object State() => new {
    rally = completed, tick = match.Tick, time = match.World.Time,
    ball = new { position = V(match.World.Ball.position), velocity = V(match.World.Ball.linearVelocity),
        spin = V(match.World.Ball.angularVelocity), rotation = Q(match.World.Ball.rotation), sleeping = match.World.Ball.IsSleeping() },
    players = match.World.Players.Select((p, i) => new {
        player = i, position = V(p.Position), velocity = V(p.Velocity), paddle = V(p.Paddle.position),
        rotation = Q(p.Paddle.rotation), paddleVelocity = V(p.PaddleVelocity), angularVelocity = V(p.AngularVelocity),
        shoulder = V(p.Shoulder), hand = V(p.Hand), leftFoot = V(p.LeftFoot), rightFoot = V(p.RightFoot),
        action = match.Actors.ActionFor(i)
    }).ToArray(),
    baseline = new { match.Baseline.ActivePlayer, match.Baseline.LastShot,
        target = new[] { match.Baseline.Target.x, match.Baseline.Target.y },
        strokes = match.Baseline.Strokes.Select(s => new { s.Planned, impact = V(s.Impact), s.ImpactAt, normal = V(s.Normal), s.Swing, kind = s.Kind.ToString() }).ToArray() },
    rules = new { phase = match.World.Rules.Phase.ToString(), match.World.Rules.Hits, match.World.Rules.Dead,
        match.World.Rules.Winner, match.World.Rules.GameWinner, match.World.Rules.Server, match.World.Rules.ExpectedTeam,
        score = (int[])match.World.Rules.Score.Clone(), fault = match.World.Rules.LastFault.ToString() }
};
void Jitter() => match.ServeJitter = new UnityEngine.Vector2((float)(serveRandom.NextDouble()*.6-.3), (float)(serveRandom.NextDouble()*.8-.4));
void Start()
{
    var contact = Picklebot.Doubles.ContactModel.Load(System.IO.File.ReadAllText(contactPath));
    var opponentContact = Picklebot.Doubles.ContactModel.Load(System.IO.File.ReadAllText(contactPath));
    var opponent = Picklebot.Doubles.DoublesModels.Load(System.IO.File.ReadAllText(opponentPath));
    var policies = Enumerable.Range(0, 4).Select(i => i < 2
        ? (Picklebot.PlayerAgents.IPlayerPolicy)new Picklebot.PlayerAgents.PlayerActor(actor, false)
        : new Picklebot.PlayerAgents.ConstantPlayerPolicy(default)).ToArray();
    match = new Picklebot.PlayerAgents.PlayerMatch(false, policies, contact, seed,
        new Picklebot.PlayerAgents.BaselineControl(2, opponent, opponentContact, seed, false)) { AutoNext = false };
    if (match.World.Configuration.ConfigurationHash != actor.configurationHash)
        throw new System.InvalidOperationException("Physics configuration mismatch.");
    completed = 0; steps = 0; decisionCount = 0; gameSeconds = 0; rallies.Clear();
    trace = new System.IO.StreamWriter(new System.IO.Compression.GZipStream(
        new System.IO.FileStream(folder + "/run-" + run + ".steps.jsonl.gz", System.IO.FileMode.CreateNew), System.IO.Compression.CompressionLevel.Fastest));
    decisions = new System.IO.StreamWriter(new System.IO.FileStream(folder + "/run-" + run + ".decisions.jsonl", System.IO.FileMode.CreateNew));
    match.Actors.Decided += d => {
        if (d.player < 0 || d.player > 1 || d.observation.player != d.player)
            throw new System.InvalidOperationException("Candidate ownership changed.");
        decisionCount++;
        decisions.WriteLine(Newtonsoft.Json.JsonConvert.SerializeObject(new {
            rally = completed, d.player, identity = match.Actors.IdentityFor(d.player), d.observationTick, d.applyTick,
            observation = d.observation.values, action = d.action
        }));
    };
    serveRandom = new System.Random(seed); Jitter();
    trace.WriteLine(Newtonsoft.Json.JsonConvert.SerializeObject(new { state = State(), contacts = new object[0] }));
}
void End(bool complete, string reason)
{
    trace.Dispose(); trace = null; decisions.Dispose(); decisions = null;
    var report = new {
        run, seed, complete, reason, steps, decisionCount, completedRallies = completed,
        score = (int[])match.World.Rules.Score.Clone(), winner = complete ? match.World.Rules.GameWinner : -1,
        gameSeconds, rallies = rallies.ToArray(), metrics = Newtonsoft.Json.Linq.JObject.Parse(UnityEngine.JsonUtility.ToJson(match.Metrics)),
        stepsHash = Hash(folder + "/run-" + run + ".steps.jsonl.gz"), decisionsHash = Hash(folder + "/run-" + run + ".decisions.jsonl")
    };
    reports.Add(report);
    System.IO.File.WriteAllText(folder + "/run-" + run + ".json", Newtonsoft.Json.JsonConvert.SerializeObject(report, Newtonsoft.Json.Formatting.Indented));
    match.Dispose(); match = null; run++;
}
void TickFixedPolicyRepeat()
{
    try
    {
        if (!UnityEditor.EditorApplication.isPlaying) throw new System.InvalidOperationException("Play stopped.");
        double until = UnityEditor.EditorApplication.timeSinceStartup + .02;
        while (run < repeats && UnityEditor.EditorApplication.timeSinceStartup < until)
        {
            if (match == null) Start();
            int contactsBefore = match.World.Contacts.Count;
            match.Step(); steps++;
            trace.WriteLine(Newtonsoft.Json.JsonConvert.SerializeObject(new {
                state = State(), contacts = match.World.Contacts.Skip(contactsBefore).Select(c => new {
                    c.time, c.player, c.surface, point = V(c.point), normal = V(c.normal), incoming = V(c.incoming),
                    velocity = V(c.velocity), spin = V(c.spin)
                }).ToArray()
            }));
            if (match.World.Time > 35) { End(false, "rally resolution cap"); break; }
            if (match.CompletedRallies == completed) continue;
            completed = match.CompletedRallies; gameSeconds += match.World.Time;
            var rules = match.World.Rules;
            rallies.Add(new { rally = completed-1, rules.Winner, rules.Hits, score = (int[])rules.Score.Clone(),
                fault = rules.LastFault.ToString(), seconds = match.World.Time });
            if (rules.GameWinner >= 0) { End(true, "game complete"); break; }
            if (completed >= plan.maxRallies || gameSeconds >= plan.maxGameSeconds) { End(false, "game safety cap"); break; }
            match.Next(); Jitter();
            trace.WriteLine(Newtonsoft.Json.JsonConvert.SerializeObject(new { state = State(), contacts = new object[0] }));
        }
        UnityEditor.SessionState.SetString("Picklebot.FixedPolicyRepeat.Status", "running: " + run + "/" + repeats + "; rally " + completed + "; " + folder);
        if (run == repeats)
        {
            if (source != Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash() || Hash(planPath) != planHash
                || hashes.Any(p => Hash(p.Key) != p.Value)) throw new System.InvalidOperationException("Provenance changed.");
            UnityEditor.EditorApplication.update -= TickFixedPolicyRepeat;
            System.IO.File.WriteAllText(folder + "/completion.json", Newtonsoft.Json.JsonConvert.SerializeObject(new {
                status = "complete", planHash, sourceHash = source, wallSeconds = watch.Elapsed.TotalSeconds,
                reportHashes = Enumerable.Range(0, repeats).ToDictionary(i => "run-" + i + ".json", i => Hash(folder + "/run-" + i + ".json"))
            }, Newtonsoft.Json.Formatting.Indented));
            UnityEditor.SessionState.SetString("Picklebot.FixedPolicyRepeat.Status", "complete: " + folder);
        }
    }
    catch (System.Exception error)
    {
        UnityEditor.EditorApplication.update -= TickFixedPolicyRepeat;
        trace?.Dispose(); decisions?.Dispose(); match?.Dispose(); trace = null; decisions = null; match = null;
        System.IO.File.WriteAllText(folder + "/failure.json", Newtonsoft.Json.JsonConvert.SerializeObject(new { run, completed, steps, error = error.ToString() }));
        UnityEditor.SessionState.SetString("Picklebot.FixedPolicyRepeat.Status", "failed: " + folder);
    }
}
UnityEditor.EditorApplication.update += TickFixedPolicyRepeat;
UnityEditor.SessionState.SetString("Picklebot.FixedPolicyRepeat.Status", "scheduled: " + folder);
return folder;

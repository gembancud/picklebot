// Diagnostic command trace. No scene changes or new training data.
if (!UnityEditor.EditorApplication.isPlaying || Picklebot.PlayerAgents.Editor.PlayerCompetition.Running
    || Picklebot.PlayerAgents.Editor.PlayerCurriculum.Running || Picklebot.PlayerAgents.Editor.PlayerEvaluation.Running
    || Picklebot.PlayerAgents.Editor.PlayerTeacher.Running || Picklebot.PlayerAgents.Editor.PlayerControlProbe.Running
    || Picklebot.PlayerAgents.Editor.PlayerDiagnostics.Running
    || UnityEditor.EditorApplication.update.GetInvocationList().Any(d => d.Method.Name.Contains("TickFinal")
        || d.Method.Name.Contains("TickIncoming") || d.Method.Name.Contains("TickCoverage") || d.Method.Name.Contains("TickMotorTrace")))
    throw new System.InvalidOperationException("Start Play and finish other jobs first.");
string actorPath = UnityEditor.SessionState.GetString("Picklebot.MotorTrace.ActorPath", "artifacts/player-agents/ppo-20260906-192151/actor.json");
int seed = UnityEditor.SessionState.GetInt("Picklebot.MotorTrace.Seed", 1126000);
int team = UnityEditor.SessionState.GetInt("Picklebot.MotorTrace.Team", 0);
string sourceReportPath = UnityEditor.SessionState.GetString("Picklebot.MotorTrace.SourceReport", "");
string opponentPath = UnityEditor.SessionState.GetString("Picklebot.MotorTrace.OpponentPath", "");
bool allowHistoricalReplay = UnityEditor.SessionState.GetBool("Picklebot.MotorTrace.AllowHistoricalReplay", false);
string sourceReportRuntimeHash = "";
int randomSeed = seed, skipRallies = 0;
bool sampledActor = false;
string split = "development";
bool sampledBaseline = UnityEditor.SessionState.GetBool("Picklebot.MotorTrace.SampledBaseline", false);
string Hash(string p) => Picklebot.Doubles.Editor.ContactTraining.Hash(System.IO.File.ReadAllText(p));
if (!string.IsNullOrEmpty(sourceReportPath))
{
    var recorded = Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(sourceReportPath));
    if ((string)recorded["status"] != "complete" || (string)recorded["split"] != "training"
        || (!allowHistoricalReplay && (string)recorded["sourceHash"] != Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash())
        || (string)recorded["actorHash"] != Hash(actorPath)
        || string.IsNullOrEmpty(opponentPath) || (string)recorded["opponentHash"] != Hash(opponentPath)
        || seed < 1000000 || seed >= 1100000)
        throw new System.ArgumentException("Exact current-source training replay identity mismatch.");
    var gameRecord = recorded["games"].Single(g => (int)g["gameSeed"] == seed);
    team = (int)gameRecord["candidateTeam"];
    randomSeed = (int)recorded["seed"];
    sourceReportRuntimeHash = (string)recorded["sourceHash"];
    skipRallies = recorded["rallies"].TakeWhile(r => (int)r["gameSeed"] != seed).Count();
    sampledActor = (bool)recorded["sampledActor"];
    split = "training-diagnostic";
}
else if (seed < 1100000 || seed >= 1200000 || !string.IsNullOrEmpty(opponentPath))
    throw new System.ArgumentException("Use development seeds, or an exact saved training report.");
if (team < 0 || team > 1) throw new System.ArgumentException("Invalid team.");
var actor = Picklebot.PlayerAgents.PlayerActorModel.Load(System.IO.File.ReadAllText(actorPath));
var opponent = string.IsNullOrEmpty(opponentPath) ? null : Picklebot.PlayerAgents.PlayerActorModel.Load(System.IO.File.ReadAllText(opponentPath));
var contact = Picklebot.Doubles.ContactModel.Load(System.IO.File.ReadAllText("Assets/Picklebot/Doubles/Models/contact.json"));
var teams = Picklebot.Doubles.DoublesModels.Load(System.IO.File.ReadAllText("Assets/Picklebot/Doubles/Models/teams.json"));
string source = Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash();
string scriptPath = "scripts/player-paddle-command-trace.cs", scriptHash = Hash(scriptPath);
string stem = "artifacts/player-agents/paddle-commands-" + System.DateTime.UtcNow.ToString("yyyyMMdd-HHmmss");
if (System.IO.File.Exists(stem + ".json")) throw new System.IO.IOException("Output exists.");
System.IO.File.Copy(scriptPath, stem + ".collector.cs");
var baseline = opponent == null ? new Picklebot.PlayerAgents.BaselineControl(1 << (1 - team), teams, contact, seed, sampledBaseline) : null;
var policies = Enumerable.Range(0, 4).Select(i => i / 2 == team ? (Picklebot.PlayerAgents.IPlayerPolicy)new Picklebot.PlayerAgents.PlayerActor(actor, sampledActor)
    : opponent != null ? new Picklebot.PlayerAgents.PlayerActor(opponent, true) : new Picklebot.PlayerAgents.ConstantPlayerPolicy(default)).ToArray();
var match = new Picklebot.PlayerAgents.PlayerMatch(false, policies, contact, seed, baseline) { AutoNext = false };
var random = new System.Random(randomSeed); int completed = 0;
for (int i = 0; i < skipRallies * 2; i++) random.NextDouble();
var rings = Enumerable.Range(0, 4).Select(_ => new System.Collections.Generic.Queue<object>()).ToArray();
var watch = System.Diagnostics.Stopwatch.StartNew();
void Vary() => match.ServeJitter = new UnityEngine.Vector2((float)(random.NextDouble() * .6 - .3), (float)(random.NextDouble() * .8 - .4));
float[] V(UnityEngine.Vector3 p) => new[] { p.x, p.y, p.z };
float[] Q(UnityEngine.Quaternion q) => new[] { q.x, q.y, q.z, q.w };
object State(Picklebot.Doubles.PlayerBody body) => new { position = V(body.Position), velocity = V(body.Velocity),
    paddle = V(body.Paddle.position), rotation = Q(body.Paddle.rotation), paddleVelocity = V(body.PaddleVelocity), shoulderHeight = body.Shoulder.y };
void FinishTrace(string status, object[] frames, int player, string error = null)
{
    UnityEditor.EditorApplication.update -= TickMotorTrace;
    var report = new { status, error, sourceHash = source, actorHash = Hash(actorPath), actorTrainingSourceHash = actor.sourceHash,
        historicalCandidate = actor.sourceHash != source, split, seed, randomSeed, skipRallies, sampledActor, sampledBaseline, candidateTeam = team, player, rally = completed,
        tracedActorHash = player >= 0 && player / 2 != team && opponent != null ? Hash(opponentPath) : Hash(actorPath),
        sourceReportPath, sourceReportRuntimeHash, allowHistoricalReplay,
        sourceReportHash = string.IsNullOrEmpty(sourceReportPath) ? "" : Hash(sourceReportPath),
        collectorHash = scriptHash, collectorSnapshotPath = stem + ".collector.cs", configurationHash = match.World.Configuration.ConfigurationHash,
        contactModelHash = Hash("Assets/Picklebot/Doubles/Models/contact.json"), opponentHash = Hash(opponentPath == "" ? "Assets/Picklebot/Doubles/Models/teams.json" : opponentPath),
        physicsHz = 240, frames, metrics = match.Metrics, gameWinner = match.World.Rules.GameWinner,
        score = match.World.Rules.Score, wallSeconds = watch.Elapsed.TotalSeconds,
        method = "Raw scripted paddle commands reconstructed from the retained contact plan; compare replay to recorded after-state before using as a regression." };
    System.IO.File.WriteAllText(stem + ".json", Newtonsoft.Json.JsonConvert.SerializeObject(report, Newtonsoft.Json.Formatting.Indented));
    match.Dispose(); match = null;
    UnityEditor.SessionState.SetString("Picklebot.MotorTrace.Status", status + ": " + stem + ".json");
}
void TickMotorTrace()
{
    try
    {
        if (!UnityEditor.EditorApplication.isPlaying) throw new System.InvalidOperationException("Play stopped.");
        double until = UnityEditor.EditorApplication.timeSinceStartup + .02;
        while (match != null && UnityEditor.EditorApplication.timeSinceStartup < until)
        {
            var w = match.World; var phase = w.Rules.Phase; float time = w.Time;
            var before = w.Players.Select(State).ToArray();
            var positions = w.Players.Select(p => p.Position).ToArray();
            var previousVelocity = w.Players.Select(p => p.PaddleVelocity).ToArray();
            match.Step();
            if (phase != Picklebot.Doubles.RallyPhase.AwaitServe && phase != Picklebot.Doubles.RallyPhase.Dead)
            {
                for (int i = opponent == null ? team * 2 : 0; i < (opponent == null ? team * 2 + 2 : 4); i++)
                {
                    var swing = match.Swings[i]; var plan = swing.Contact; int side = w.Players[i].Side;
                    var rotation = plan.Rotation(side);
                    var target = plan.Planned ? plan.Impact - plan.Normal * (Picklebot.Core.CourtGeometryV1.BallRadius + .008f) - rotation * UnityEngine.Vector3.up * .0635f
                        : positions[i] + new UnityEngine.Vector3(-side * .19f, 1.1f, -side * .46f);
                    var feed = UnityEngine.Vector3.zero;
                    if (plan.Planned)
                    {
                        float offset = time - plan.ImpactAt;
                        float brush = (plan.Kind == Picklebot.Doubles.StrokeKind.Topspin ? 2.4f : plan.Kind == Picklebot.Doubles.StrokeKind.Slice ? -2.4f : 0) * plan.BrushScale + plan.BrushBias;
                        var stroke = plan.Normal * plan.Swing + UnityEngine.Vector3.ProjectOnPlane(UnityEngine.Vector3.up, plan.Normal).normalized * brush;
                        target += stroke * UnityEngine.Mathf.Clamp(offset, -.06f, .055f);
                        if (offset > -.06f && offset < .055f) feed = stroke;
                    }
                    float acceleration = (w.Players[i].PaddleVelocity - previousVelocity[i]).magnitude / Picklebot.Doubles.DoublesWorld.Dt;
                    rings[i].Enqueue(new { tick = match.Tick, time, phase = phase.ToString(), before = before[i],
                        partner = i % 2 == 0 ? before[i ^ 1] : State(w.Players[i ^ 1]), moveTarget = V(swing.MoveTarget), target = V(target), rotation = Q(rotation), feed = V(feed),
                        after = State(w.Players[i]), guardFeasible = swing.PaddleStepFeasible, acceleration });
                    while (rings[i].Count > 120) rings[i].Dequeue();
                    if (!swing.PaddleStepFeasible || acceleration > 100.1f)
                    {
                        if (source != Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash() || scriptHash != Hash(scriptPath))
                            throw new System.InvalidOperationException("Trace source changed.");
                        FinishTrace("captured", rings[i].ToArray(), i); return;
                    }
                }
            }
            if (match.CompletedRallies != completed)
            {
                completed = match.CompletedRallies;
                if (w.Rules.GameWinner >= 0 || completed >= 100) { FinishTrace("no_failure", new object[0], -1); return; }
                match.Next(); Vary(); foreach (var ring in rings) ring.Clear();
            }
            if (w.Time > 35) throw new System.InvalidOperationException("Unresolved rally.");
        }
    }
    catch (System.Exception e) { if (match != null) FinishTrace("failed", new object[0], -1, e.ToString()); }
}
Vary(); UnityEditor.SessionState.SetString("Picklebot.MotorTrace.Status", "running: " + stem + ".json");
UnityEditor.EditorApplication.update += TickMotorTrace;
return stem + ".json";

// Development-only shot trace. No training labels, scene changes or ball steering.
if (!UnityEditor.EditorApplication.isPlaying
    || Picklebot.PlayerAgents.Editor.PlayerCompetition.Running || Picklebot.PlayerAgents.Editor.PlayerCurriculum.Running
    || Picklebot.PlayerAgents.Editor.PlayerEvaluation.Running || Picklebot.PlayerAgents.Editor.PlayerTeacher.Running
    || Picklebot.PlayerAgents.Editor.PlayerControlProbe.Running || Picklebot.PlayerAgents.Editor.PlayerDiagnostics.Running
    || UnityEditor.EditorApplication.update.GetInvocationList().Any(d => d.Method.Name.Contains("TickIncoming")
        || d.Method.Name.Contains("TickCoverage") || d.Method.Name.Contains("TickFinal")
        || d.Method.Name.Contains("TickMixedPartner") || d.Method.Name.Contains("TickServeDelivery")
        || d.Method.Name.Contains("TickBrushCommand") || d.Method.Name.Contains("TickContactOutcome")
        || d.Method.Name.Contains("TickActionAblation") || d.Method.Name.Contains("TickContactFit")))
    throw new System.InvalidOperationException("Start Play and finish other jobs first.");
string Hash(string path)
{
    using var algorithm = System.Security.Cryptography.SHA256.Create();
    using var input = System.IO.File.OpenRead(path);
    return System.BitConverter.ToString(algorithm.ComputeHash(input)).Replace("-", "").ToLowerInvariant();
}
string actorPath = UnityEditor.SessionState.GetString("Picklebot.BrushCommand.ActorPath", "");
int seedBase = UnityEditor.SessionState.GetInt("Picklebot.BrushCommand.Seed", 1150000);
bool allowHistorical = UnityEditor.SessionState.GetBool("Picklebot.BrushCommand.AllowHistoricalCandidate", false);
const float flatPitchOffset = 0;
float flatBrushBias = UnityEditor.SessionState.GetFloat("Picklebot.BrushCommand.FlatBrushBias", 5);
if (flatBrushBias != 0 && flatBrushBias != 5)
    throw new System.ArgumentException("Use the paired flat-brush command values zero or five.");
if (seedBase < 1100000 || seedBase + 4 >= 1200000) throw new System.ArgumentException("Development seeds only.");
string source = Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash(), actorHash = Hash(actorPath);
string contactPath = "Assets/Picklebot/Doubles/Models/contact.json", teamsPath = "Assets/Picklebot/Doubles/Models/teams.json";
string manifestPath = "artifacts/player-agents/baseline-manifest.json", protocolPath = "config/player-agents/evaluation-v1.json";
var actor = Picklebot.PlayerAgents.PlayerActorModel.Load(System.IO.File.ReadAllText(actorPath));
var metadata = Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(actorPath));
var manifest = Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(manifestPath));
foreach (var file in ((Newtonsoft.Json.Linq.JObject)manifest["files"]).Properties())
    if (Hash(file.Name) != (string)file.Value) throw new System.InvalidOperationException("Frozen baseline changed: " + file.Name);
if ((actor.sourceHash != source && !allowHistorical) || actor.trainingSteps <= 0 || actor.contactModelHash != Hash(contactPath)
    || actor.protocolHash != Hash(protocolPath) || (string)metadata["baselineManifestHash"] != Hash(manifestPath))
    throw new System.InvalidOperationException("Actor provenance mismatch.");
string stem = "artifacts/player-agents/brush-command-" + System.DateTime.UtcNow.ToString("yyyyMMdd-HHmmss");
System.IO.File.Copy("scripts/player-brush-command.cs", stem + ".collector.cs");
System.IO.File.Copy("Assets/Picklebot/PlayerAgents/PlayerSwing.cs", stem + ".PlayerSwing.cs");
System.IO.File.Copy("Assets/Picklebot/PlayerAgents/PlayerContactPlan.cs", stem + ".PlayerContactPlan.cs");
string collectorHash = Hash(stem + ".collector.cs");
var contact = Picklebot.Doubles.ContactModel.Load(System.IO.File.ReadAllText(contactPath));
// The baseline retains its original contact object. Only this temporary
// candidate object receives the explicitly reported diagnostic correction.
var candidateContact = Picklebot.Doubles.ContactModel.Load(System.IO.File.ReadAllText(contactPath));
candidateContact.strokes[0].brushBias = flatBrushBias;
var teams = Picklebot.Doubles.DoublesModels.Load(System.IO.File.ReadAllText(teamsPath));
var rallies = new System.Collections.Generic.List<object>();
var games = new System.Collections.Generic.List<object>();
var shots = new System.Collections.Generic.List<object>();
Picklebot.PlayerAgents.PlayerMatch match = null;
System.Random random = null;
int index = 0, completed = 0, eventCount = 0;
var watch = System.Diagnostics.Stopwatch.StartNew();
float[] V(UnityEngine.Vector3 value) => new[] { value.x, value.y, value.z };
void VaryServe() => match.ServeJitter = new UnityEngine.Vector2((float)(random.NextDouble() * .6 - .3), (float)(random.NextDouble() * .8 - .4));
void NewCase()
{
    int team = index % 2, seed = seedBase + index;
    var policies = Enumerable.Range(0, 4).Select(i => i / 2 == team
        ? (Picklebot.PlayerAgents.IPlayerPolicy)new Picklebot.PlayerAgents.PlayerActor(actor, false)
        : new Picklebot.PlayerAgents.ConstantPlayerPolicy(default)).ToArray();
    var baseline = new Picklebot.PlayerAgents.BaselineControl(1 << (1 - team), teams, contact, seed, true);
    match = new Picklebot.PlayerAgents.PlayerMatch(false, policies, candidateContact, seed, baseline) { AutoNext = false };
    if (actor.configurationHash != match.World.Configuration.ConfigurationHash) throw new System.InvalidOperationException("Physics mismatch.");
    random = new System.Random(seed); completed = 0; eventCount = 0; shots.Clear(); VaryServe();
}
void Save(string status, string error = null)
{
    var report = new { version = "player-brush-command-v1", status, error, split = "development", sourceHash = source,
        actorPath, actorHash, actorTrainingSourceHash = actor.sourceHash, historicalCandidate = actor.sourceHash != source,
        contactHash = Hash(contactPath), opponentHash = Hash(teamsPath),
        flatPitchOffsetDegrees = flatPitchOffset, flatBrushBias,
        experimentalContactOverride = flatBrushBias != contact.strokes[0].brushBias,
        candidateContactParameters = candidateContact.strokes,
        baselineManifestHash = Hash(manifestPath), protocolHash = Hash(protocolPath), configurationHash = actor.configurationHash,
        collectorHash, collectorSnapshotPath = stem + ".collector.cs", swingSourcePath = stem + ".PlayerSwing.cs",
        swingSourceHash = Hash(stem + ".PlayerSwing.cs"), seedBase, caseCount = 4, maximumRalliesPerCase = 16,
        planSourcePath = stem + ".PlayerContactPlan.cs", planSourceHash = Hash(stem + ".PlayerContactPlan.cs"),
        sampledActor = false, sampledBaseline = true, wallSeconds = watch.Elapsed.TotalSeconds, games, rallies,
        limitation = "Short contact diagnosis only. Requested-limit partial games are retained. Not a match-strength test or training data. "
            + "Only the temporary candidate flat-stroke brush command can differ. No paddle material or ball physics changes. The frozen baseline and saved scene are unchanged." };
    System.IO.File.WriteAllText(stem + ".json", Newtonsoft.Json.JsonConvert.SerializeObject(report, Newtonsoft.Json.Formatting.Indented));
    UnityEditor.SessionState.SetString("Picklebot.BrushCommand.Status", status + ": " + index + "/4; " + stem + ".json");
}
void EndCase(string reason)
{
    var rules = match.World.Rules;
    games.Add(new { gameSeed = seedBase + index, candidateTeam = index % 2, complete = rules.GameWinner >= 0,
        winner = rules.GameWinner, reason, rallies = completed, score = (int[])rules.Score.Clone(),
        metrics = Newtonsoft.Json.Linq.JObject.Parse(UnityEngine.JsonUtility.ToJson(match.Metrics)) });
    match.Dispose(); match = null; index++; Save("running");
}
void TickBrushCommand()
{
    try
    {
        if (!UnityEditor.EditorApplication.isPlaying) throw new System.InvalidOperationException("Play stopped.");
        double until = UnityEditor.EditorApplication.timeSinceStartup + .02;
        while (index < 4 && UnityEditor.EditorApplication.timeSinceStartup < until)
        {
            if (match == null) NewCase();
            var world = match.World; var rules = world.Rules;
            string phaseBefore = rules.Phase.ToString(); int firstContact = world.Contacts.Count;
            match.Step();
            for (; eventCount < rules.Events.Count; eventCount++)
            {
                var e = rules.Events[eventCount];
                if (e.kind != "hit" || e.player / 2 != index % 2) continue;
                var swing = match.Swings[e.player]; var body = world.Players[e.player];
                shots.Add(new { eventIndex = eventCount, e.player, e.time, phaseBefore, selectedShot = swing.SelectedShot,
                    requestedShot = swing.RequestedShot, planned = swing.Contact.Planned, lowContact = swing.Contact.LowContact,
                    target = V(swing.ShotTarget), plannedNormal = V(swing.Contact.Normal), plannedSwing = swing.Contact.Swing,
                    plannedImpactAt = swing.Contact.ImpactAt, ballPosition = V(world.Ball.position), ballVelocity = V(world.Ball.linearVelocity),
                    bodyPosition = V(body.Position), bodyVelocity = V(body.Velocity), paddleVelocity = V(body.PaddleVelocity),
                    shoulder = V(body.Shoulder), hand = V(body.Hand), reach = UnityEngine.Vector3.Distance(body.Shoulder, body.Hand),
                    paddlePosition = V(body.Paddle.position), paddleAngularVelocity = V(body.AngularVelocity),
                    plannedImpact = V(swing.Contact.Impact),
                    requestedMove = V(swing.RequestedVelocity), appliedMove = V(swing.AppliedVelocity),
                    contacts = world.Contacts.Skip(firstContact).Where(c => c.player == e.player).Select(c => new {
                        c.surface, point = V(c.point), normal = V(c.normal), incoming = V(c.incoming), outgoing = V(c.velocity), spin = V(c.spin)
                    }).ToArray() });
            }
            if (match.CompletedRallies != completed || world.Time > 35)
            {
                bool resolved = match.CompletedRallies != completed;
                completed = match.CompletedRallies;
                rallies.Add(new { gameSeed = seedBase + index, candidateTeam = index % 2, rally = completed,
                    resolved, winner = rules.Winner, fault = rules.LastFault.ToString(), hits = rules.Hits, shots = shots.ToArray(),
                    events = rules.Events.Select(e => new { e.time, e.kind, e.player, e.winner, fault = e.fault.ToString(), position = V(e.position) }).ToArray() });
                if (!resolved || rules.GameWinner >= 0 || completed >= 16)
                    EndCase(!resolved ? "resolution cap" : rules.GameWinner >= 0 ? "game complete" : "requested diagnostic limit");
                else { match.Next(); eventCount = 0; shots.Clear(); VaryServe(); }
            }
        }
        if (index == 4)
        {
            if (source != Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash() || Hash(actorPath) != actorHash
                || Hash("scripts/player-brush-command.cs") != collectorHash)
                throw new System.InvalidOperationException("Source or actor changed.");
            UnityEditor.EditorApplication.update -= TickBrushCommand; Save("complete");
        }
    }
    catch (System.Exception error)
    {
        match?.Dispose(); match = null; UnityEditor.EditorApplication.update -= TickBrushCommand; Save("failed", error.ToString());
    }
}
Save("running");
UnityEditor.EditorApplication.update += TickBrushCommand;
return stem + ".json";

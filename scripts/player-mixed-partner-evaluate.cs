// Development-only paired partner comparison. No teacher or training records.
if (!UnityEditor.EditorApplication.isPlaying
    || Picklebot.PlayerAgents.Editor.PlayerCompetition.Running || Picklebot.PlayerAgents.Editor.PlayerCurriculum.Running
    || Picklebot.PlayerAgents.Editor.PlayerEvaluation.Running || Picklebot.PlayerAgents.Editor.PlayerTeacher.Running
    || Picklebot.PlayerAgents.Editor.PlayerControlProbe.Running || Picklebot.PlayerAgents.Editor.PlayerDiagnostics.Running
    || UnityEditor.EditorApplication.update.GetInvocationList().Any(d => d.Method.Name.Contains("TickIncoming")
        || d.Method.Name.Contains("TickCoverage") || d.Method.Name.Contains("TickFinal")
        || d.Method.Name.Contains("TickMixedPartner") || d.Method.Name.Contains("TickServeDelivery")))
    throw new System.InvalidOperationException("Start Play and finish other jobs first.");
string Hash(string path)
{
    using var algorithm = System.Security.Cryptography.SHA256.Create();
    using var input = System.IO.File.OpenRead(path);
    return System.BitConverter.ToString(algorithm.ComputeHash(input)).Replace("-", "").ToLowerInvariant();
}
string candidatePath = UnityEditor.SessionState.GetString("Picklebot.Partner.CandidatePath", "");
string olderPath = UnityEditor.SessionState.GetString("Picklebot.Partner.OlderPath", "");
string protocolPath = "config/player-agents/partner-evaluation-v1.json";
string collectorPath = "scripts/player-mixed-partner-evaluate.cs";
string source = Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash();
string candidateHash = Hash(candidatePath), olderHash = Hash(olderPath), protocolHash = Hash(protocolPath), collectorHash = Hash(collectorPath);
if (candidateHash == olderHash) throw new System.ArgumentException("Choose a distinct older policy.");
var candidate = Picklebot.PlayerAgents.PlayerActorModel.Load(System.IO.File.ReadAllText(candidatePath));
var older = Picklebot.PlayerAgents.PlayerActorModel.Load(System.IO.File.ReadAllText(olderPath));
var protocol = Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(protocolPath));
int seedBase = (int)protocol["seedBase"], perSeat = (int)protocol["seedsPerCourtEndAndSeat"];
if ((string)protocol["version"] != "player-partner-development-v1" || (string)protocol["split"] != "development"
    || seedBase < 1100000 || perSeat < 1 || perSeat > 10 || seedBase + 4 * perSeat >= 1200000
    || (bool)protocol["trainingData"] || (bool)protocol["candidateSampled"] || (bool)protocol["partnerSampled"]
    || !(bool)protocol["opponentSampled"] || candidate.sourceHash != source
    || !protocol["conditions"].Values<string>().SequenceEqual(new[] { "same-policy partner", "older-policy partner" }))
    throw new System.ArgumentException("Unsupported partner protocol or stale candidate.");
string contactPath = "Assets/Picklebot/Doubles/Models/contact.json", manifestPath = "artifacts/player-agents/baseline-manifest.json";
string contactHash = Hash(contactPath), manifestHash = Hash(manifestPath), mainProtocolHash = Hash("config/player-agents/evaluation-v1.json");
var manifest = Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(manifestPath));
foreach (var entry in ((Newtonsoft.Json.Linq.JObject)manifest["files"]).Properties())
    if (Hash(entry.Name) != (string)entry.Value) throw new System.InvalidOperationException("Frozen baseline changed: " + entry.Name);
foreach (string path in new[] { candidatePath, olderPath })
{
    var metadata = Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(path));
    if ((string)metadata["contactModelHash"] != contactHash || (string)metadata["protocolHash"] != mainProtocolHash
        || (string)metadata["baselineManifestHash"] != manifestHash || (int)metadata["trainingSteps"] <= 0)
        throw new System.InvalidOperationException("Incompatible saved policy: " + path);
}
string stem = "artifacts/player-agents/mixed-partner-" + System.DateTime.UtcNow.ToString("yyyyMMdd-HHmmss");
if (System.IO.File.Exists(stem + ".plan.json")) throw new System.IO.IOException("Output already exists.");
System.IO.File.Copy(collectorPath, stem + ".collector.cs");
var schedule = Enumerable.Range(0, 8 * perSeat).Select(index => new {
    index, pair = index / 2, seed = seedBase + index / 2,
    candidateTeam = index / (4 * perSeat), candidateSeat = (index / (2 * perSeat)) % 4,
    mixedPartner = (index & 1) != 0
}).ToArray();
System.IO.File.WriteAllText(stem + ".plan.json", Newtonsoft.Json.JsonConvert.SerializeObject(new {
    sourceHash = source, candidateHash, olderHash, protocolHash, collectorHash, contactHash, manifestHash, schedule
}, Newtonsoft.Json.Formatting.Indented));
string planHash = Hash(stem + ".plan.json");
var contact = Picklebot.Doubles.ContactModel.Load(System.IO.File.ReadAllText(contactPath));
var games = new System.Collections.Generic.List<object>();
var rallies = new System.Collections.Generic.List<object>();
var watch = System.Diagnostics.Stopwatch.StartNew();
Picklebot.PlayerAgents.PlayerMatch match = null;
System.Random serveRandom = null;
int next = 0, completed = 0;
double gameSeconds = 0;
int[] decisionCounts = null, ownershipFailures = null, angularViolations = null;
object[] firstDecisions = null;
void VaryServe() => match.ServeJitter = new UnityEngine.Vector2((float)(serveRandom.NextDouble() * .6 - .3), (float)(serveRandom.NextDouble() * .8 - .4));
void NewGame()
{
    var c = schedule[next];
    var policies = Enumerable.Range(0, 4).Select(i => (Picklebot.PlayerAgents.IPlayerPolicy)new Picklebot.PlayerAgents.PlayerActor(
        i / 2 != c.candidateTeam || (c.mixedPartner && i != c.candidateSeat) ? older : candidate,
        i / 2 != c.candidateTeam)).ToArray();
    match = new Picklebot.PlayerAgents.PlayerMatch(false, policies, contact, c.seed) { AutoNext = false };
    if (candidate.configurationHash != match.World.Configuration.ConfigurationHash || older.configurationHash != candidate.configurationHash)
        throw new System.InvalidOperationException("Policy physics configuration mismatch.");
    completed = 0; gameSeconds = 0; decisionCounts = new int[4]; ownershipFailures = new int[4]; angularViolations = new int[4]; firstDecisions = new object[4];
    match.Actors.Decided += d => {
        decisionCounts[d.player]++;
        if (d.observation.player != d.player || match.Actors.IdentityFor(d.player) != d.player) ownershipFailures[d.player]++;
        if (firstDecisions[d.player] == null) firstDecisions[d.player] = new { d.player, observationPlayer = d.observation.player,
            d.observationTick, d.applyTick, action = new { d.action.moveX, d.action.moveZ, d.action.attempt, d.action.shot } };
    };
    serveRandom = new System.Random(c.seed); VaryServe();
}
void Save(string status, string error = null)
{
    System.IO.File.WriteAllText(stem + ".json", Newtonsoft.Json.JsonConvert.SerializeObject(new {
        status, error, split = "development", sourceHash = source, candidatePath, candidateHash, olderPath, olderHash,
        olderTrainingSourceHash = older.sourceHash, historicalOlderPolicy = older.sourceHash != source,
        protocolHash, collectorHash, collectorSnapshotPath = stem + ".collector.cs", planPath = stem + ".plan.json", planHash,
        wallSeconds = watch.Elapsed.TotalSeconds, games, rallies,
        limitation = "Paired development evidence only. The older opponent uses current runtime physics. No teacher, training rows, or automatic acceptance."
    }, Newtonsoft.Json.Formatting.Indented));
    UnityEditor.SessionState.SetString("Picklebot.Partner.Status", status + ": " + next + "/" + schedule.Length + "; " + stem + ".json");
}
void EndGame(bool complete, string reason)
{
    var c = schedule[next]; var rules = match.World.Rules;
    games.Add(new { c.index, c.pair, gameSeed = c.seed, c.candidateTeam, c.candidateSeat, c.mixedPartner,
        complete, reason, winner = complete ? rules.GameWinner : -1, score = (int[])rules.Score.Clone(), rallies = completed,
        decisionCounts, ownershipFailures, firstDecisions, angularViolations,
        policyHashBySeat = Enumerable.Range(0, 4).Select(i => i / 2 != c.candidateTeam || (c.mixedPartner && i != c.candidateSeat) ? olderHash : candidateHash).ToArray(),
        metrics = Newtonsoft.Json.Linq.JObject.Parse(UnityEngine.JsonUtility.ToJson(match.Metrics)) });
    match.Dispose(); match = null; next++; Save("running");
}
void TickMixedPartner()
{
    try
    {
        if (!UnityEditor.EditorApplication.isPlaying) throw new System.InvalidOperationException("Play stopped");
        double until = UnityEditor.EditorApplication.timeSinceStartup + .02;
        while (next < schedule.Length && UnityEditor.EditorApplication.timeSinceStartup < until)
        {
            if (match == null) NewGame();
            match.Step(); var rules = match.World.Rules; var c = schedule[next];
            for (int i = 0; i < 4; i++)
                if (!float.IsFinite(match.World.Players[i].AngularVelocity.magnitude) || match.World.Players[i].AngularVelocity.magnitude > 12.01f) angularViolations[i]++;
            if (match.World.Time > (float)protocol["rallyResolutionMaximumSeconds"]) { EndGame(false, "rally resolution cap"); continue; }
            if (match.CompletedRallies == completed) continue;
            completed = match.CompletedRallies; gameSeconds += match.World.Time;
            rallies.Add(new { c.index, gameSeed = c.seed, rally = completed, winner = rules.Winner, hits = rules.Hits, fault = rules.LastFault.ToString() });
            if (rules.GameWinner >= 0) { EndGame(true, "game complete"); continue; }
            if (completed >= (int)protocol["gameSafetyMaximumRallies"] || gameSeconds >= (double)protocol["gameSafetyMaximumSimulatedSeconds"])
            { EndGame(false, "game safety cap"); continue; }
            match.Next(); VaryServe();
        }
        if (next == schedule.Length)
        {
            if (source != Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash() || Hash(candidatePath) != candidateHash
                || Hash(olderPath) != olderHash || Hash(protocolPath) != protocolHash || Hash(collectorPath) != collectorHash
                || Hash(contactPath) != contactHash || Hash(manifestPath) != manifestHash || Hash(stem + ".plan.json") != planHash)
                throw new System.InvalidOperationException("Evaluation provenance changed");
            UnityEditor.EditorApplication.update -= TickMixedPartner; Save("complete");
        }
    }
    catch (System.Exception error)
    { UnityEditor.EditorApplication.update -= TickMixedPartner; match?.Dispose(); match = null; Save("failed", error.ToString()); }
}
Save("scheduled"); UnityEditor.EditorApplication.update += TickMixedPartner;
return stem + ".json";

// Unity eval_file. Default: an eight-game DEVELOPMENT rehearsal, never final seeds.
// This runner emits no training decisions. It retains all scheduled games.
if (!UnityEditor.EditorApplication.isPlaying
    || Picklebot.PlayerAgents.Editor.PlayerCompetition.Running || Picklebot.PlayerAgents.Editor.PlayerCurriculum.Running
    || Picklebot.PlayerAgents.Editor.PlayerEvaluation.Running || Picklebot.PlayerAgents.Editor.PlayerTeacher.Running
    || Picklebot.PlayerAgents.Editor.PlayerControlProbe.Running || Picklebot.PlayerAgents.Editor.PlayerDiagnostics.Running
    || UnityEditor.EditorApplication.update.GetInvocationList().Any(d => d.Method.Name.Contains("TickIncoming")
        || d.Method.Name.Contains("TickCoverage") || d.Method.Name.Contains("TickFinal")
        || d.Method.Name.Contains("TickContactOutcome") || d.Method.Name.Contains("TickContactFit")))
    throw new System.InvalidOperationException("Start Play and finish other jobs first.");
bool development = UnityEditor.SessionState.GetBool("Picklebot.Final.Development", true);
int seedBase = UnityEditor.SessionState.GetInt("Picklebot.Final.Seed", development ? 1126000 : 1200000);
int perGroup = UnityEditor.SessionState.GetInt("Picklebot.Final.GamesPerGroup", development ? 1 : 10);
bool sampledActor = UnityEditor.SessionState.GetBool("Picklebot.Final.SampledActor", false);
bool historicalAllowed = development && UnityEditor.SessionState.GetBool("Picklebot.Final.AllowHistoricalCandidate", false);
float flatPitchOffset = UnityEditor.SessionState.GetFloat("Picklebot.Final.FlatPitchOffset", 0);
if (!float.IsFinite(flatPitchOffset) || UnityEngine.Mathf.Abs(flatPitchOffset) > 6 || (!development && flatPitchOffset != 0))
    throw new System.ArgumentException("Contact overrides are bounded development experiments, never final evaluation.");
string actorPath = UnityEditor.SessionState.GetString("Picklebot.Final.ActorPath", "");
int lower = development ? 1100000 : 1200000;
if (perGroup < 1 || perGroup > 10 || (!development && perGroup != 10)
    || seedBase < lower || seedBase + 8 * perGroup > lower + 100000)
    throw new System.ArgumentException("Invalid evaluation schedule or seed partition.");
string Hash(string path)
{
    using var hash = System.Security.Cryptography.SHA256.Create();
    using var input = System.IO.File.OpenRead(path);
    return System.BitConverter.ToString(hash.ComputeHash(input)).Replace("-", "").ToLowerInvariant();
}
string source = Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash();
string actorHash = Hash(actorPath);
var actor = Picklebot.PlayerAgents.PlayerActorModel.Load(System.IO.File.ReadAllText(actorPath));
var actorMetadata = Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(actorPath));
string protocolPath = "config/player-agents/evaluation-v1.json", manifestPath = "artifacts/player-agents/baseline-manifest.json";
string contactPath = "Assets/Picklebot/Doubles/Models/contact.json", opponentPath = "Assets/Picklebot/Doubles/Models/teams.json";
string protocolHash = Hash(protocolPath), baselineManifestHash = Hash(manifestPath), contactHash = Hash(contactPath), opponentHash = Hash(opponentPath);
var protocol = Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(protocolPath));
var manifest = Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(manifestPath));
foreach (var entry in ((Newtonsoft.Json.Linq.JObject)manifest["files"]).Properties())
    if (Hash(entry.Name) != (string)entry.Value) throw new System.InvalidOperationException("Frozen baseline changed: " + entry.Name);
if ((actor.sourceHash != source && !historicalAllowed) || actor.protocolHash != protocolHash
    || actor.contactModelHash != contactHash || (string)actorMetadata["baselineManifestHash"] != baselineManifestHash || actor.trainingSteps <= 0)
    throw new System.InvalidOperationException("Actor provenance mismatch or no recorded training.");
if ((int)protocol["physicsHz"] != 240 || (int)protocol["decisionTicks"] != Picklebot.PlayerAgents.PlayerDecisionLoop.DecisionTicks
    || (int)protocol["actionLatencyTicks"] != Picklebot.PlayerAgents.PlayerDecisionLoop.LatencyTicks
    || (int)protocol["baselineGames"] != 80 || (int)protocol["gamesPerBaselineMode"] != 40
    || (int)protocol["gamesPerModePerCourtEnd"] != 20 || (float)protocol["rallyTimeLimitSeconds"] != 30f
    || !(bool)protocol["swapPartnerIdentitiesInHalfOfEachGroup"])
    throw new System.InvalidOperationException("This runner does not implement the supplied protocol.");
if (!development)
{
    string parityPath = System.IO.Path.Combine(System.IO.Path.GetDirectoryName(actorPath), "unity-parity.json");
    var parity = Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(parityPath));
    if (!(bool)parity["passed"] || (string)parity["actorHash"] != actorHash || (string)parity["sourceHash"] != source
        || (int)parity["cases"] < 1 || !((float)parity["maximumError"] >= 0 && (float)parity["maximumError"] < .0001f)
        || (string)parity["inputHash"] != Hash(System.IO.Path.Combine(System.IO.Path.GetDirectoryName(actorPath), "parity-input.json")))
        throw new System.InvalidOperationException("Final actor export parity is missing or stale.");
    // Reserve the full seed block before simulation, including failed attempts.
    foreach (string planPath in System.IO.Directory.GetFiles("artifacts/player-agents", "evaluation-plan.json", System.IO.SearchOption.AllDirectories))
    {
        var previous = Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(planPath));
        if ((string)previous["split"] != "final") continue;
        if (previous["seedList"].Values<int>().Any(s => s >= seedBase && s < seedBase + 8 * perGroup))
            throw new System.InvalidOperationException("Final seed block was already reserved: " + planPath);
    }
}
string collectorPath = "scripts/player-final-evaluate.cs", collectorHash = Hash(collectorPath);
string folder = "artifacts/player-agents/" + (development ? "development-evaluation-" : "final-evaluation-")
    + System.DateTime.UtcNow.ToString("yyyyMMdd-HHmmss");
if (System.IO.Directory.Exists(folder)) throw new System.IO.IOException("Evaluation folder already exists.");
System.IO.Directory.CreateDirectory(folder);
string snapshotPath = folder + "/collector.cs";
System.IO.File.Copy(collectorPath, snapshotPath);
var created = System.DateTime.UtcNow.ToString("O");
var contact = Picklebot.Doubles.ContactModel.Load(System.IO.File.ReadAllText(contactPath));
var candidateContact = Picklebot.Doubles.ContactModel.Load(System.IO.File.ReadAllText(contactPath));
candidateContact.strokes[0].pitch += flatPitchOffset;
var plan = new {
    version = "player-final-runner-v1", createdUtc = created, split = development ? "development" : "final",
    sourceHash = source, actorHash, protocolHash, baselineManifestHash, contactModelHash = contactHash, opponentHash,
    collectorHash, collectorSnapshotPath = snapshotPath, sampledActor, gamesPerGroup = perGroup,
    flatPitchOffsetDegrees = flatPitchOffset, experimentalContactOverride = flatPitchOffset != 0,
    candidateContactParameters = candidateContact.strokes,
    seedList = Enumerable.Range(seedBase, 8 * perGroup).ToArray(),
    groups = Enumerable.Range(0, 8).Select(g => new { group = g, candidateTeam = (g / 2) % 2,
        sampleBaseline = g >= 4, swapPartnerIdentities = (g & 1) != 0,
        seeds = Enumerable.Range(seedBase + g * perGroup, perGroup).ToArray() }).ToArray(),
    limitation = "Shared deterministic weights can make identity swaps behaviourally identical. This is not a different-partner-model test."
};
string planPathOut = folder + "/evaluation-plan.json";
System.IO.File.WriteAllText(planPathOut, Newtonsoft.Json.JsonConvert.SerializeObject(plan, Newtonsoft.Json.Formatting.Indented));
string planHash = Hash(planPathOut);
var watch = System.Diagnostics.Stopwatch.StartNew();
Picklebot.PlayerAgents.PlayerMatch match = null;
var opponent = Picklebot.Doubles.DoublesModels.Load(System.IO.File.ReadAllText(opponentPath));
var games = new System.Collections.Generic.List<object>();
var rallies = new System.Collections.Generic.List<object>();
int group = 0, game = 0, completed = 0, team = 0;
int[] previousHits = new int[4], identities = null, decisionCounts = null;
object[] firstDecisions = null;
System.Collections.Generic.Dictionary<string, int> motorViolations = null;
System.Collections.Generic.Dictionary<string, float> motorMaxima = null;
System.Collections.Generic.List<object> motorFailureSamples = null;
int omittedMotorSamples = 0;
double gameSeconds = 0;
string configurationHash = "";
System.Random serveRandom = null;

void SaveFinalGroup(string status, string error = null)
{
    var report = new {
        status, error, sourceHash = source, actorHash, actorTrainingSourceHash = actor.sourceHash,
        historicalCandidate = actor.sourceHash != source, opponentHash,
        opponentMode = group >= 4 ? "baseline / sampled" : "baseline / maximum probability",
        configurationHash, contactModelHash = contactHash, protocolHash, baselineManifestHash, createdUtc = created,
        flatPitchOffsetDegrees = flatPitchOffset, experimentalContactOverride = flatPitchOffset != 0,
        candidateContactParameters = candidateContact.strokes,
        dataPath = "", split = development ? "development" : "final", rewardMode = "game_win", sampledActor,
        swapPartnerIdentities = (group & 1) != 0, initialCandidateTeam = team, alternateEnds = false,
        physicsHz = 240, decisionTicks = Picklebot.PlayerAgents.PlayerDecisionLoop.DecisionTicks,
        actionLatencyTicks = Picklebot.PlayerAgents.PlayerDecisionLoop.LatencyTicks,
        collectorHash, collectorSnapshotPath = snapshotPath, evaluationPlanPath = planPathOut, evaluationPlanHash = planHash,
        trainingSteps = actor.trainingSteps, group, wallSeconds = watch.Elapsed.TotalSeconds,
        games = games.ToArray(), rallies = rallies.ToArray()
    };
    System.IO.File.WriteAllText(folder + "/group-" + group + ".json", Newtonsoft.Json.JsonConvert.SerializeObject(report, Newtonsoft.Json.Formatting.Indented));
    UnityEditor.SessionState.SetString("Picklebot.Final.Status", status + ": group " + group + "; " + folder);
}

void StartFinalGame()
{
    int seed = seedBase + group * perGroup + game; team = (group / 2) % 2;
    identities = Enumerable.Range(0, 4).ToArray();
    if ((group & 1) != 0) { identities[team * 2] ^= 1; identities[team * 2 + 1] ^= 1; }
    // Policies are created by identity, then assigned to seats. The loop also
    // attaches each independent RNG stream to that identity, not the seat.
    var byIdentity = Enumerable.Range(0, 4).Select(i => i / 2 == team
        ? (Picklebot.PlayerAgents.IPlayerPolicy)new Picklebot.PlayerAgents.PlayerActor(actor, sampledActor)
        : new Picklebot.PlayerAgents.ConstantPlayerPolicy(default)).ToArray();
    var policies = identities.Select(i => byIdentity[i]).ToArray();
    var baseline = new Picklebot.PlayerAgents.BaselineControl(1 << (1 - team), opponent, contact, seed, group >= 4);
    // Preserve the baseline object; only the candidate can use the disclosed
    // development correction. No corrected model is saved or accepted here.
    match = new Picklebot.PlayerAgents.PlayerMatch(false, policies, candidateContact, seed, baseline, identities) { AutoNext = false };
    configurationHash = match.World.Configuration.ConfigurationHash;
    if (actor.configurationHash != configurationHash || (string)manifest["configurationHash"] != configurationHash)
        throw new System.InvalidOperationException("Actor or baseline physics configuration mismatch.");
    for (int i = 0; i < 4; i++)
        if (match.Actors.IdentityFor(i) != identities[i]) throw new System.InvalidOperationException("Player identity assignment failed.");
    decisionCounts = new int[4]; firstDecisions = new object[4];
    motorViolations = new System.Collections.Generic.Dictionary<string, int>();
    motorMaxima = new System.Collections.Generic.Dictionary<string, float>();
    motorFailureSamples = new System.Collections.Generic.List<object>(); omittedMotorSamples = 0;
    match.Actors.Decided += d => {
        decisionCounts[d.player]++;
        if (firstDecisions[d.player] == null) firstDecisions[d.player] = new {
            player = d.player, identity = match.Actors.IdentityFor(d.player), d.observationTick, d.applyTick,
            observationPlayer = d.observation.player, action = new { d.action.moveX, d.action.moveZ, d.action.attempt, d.action.shot }
        };
    };
    completed = 0; gameSeconds = 0; previousHits = new int[4];
    serveRandom = new System.Random(seed); VaryFinalServe(); SaveFinalGroup("running");
}
void VaryFinalServe() => match.ServeJitter = new UnityEngine.Vector2(
    (float)(serveRandom.NextDouble() * .6 - .3), (float)(serveRandom.NextDouble() * .8 - .4));
void EndFinalGame(bool complete, string reason)
{
    var rules = match.World.Rules;
    int seed = seedBase + group * perGroup + game;
    games.Add(new { gameSeed = seed, candidateTeam = team, winner = complete ? rules.GameWinner : -1, complete, reason,
        rallies = completed, score = (int[])rules.Score.Clone(), identityBySeat = (int[])identities.Clone(),
        randomSeedBySeat = identities.Select(i => unchecked(seed * 397 + i * 7919)).ToArray(),
        decisionCounts = (int[])decisionCounts.Clone(), firstDecisions = (object[])firstDecisions.Clone(),
        motorViolations, motorMaxima, motorFailureSamples = motorFailureSamples.ToArray(), omittedMotorSamples,
        simulatedSeconds = gameSeconds, metrics = Newtonsoft.Json.Linq.JObject.Parse(UnityEngine.JsonUtility.ToJson(match.Metrics)) });
    match.Dispose(); match = null; game++;
    // Do not omit or replace incomplete games. Continue the original schedule.
    SaveFinalGroup("running");
    if (game == perGroup)
    {
        SaveFinalGroup("complete"); group++; game = 0; games.Clear(); rallies.Clear();
    }
}
void AuditedFinalStep()
{
    var world = match.World;
    var phase = world.Rules.Phase; int server = world.Rules.Server;
    var velocities = world.Players.Select(p => p.Velocity).ToArray();
    var paddleVelocities = world.Players.Select(p => p.PaddleVelocity).ToArray();
    var positions = world.Players.Select(p => p.Position).ToArray();
    var hands = world.Players.Select(p => p.Hand).ToArray();
    var shoulders = world.Players.Select(p => p.Shoulder).ToArray();
    match.Step();
    float[] V(UnityEngine.Vector3 p) => new[] { p.x, p.y, p.z };
    for (int i = 0; i < 4; i++)
    {
        var body = world.Players[i];
        bool candidate = i / 2 == team;
        bool scriptedServe = candidate && phase == Picklebot.Doubles.RallyPhase.AwaitServe && i == server;
        bool guarded = candidate && !scriptedServe;
        string prefix = (candidate ? scriptedServe ? "candidate serve" : "candidate guarded" : "frozen baseline") + "/" + phase;
        float speed = body.Velocity.magnitude, acceleration = (body.Velocity - velocities[i]).magnitude / Picklebot.Doubles.DoublesWorld.Dt;
        float paddleSpeed = body.PaddleVelocity.magnitude;
        float paddleAcceleration = (body.PaddleVelocity - paddleVelocities[i]).magnitude / Picklebot.Doubles.DoublesWorld.Dt;
        float reach = UnityEngine.Vector3.Distance(body.Shoulder, body.Hand), angular = body.AngularVelocity.magnitude;
        bool failed = false;
        void Measure(string name, float value, float limit)
        {
            string key = prefix + "/" + name;
            motorMaxima[key] = motorMaxima.TryGetValue(key, out float previous) ? UnityEngine.Mathf.Max(previous, value) : value;
            if (!float.IsFinite(value) || value > limit)
            { motorViolations[key] = motorViolations.TryGetValue(key, out int count) ? count + 1 : 1; failed = true; }
        }
        Measure("speed", speed, 3.801f); Measure("acceleration", acceleration, 14.05f);
        Measure("paddleSpeed", paddleSpeed, 12.01f); Measure("paddleAcceleration", paddleAcceleration, 100.1f);
        Measure("reach", reach, .6201f); Measure("angularSpeed", angular, 12.01f);
        if (guarded && !match.Swings[i].PaddleStepFeasible)
        {
            string key = prefix + "/infeasibleGuard";
            motorViolations[key] = motorViolations.TryGetValue(key, out int count) ? count + 1 : 1; failed = true;
        }
        if (failed)
        {
            // Keep separate controller/phase quotas so a serve failure cannot
            // hide a later learned-player failure. Counts are uncapped.
            int quota = candidate ? 16 : 4;
            int retained = motorFailureSamples.Count(sample => ((Newtonsoft.Json.Linq.JObject)sample).Value<string>("controllerPhase") == prefix);
            if (retained >= quota) { omittedMotorSamples++; continue; }
            motorFailureSamples.Add(Newtonsoft.Json.Linq.JObject.FromObject(new {
                player = i, candidate, scriptedServe, controllerPhase = prefix, phase = phase.ToString(), afterPhase = world.Rules.Phase.ToString(),
                rally = completed, tick = match.Tick, time = world.Time, speed, acceleration, paddleSpeed, paddleAcceleration, reach, angular,
                guardFeasible = guarded ? (bool?)match.Swings[i].PaddleStepFeasible : null,
                previousPosition = V(positions[i]), position = V(body.Position), previousVelocity = V(velocities[i]), velocity = V(body.Velocity),
                previousPaddleVelocity = V(paddleVelocities[i]), paddleVelocity = V(body.PaddleVelocity),
                previousHand = V(hands[i]), hand = V(body.Hand), previousShoulder = V(shoulders[i]), shoulder = V(body.Shoulder),
                requestedVelocity = V(match.Swings[i].RequestedVelocity), appliedVelocity = V(match.Swings[i].AppliedVelocity)
            }));
        }
    }
}
void TickFinal()
{
    try
    {
        if (!UnityEditor.EditorApplication.isPlaying) throw new System.InvalidOperationException("Play stopped during evaluation.");
        double until = UnityEditor.EditorApplication.timeSinceStartup + .02;
        while (group < 8 && UnityEditor.EditorApplication.timeSinceStartup < until)
        {
            if (match == null) StartFinalGame();
            AuditedFinalStep(); var rules = match.World.Rules;
            if (match.World.Time > 35) { EndFinalGame(false, "rally did not resolve within 35 seconds"); continue; }
            if (match.CompletedRallies == completed) continue;
            completed = match.CompletedRallies; gameSeconds += match.World.Time;
            var hits = Enumerable.Range(0, 4).Select(i => match.Metrics.legalHits[i] - previousHits[i]).ToArray();
            previousHits = (int[])match.Metrics.legalHits.Clone();
            rallies.Add(new { gameSeed = seedBase + group * perGroup + game, candidateTeam = team, winner = rules.Winner,
                hits = rules.Hits, fault = rules.LastFault.ToString(), score = (int[])rules.Score.Clone(), legalHits = hits, seconds = match.World.Time });
            if (rules.GameWinner >= 0) { EndFinalGame(true, "game complete"); continue; }
            if (completed >= (int)protocol["gameSafetyMaximumRallies"] || gameSeconds >= (double)protocol["gameSafetyMaximumSimulatedSeconds"])
            { EndFinalGame(false, "game safety cap"); continue; }
            match.Next(); VaryFinalServe();
        }
        if (group == 8)
        {
            if (source != Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash() || Hash(actorPath) != actorHash
                || Hash(collectorPath) != collectorHash || Hash(protocolPath) != protocolHash || Hash(manifestPath) != baselineManifestHash
                || Hash(contactPath) != contactHash || Hash(opponentPath) != opponentHash || Hash(planPathOut) != planHash)
                throw new System.InvalidOperationException("Evaluation provenance changed during the run.");
            UnityEditor.EditorApplication.update -= TickFinal;
            UnityEditor.SessionState.SetString("Picklebot.Final.Status", "complete: " + folder);
            System.IO.File.WriteAllText(folder + "/completion.json", Newtonsoft.Json.JsonConvert.SerializeObject(new {
                status = "complete", sourceHash = source, actorHash, evaluationPlanHash = planHash, games = 8 * perGroup,
                reportHashes = Enumerable.Range(0, 8).ToDictionary(g => "group-" + g + ".json", g => Hash(folder + "/group-" + g + ".json")),
                wallSeconds = watch.Elapsed.TotalSeconds, acceptance = "Recorded evaluation only. Run the independent verifier." }));
        }
    }
    catch (System.Exception error)
    {
        UnityEditor.EditorApplication.update -= TickFinal; match?.Dispose(); match = null;
        SaveFinalGroup("failed", error.ToString());
    }
}
UnityEditor.SessionState.SetString("Picklebot.Final.Status", "scheduled: " + folder);
UnityEditor.EditorApplication.update += TickFinal;
return folder;

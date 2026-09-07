// Unity eval_file. Four TRAINING games against a frozen older player actor.
// Both teams use independent motors. The candidate selector and older opponents sample.
// Candidate return experts remain deterministic and all saved weights stay fixed.
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

const int seedBase = 1071000, perGroup = 1;
const double logitScale = .5, explorationFloor = .05;
const bool sampledActor = false; // Expert actions are deterministic; the selector is sampled.
const float flatPitchOffset = 0;
string source = Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash();
string protocolPath = "config/player-agents/evaluation-v1.json", manifestPath = "artifacts/player-agents/baseline-manifest.json";
string contactPath = "Assets/Picklebot/Doubles/Models/contact.json", opponentPath = "Assets/Picklebot/Doubles/Models/teams.json";
string protocolHash = Hash(protocolPath), baselineManifestHash = Hash(manifestPath), contactHash = Hash(contactPath), opponentHash = Hash(opponentPath);
var protocol = Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(protocolPath));
var manifest = Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(manifestPath));
foreach (var entry in ((Newtonsoft.Json.Linq.JObject)manifest["files"]).Properties())
    if (Hash(entry.Name) != (string)entry.Value) throw new System.InvalidOperationException("Frozen baseline changed: " + entry.Name);

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
    || (string)gateMeta["baselineManifestHash"] != baselineManifestHash)
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
string actorHash = Hash(actorPath);
var actor = Picklebot.PlayerAgents.PlayerActorModel.Load(System.IO.File.ReadAllText(actorPath));
var actorMeta = Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(actorPath));
if (actor.trainingSteps <= 0 || actor.contactModelHash != contactHash || actor.protocolHash != protocolHash
    || (string)actorMeta["baselineManifestHash"] != baselineManifestHash)
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

if ((int)protocol["physicsHz"] != 240 || (int)protocol["decisionTicks"] != Picklebot.PlayerAgents.PlayerDecisionLoop.DecisionTicks
    || (int)protocol["actionLatencyTicks"] != Picklebot.PlayerAgents.PlayerDecisionLoop.LatencyTicks
    || (int)protocol["baselineGames"] != 80 || (int)protocol["gamesPerBaselineMode"] != 40
    || (int)protocol["gamesPerModePerCourtEnd"] != 20 || (float)protocol["rallyTimeLimitSeconds"] != 30f
    || !(bool)protocol["swapPartnerIdentitiesInHalfOfEachGroup"])
    throw new System.InvalidOperationException("This runner does not implement the supplied protocol.");

string collectorPath = "scripts/player-skill-gate-collect.cs", collectorHash = Hash(collectorPath);
string folder = "artifacts/player-agents/" + "skill-gate-training-"
    + System.DateTime.UtcNow.ToString("yyyyMMdd-HHmmss");
if (System.IO.Directory.Exists(folder)) throw new System.IO.IOException("Evaluation folder already exists.");
foreach (string priorFolder in System.IO.Directory.GetDirectories("artifacts/player-agents", "skill-gate-training-*"))
{
    string priorPlan = System.IO.Path.Combine(priorFolder, "training-plan.json");
    if (System.IO.File.Exists(priorPlan))
    {
        var old = Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(priorPlan));
        if (old["seedList"].Values<int>().Any(seed => seed >= seedBase && seed < seedBase+4))
            throw new System.InvalidOperationException("Training seed block already reserved: " + priorPlan);
    }
}
System.IO.Directory.CreateDirectory(folder);
string snapshotPath = folder + "/collector.cs";
System.IO.File.Copy(collectorPath, snapshotPath);
var created = System.DateTime.UtcNow.ToString("O");
var contact = Picklebot.Doubles.ContactModel.Load(System.IO.File.ReadAllText(contactPath));
var candidateContact = Picklebot.Doubles.ContactModel.Load(System.IO.File.ReadAllText(contactPath));
candidateContact.strokes[0].pitch += flatPitchOffset;
var plan = new {
    version = "player-skill-gate-training-v1",
    gatePath, gateHash, shortActorPath, shortActorHash, parityPath, parityHash, parityCases, parityMaxError,
    olderExpertPath = actorPath, olderExpertHash = actorHash,
    baseCollectorHash = Hash("scripts/player-skill-gate-games.cs"),
    sampledSelector = true, logitScale, explorationFloor,
    opponentMode = "older actor / sampled", opponentActorPath = actorPath, opponentActorHash = actorHash,
    trainingObjective = "complete team-game win: +1 win, -1 loss; no rally shaping",
    plannedOptimizer = new { epochs = 4, batch = 1024, learningRate = .0003, clip = .2, maximumKl = .02,
        baseline = "zero, no advantage normalization", weighting = "equal mass per complete game" }, createdUtc = created, split = "training",
    sourceHash = source, actorHash, protocolHash, baselineManifestHash, contactModelHash = contactHash, opponentHash,
    collectorHash, collectorSnapshotPath = snapshotPath, sampledActor, gamesPerGroup = perGroup,
    flatPitchOffsetDegrees = flatPitchOffset, experimentalContactOverride = flatPitchOffset != 0,
    candidateContactParameters = candidateContact.strokes,
    seedList = Enumerable.Range(seedBase, 4 * perGroup).ToArray(),
    groups = Enumerable.Range(0, 4).Select(g => new { group = g, candidateTeam = (g / 2) % 2,
        sampledOpponent = true, swapPartnerIdentities = (g & 1) != 0,
        seeds = Enumerable.Range(seedBase + g * perGroup, perGroup).ToArray() }).ToArray(),
    limitation = "Training-only four-game curriculum against a frozen older actor. Not baseline strength or final acceptance. Gate samples from each player\'s own observations. No teacher or return-expert weight updates."
};
string planPathOut = folder + "/training-plan.json";
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
System.IO.StreamWriter decisionTrace = null;
string decisionTracePath = "";
int[] expertSelections = null, expertSwitches = null, previousExpert = null;
uint[] selectorRandomSeeds = null, selectorRandomStates = null;
double SelectorDraw(int identity)
{
    uint state = selectorRandomStates[identity]; state ^= state << 13; state ^= state >> 17; state ^= state << 5;
    selectorRandomStates[identity] = state;
    return (state >> 8) / 16777216.0;
}

void SaveFinalGroup(string status, string error = null)
{
    var report = new {
        version = "player-skill-gate-training-v1", gatePath, gateHash, shortActorPath, shortActorHash,
        status, error, sourceHash = source, actorHash, actorTrainingSourceHash = actor.sourceHash,
        historicalCandidate = actor.sourceHash != source, opponentHash,
        opponentMode = "older actor / sampled", opponentActorPath = actorPath, opponentActorHash = actorHash,
        sampledSelector = true, logitScale, explorationFloor,
        configurationHash, contactModelHash = contactHash, protocolHash, baselineManifestHash, createdUtc = created,
        flatPitchOffsetDegrees = flatPitchOffset, experimentalContactOverride = flatPitchOffset != 0,
        candidateContactParameters = candidateContact.strokes,
        dataPath = "", split = "training", rewardMode = "game_win", sampledActor,
        swapPartnerIdentities = (group & 1) != 0, initialCandidateTeam = team, alternateEnds = false,
        physicsHz = 240, decisionTicks = Picklebot.PlayerAgents.PlayerDecisionLoop.DecisionTicks,
        actionLatencyTicks = Picklebot.PlayerAgents.PlayerDecisionLoop.LatencyTicks,
        collectorHash, collectorSnapshotPath = snapshotPath, evaluationPlanPath = planPathOut, evaluationPlanHash = planHash,
        trainingSteps = (int)gateMeta["trainingSteps"], method = (string)gateMeta["method"],
        group, wallSeconds = watch.Elapsed.TotalSeconds,
        games = games.ToArray(), rallies = rallies.ToArray()
    };
    System.IO.File.WriteAllText(folder + "/group-" + group + ".json", Newtonsoft.Json.JsonConvert.SerializeObject(report, Newtonsoft.Json.Formatting.Indented));
    UnityEditor.SessionState.SetString("Picklebot.SkillGateTraining.Status", status + ": group " + group + "; " + folder);
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
        : new Picklebot.PlayerAgents.PlayerActor(actor, true)).ToArray();
    var policies = identities.Select(i => byIdentity[i]).ToArray();
    Picklebot.PlayerAgents.BaselineControl baseline = null; // All four seats use independent player motors.
    // No contact correction or baseline controller is used in this curriculum.
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
    decisionTracePath = folder + "/group-" + group + ".decisions.jsonl";
    decisionTrace = new System.IO.StreamWriter(new System.IO.FileStream(decisionTracePath, System.IO.FileMode.CreateNew, System.IO.FileAccess.Write));
    expertSelections = new int[2]; expertSwitches = new int[4]; previousExpert = new[] { -1, -1, -1, -1 };
    var shortByIdentity = Enumerable.Range(0, 4).Select(i => new Picklebot.PlayerAgents.PlayerActor(shortActor, false)).ToArray();
    var shortRandomByIdentity = Enumerable.Range(0, 4).Select(i => new System.Random(unchecked(seed*397+i*7919))).ToArray();
    selectorRandomSeeds = Enumerable.Range(0, 4).Select(i => unchecked((uint)(seed*397+i*7919)) ^ 0x9e3779b9u).ToArray();
    selectorRandomStates = (uint[])selectorRandomSeeds.Clone();
    match.Actors.Decided += d => {
        int identity = match.Actors.IdentityFor(d.player);
        bool candidate = d.player/2 == team;
        float gateLogit = 0; int selectedExpert = -1;
        double shortProbability = 0, selectorDraw = 0, selectorLogProbability = 0;
        if (candidate)
        {
            gateLogit = GateForward(d.observation.values);
            shortProbability = explorationFloor + (1-2*explorationFloor)/(1+System.Math.Exp(-logitScale*gateLogit));
            selectorDraw = SelectorDraw(identity); selectedExpert = selectorDraw < shortProbability ? 1 : 0;
            selectorLogProbability = System.Math.Log(selectedExpert == 1 ? shortProbability : 1-shortProbability);
            if (selectedExpert == 1)
                d.action = shortByIdentity[identity].Decide(d.observation.Copy(), shortRandomByIdentity[identity]).Validated();
            d.trace = null;
            expertSelections[selectedExpert]++;
            if (previousExpert[d.player] >= 0 && previousExpert[d.player] != selectedExpert) expertSwitches[d.player]++;
            previousExpert[d.player] = selectedExpert;
        }
        decisionTrace.WriteLine(Newtonsoft.Json.JsonConvert.SerializeObject(new {
            gameSeed = seed, rally = completed, candidateTeam = team, d.player, identity,
            observationPlayer = d.observation.player, d.observationTick, d.applyTick,
            observation = d.observation.values, gateLogit, selectedExpert, shortProbability, selectorDraw, selectorLogProbability,
            executedBy = candidate ? "selector" : "older-opponent", opponentSample = candidate ? null : d.trace,
            action = new { d.action.moveX, d.action.moveZ, d.action.attempt, d.action.shot }
        }));
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
    decisionTrace.Dispose(); decisionTrace = null;
    games.Add(new { gameSeed = seed, candidateTeam = team, winner = complete ? rules.GameWinner : -1, complete, reason,
        rallies = completed, score = (int[])rules.Score.Clone(), identityBySeat = (int[])identities.Clone(),
        decisionTracePath, decisionTraceHash = Hash(decisionTracePath), expertSelections, expertSwitches,
        selectorRandomSeedBySeat = identities.Select(i => selectorRandomSeeds[i]).ToArray(),
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
        bool guarded = phase != Picklebot.Doubles.RallyPhase.AwaitServe || i != server;
        string prefix = (candidate ? scriptedServe ? "candidate serve" : "candidate guarded" : phase == Picklebot.Doubles.RallyPhase.AwaitServe && i == server ? "older opponent serve" : "older opponent guarded") + "/" + phase;
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
void TickSkillGateTraining()
{
    try
    {
        if (!UnityEditor.EditorApplication.isPlaying) throw new System.InvalidOperationException("Play stopped during evaluation.");
        double until = UnityEditor.EditorApplication.timeSinceStartup + .02;
        while (group < 4 && UnityEditor.EditorApplication.timeSinceStartup < until)
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
        if (group == 4)
        {
            if (source != Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash() || Hash(actorPath) != actorHash
                || Hash(collectorPath) != collectorHash || Hash(protocolPath) != protocolHash || Hash(manifestPath) != baselineManifestHash
                || Hash(contactPath) != contactHash || Hash(opponentPath) != opponentHash || Hash(planPathOut) != planHash
                || Hash(gatePath) != gateHash || Hash(shortActorPath) != shortActorHash || Hash(parityPath) != parityHash)
                throw new System.InvalidOperationException("Evaluation provenance changed during the run.");
            UnityEditor.EditorApplication.update -= TickSkillGateTraining;
            UnityEditor.SessionState.SetString("Picklebot.SkillGateTraining.Status", "complete: " + folder);
            System.IO.File.WriteAllText(folder + "/completion.json", Newtonsoft.Json.JsonConvert.SerializeObject(new {
                status = "complete", sourceHash = source, actorHash, gateHash, shortActorHash, evaluationPlanHash = planHash, games = 4 * perGroup,
                reportHashes = Enumerable.Range(0, 4).ToDictionary(g => "group-" + g + ".json", g => Hash(folder + "/group-" + g + ".json")),
                wallSeconds = watch.Elapsed.TotalSeconds, acceptance = "Recorded evaluation only. Run the independent verifier." }));
        }
    }
    catch (System.Exception error)
    {
        UnityEditor.EditorApplication.update -= TickSkillGateTraining; decisionTrace?.Dispose(); decisionTrace = null; match?.Dispose(); match = null;
        SaveFinalGroup("failed", error.ToString());
    }
}
UnityEditor.SessionState.SetString("Picklebot.SkillGateTraining.Status", "scheduled: " + folder);
UnityEditor.EditorApplication.update += TickSkillGateTraining;
return folder;

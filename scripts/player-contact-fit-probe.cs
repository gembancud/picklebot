// Isolated diagnostic of the bounded swing with frozen versus neutral residuals.
// No actor, learned movement, model fitting, scene edits, or asset writes.
if (!UnityEditor.EditorApplication.isPlaying
    || Picklebot.PlayerAgents.Editor.PlayerCompetition.Running
    || Picklebot.PlayerAgents.Editor.PlayerCurriculum.Running
    || Picklebot.PlayerAgents.Editor.PlayerEvaluation.Running
    || Picklebot.PlayerAgents.Editor.PlayerTeacher.Running
    || Picklebot.PlayerAgents.Editor.PlayerControlProbe.Running
    || Picklebot.PlayerAgents.Editor.PlayerDiagnostics.Running
    || UnityEditor.EditorApplication.update.GetInvocationList().Any(d =>
        d.Method.Name.Contains("TickFinal") || d.Method.Name.Contains("TickCoverage")
        || d.Method.Name.Contains("TickContactOutcome") || d.Method.Name.Contains("TickContactFit")
        || d.Method.Name.Contains("TickMixedPartner") || d.Method.Name.Contains("TickIncoming")))
    throw new System.InvalidOperationException("Start Play and finish other collectors first.");
string Hash(string path)
{
    using var algorithm = System.Security.Cryptography.SHA256.Create();
    using var input = System.IO.File.OpenRead(path);
    return System.BitConverter.ToString(algorithm.ComputeHash(input)).Replace("-", "").ToLowerInvariant();
}
string scriptPath = "scripts/player-contact-fit-probe.cs";
string contactPath = "Assets/Picklebot/Doubles/Models/contact.json";
string source = Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash();
string scriptHash = Hash(scriptPath), contactHash = Hash(contactPath);
var contact = Picklebot.Doubles.ContactModel.Load(System.IO.File.ReadAllText(contactPath));
string stem = "artifacts/player-agents/contact-fit-probe-" + System.DateTime.UtcNow.ToString("yyyyMMdd-HHmmss");
System.IO.File.Copy(scriptPath, stem + ".collector.cs");
var rows = new System.Collections.Generic.List<object>();
var watch = System.Diagnostics.Stopwatch.StartNew();
float[] depths = { 3.5f, 4.5f, 5.5f, 6.5f };
int[] shots = { 4, 6, 8 };
int index = 0, ticks = 0, player = 0, shot = 0, infeasible = 0, seenContacts = 0;
float depth = 0, started = 0, maxSpeed = 0, maxAcceleration = 0, maxReach = 0, maxAngularSpeed = 0;
bool fitted = false, hit = false, landed = false, lowPlan = false;
UnityEngine.Vector3 startFeet = default, target = default, landing = default;
Picklebot.Doubles.DoublesWorld world = null;
Picklebot.PlayerAgents.PlayerSwing swing = null;
var contacts = new System.Collections.Generic.List<object>();
string configurationHash = "";
float[] V(UnityEngine.Vector3 v) => new[] { v.x, v.y, v.z };
const int Count = 48; // two residual modes, three shots, four depths, two ends.

void StartContactFitCase()
{
    fitted = index % 2 == 0; int fixture = index / 2;
    shot = shots[fixture % 3]; depth = depths[(fixture / 3) % 4]; player = fixture / 12 * 2;
    world = new Picklebot.Doubles.DoublesWorld(false);
    configurationHash = world.Configuration.ConfigurationHash;
    for (int tick = 0; tick < 480 && !world.ServeBounced && !world.Rules.Dead; tick++) world.Simulate();
    if (!world.ServeBounced || world.Rules.Dead) throw new System.InvalidOperationException("Drop setup failed.");
    var rules = world.Rules;
    rules.Serve(0, true, true, true, true, false, false, false, world.Time);
    rules.Bounce(new UnityEngine.Vector3(rules.ServiceX(rules.DesignatedReceiver), 0, 4), world.Time);
    rules.Hit(2, world.Time); rules.Bounce(new UnityEngine.Vector3(1, 0, -4), world.Time); rules.Hit(0, world.Time);
    if (player == 0) rules.Hit(2, world.Time);
    if (rules.Dead || rules.ExpectedTeam != player / 2 || !rules.CanVolley)
        throw new System.InvalidOperationException("Invalid contact rule fixture.");
    UnityEngine.Vector3 W(UnityEngine.Vector3 p) => Picklebot.PlayerAgents.PlayerObservation.ToWorld(p, player);
    world.Players[player].Reset(W(new UnityEngine.Vector3(.82f, 0, -depth)));
    world.Players[player ^ 1].Reset(W(new UnityEngine.Vector3(-1.55f, 0, -6)));
    world.Ball.position = W(new UnityEngine.Vector3(1.2f, 1.2f, .4f));
    world.Ball.transform.position = world.Ball.position;
    world.Ball.linearVelocity = W(new UnityEngine.Vector3(0, 1.2f, -8));
    world.Ball.angularVelocity = UnityEngine.Vector3.zero; world.Ball.WakeUp();
    UnityEngine.Physics.SyncTransforms(); rules.Events.Clear(); world.Contacts.Clear();
    startFeet = world.Players[player].Position; started = world.Time;
    var goal = new Picklebot.PlayerAgents.PlayerAction { shot = shot }.WorldShotTarget(player);
    target = new UnityEngine.Vector3(goal.x, 0, -world.Players[player].Side * goal.y);
    swing = new Picklebot.PlayerAgents.PlayerSwing(); contacts.Clear();
    ticks = infeasible = seenContacts = 0; hit = landed = lowPlan = false; landing = default;
    maxSpeed = maxAcceleration = maxReach = maxAngularSpeed = 0;
}

void SaveContactFit(string status, string error = null)
{
    System.IO.File.WriteAllText(stem + ".json", Newtonsoft.Json.JsonConvert.SerializeObject(new {
        version = "player-contact-fit-probe-v1", status, error, sourceHash = source, configurationHash,
        collectorSnapshotPath = stem + ".collector.cs", collectorHash = scriptHash,
        contactPath, contactHash, frozenParameters = contact.strokes, expectedCases = Count,
        split = "diagnostic", depths, shots, incomingPosition = new[] { 1.2f, 1.2f, .4f },
        incomingVelocity = new[] { 0f, 1.2f, -8f }, incomingSpin = new[] { 0f, 0f, 0f },
        elapsedSeconds = watch.Elapsed.TotalSeconds, rows,
        limitation = "Injected stationary-player contact fixtures. No learned actor or contact fit. "
            + "Player colliders are disabled only after a legal hit to isolate its outgoing flight. "
            + "Not match-strength evidence or real-ball calibration. No model is selected automatically."
    }, Newtonsoft.Json.Formatting.Indented));
    UnityEditor.SessionState.SetString("Picklebot.ContactFit.Status", status + ": " + index + "/48; " + stem + ".json");
}

void EndContactFitCase()
{
    var body = world.Players[player];
    bool legalLanding = landed && landing.z * body.Side < 0
        && UnityEngine.Mathf.Abs(landing.z) <= Picklebot.Doubles.DoublesRules.HalfLength
        && UnityEngine.Mathf.Abs(landing.x) <= Picklebot.Doubles.DoublesRules.HalfWidth;
    rows.Add(new { index, fixture = index / 2, player, shot, depth, fitted, hit, landed, legalLanding, lowPlan,
        target = V(target), landing = landed ? V(landing) : null,
        targetError = landed ? (float?)UnityEngine.Vector2.Distance(new UnityEngine.Vector2(landing.x, landing.z), new UnityEngine.Vector2(target.x, target.z)) : null,
        fault = world.Rules.LastFault.ToString(), elapsedSeconds = world.Time - started,
        movement = UnityEngine.Vector3.Distance(startFeet, body.Position), infeasible,
        maxSpeed, maxAcceleration, maxReach, maxAngularSpeed, contacts = contacts.ToArray() });
    world.Dispose(); world = null; index++; SaveContactFit("running");
}

void TickContactFit()
{
    try
    {
        if (!UnityEditor.EditorApplication.isPlaying) throw new System.InvalidOperationException("Play stopped.");
        double until = UnityEditor.EditorApplication.timeSinceStartup + .02;
        while (index < Count && UnityEditor.EditorApplication.timeSinceStartup < until)
        {
            if (world == null) StartContactFitCase();
            var body = world.Players[player];
            if (!hit)
            {
                var previous = body.PaddleVelocity;
                swing.Step(world, player, new Picklebot.PlayerAgents.PlayerAction { attempt = true, shot = shot }, fitted ? contact : null);
                lowPlan |= swing.Contact.LowContact;
                if (!swing.PaddleStepFeasible) infeasible++;
                maxSpeed = UnityEngine.Mathf.Max(maxSpeed, body.PaddleVelocity.magnitude);
                maxAcceleration = UnityEngine.Mathf.Max(maxAcceleration, (body.PaddleVelocity - previous).magnitude / Picklebot.Doubles.DoublesWorld.Dt);
                maxReach = UnityEngine.Mathf.Max(maxReach, UnityEngine.Vector3.Distance(body.Hand, body.Shoulder));
                maxAngularSpeed = UnityEngine.Mathf.Max(maxAngularSpeed, body.AngularVelocity.magnitude);
            }
            world.Simulate(); ticks++;
            for (; seenContacts < world.Contacts.Count; seenContacts++)
            {
                var c = world.Contacts[seenContacts];
                if (c.player == player) contacts.Add(new { c.surface, c.time, normal = V(c.normal), outgoing = V(c.velocity), spin = V(c.spin),
                    planned = swing.Contact.Planned, low = swing.Contact.LowContact, plannedSwing = swing.Contact.Swing,
                    plannedImpactAt = swing.Contact.ImpactAt, paddleVelocity = V(body.PaddleVelocity) });
                if (!hit && c.player == player && world.Rules.Events.Any(e => e.kind == "hit" && e.player == player))
                {
                    hit = true;
                    foreach (var p in world.Players)
                    {
                        foreach (var collider in p.Paddle.GetComponentsInChildren<UnityEngine.Collider>()) collider.enabled = false;
                        foreach (var collider in p.Root.GetComponentsInChildren<UnityEngine.Collider>()) collider.enabled = false;
                    }
                }
                else if (hit && (c.surface == "CourtSurface" || c.surface == "OutCatchFloor"))
                { landing = c.point; landed = true; }
            }
            if (landed || (!hit && world.Rules.Dead) || world.Time - started > 8f || world.Ball.position.y < -.5f)
                EndContactFitCase();
        }
        if (index == Count)
        {
            if (source != Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash()
                || scriptHash != Hash(scriptPath) || contactHash != Hash(contactPath))
                throw new System.InvalidOperationException("Diagnostic inputs changed.");
            UnityEditor.EditorApplication.update -= TickContactFit; SaveContactFit("complete");
        }
    }
    catch (System.Exception error)
    { world?.Dispose(); world = null; UnityEditor.EditorApplication.update -= TickContactFit; SaveContactFit("failed", error.ToString()); }
}
SaveContactFit("running"); UnityEditor.EditorApplication.update += TickContactFit;
return stem + ".json";

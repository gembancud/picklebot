// Isolated swing timing test: runtime, exact local copy, and 120 ms acceleration ramp.
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
        || d.Method.Name.Contains("TickContactOutcome") || d.Method.Name.Contains("TickSwingRamp")
        || d.Method.Name.Contains("TickSwingRamp") || d.Method.Name.Contains("TickBrushCommand")
        || d.Method.Name.Contains("TickActionAblation") || d.Method.Name.Contains("TickMixedPartner") || d.Method.Name.Contains("TickIncoming")))
    throw new System.InvalidOperationException("Start Play and finish other collectors first.");
string Hash(string path)
{
    using var algorithm = System.Security.Cryptography.SHA256.Create();
    using var input = System.IO.File.OpenRead(path);
    return System.BitConverter.ToString(algorithm.ComputeHash(input)).Replace("-", "").ToLowerInvariant();
}
string scriptPath = "scripts/player-swing-ramp-probe.cs";
string contactPath = "Assets/Picklebot/Doubles/Models/contact.json";
string source = Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash();
string scriptHash = Hash(scriptPath), contactHash = Hash(contactPath);
var contact = Picklebot.Doubles.ContactModel.Load(System.IO.File.ReadAllText(contactPath));
string stem = "artifacts/player-agents/swing-ramp-probe-" + System.DateTime.UtcNow.ToString("yyyyMMdd-HHmmss");
System.IO.File.Copy(scriptPath, stem + ".collector.cs");
var rows = new System.Collections.Generic.List<object>();
var watch = System.Diagnostics.Stopwatch.StartNew();
float[] depths = { 3.5f, 4.5f, 5.5f, 6.5f };
int[] shots = { 4, 6, 8 };
int mode = 0;
int index = 0, ticks = 0, player = 0, shot = 0, infeasible = 0, seenContacts = 0;
float depth = 0, started = 0, maxSpeed = 0, maxAcceleration = 0, maxReach = 0, maxAngularSpeed = 0;
bool hit = false, landed = false, lowPlan = false;
UnityEngine.Vector3 startFeet = default, target = default, landing = default;
Picklebot.Doubles.DoublesWorld world = null;
Picklebot.PlayerAgents.PlayerSwing swing = null;
var contacts = new System.Collections.Generic.List<object>();
string configurationHash = "";
float[] V(UnityEngine.Vector3 v) => new[] { v.x, v.y, v.z };
const int Count = 72; // three trajectories, three shots, four depths, two ends.
var trace = new System.Text.StringBuilder();
float[] Q(Quaternion q) => new[] { q.x, q.y, q.z, q.w };
object[] Events() => world.Rules.Events.Select(e => (object)new {
    e.time, e.kind, e.player, e.winner, fault = e.fault.ToString(), position = V(e.position)
}).ToArray();

var Contact = new Picklebot.PlayerAgents.PlayerContactPlan();
Vector3 MoveTarget = default, ShotTarget = default, RequestedVelocity = default, AppliedVelocity = default;
int lastShot = -1, RequestedShot = 0;
float nextAttempt = 0;
bool ShotCommitted = false, PaddleStepFeasible = true;
Picklebot.PlayerAgents.PlayerContactPlan ActiveContact() => mode == 0 ? swing.Contact : Contact;
void StepTrial(Picklebot.Doubles.DoublesWorld world, int player,
    Picklebot.PlayerAgents.PlayerAction action, Picklebot.Doubles.ContactModel model)
{
            action = action.Validated();
            var body = world.Players[player];
            int side = body.Side;
            RequestedShot = action.shot;
            // A missed contact must not stay committed to a past ball position.
            // Keep the bounded follow-through, then allow a fresh swing plan.
            if (Contact.Planned && world.Time > Contact.ImpactAt + .055f)
            { Contact.Reset(); nextAttempt = 0; }
            ShotCommitted = Contact.Planned && world.Time >= Contact.ImpactAt - .13f && world.Time <= Contact.ImpactAt + .055f;
            // The final contact/follow-through window cannot restart at each
            // 20 Hz categorical sample. The actor can still cancel the attempt.
            if (lastShot != action.shot && (!ShotCommitted || !action.attempt))
            { Contact.Reset(); lastShot = action.shot; nextAttempt = 0; }
            var selected = action; selected.shot = lastShot;
            var goal = selected.WorldShotTarget(player);
            ShotTarget = new Vector3(goal.x, 0, -side * goal.y);
            Contact.Kind = Picklebot.Doubles.TeamPolicy.Kind(lastShot);
            if (model != null) model.strokes[(int)Contact.Kind].Apply(Contact.Residuals);
            if (!action.attempt) { Contact.Reset(); nextAttempt = 0; ShotCommitted = false; }
            else if (world.Time >= nextAttempt)
            {
                nextAttempt = world.Time + .05f;
                if (!Contact.Plan(world, player, goal)) Contact.Reset();
            }

            var rotation = Contact.Rotation(side);
            var paddle = Contact.Planned
                ? Contact.Impact - Contact.Normal * (Picklebot.Core.CourtGeometryV1.BallRadius + .008f) - rotation * Vector3.up * .0635f
                : body.Position + new Vector3(-side * .19f, 1.1f, -side * .46f);
            Vector3 feed = Vector3.zero;
            if (Contact.Planned)
            {
                float phase = world.Time - Contact.ImpactAt;
                float brushSpeed = (Contact.Kind == Picklebot.Doubles.StrokeKind.Topspin ? 2.4f : Contact.Kind == Picklebot.Doubles.StrokeKind.Slice ? -2.4f : 0)
                    * Contact.BrushScale + Contact.BrushBias;
                var velocity = Contact.Normal * Contact.Swing
                    + Vector3.ProjectOnPlane(Vector3.up, Contact.Normal).normalized * brushSpeed;
                if (mode == 2 && phase < 0)
                {
                    // Same -.06 * velocity backswing; smooth acceleration over .12 s.
                    const float ramp = .12f;
                    float t = Mathf.Clamp(phase, -ramp, 0);
                    paddle += velocity * (t + t * t / (2 * ramp));
                    if (phase > -ramp) feed = velocity * (1 + phase / ramp);
                }
                else
                {
                paddle += velocity * Mathf.Clamp(phase, -.06f, .055f);
                if (phase > -.06f && phase < .055f) feed = velocity;
                }
            }
            // PlayerBody converts target error to wanted velocity with gain 4.
            RequestedVelocity = action.WorldVelocity(player);
            AppliedVelocity = Picklebot.PlayerAgents.PlayerMovement.Constrain(body, world.Players[player ^ 1], RequestedVelocity);
            MoveTarget = body.Position + AppliedVelocity / 4f;
            PaddleStepFeasible = Picklebot.PlayerAgents.PlayerPaddleMotor.Constrain(body, world.Players[player ^ 1], MoveTarget,
                ref paddle, ref rotation, ref feed, Picklebot.Doubles.DoublesWorld.Dt);
            body.Step(MoveTarget, paddle, rotation, feed, world.Players[player ^ 1], Picklebot.Doubles.DoublesWorld.Dt);

}


void StartSwingRampCase()
{
    mode = index % 3; int fixture = index / 3;
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
    swing = new Picklebot.PlayerAgents.PlayerSwing(); contacts.Clear(); trace.Clear();
    Contact = new Picklebot.PlayerAgents.PlayerContactPlan();
    lastShot = -1; nextAttempt = 0; ShotCommitted = false; PaddleStepFeasible = true;
    MoveTarget = ShotTarget = RequestedVelocity = AppliedVelocity = default; RequestedShot = 0;
    ticks = infeasible = seenContacts = 0; hit = landed = lowPlan = false; landing = default;
    maxSpeed = maxAcceleration = maxReach = maxAngularSpeed = 0;
}

void SaveSwingRamp(string status, string error = null)
{
    System.IO.File.WriteAllText(stem + ".json", Newtonsoft.Json.JsonConvert.SerializeObject(new {
        version = "player-swing-ramp-probe-v1", status, error, sourceHash = source, configurationHash,
        collectorSnapshotPath = stem + ".collector.cs", collectorHash = scriptHash,
        contactPath, contactHash, frozenParameters = contact.strokes,
        modes = new[] { "runtime", "local-control", "ramp-120ms" },
        runtimeSwingPath = "Assets/Picklebot/PlayerAgents/PlayerSwing.cs",
        runtimeSwingHash = Hash("Assets/Picklebot/PlayerAgents/PlayerSwing.cs"),
        expectedCases = Count,
        split = "diagnostic", depths, shots, incomingPosition = new[] { 1.2f, 1.2f, .4f },
        incomingVelocity = new[] { 0f, 1.2f, -8f }, incomingSpin = new[] { 0f, 0f, 0f },
        elapsedSeconds = watch.Elapsed.TotalSeconds, rows,
        limitation = "Injected stationary-player contact fixtures. No learned actor or contact fit. "
            + "Player colliders are disabled only after a legal hit to isolate its outgoing flight. "
            + "Not match-strength evidence or real-ball calibration. No model is selected automatically."
    }, Newtonsoft.Json.Formatting.Indented));
    UnityEditor.SessionState.SetString("Picklebot.SwingRamp.Status", status + ": " + index + "/72; " + stem + ".json");
}

void EndSwingRampCase()
{
    var body = world.Players[player];
    bool legalLanding = landed && landing.z * body.Side < 0
        && UnityEngine.Mathf.Abs(landing.z) <= Picklebot.Doubles.DoublesRules.HalfLength
        && UnityEngine.Mathf.Abs(landing.x) <= Picklebot.Doubles.DoublesRules.HalfWidth;
    string tracePath = stem + ".case-" + index.ToString("D2") + ".jsonl";
    System.IO.File.WriteAllText(tracePath, trace.ToString());
    rows.Add(new { index, fixture = index / 3, player, shot, depth, mode, tracePath, traceHash = Hash(tracePath), ticks, hit, landed, legalLanding, lowPlan,
        target = V(target), landing = landed ? V(landing) : null,
        targetError = landed ? (float?)UnityEngine.Vector2.Distance(new UnityEngine.Vector2(landing.x, landing.z), new UnityEngine.Vector2(target.x, target.z)) : null,
        fault = world.Rules.LastFault.ToString(), elapsedSeconds = world.Time - started,
        movement = UnityEngine.Vector3.Distance(startFeet, body.Position), infeasible,
        maxSpeed, maxAcceleration, maxReach, maxAngularSpeed, contacts = contacts.ToArray(), events = Events() });
    world.Dispose(); world = null; index++; SaveSwingRamp("running");
}

void TickSwingRamp()
{
    try
    {
        if (!UnityEditor.EditorApplication.isPlaying) throw new System.InvalidOperationException("Play stopped.");
        double until = UnityEditor.EditorApplication.timeSinceStartup + .02;
        while (index < Count && UnityEditor.EditorApplication.timeSinceStartup < until)
        {
            if (world == null) StartSwingRampCase();
            var body = world.Players[player];
            if (!hit)
            {
                var previous = body.PaddleVelocity;
                var action = new Picklebot.PlayerAgents.PlayerAction { attempt = true, shot = shot };
                if (mode == 0) swing.Step(world, player, action, contact);
                else StepTrial(world, player, action, contact);
                lowPlan |= ActiveContact().LowContact;
                if (!(mode == 0 ? swing.PaddleStepFeasible : PaddleStepFeasible)) infeasible++;
                maxSpeed = UnityEngine.Mathf.Max(maxSpeed, body.PaddleVelocity.magnitude);
                maxAcceleration = UnityEngine.Mathf.Max(maxAcceleration, (body.PaddleVelocity - previous).magnitude / Picklebot.Doubles.DoublesWorld.Dt);
                maxReach = UnityEngine.Mathf.Max(maxReach, UnityEngine.Vector3.Distance(body.Hand, body.Shoulder));
                maxAngularSpeed = UnityEngine.Mathf.Max(maxAngularSpeed, body.AngularVelocity.magnitude);
            }
            world.Simulate(); ticks++;
            trace.AppendLine(Newtonsoft.Json.JsonConvert.SerializeObject(new {
                ticks, time = world.Time, ball = V(world.Ball.position), velocity = V(world.Ball.linearVelocity),
                spin = V(world.Ball.angularVelocity), feet = V(body.Position), bodyVelocity = V(body.Velocity),
                shoulder = V(body.Shoulder), hand = V(body.Hand), paddle = V(body.Paddle.position),
                rotation = Q(body.Paddle.rotation), paddleVelocity = V(body.PaddleVelocity),
                angularVelocity = V(body.AngularVelocity), leftFoot = V(body.LeftFoot), rightFoot = V(body.RightFoot),
                planned = ActiveContact().Planned, impact = V(ActiveContact().Impact),
                impactAt = ActiveContact().ImpactAt, normal = V(ActiveContact().Normal), swingSpeed = ActiveContact().Swing,
                low = ActiveContact().LowContact, feasible = mode == 0 ? swing.PaddleStepFeasible : PaddleStepFeasible,
                events = Events()
            }));
            for (; seenContacts < world.Contacts.Count; seenContacts++)
            {
                var c = world.Contacts[seenContacts];
                if (c.player == player) contacts.Add(new { c.surface, c.time, normal = V(c.normal), outgoing = V(c.velocity), spin = V(c.spin),
                    planned = ActiveContact().Planned, low = ActiveContact().LowContact, plannedSwing = ActiveContact().Swing,
                    plannedImpactAt = ActiveContact().ImpactAt, paddleVelocity = V(body.PaddleVelocity) });
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
                EndSwingRampCase();
        }
        if (index == Count)
        {
            if (source != Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash()
                || scriptHash != Hash(scriptPath) || contactHash != Hash(contactPath))
                throw new System.InvalidOperationException("Diagnostic inputs changed.");
            UnityEditor.EditorApplication.update -= TickSwingRamp; SaveSwingRamp("complete");
        }
    }
    catch (System.Exception error)
    { world?.Dispose(); world = null; UnityEditor.EditorApplication.update -= TickSwingRamp; SaveSwingRamp("failed", error.ToString()); }
}
SaveSwingRamp("running"); UnityEditor.EditorApplication.update += TickSwingRamp;
return stem + ".json";

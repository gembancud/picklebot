// Development-only physical contact fixture. No actor or automatic foot movement.
if (!UnityEditor.EditorApplication.isPlaying) throw new System.InvalidOperationException("Start Play first.");
var rows = new System.Collections.Generic.List<object>();
var contact = Picklebot.Doubles.ContactModel.Load(System.IO.File.ReadAllText("Assets/Picklebot/Doubles/Models/contact.json"));
float[] V(UnityEngine.Vector3 p) => new[] { p.x, p.y, p.z };
foreach (int player in new[] { 0, 2 })
foreach (float depth in new[] { 5.5f, 6f, 6.5f, 7f })
foreach (bool residual in new[] { false, true })
{
    using var w = new Picklebot.Doubles.DoublesWorld(false);
    for (int tick = 0; tick < 480 && !w.ServeBounced; tick++) w.Simulate();
    var r = w.Rules;
    r.Serve(0, true, true, true, true, false, false, false, w.Time);
    r.Bounce(new UnityEngine.Vector3(r.ServiceX(r.DesignatedReceiver), 0, 4), w.Time);
    r.Hit(2, w.Time); r.Bounce(new UnityEngine.Vector3(1, 0, -4), w.Time); r.Hit(0, w.Time);
    if (player == 0) r.Hit(2, w.Time);
    UnityEngine.Vector3 World(UnityEngine.Vector3 p) => Picklebot.PlayerAgents.PlayerObservation.ToWorld(p, player);
    w.Players[player].Reset(World(new UnityEngine.Vector3(.82f, 0, -depth)));
    w.Players[player ^ 1].Reset(World(new UnityEngine.Vector3(-1.55f, 0, -6)));
    w.Ball.position = World(new UnityEngine.Vector3(1.2f, 1.2f, .4f)); w.Ball.transform.position = w.Ball.position;
    w.Ball.linearVelocity = World(new UnityEngine.Vector3(0, 1.2f, -8)); w.Ball.angularVelocity = UnityEngine.Vector3.zero;
    UnityEngine.Physics.SyncTransforms(); r.Events.Clear(); w.Contacts.Clear();
    var swing = new Picklebot.PlayerAgents.PlayerSwing(); var body = w.Players[player];
    var start = body.Position; float reach = 0, speed = 0, acceleration = 0, rotationSpeed = 0;
    var frames = new System.Collections.Generic.List<object>();
    var corrections = new System.Collections.Generic.List<object>();
    bool lowPlan = false; int infeasible = 0;
    for (int tick = 0; tick < 900 && !r.Dead; tick++)
    {
        var previous = body.PaddleVelocity;
        var beforeHand = body.Hand; var beforeShoulder = body.Shoulder; var beforePaddle = body.Paddle.position;
        swing.Step(w, player, new Picklebot.PlayerAgents.PlayerAction { attempt = true }, residual ? contact : null);
        lowPlan |= swing.Contact.LowContact;
        if (!swing.PaddleStepFeasible) infeasible++;
        speed = UnityEngine.Mathf.Max(speed, body.PaddleVelocity.magnitude);
        acceleration = UnityEngine.Mathf.Max(acceleration, (body.PaddleVelocity - previous).magnitude / Picklebot.Doubles.DoublesWorld.Dt);
        rotationSpeed = UnityEngine.Mathf.Max(rotationSpeed, body.AngularVelocity.magnitude);
        w.Simulate();
        if (!swing.PaddleStepFeasible || (body.PaddleVelocity - previous).magnitude / Picklebot.Doubles.DoublesWorld.Dt > 101)
            corrections.Add(new { w.Time, feasible = swing.PaddleStepFeasible, beforeHand = V(beforeHand), beforeShoulder = V(beforeShoulder), beforePaddle = V(beforePaddle),
                previousVelocity = V(previous), velocity = V(body.PaddleVelocity), hand = V(body.Hand), shoulder = V(body.Shoulder), paddle = V(body.Paddle.position),
                low = swing.Contact.LowContact, swing.Contact.Planned });
        reach = UnityEngine.Mathf.Max(reach, UnityEngine.Vector3.Distance(body.Hand, body.Shoulder));
        if (tick % 12 == 0) frames.Add(new { w.Time, ball = V(w.Ball.position), paddle = V(body.Paddle.position),
            shoulder = V(body.Shoulder), hand = V(body.Hand), low = swing.Contact.LowContact, swing.Contact.Planned,
            impact = V(swing.Contact.Impact), swing.Contact.ImpactAt });
        if (r.Events.Any(e => e.kind == "bounce" && e.position.z * body.Side < 0)) break;
    }
    rows.Add(new { player, depth, residual, lowPlan, reach, speed, acceleration, rotationSpeed, infeasible,
        movement = UnityEngine.Vector3.Distance(start, body.Position), fault = r.LastFault.ToString(),
        legalHit = r.Events.Any(e => e.kind == "hit" && e.player == player),
        legalLanding = r.Events.Any(e => e.kind == "bounce" && e.position.z * body.Side < 0),
        contacts = w.Contacts.Select(c => new { c.player, c.surface, c.time, point = V(c.point), velocity = V(c.velocity) }).ToArray(), frames, corrections });
}
string output = "artifacts/player-agents/low-contact-" + System.DateTime.UtcNow.ToString("yyyyMMdd-HHmmss") + ".json";
if (System.IO.File.Exists(output)) throw new System.IO.IOException("Output exists.");
System.IO.File.WriteAllText(output, Newtonsoft.Json.JsonConvert.SerializeObject(new {
    sourceHash = Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash(),
    scriptHash = Picklebot.Doubles.Editor.ContactTraining.Hash(System.IO.File.ReadAllText("scripts/player-low-contact-probe.cs")),
    split = "development", fixture = "stationary low rebound contact; no learned actor", rows
}, Newtonsoft.Json.Formatting.Indented));
return output;

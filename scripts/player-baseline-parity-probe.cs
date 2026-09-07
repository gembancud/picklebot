// Diagnose the first divergence without changing either controller.
if (!UnityEditor.EditorApplication.isPlaying) throw new System.InvalidOperationException("Start Play.");
const int seed = 1100600;
var contact = Picklebot.Doubles.ContactModel.Load(System.IO.File.ReadAllText("Assets/Picklebot/Doubles/Models/contact.json"));
Picklebot.Doubles.DoublesModels Models() => Picklebot.Doubles.DoublesModels.Load(System.IO.File.ReadAllText("Assets/Picklebot/Doubles/Models/teams.json"));
if (UnityEditor.EditorApplication.update.GetInvocationList().Any(d => d.Method.Name.Contains("TickBaselineParity") || d.Method.Name.Contains("TickFinal") || d.Method.Name.Contains("TickMotorTrace")))
    throw new System.InvalidOperationException("Finish the current diagnostic first.");
var original = new Picklebot.Doubles.DoublesMatch(false, seed) { CentreOnly = false, AutoNext = false, SampleActions = true, ContactModel = contact, Models = Models() };
var policies = new Picklebot.PlayerAgents.IPlayerPolicy[4];
for (int i = 0; i < 4; i++) policies[i] = new Picklebot.PlayerAgents.ConstantPlayerPolicy(default);
var adapted = new Picklebot.PlayerAgents.PlayerMatch(false, policies, contact, seed, new Picklebot.PlayerAgents.BaselineControl(3, Models(), contact, seed, true)) { AutoNext = false };
original.ServeJitter = adapted.ServeJitter = new UnityEngine.Vector2(.13f, -.27f);
float[] V(UnityEngine.Vector3 p) => new[] { p.x, p.y, p.z };
object State(Picklebot.Doubles.DoublesWorld w) => new { time = w.Time, phase = w.Rules.Phase.ToString(), hits = w.Rules.Hits, fault = w.Rules.LastFault.ToString(), ball = V(w.Ball.position), velocity = V(w.Ball.linearVelocity), contacts = w.Contacts.Count, events = w.Rules.Events.Count };
var ring = new System.Collections.Generic.Queue<object>();
int previous = 0, failedTick = -1, tick = 0;
string source = Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash();
string path = "artifacts/player-agents/baseline-parity-" + System.DateTime.UtcNow.ToString("yyyyMMdd-HHmmss") + ".json";
if (System.IO.File.Exists(path)) throw new System.IO.IOException("Output exists.");
object Contacts(Picklebot.Doubles.DoublesWorld w) => w.Contacts.Select(c => new { c.time, c.player, c.surface, point = V(c.point), normal = V(c.normal), incoming = V(c.incoming), velocity = V(c.velocity) }).ToArray();
object Events(Picklebot.Doubles.DoublesWorld w) => w.Rules.Events.Select(e => new { e.time, e.kind, e.player, e.winner, fault = e.fault.ToString(), position = V(e.position) }).ToArray();
void Finish(string error = null)
{
    UnityEditor.EditorApplication.update -= TickBaselineParity;
    try
    {
        var result = new { sourceHash = source, seed, failedTick, tick, error, originalRallies = original.CompletedRallies, adaptedRallies = adapted.CompletedRallies, actorDecisions = adapted.Actors.Decisions, originalContacts = Contacts(original.World), adaptedContacts = Contacts(adapted.World), originalEvents = Events(original.World), adaptedEvents = Events(adapted.World), frames = ring };
        System.IO.File.WriteAllText(path, Newtonsoft.Json.JsonConvert.SerializeObject(result, Newtonsoft.Json.Formatting.Indented));
        UnityEditor.SessionState.SetString("Picklebot.BaselineParity.Status", "complete: " + path);
    }
    finally { original.Dispose(); adapted.Dispose(); }
}
void TickBaselineParity()
{
  try
  {
    if (!UnityEditor.EditorApplication.isPlaying) { Finish("Play stopped"); return; }
    double until = UnityEditor.EditorApplication.timeSinceStartup + .02;
    while (UnityEditor.EditorApplication.timeSinceStartup < until)
    {
    original.Step(); adapted.Step();
    var bodies = new float[4]; var paddles = new float[4];
    for (int i = 0; i < 4; i++) { bodies[i] = UnityEngine.Vector3.Distance(original.World.Players[i].Position, adapted.World.Players[i].Position); paddles[i] = UnityEngine.Vector3.Distance(original.World.Players[i].Paddle.position, adapted.World.Players[i].Paddle.position); }
    float ball = UnityEngine.Vector3.Distance(original.World.Ball.position, adapted.World.Ball.position);
    float velocity = UnityEngine.Vector3.Distance(original.World.Ball.linearVelocity, adapted.World.Ball.linearVelocity);
    ring.Enqueue(new { tick, original = State(original.World), adapted = State(adapted.World), ball, velocity, bodies, paddles, clearance = adapted.Metrics.deadBallClearanceSteps });
    if (ring.Count > 16) ring.Dequeue();
    bool different = ball >= .0001f || velocity >= .0001f || original.World.Rules.Phase != adapted.World.Rules.Phase;
    for (int i = 0; i < 4; i++) different |= bodies[i] >= .0001f || paddles[i] >= .0001f;
    if (different) { failedTick = tick; Finish(); return; }
    if (original.CompletedRallies != previous) { previous = original.CompletedRallies; if (previous < 8) { original.Next(); adapted.Next(); } }
    tick++;
    if (tick >= 65000 || original.CompletedRallies >= 8) { Finish(); return; }
    }
  }
  catch (System.Exception error) { Finish(error.ToString()); }
}
UnityEditor.SessionState.SetString("Picklebot.BaselineParity.Status", "running: " + path);
UnityEditor.EditorApplication.update += TickBaselineParity;
return path;

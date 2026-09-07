// Development-only crossing and changing-direction partner stress.
// No model, teacher or ball target selects these movement commands.
string source = Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash();
var results = new System.Collections.Generic.List<object>();
for (int scenario = 0; scenario < 4; scenario++)
{
    using var w = new Picklebot.Doubles.DoublesWorld(false);
    var random = new System.Random(1100500 + scenario);
    w.Players[0].Reset(new Vector3(-.75f, 0, -5));
    w.Players[1].Reset(new Vector3(.75f, 0, -5.4f));
    var swings = new[] {new Picklebot.PlayerAgents.PlayerSwing(), new Picklebot.PlayerAgents.PlayerSwing()};
    var actions = new Picklebot.PlayerAgents.PlayerAction[2];
    float maxAcceleration = 0, minSeparation = float.MaxValue;
    int violations = 0, firstTick = -1;
    for (int tick = 0; tick < 4800; tick++)
    {
        for (int i = 0; i < 2; i++)
        {
            if (tick % 12 == 0)
            {
                var toward = (w.Players[i ^ 1].Position - w.Players[i].Position).normalized;
                var cross = new Vector3(-toward.z, 0, toward.x);
                var requested = toward + cross * (float)(random.NextDouble() * 3 - 1.5);
                if (scenario == 1) requested += Vector3.forward;
                if (scenario == 2 && tick % 480 < 240) requested = -requested;
                if (scenario == 3) requested += Vector3.right * 1.5f;
                requested = Vector3.ClampMagnitude(requested, 1);
                actions[i] = new Picklebot.PlayerAgents.PlayerAction {moveX = requested.x, moveZ = requested.z};
            }
            var before = w.Players[i].Velocity;
            swings[i].Step(w, i, tick % 960 >= 720 ? default : actions[i], null);
            float acceleration = (w.Players[i].Velocity - before).magnitude / Picklebot.Doubles.DoublesWorld.Dt;
            maxAcceleration = Mathf.Max(maxAcceleration, acceleration);
            if (acceleration > 14.05f) { violations++; if (firstTick < 0) firstTick = tick; }
        }
        minSeparation = Mathf.Min(minSeparation, Vector3.Distance(w.Players[0].Position, w.Players[1].Position));
        w.Simulate();
    }
    results.Add(new {scenario, seed = 1100500 + scenario, maxAcceleration, minSeparation, violations, firstTick});
}
if (source != Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash()) throw new System.InvalidOperationException("Source changed during stress.");
return new {sourceHash = source, results};

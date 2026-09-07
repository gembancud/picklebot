var results = new System.Collections.Generic.List<object>();
for (int scenario = 0; scenario < 4; scenario++)
{
    using var w = new Picklebot.Doubles.DoublesWorld(false);
    var rng = new System.Random(1100310 + scenario);
    w.Players[0].Reset(new Vector3(3, 0, -7));
    w.Players[1].Reset(new Vector3(scenario < 2 ? -3 : 2, 0, -6.5f));
    var swings = new[] {new Picklebot.PlayerAgents.PlayerSwing(), new Picklebot.PlayerAgents.PlayerSwing()};
    var actions = new Picklebot.PlayerAgents.PlayerAction[2];
    float maxAcceleration = 0, minSeparation = float.MaxValue, minBoundary = float.MaxValue;
    int violations = 0, firstTick = -1;
    for (int tick = 0; tick < 4800; tick++)
    {
        for (int i = 0; i < 2; i++)
        {
            if (tick % 12 == 0)
            {
                if (scenario == 0) actions[i] = new Picklebot.PlayerAgents.PlayerAction {moveX = i == 0 ? 1 : -1, moveZ = tick % 240 < 120 ? -1 : 1}.Validated();
                else if (scenario == 1) actions[i] = new Picklebot.PlayerAgents.PlayerAction {moveX = (float)(rng.NextDouble() * 2 - 1), moveZ = (float)(rng.NextDouble() * 2 - 1)}.Validated();
                else
                {
                    var target = scenario == 2 ? new Vector3(4.2f, 0, -8.1f) : w.Players[i ^ 1].Position;
                    var direction = (target - w.Players[i].Position).normalized;
                    actions[i] = new Picklebot.PlayerAgents.PlayerAction {moveX = direction.x, moveZ = direction.z};
                }
            }
            // Include one second of dead-ball settling after each burst.
            var action = tick % 960 >= 720 ? default : actions[i];
            var before = w.Players[i].Velocity;
            swings[i].Step(w, i, action, null);
            float acceleration = (w.Players[i].Velocity - before).magnitude / Picklebot.Doubles.DoublesWorld.Dt;
            maxAcceleration = Mathf.Max(maxAcceleration, acceleration);
            if (acceleration > 14.05f) { violations++; if (firstTick < 0) firstTick = tick; }
            var p = w.Players[i].Position;
            minBoundary = Mathf.Min(minBoundary, 4.2f - Mathf.Abs(p.x), -p.z - .38f, 8.1f + p.z);
        }
        minSeparation = Mathf.Min(minSeparation, Vector3.Distance(w.Players[0].Position, w.Players[1].Position));
        w.Simulate();
    }
    results.Add(new {scenario, maxAcceleration, minSeparation, minBoundary, violations, firstTick});
}
return new {sourceHash = Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash(), results};

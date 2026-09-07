// Restore a recorded motor state in a diagnostic world, then replay movement.
// Reflection is limited to this test's initial velocity. It is never a game action.
string path = "artifacts/player-agents/partner-motion-fixture-v1.csv";
var text = System.IO.File.ReadAllText(path);
var lines = System.IO.File.ReadAllLines(path);
var rows = new System.Collections.Generic.List<float[]>();
for (int n = 1; n < lines.Length; n++)
{
    var row = System.Linq.Enumerable.ToArray(System.Linq.Enumerable.Select(lines[n].Split(','), s => float.Parse(s, System.Globalization.CultureInfo.InvariantCulture)));
    if (row.Length != 9 || System.Linq.Enumerable.Any(row, x => !float.IsFinite(x))) throw new System.ArgumentException("Invalid fixture row.");
    if (row[1] == 2 || row[1] == 3) rows.Add(row);
}
if (rows.Count != 240) throw new System.ArgumentException("Expected 120 paired frames.");
using var w = new Picklebot.Doubles.DoublesWorld(false);
var swings = new[] {new Picklebot.PlayerAgents.PlayerSwing(), new Picklebot.PlayerAgents.PlayerSwing()};
for (int i = 0; i < 2; i++)
{
    var row = rows[i]; int id = (int)row[1];
    w.Players[id].Reset(new Vector3(row[2], 0, row[3]));
    typeof(Picklebot.Doubles.PlayerBody).GetProperty("Velocity").SetValue(w.Players[id], new Vector3(row[4], 0, row[5]));
}
float maxAcceleration = 0, minSeparation = float.MaxValue;
int firstViolationTick = -1, violations = 0;
for (int n = 0; n < rows.Count; n += 2)
{
    if (rows[n][0] != rows[n + 1][0] || rows[n][1] != 2 || rows[n + 1][1] != 3) throw new System.ArgumentException("Invalid paired frame order.");
    for (int i = 0; i < 2; i++)
    {
        var row = rows[n + i]; int id = (int)row[1];
        var local = Picklebot.PlayerAgents.PlayerObservation.ToLocal(new Vector3(row[6], 0, row[7]) / Picklebot.Doubles.PlayerBody.Speed, id);
        var oldVelocity = w.Players[id].Velocity;
        swings[i].Step(w, id, new Picklebot.PlayerAgents.PlayerAction {moveX = local.x, moveZ = local.z}, null);
        float acceleration = (w.Players[id].Velocity - oldVelocity).magnitude / Picklebot.Doubles.DoublesWorld.Dt;
        maxAcceleration = Mathf.Max(maxAcceleration, acceleration);
        if (acceleration > 14.05f) { violations++; if (firstViolationTick < 0) firstViolationTick = (int)row[0]; }
    }
    minSeparation = Mathf.Min(minSeparation, Vector3.Distance(w.Players[2].Position, w.Players[3].Position));
    w.Simulate();
}
return new {sourceHash = Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash(), fixtureHash = Picklebot.Doubles.Editor.ContactTraining.Hash(text),
    maxAcceleration, minSeparation, violations, firstViolationTick};

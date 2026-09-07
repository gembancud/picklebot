// Save the actual recent movement inputs that caused the third actor's fault.
// This is a diagnostic world. It does not change the saved scene or model.
string actorPath = "artifacts/player-agents/imitation-20260906-074116/actor.json";
var model = Picklebot.PlayerAgents.PlayerActorModel.Load(System.IO.File.ReadAllText(actorPath));
string source = Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash();
if (model.sourceHash != source) throw new System.InvalidOperationException("Fixture capture requires matching source.");
var policies = System.Linq.Enumerable.ToArray(System.Linq.Enumerable.Select(System.Linq.Enumerable.Range(0, 4), i => (Picklebot.PlayerAgents.IPlayerPolicy)new Picklebot.PlayerAgents.PlayerActor(model)));
using var match = new Picklebot.PlayerAgents.PlayerMatch(false, policies, Picklebot.Doubles.ContactModel.Load(System.IO.File.ReadAllText("Assets/Picklebot/Doubles/Models/contact.json")), 1100100) { AutoNext = false };
var random = new System.Random(1100100);
var recent = new System.Collections.Generic.Queue<string>();
for (int rally = 0; rally < 20; rally++)
{
    recent.Clear();
    match.ServeJitter = new Vector2((float)(random.NextDouble() * .6 - .3), (float)(random.NextDouble() * .8 - .4));
    int completed = match.CompletedRallies;
    while (match.CompletedRallies == completed)
    {
        var positions = System.Linq.Enumerable.ToArray(System.Linq.Enumerable.Select(match.World.Players, p => p.Position));
        var velocities = System.Linq.Enumerable.ToArray(System.Linq.Enumerable.Select(match.World.Players, p => p.Velocity));
        var phase = match.World.Rules.Phase;
        int tick = match.Tick;
        match.Step();
        int failedPlayer = -1; float maxAcceleration = 0;
        for (int i = 0; i < 4; i++)
        {
            var request = match.Swings[i].RequestedVelocity;
            var values = new[] {(float)tick, i, positions[i].x, positions[i].z, velocities[i].x, velocities[i].z, request.x, request.z, (float)phase};
            recent.Enqueue(string.Join(",", System.Linq.Enumerable.Select(values, x => x.ToString("R", System.Globalization.CultureInfo.InvariantCulture))));
            float acceleration = (match.World.Players[i].Velocity - velocities[i]).magnitude / Picklebot.Doubles.DoublesWorld.Dt;
            if (acceleration > 20) { failedPlayer = i; maxAcceleration = Mathf.Max(maxAcceleration, acceleration); }
        }
        while (recent.Count > 480) recent.Dequeue();
        if (failedPlayer >= 0)
        {
            if (source != Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash()) throw new System.InvalidOperationException("Source changed during fixture capture.");
            string output = "artifacts/player-agents/partner-motion-fixture-v1.csv";
            var lines = new System.Collections.Generic.List<string> {"tick,player,x,z,vx,vz,requestX,requestZ,phase"};
            lines.AddRange(recent); System.IO.File.WriteAllLines(output, lines);
            return new {sourceHash = source, actorPath, rally, failedPlayer, maxAcceleration, path = output, frames = recent.Count / 4};
        }
    }
    if (match.World.Rules.GameWinner >= 0) break;
    match.Next();
}
return "No correction found; no fixture saved.";

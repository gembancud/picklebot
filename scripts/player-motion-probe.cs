// Development-only first-failure trace. This does not mutate the saved scene.
var model = Picklebot.PlayerAgents.PlayerActorModel.Load(System.IO.File.ReadAllText("artifacts/player-agents/imitation-20260906-074116/actor.json"));
string source = Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash();
if (model.sourceHash != source) throw new System.InvalidOperationException("Use a source-matched actor for this trace.");
var policies = System.Linq.Enumerable.ToArray(System.Linq.Enumerable.Select(System.Linq.Enumerable.Range(0, 4), i => (Picklebot.PlayerAgents.IPlayerPolicy)new Picklebot.PlayerAgents.PlayerActor(model)));
using var match = new Picklebot.PlayerAgents.PlayerMatch(false, policies, Picklebot.Doubles.ContactModel.Load(System.IO.File.ReadAllText("Assets/Picklebot/Doubles/Models/contact.json")), 1100100) { AutoNext = false };
var random = new System.Random(1100100);
for (int rally = 0; rally < 20; rally++)
{
    match.ServeJitter = new UnityEngine.Vector2((float)(random.NextDouble() * .6 - .3), (float)(random.NextDouble() * .8 - .4));
    int completed = match.CompletedRallies;
    while (match.CompletedRallies == completed)
    {
        var positions = System.Linq.Enumerable.ToArray(System.Linq.Enumerable.Select(match.World.Players, p => p.Position));
        var velocities = System.Linq.Enumerable.ToArray(System.Linq.Enumerable.Select(match.World.Players, p => p.Velocity));
        var phase = match.World.Rules.Phase;
        match.Step();
        for (int i = 0; i < 4; i++)
        {
            float acceleration = (match.World.Players[i].Velocity - velocities[i]).magnitude / Picklebot.Doubles.DoublesWorld.Dt;
            if (acceleration > 20)
                return new { sourceHash = source, rally, time = match.World.Time, phase, player = i, acceleration, beforePosition = positions[i],
                    afterPosition = match.World.Players[i].Position, beforeVelocity = velocities[i], afterVelocity = match.World.Players[i].Velocity,
                    partnerPosition = positions[i ^ 1], partnerVelocity = velocities[i ^ 1], requested = match.Swings[i].RequestedVelocity,
                    limited = match.Swings[i].AppliedVelocity, action = match.Actors.ActionFor(i) };
        }
    }
    if (match.World.Rules.GameWinner >= 0) break;
    match.Next();
}
return "No correction above 20 m/s² in this probe.";

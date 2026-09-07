var path = "artifacts/player-agents/unresolved-probe-20260906-1645.json";
if (System.IO.File.Exists(path)) throw new System.InvalidOperationException("Preserve the existing probe report.");
var flags = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static;
var instanceFlags = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var field = typeof(Picklebot.PlayerAgents.Editor.PlayerCurriculum).GetField("match", flags);
UnityEditor.EditorApplication.CallbackFunction check = null;
check = () => {
    var match = field.GetValue(null) as Picklebot.PlayerAgents.PlayerMatch;
    if (match == null) { UnityEditor.EditorApplication.update -= check; return; }
    if (match.World.Time < 34) return;
    var world = match.World;
    var pending = (bool[])typeof(Picklebot.Doubles.DoublesRules).GetField("volleyPending", instanceFlags).GetValue(world.Rules);
    var result = new {
        sourceHash = Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash(),
        time = world.Time, phase = world.Rules.Phase.ToString(), fault = world.Rules.LastFault.ToString(),
        winner = world.Rules.Winner, hits = world.Rules.Hits, pending = (bool[])pending.Clone(),
        eventCount = world.Rules.Events.Count,
        firstEvents = world.Rules.Events.Take(12).ToArray(), lastEvents = world.Rules.Events.TakeLast(12).ToArray(),
        players = world.Players.Select(p => new {
            position = new[] {p.Position.x,p.Position.y,p.Position.z},
            velocity = new[] {p.Velocity.x,p.Velocity.y,p.Velocity.z},
            feetInKitchen = p.FeetInKitchen, bothFeetOutside = p.BothFeetOutside, balanceRecovered = p.BalanceRecovered
        }).ToArray()
    };
    System.IO.File.WriteAllText(path, Newtonsoft.Json.JsonConvert.SerializeObject(result, Newtonsoft.Json.Formatting.Indented));
    UnityEditor.EditorApplication.update -= check;
};
UnityEditor.EditorApplication.update += check;
return path;

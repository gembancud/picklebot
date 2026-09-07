// Offline flight diagnosis in the live Editor. No world, actor or collider is changed.
// The impulse comparisons omit friction and brush transfer. They are not PhysX replays.
string Hash(string path)
{
    using var algorithm = System.Security.Cryptography.SHA256.Create();
    using var input = System.IO.File.OpenRead(path);
    return System.BitConverter.ToString(algorithm.ComputeHash(input)).Replace("-", "").ToLowerInvariant();
}
UnityEngine.Vector3 V(Newtonsoft.Json.Linq.JToken value)
{
    if (!(value is Newtonsoft.Json.Linq.JArray a) || a.Count != 3)
        throw new System.ArgumentException("Expected a three-element vector.");
    var result = new UnityEngine.Vector3((float)a[0], (float)a[1], (float)a[2]);
    if (!float.IsFinite(result.x) || !float.IsFinite(result.y) || !float.IsFinite(result.z))
        throw new System.ArgumentException("Non-finite vector.");
    return result;
}
float[] A(UnityEngine.Vector3 value) => new[] { value.x, value.y, value.z };
string source = Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash();
string script = "scripts/player-flight-plan-audit.cs", scriptHash = Hash(script);
string[] paths = { "artifacts/player-agents/contact-outcomes-20260907-052617.json",
    "artifacts/player-agents/contact-outcomes-20260907-052833.json" };
string[] hashes = paths.Select(Hash).ToArray();
string output = "artifacts/player-agents/flight-plan-audit-" + System.DateTime.UtcNow.ToString("yyyyMMdd-HHmmss") + ".json";
if (System.IO.File.Exists(output)) throw new System.IO.IOException("Output exists.");
var config = UnityEngine.ScriptableObject.CreateInstance<Picklebot.Core.SimulationConfigV1>();
var rows = new System.Collections.Generic.List<object>();
int skippedUnplanned = 0, skippedContactCount = 0, skippedNonface = 0;
object Flight(UnityEngine.Vector3 p, UnityEngine.Vector3 velocity, UnityEngine.Vector3 spin, UnityEngine.Vector3 target, int side)
{
    UnityEngine.Vector3? crossing = null, floor = null;
    float? crossingTime = null, floorTime = null, clearance = null;
    for (int step = 1; step <= 960; step++)
    {
        var before = p;
        Picklebot.Doubles.StrokeController.Fly(ref p, ref velocity, ref spin, config, Picklebot.Doubles.DoublesWorld.Dt);
        if (!crossing.HasValue && before.z * side > 0 && p.z * side <= 0)
        {
            float fraction = before.z / (before.z - p.z);
            crossing = UnityEngine.Vector3.Lerp(before, p, fraction);
            crossingTime = (step - 1 + fraction) * Picklebot.Doubles.DoublesWorld.Dt;
            if (UnityEngine.Mathf.Abs(crossing.Value.x) <= Picklebot.Core.CourtGeometryV1.HalfNetPostSpan)
                clearance = crossing.Value.y - config.BallDiameter / 2f
                    - Picklebot.Core.CourtGeometryV1.NetHeightAtX(crossing.Value.x);
        }
        if (p.y <= config.BallDiameter / 2f && velocity.y < 0)
        {
            float fraction = UnityEngine.Mathf.Clamp01((before.y - config.BallDiameter / 2f) / (before.y - p.y));
            floor = UnityEngine.Vector3.Lerp(before, p, fraction);
            floorTime = (step - 1 + fraction) * Picklebot.Doubles.DoublesWorld.Dt;
            break;
        }
    }
    return new { crossedNetPlane = crossing.HasValue, netCrossing = crossing.HasValue ? A(crossing.Value) : null,
        crossingTime, netClearance = clearance, floor = floor.HasValue ? A(floor.Value) : null, floorTime,
        floorInOppositeCourt = floor.HasValue && floor.Value.z * side < 0
            && UnityEngine.Mathf.Abs(floor.Value.x) <= Picklebot.Doubles.DoublesRules.HalfWidth
            && UnityEngine.Mathf.Abs(floor.Value.z) <= Picklebot.Doubles.DoublesRules.HalfLength,
        targetError = floor.HasValue ? (float?)UnityEngine.Vector2.Distance(new UnityEngine.Vector2(floor.Value.x, floor.Value.z),
            new UnityEngine.Vector2(target.x, target.z)) : null };
}
try
{
    config.ValidateOrThrow();
    for (int reportIndex = 0; reportIndex < paths.Length; reportIndex++)
    {
        var report = Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(paths[reportIndex]));
        if ((string)report["status"] != "complete" || (string)report["split"] != "development"
            || (string)report["sourceHash"] != source || (string)report["configurationHash"] != config.ConfigurationHash
            || (string)report["contactHash"] != Hash("Assets/Picklebot/Doubles/Models/contact.json"))
            throw new System.InvalidOperationException("Stale or incompatible contact report.");
        foreach (var rally in report["rallies"])
        foreach (var shot in rally["shots"])
        {
            if (!(bool)shot["planned"]) { skippedUnplanned++; continue; }
            var contacts = (Newtonsoft.Json.Linq.JArray)shot["contacts"];
            if (contacts.Count != 1) { skippedContactCount++; continue; }
            var contact = contacts[0];
            if ((string)contact["surface"] != "RoundedHittingFace") { skippedNonface++; continue; }
            int player = (int)shot["player"], side = player < 2 ? -1 : 1;
            var p = V(shot["ballPosition"]); var target = V(shot["target"]);
            var incoming = V(contact["incoming"]); var outgoing = V(contact["outgoing"]); var spin = V(contact["spin"]);
            var normal = V(shot["plannedNormal"]).normalized;
            var actualNormal = V(contact["normal"]).normalized;
            if (UnityEngine.Vector3.Dot(actualNormal, normal) < 0) actualNormal = -actualNormal;
            float speed = (float)shot["plannedSwing"];
            var pointVelocity = V(shot["paddleVelocity"]) + UnityEngine.Vector3.Cross(V(shot["paddleAngularVelocity"]),
                V(contact["point"]) - V(shot["paddlePosition"]));
            float actualNormalSpeed = UnityEngine.Vector3.Dot(pointVelocity, actualNormal);
            var plannedImpulse = incoming + (1 + config.PaddleRestitution)
                * (speed - UnityEngine.Vector3.Dot(incoming, normal)) * normal;
            var measuredImpulse = incoming + (1 + config.PaddleRestitution)
                * (actualNormalSpeed - UnityEngine.Vector3.Dot(incoming, actualNormal)) * actualNormal;
            rows.Add(new { reportIndex, gameSeed = (int)rally["gameSeed"], rally = (int)rally["rally"],
                player, eventIndex = (int)shot["eventIndex"], selectedShot = (int)shot["selectedShot"],
                lowContact = (bool)shot["lowContact"], phaseBefore = (string)shot["phaseBefore"],
                plannedSpeed = speed, actualNormalSpeed, normalAngle = UnityEngine.Vector3.Angle(normal, actualNormal),
                plannedNormal = A(normal), actualNormal = A(actualNormal), incoming = A(incoming),
                recordedOutgoing = A(outgoing), recordedSpin = A(spin), pointVelocity = A(pointVelocity),
                plannedImpulseOutgoing = A(plannedImpulse), measuredImpulseOutgoing = A(measuredImpulse),
                recordedFlight = Flight(p, outgoing, spin, target, side),
                recordedWithoutSpin = Flight(p, outgoing, UnityEngine.Vector3.zero, target, side),
                plannedImpulseFlight = Flight(p, plannedImpulse, UnityEngine.Vector3.zero, target, side),
                measuredImpulseFlight = Flight(p, measuredImpulse, UnityEngine.Vector3.zero, target, side) });
        }
    }
    if (source != Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash() || Hash(script) != scriptHash
        || paths.Where((path, i) => Hash(path) != hashes[i]).Any())
        throw new System.InvalidOperationException("Audit inputs changed.");
    System.IO.File.Copy(script, output + ".collector.cs");
    System.IO.File.WriteAllText(output, Newtonsoft.Json.JsonConvert.SerializeObject(new {
        version = "player-flight-plan-audit-v1", status = "complete", sourceHash = source,
        configurationHash = config.ConfigurationHash, scriptHash, paths, reportHashes = hashes,
        skippedUnplanned, skippedContactCount, skippedNonface, rows,
        limitation = "Offline counterfactual flight, not physical replay or match performance. No collision or opponent interception. "
            + "Net clearance uses the geometric net profile. Impulse branches omit friction, brush and spin transfer; "
            + "recorded incoming is pre-physics-step, not exact impact velocity. These comparisons do not prove a motor or solver cause."
    }, Newtonsoft.Json.Formatting.Indented));
}
finally { UnityEngine.Object.DestroyImmediate(config); }
return output;

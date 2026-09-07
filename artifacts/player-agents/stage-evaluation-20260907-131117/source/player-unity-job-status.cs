// Read-only Unity eval_file. Generated local-function names do not start with Tick.
bool IsJob(System.Delegate d) {
    string owner = d.Method.DeclaringType?.FullName ?? "";
    return (owner.StartsWith("PipelineEvaluation.") && d.Method.Name.Contains("g__Tick"))
        || (owner.StartsWith("Picklebot.") && d.Method.Name.Contains("Tick"));
}
void TickStatusProbe() { }
bool generatedCallbackDetection = IsJob(new UnityEditor.EditorApplication.CallbackFunction(TickStatusProbe));
if (!generatedCallbackDetection) throw new System.InvalidOperationException("Cannot identify generated test callbacks.");
var jobs = UnityEditor.EditorApplication.update.GetInvocationList().Where(IsJob)
    .Select(d => new { name = d.Method.Name, owner = d.Method.DeclaringType.FullName }).ToArray();
bool running = Picklebot.PlayerAgents.Editor.PlayerCompetition.Running
    || Picklebot.PlayerAgents.Editor.PlayerCurriculum.Running || Picklebot.PlayerAgents.Editor.PlayerEvaluation.Running
    || Picklebot.PlayerAgents.Editor.PlayerTeacher.Running || Picklebot.PlayerAgents.Editor.PlayerControlProbe.Running
    || Picklebot.PlayerAgents.Editor.PlayerDiagnostics.Running;
return new { playing = UnityEditor.EditorApplication.isPlaying, busy = running || jobs.Length > 0, jobs, generatedCallbackDetection,
    source = Picklebot.PlayerAgents.Editor.PlayerDiagnostics.SourceHash(),
    finalStatus = UnityEditor.SessionState.GetString("Picklebot.Final.Status", "missing") };

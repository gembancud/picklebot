param(
    [Parameter(Mandatory=$true)][string]$Actor,
    [Parameter(Mandatory=$true)][string]$Output,
    [Parameter(Mandatory=$true)][int]$FirstSeed,
    [Parameter(Mandatory=$true)][int]$Episodes,
    [ValidateSet('interactive','development','training')][string]$Split='interactive',
    [ValidateSet('contact','reaction-contact','reaction-return','near-return','drop-serve')][string]$Task='reaction-contact',
    [switch]$Stationary,
    [switch]$FixedPolicy
)
$ErrorActionPreference='Stop'
$project='F:\dev\picklebot'
$cli=Join-Path $env:LOCALAPPDATA 'Unity\bin\unity.exe'
function Invoke-Eval([string]$Code) {
    $r=(& $cli command eval $Code --project-path $project --format json | ConvertFrom-Json)
    if(-not $r.success -or -not $r.data.result.success){throw ($r | ConvertTo-Json -Depth 12)}
    return $r.data.result.result
}
function Cs-String([string]$Value) {return '"'+$Value.Replace('\','\\').Replace('"','\"')+'"'}
if(Test-Path -LiteralPath (Join-Path $project $Output)){throw 'Rollout evidence already exists'}
$null=Invoke-Eval 'if(UnityEditor.EditorApplication.isCompiling||UnityEditor.EditorUtility.scriptCompilationFailed||Picklebot.PlayerControlsIntegration.Editor.PlayerDrillRolloutV3.Running)throw new System.InvalidOperationException("Compiled idle Unity required"); UnityEditor.EditorApplication.isPlaying=true; return "enter play";'
$watch=[Diagnostics.Stopwatch]::StartNew()
do {
    Start-Sleep -Milliseconds 300
    $playing=Invoke-Eval 'return UnityEditor.EditorApplication.isPlaying;'
    if($watch.Elapsed.TotalSeconds -gt 30){throw 'Play Mode did not start'}
} while(-not $playing)
$code='Picklebot.PlayerControlsIntegration.Editor.PlayerDrillRolloutV3.Start({0},{1},{2},{3},{4},{5},{6},{7});return Picklebot.PlayerControlsIntegration.Editor.PlayerDrillRolloutV3.Status;' -f (Cs-String $Actor),(Cs-String $Output),$FirstSeed,$Episodes,(Cs-String $Split),(Cs-String $Task),(-not $FixedPolicy).ToString().ToLowerInvariant(),$Stationary.IsPresent.ToString().ToLowerInvariant()
$null=Invoke-Eval $code
$reportPath=Join-Path (Join-Path $project $Output) 'report.json'
while(-not (Test-Path -LiteralPath $reportPath)) {
    Start-Sleep -Seconds 2
    if($watch.Elapsed.TotalMinutes -gt 20){throw 'Collector timeout; inspect the existing run before retrying'}
}
$report=Get-Content -LiteralPath $reportPath -Raw | ConvertFrom-Json
if($report.status -ne 'complete'){throw ($report | Select-Object status,failure | ConvertTo-Json)}
$counts=@{}
foreach($e in $report.episodes){$counts[$e.outcome]++}
[pscustomobject]@{output=$Output;task=$report.task;episodes=$report.episodes.Count;outcomes=$counts;seconds=$report.elapsedSeconds} | ConvertTo-Json -Depth 5 -Compress

#requires -Version 7.0

param(
  [Parameter(Mandatory = $true)][string]$RepositoryRoot,
  [Parameter(Mandatory = $true)][string]$CandidateRevision,
  [Parameter(Mandatory = $true)][string]$TaskRoot,
  [Parameter(Mandatory = $true)][string]$EvidenceOutput
)

$ErrorActionPreference = 'Stop'
$CommandTimeoutSeconds = 60

if (-not $IsWindows) {
  throw 'GT-20 exact package lifecycle evaluator requires Windows.'
}

function ConvertTo-PortablePath {
  param([Parameter(Mandatory = $true)][string]$Path)
  $value = [System.IO.Path]::GetFullPath($Path)
  foreach ($item in @(
    @($env:LOCALAPPDATA, '%LOCALAPPDATA%'),
    @($env:APPDATA, '%APPDATA%'),
    @($env:USERPROFILE, '%USERPROFILE%')
  )) {
    if ($item[0] -and $value.StartsWith(
        [System.IO.Path]::GetFullPath($item[0]),
        [System.StringComparison]::OrdinalIgnoreCase)) {
      return $item[1] + $value.Substring([System.IO.Path]::GetFullPath($item[0]).Length)
    }
  }
  return $value
}

function Invoke-Captured {
  param(
    [Parameter(Mandatory = $true)][string]$File,
    [Parameter(Mandatory = $true)][string[]]$Arguments,
    [Parameter(Mandatory = $true)][string]$WorkingDirectory,
    [hashtable]$Environment = @{},
    [string]$InputText = ''
  )
  $command = Get-Command "$File.exe" -CommandType Application -ErrorAction SilentlyContinue |
    Select-Object -First 1
  if ($null -eq $command) {
    $command = Get-Command "$File.cmd" -CommandType Application -ErrorAction Stop |
      Select-Object -First 1
  }
  $info = [System.Diagnostics.ProcessStartInfo]::new()
  $isCommandShim = [System.IO.Path]::GetExtension($command.Source) -eq '.cmd'
  $info.FileName = if ($isCommandShim) { $env:ComSpec } else { $command.Source }
  $info.WorkingDirectory = $WorkingDirectory
  $info.UseShellExecute = $false
  $info.RedirectStandardOutput = $true
  $info.RedirectStandardError = $true
  $info.RedirectStandardInput = $true
  if ($isCommandShim) {
    foreach ($argument in @('/d', '/s', '/c', $command.Source)) {
      [void]$info.ArgumentList.Add($argument)
    }
  }
  foreach ($argument in $Arguments) {
    [void]$info.ArgumentList.Add($argument)
  }
  foreach ($entry in $Environment.GetEnumerator()) {
    $info.Environment[$entry.Key] = [string]$entry.Value
  }
  $process = [System.Diagnostics.Process]::new()
  $process.StartInfo = $info
  [void]$process.Start()
  if ($InputText.Length -gt 0) {
    $process.StandardInput.Write($InputText)
  }
  $process.StandardInput.Close()
  $stdout = $process.StandardOutput.ReadToEndAsync()
  $stderr = $process.StandardError.ReadToEndAsync()
  $timedOut = -not $process.WaitForExit($CommandTimeoutSeconds * 1000)
  if ($timedOut) {
    try { $process.Kill($true) } catch { }
    $process.WaitForExit()
  }
  $exitCode = if ($timedOut) { 124 } else { $process.ExitCode }
  return [ordered]@{
    argv = @($File) + $Arguments
    resolvedCommand = ConvertTo-PortablePath $command.Source
    resolvedCommandSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $command.Source).Hash.ToLowerInvariant()
    launcher = ConvertTo-PortablePath $info.FileName
    launcherSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $info.FileName).Hash.ToLowerInvariant()
    timeoutSeconds = $CommandTimeoutSeconds
    timedOut = $timedOut
    exitCode = $exitCode
    stdout = $stdout.Result
    stderr = $stderr.Result
  }
}

function Assert-Exit {
  param([System.Collections.IDictionary]$Result, [int]$Expected, [string]$Label)
  if ($Result.exitCode -ne $Expected) {
    throw "$Label exit code $($Result.exitCode), expected $Expected"
  }
}

function Get-FileMap {
  param([string]$Root)
  $resolved = [System.IO.Path]::GetFullPath($Root)
  $map = [ordered]@{}
  foreach ($file in Get-ChildItem -LiteralPath $resolved -Recurse -File | Sort-Object FullName) {
    $relative = [System.IO.Path]::GetRelativePath($resolved, $file.FullName).Replace('\', '/')
    $map[$relative] = (Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName).Hash.ToLowerInvariant()
  }
  return $map
}

function Assert-FileMapsEqual {
  param([string]$ExpectedRoot, [string]$ActualRoot, [string]$Label)
  $expected = Get-FileMap $ExpectedRoot
  $actual = Get-FileMap $ActualRoot
  if (($expected | ConvertTo-Json -Compress) -ne ($actual | ConvertTo-Json -Compress)) {
    throw "$Label installed bytes differ"
  }
  return $actual.Count
}

function Read-JsonOutput {
  param([System.Collections.IDictionary]$Result, [string]$Label)
  try {
    return $Result.stdout | ConvertFrom-Json
  } catch {
    throw "$Label did not return JSON"
  }
}

function Assert-InstalledInventory {
  param(
    [System.Collections.IDictionary]$Result,
    [ValidateSet('codex', 'claude')][string]$HostId,
    [string]$ExpectedVersion,
    [string]$Label
  )
  $value = Read-JsonOutput $Result $Label
  $items = if ($HostId -eq 'codex') { @($value.installed) } else { @($value) }
  $expectedId = if ($HostId -eq 'codex') {
    'yiyuan-accord-codex@yiyuan-accord'
  } else {
    'yiyuan-accord-claude@yiyuan-accord'
  }
  $actualId = if ($HostId -eq 'codex') { $items[0].pluginId } else { $items[0].id }
  if ($items.Count -ne 1 -or $actualId -ne $expectedId -or
      $items[0].version -ne $ExpectedVersion -or -not $items[0].enabled) {
    throw "$Label inventory is invalid."
  }
}

function Get-RunnerProcessIds {
  $ids = [System.Collections.Generic.HashSet[int]]::new()
  $current = $PID
  for ($depth = 0; $depth -lt 16 -and $current -gt 0; $depth++) {
    if (-not $ids.Add($current)) { break }
    $entry = Get-CimInstance -Query (
      "SELECT ProcessId, ParentProcessId FROM Win32_Process WHERE ProcessId=$current"
    )
    if ($null -eq $entry) { break }
    $current = [int]$entry.ParentProcessId
  }
  return @($ids)
}

function Get-TaskProcessIds {
  param([Parameter(Mandatory = $true)][string]$TaskPath)
  $escapedTask = $TaskPath.Replace('\', '\\').Replace("'", "''")
  $runnerProcesses = @(Get-RunnerProcessIds)
  return @(Get-CimInstance -Query (
    "SELECT ProcessId FROM Win32_Process WHERE CommandLine LIKE '%$escapedTask%'"
  ) | ForEach-Object { [int]$_.ProcessId } | Where-Object {
    $_ -notin $runnerProcesses
  })
}

function Stop-TaskProcesses {
  param([Parameter(Mandatory = $true)][string]$TaskPath)
  for ($attempt = 0; $attempt -lt 5; $attempt++) {
    $processIds = @(Get-TaskProcessIds $TaskPath)
    if ($processIds.Count -eq 0) { return @() }
    foreach ($processId in $processIds) {
      try {
        $owned = [System.Diagnostics.Process]::GetProcessById($processId)
        $owned.Kill($true)
        [void]$owned.WaitForExit(5000)
      } catch { }
    }
    Start-Sleep -Milliseconds 200
  }
  return @(Get-TaskProcessIds $TaskPath)
}

$repository = [System.IO.Path]::GetFullPath($RepositoryRoot)
$task = [System.IO.Path]::GetFullPath($TaskRoot)
$evidencePath = [System.IO.Path]::GetFullPath($EvidenceOutput)
$temporaryBase = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
if (-not $task.StartsWith($temporaryBase, [System.StringComparison]::OrdinalIgnoreCase) -or
    -not ([System.IO.Path]::GetFileName($task)).StartsWith('yiyuan-accord-gt20-formal-')) {
  throw 'TaskRoot must be a specifically named temporary directory.'
}
if ($task.StartsWith($repository, [System.StringComparison]::OrdinalIgnoreCase)) {
  throw 'TaskRoot must be outside the repository.'
}
if (-not $evidencePath.StartsWith($temporaryBase, [System.StringComparison]::OrdinalIgnoreCase) -or
    -not ([System.IO.Path]::GetFileName($evidencePath)).StartsWith('yiyuan-accord-gt20-formal-evidence-') -or
    [System.IO.Path]::GetExtension($evidencePath) -ne '.json' -or
    $evidencePath.StartsWith($task, [System.StringComparison]::OrdinalIgnoreCase) -or
    $evidencePath.StartsWith($repository, [System.StringComparison]::OrdinalIgnoreCase)) {
  throw 'EvidenceOutput must be a specifically named temporary JSON file outside the task root and repository.'
}
if (Test-Path -LiteralPath $task) {
  throw 'TaskRoot must not already exist.'
}
if (Test-Path -LiteralPath $evidencePath) {
  throw 'EvidenceOutput must not already exist.'
}
if ($CandidateRevision -notmatch '^[0-9a-f]{40}$') {
  throw 'CandidateRevision must be a lowercase 40-character Git object id.'
}
$resolvedCommit = git -C $repository rev-parse --verify "$CandidateRevision`^{commit}" 2>$null
if ($LASTEXITCODE -ne 0 -or $resolvedCommit.Trim() -ne $CandidateRevision) {
  throw 'CandidateRevision is not an exact commit.'
}

$commands = [System.Collections.Generic.List[object]]::new()
$succeeded = $false
try {
New-Item -ItemType Directory -Path $task | Out-Null
$oldSource = Join-Path $task 'old-source'
$candidateSource = Join-Path $task 'candidate-source'
$mutableSource = Join-Path $task 'mutable-source'
$codexRoot = Join-Path $task 'codex-host'
$claudeRoot = Join-Path $task 'claude-host'
foreach ($path in ($oldSource, $candidateSource, $codexRoot, $claudeRoot)) {
  New-Item -ItemType Directory -Path $path | Out-Null
}

$gitVersion = Invoke-Captured git @('--version') $task
$commands.Add($gitVersion)
Assert-Exit $gitVersion 0 'Git version'
$tarVersion = Invoke-Captured tar @('--version') $task
$commands.Add($tarVersion)
Assert-Exit $tarVersion 0 'tar version'

$oldArchive = Join-Path $task 'old.tar'
$candidateArchive = Join-Path $task 'candidate.tar'
$archiveOld = Invoke-Captured git @('-C', $repository, 'archive', '--format=tar', "--output=$oldArchive", 'v3.0.1') $repository
$commands.Add($archiveOld)
Assert-Exit $archiveOld 0 'archive old release'
$archiveCandidate = Invoke-Captured git @('-C', $repository, 'archive', '--format=tar', "--output=$candidateArchive", $CandidateRevision) $repository
$commands.Add($archiveCandidate)
Assert-Exit $archiveCandidate 0 'archive candidate'
$extractOld = Invoke-Captured tar @('-xf', $oldArchive, '-C', $oldSource) $task
$commands.Add($extractOld)
Assert-Exit $extractOld 0 'extract old release'
$extractCandidate = Invoke-Captured tar @('-xf', $candidateArchive, '-C', $candidateSource) $task
$commands.Add($extractCandidate)
Assert-Exit $extractCandidate 0 'extract candidate'
Copy-Item -LiteralPath $oldSource -Destination $mutableSource -Recurse

$codexAgents = Join-Path $codexRoot 'AGENTS.md'
$codexConfig = Join-Path $codexRoot 'config.toml'
$claudeInstructions = Join-Path $claudeRoot 'CLAUDE.md'
$claudeSettings = Join-Path $claudeRoot 'settings.json'
Set-Content -LiteralPath $codexAgents -Encoding utf8 -NoNewline -Value "USER_CODEX_INSTRUCTIONS`n"
Set-Content -LiteralPath $codexConfig -Encoding utf8 -NoNewline -Value "# USER_CODEX_CONFIG`n"
Set-Content -LiteralPath $claudeInstructions -Encoding utf8 -NoNewline -Value "USER_CLAUDE_INSTRUCTIONS`n"
Set-Content -LiteralPath $claudeSettings -Encoding utf8 -NoNewline -Value "{`"permissions`":{`"allow`":[]},`"userSentinel`":`"USER_CLAUDE_SETTINGS`"}`n"
New-Item -ItemType Directory -Path (Join-Path $codexRoot 'foreign-plugin'), (Join-Path $claudeRoot 'foreign-plugin') | Out-Null
Set-Content -LiteralPath (Join-Path $codexRoot 'foreign-plugin/sentinel.txt') -Encoding utf8 -NoNewline -Value 'FOREIGN_CODEX'
Set-Content -LiteralPath (Join-Path $claudeRoot 'foreign-plugin/sentinel.txt') -Encoding utf8 -NoNewline -Value 'FOREIGN_CLAUDE'
Set-Content -LiteralPath (Join-Path $codexRoot 'shared-dependency.txt') -Encoding utf8 -NoNewline -Value 'SHARED_CODEX'
Set-Content -LiteralPath (Join-Path $claudeRoot 'shared-dependency.txt') -Encoding utf8 -NoNewline -Value 'SHARED_CLAUDE'

$codexEnvironment = @{CODEX_HOME = $codexRoot}
$claudeEnvironment = @{CLAUDE_CONFIG_DIR = $claudeRoot}
$codexVersion = Invoke-Captured codex @('--version') $task $codexEnvironment
$commands.Add($codexVersion)
Assert-Exit $codexVersion 0 'Codex version'
$claudeVersion = Invoke-Captured claude @('--version') $task $claudeEnvironment
$commands.Add($claudeVersion)
Assert-Exit $claudeVersion 0 'Claude version'
$nodeVersion = Invoke-Captured node @('--version') $task
$commands.Add($nodeVersion)
Assert-Exit $nodeVersion 0 'Node version'
$codexMarketplace = Invoke-Captured codex @('plugin', 'marketplace', 'add', $mutableSource, '--json') $mutableSource $codexEnvironment
$commands.Add($codexMarketplace)
Assert-Exit $codexMarketplace 0 'Codex marketplace add'
$claudeMarketplace = Invoke-Captured claude @('plugin', 'marketplace', 'add', $mutableSource, '--scope', 'user') $mutableSource $claudeEnvironment
$commands.Add($claudeMarketplace)
Assert-Exit $claudeMarketplace 0 'Claude marketplace add'
$codexInstall = Invoke-Captured codex @('plugin', 'add', 'yiyuan-accord-codex@yiyuan-accord', '--json') $mutableSource $codexEnvironment
$commands.Add($codexInstall)
Assert-Exit $codexInstall 0 'Codex install'
$claudeInstall = Invoke-Captured claude @('plugin', 'install', 'yiyuan-accord-claude@yiyuan-accord', '--scope', 'user', '-y') $mutableSource $claudeEnvironment
$commands.Add($claudeInstall)
Assert-Exit $claudeInstall 0 'Claude install'

$codexOldInstalled = Join-Path $codexRoot 'plugins/cache/yiyuan-accord/yiyuan-accord-codex/3.0.1'
$claudeOldInstalled = Join-Path $claudeRoot 'plugins/cache/yiyuan-accord/yiyuan-accord-claude/3.0.1'
[void](Assert-FileMapsEqual (Join-Path $oldSource 'plugins/yiyuan-accord-codex') $codexOldInstalled 'Codex old')
[void](Assert-FileMapsEqual (Join-Path $oldSource 'plugins/yiyuan-accord-claude') $claudeOldInstalled 'Claude old')
Add-Content -LiteralPath $codexAgents -Encoding utf8 -NoNewline -Value "CONCURRENT_CODEX_EDIT`n"
Add-Content -LiteralPath $codexConfig -Encoding utf8 -NoNewline -Value "# CONCURRENT_CODEX_CONFIG_EDIT`n"
Add-Content -LiteralPath $claudeInstructions -Encoding utf8 -NoNewline -Value "CONCURRENT_CLAUDE_EDIT`n"
$claudeSettingsValue = Get-Content -Raw -LiteralPath $claudeSettings | ConvertFrom-Json
$claudeSettingsValue | Add-Member -NotePropertyName concurrentSentinel -NotePropertyValue 'CONCURRENT_CLAUDE_SETTINGS'
[System.IO.File]::WriteAllText(
  $claudeSettings,
  ($claudeSettingsValue | ConvertTo-Json -Depth 20) + [System.Environment]::NewLine,
  [System.Text.UTF8Encoding]::new($false)
)
$sentinels = @($codexAgents, $claudeInstructions,
  (Join-Path $codexRoot 'foreign-plugin/sentinel.txt'),
  (Join-Path $claudeRoot 'foreign-plugin/sentinel.txt'),
  (Join-Path $codexRoot 'shared-dependency.txt'),
  (Join-Path $claudeRoot 'shared-dependency.txt'))
$sentinelHashes = [ordered]@{}
foreach ($path in $sentinels) {
  $sentinelHashes[$path] = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
}

Move-Item -LiteralPath (Join-Path $mutableSource 'plugins/yiyuan-accord-codex') -Destination (Join-Path $mutableSource 'plugins/yiyuan-accord-codex.failed-update-source')
Move-Item -LiteralPath (Join-Path $mutableSource 'plugins/yiyuan-accord-claude') -Destination (Join-Path $mutableSource 'plugins/yiyuan-accord-claude.failed-update-source')
$codexFailedUpdate = Invoke-Captured codex @('plugin', 'add', 'yiyuan-accord-codex@yiyuan-accord', '--json') $mutableSource $codexEnvironment
$commands.Add($codexFailedUpdate)
if ($codexFailedUpdate.exitCode -eq 0) { throw 'Codex failed update unexpectedly succeeded' }
$claudeFailedUpdate = Invoke-Captured claude @('plugin', 'update', 'yiyuan-accord-claude@yiyuan-accord', '--scope', 'user', '-y') $mutableSource $claudeEnvironment
$commands.Add($claudeFailedUpdate)
if ($claudeFailedUpdate.exitCode -eq 0) { throw 'Claude failed update unexpectedly succeeded' }
[void](Assert-FileMapsEqual (Join-Path $oldSource 'plugins/yiyuan-accord-codex') $codexOldInstalled 'Codex rollback')
[void](Assert-FileMapsEqual (Join-Path $oldSource 'plugins/yiyuan-accord-claude') $claudeOldInstalled 'Claude rollback')
$codexRollbackList = Invoke-Captured codex @('plugin', 'list', '--json') $mutableSource $codexEnvironment
$commands.Add($codexRollbackList)
Assert-Exit $codexRollbackList 0 'Codex rollback list'
$claudeRollbackList = Invoke-Captured claude @('plugin', 'list', '--json') $mutableSource $claudeEnvironment
$commands.Add($claudeRollbackList)
Assert-Exit $claudeRollbackList 0 'Claude rollback list'
Assert-InstalledInventory $codexRollbackList codex '3.0.1' 'Codex rollback'
Assert-InstalledInventory $claudeRollbackList claude '3.0.1' 'Claude rollback'

Copy-Item -LiteralPath (Join-Path $candidateSource 'plugins/yiyuan-accord-codex') -Destination (Join-Path $mutableSource 'plugins/yiyuan-accord-codex') -Recurse
Copy-Item -LiteralPath (Join-Path $candidateSource 'plugins/yiyuan-accord-claude') -Destination (Join-Path $mutableSource 'plugins/yiyuan-accord-claude') -Recurse
Copy-Item -LiteralPath (Join-Path $candidateSource '.agents/plugins/marketplace.json') -Destination (Join-Path $mutableSource '.agents/plugins/marketplace.json') -Force
Copy-Item -LiteralPath (Join-Path $candidateSource '.claude-plugin/marketplace.json') -Destination (Join-Path $mutableSource '.claude-plugin/marketplace.json') -Force
$codexUpdate = Invoke-Captured codex @('plugin', 'add', 'yiyuan-accord-codex@yiyuan-accord', '--json') $mutableSource $codexEnvironment
$commands.Add($codexUpdate)
Assert-Exit $codexUpdate 0 'Codex successful update'
$claudeUpdate = Invoke-Captured claude @('plugin', 'update', 'yiyuan-accord-claude@yiyuan-accord', '--scope', 'user', '-y') $mutableSource $claudeEnvironment
$commands.Add($claudeUpdate)
Assert-Exit $claudeUpdate 0 'Claude successful update'

$codexInstalled = Join-Path $codexRoot 'plugins/cache/yiyuan-accord/yiyuan-accord-codex/3.1.0'
$claudeInstalled = Join-Path $claudeRoot 'plugins/cache/yiyuan-accord/yiyuan-accord-claude/3.1.0'
$codexFileCount = Assert-FileMapsEqual (Join-Path $candidateSource 'plugins/yiyuan-accord-codex') $codexInstalled 'Codex candidate'
$claudeFileCount = Assert-FileMapsEqual (Join-Path $candidateSource 'plugins/yiyuan-accord-claude') $claudeInstalled 'Claude candidate'
$codexList = Invoke-Captured codex @('plugin', 'list', '--json') $mutableSource $codexEnvironment
$commands.Add($codexList)
Assert-Exit $codexList 0 'Codex list'
$claudeList = Invoke-Captured claude @('plugin', 'list', '--json') $mutableSource $claudeEnvironment
$commands.Add($claudeList)
Assert-Exit $claudeList 0 'Claude list'
Assert-InstalledInventory $codexList codex '3.1.0' 'Codex list'
Assert-InstalledInventory $claudeList claude '3.1.0' 'Claude list'

$startup = '{"hook_event_name":"SessionStart","source":"startup"}'
$resume = '{"hook_event_name":"SessionStart","source":"resume","model":"model-variable","permission_mode":"default"}'
foreach ($runtime in ((Join-Path $codexInstalled 'runtime/accord-hook.cjs'), (Join-Path $claudeInstalled 'runtime/accord-hook.cjs'))) {
  $startupResult = Invoke-Captured node @($runtime) $task @{} $startup
  $commands.Add($startupResult)
  Assert-Exit $startupResult 0 'Hook startup'
  if ($startupResult.stdout.Length -ne 0 -or $startupResult.stderr.Length -ne 0) { throw 'Hook startup was not silent.' }
  $resumeResult = Invoke-Captured node @($runtime) $task @{} $resume
  $commands.Add($resumeResult)
  Assert-Exit $resumeResult 0 'Hook resume'
  if (-not $resumeResult.stdout.Contains('yiyuan-accord-hook-context/v1')) { throw 'Hook resume did not emit typed context.' }
}

$codexRemove = Invoke-Captured codex @('plugin', 'remove', 'yiyuan-accord-codex@yiyuan-accord', '--json') $mutableSource $codexEnvironment
$commands.Add($codexRemove)
Assert-Exit $codexRemove 0 'Codex remove'
$claudeRemove = Invoke-Captured claude @('plugin', 'uninstall', 'yiyuan-accord-claude@yiyuan-accord', '--scope', 'user', '-y') $mutableSource $claudeEnvironment
$commands.Add($claudeRemove)
Assert-Exit $claudeRemove 0 'Claude remove'
$codexMarketplaceRemove = Invoke-Captured codex @('plugin', 'marketplace', 'remove', 'yiyuan-accord', '--json') $mutableSource $codexEnvironment
$commands.Add($codexMarketplaceRemove)
Assert-Exit $codexMarketplaceRemove 0 'Codex marketplace remove'
$claudeMarketplaceRemove = Invoke-Captured claude @('plugin', 'marketplace', 'remove', 'yiyuan-accord', '--scope', 'user') $mutableSource $claudeEnvironment
$commands.Add($claudeMarketplaceRemove)
Assert-Exit $claudeMarketplaceRemove 0 'Claude marketplace remove'
$codexFinal = Invoke-Captured codex @('plugin', 'list', '--json') $task $codexEnvironment
$commands.Add($codexFinal)
Assert-Exit $codexFinal 0 'Codex final list'
$claudeFinal = Invoke-Captured claude @('plugin', 'list', '--json') $task $claudeEnvironment
$commands.Add($claudeFinal)
Assert-Exit $claudeFinal 0 'Claude final list'
if ((Read-JsonOutput $codexFinal 'Codex final list').installed.Count -ne 0 -or
    (Read-JsonOutput $claudeFinal 'Claude final list').Count -ne 0) {
  throw 'Native removal left installed Accord entries.'
}
foreach ($entry in $sentinelHashes.GetEnumerator()) {
  if (-not (Test-Path -LiteralPath $entry.Key) -or
      (Get-FileHash -Algorithm SHA256 -LiteralPath $entry.Key).Hash.ToLowerInvariant() -ne $entry.Value) {
    throw "User or foreign sentinel changed: $($entry.Key)"
  }
}
$finalCodexConfig = Get-Content -Raw -LiteralPath $codexConfig
if (-not $finalCodexConfig.Contains('# USER_CODEX_CONFIG') -or
    -not $finalCodexConfig.Contains('# CONCURRENT_CODEX_CONFIG_EDIT') -or
    $finalCodexConfig.Contains('yiyuan-accord')) {
  throw 'Codex user configuration was not preserved or Accord configuration remains.'
}
$finalClaudeSettings = Get-Content -Raw -LiteralPath $claudeSettings | ConvertFrom-Json
if ($finalClaudeSettings.userSentinel -ne 'USER_CLAUDE_SETTINGS' -or
    $finalClaudeSettings.concurrentSentinel -ne 'CONCURRENT_CLAUDE_SETTINGS' -or
    @($finalClaudeSettings.permissions.allow).Count -ne 0 -or
    @($finalClaudeSettings.enabledPlugins.PSObject.Properties).Count -ne 0 -or
    @($finalClaudeSettings.extraKnownMarketplaces.PSObject.Properties).Count -ne 0) {
  throw 'Claude user configuration was not preserved or Accord configuration remains.'
}
$matchingProcesses = @(Get-TaskProcessIds $task)
if ($matchingProcesses.Count -ne 0) { throw 'Task-owned process remains.' }
$codexCache = @(Get-ChildItem -LiteralPath (Join-Path $codexRoot 'plugins/cache/yiyuan-accord') -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
  [System.IO.Path]::GetRelativePath($codexRoot, $_.FullName).Replace('\', '/')
})
$claudeCache = @(Get-ChildItem -LiteralPath (Join-Path $claudeRoot 'plugins/cache/yiyuan-accord') -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
  [System.IO.Path]::GetRelativePath($claudeRoot, $_.FullName).Replace('\', '/')
})

$candidateProgram = Get-Content -Raw -LiteralPath (Join-Path $candidateSource 'product/program.json') | ConvertFrom-Json
$candidateGolden = Get-Content -Raw -LiteralPath (Join-Path $candidateSource 'evals/golden-tasks.json') | ConvertFrom-Json
$gt20 = $candidateGolden.tasks | Where-Object id -eq 'GT-20'
$behaviorSubject = [ordered]@{}
foreach ($locator in $gt20.behaviorSubjectFiles) {
  $behaviorSubject[$locator] = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $candidateSource $locator)).Hash.ToLowerInvariant()
}
$packages = [ordered]@{}
foreach ($projection in $candidateProgram.hostProjections) {
  $packages[$projection.id] = $projection.packageSha256
}
$record = [ordered]@{
  schema = 'yiyuan-accord-gt20-exact-package-evidence/v2'
  taskId = 'GT-20'
  evaluatedRevision = $CandidateRevision
  runnerSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $PSCommandPath).Hash.ToLowerInvariant()
  packageSha256 = $packages
  behaviorSubject = $behaviorSubject
  lifecycle = [ordered]@{
    install = 'verified'
    failedUpdateRollback = 'verified'
    successfulUpdate = 'verified'
    activation = 'verified'
    remove = 'verified'
    postState = 'verified'
    cleanup = 'verified'
  }
  claimLimit = 'Bounded zero-model Windows lifecycle evidence for exact Commit A Codex and Claude package bytes in disposable non-empty scopes; production, unmanaged or cross-OS hosts, ordinary model behavior, product value and release readiness remain unclaimed.'
  fixture = [ordered]@{
    platform = 'windows'
    priorVersion = '3.0.1'
    targetVersion = '3.1.0'
    userStatePreserved = $true
    concurrentEditsPreserved = $true
    foreignStatePreserved = $true
    credentialsRead = $false
    sessionsRead = $false
    modelTurns = 0
    sourceFailureMode = 'registered-source-package-path-absent'
    codexUpdateMechanism = 'plugin-add-replaces-installed-version'
    claudeUpdateMechanism = 'plugin-update'
    rollbackBytesMatchPriorRelease = $true
    installedBytesMatchDeclaredPackages = $true
    startupHookSilent = $true
    resumeHookTypedContext = $true
    powerShellVersion = $PSVersionTable.PSVersion.ToString()
    powerShellEdition = $PSVersionTable.PSEdition
    powerShellExecutable = ConvertTo-PortablePath ([System.Environment]::ProcessPath)
    powerShellExecutableSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath ([System.Environment]::ProcessPath)).Hash.ToLowerInvariant()
    gitVersion = $gitVersion.stdout.Trim()
    tarVersion = $tarVersion.stdout.Trim()
    codexCliVersion = $codexVersion.stdout.Trim()
    claudeCliVersion = $claudeVersion.stdout.Trim()
    nodeVersion = $nodeVersion.stdout.Trim()
    codexInstalledFileCount = $codexFileCount
    claudeInstalledFileCount = $claudeFileCount
  }
  commands = $commands
  postState = [ordered]@{
    codexInstalledEntries = 0
    claudeInstalledEntries = 0
    taskProcesses = 0
    codexCacheFiles = $codexCache
    claudeCacheFiles = $claudeCache
    taskRootRemoved = $true
  }
}

Remove-Item -LiteralPath $task -Recurse -Force
if (Test-Path -LiteralPath $task) { throw 'TaskRoot cleanup failed.' }
$evidenceDirectory = Split-Path -Parent $evidencePath
if (-not (Test-Path -LiteralPath $evidenceDirectory)) {
  New-Item -ItemType Directory -Path $evidenceDirectory | Out-Null
}
$evidenceJson = $record | ConvertTo-Json -Depth 20
[System.IO.File]::WriteAllText(
  $evidencePath,
  $evidenceJson + [System.Environment]::NewLine,
  [System.Text.UTF8Encoding]::new($false)
)
$succeeded = $true
Write-Output $evidencePath
} finally {
  $cleanupErrors = [System.Collections.Generic.List[string]]::new()
  try {
    if (@(Stop-TaskProcesses $task).Count -ne 0) {
      $cleanupErrors.Add('task process cleanup failed')
    }
  } catch { $cleanupErrors.Add('task process cleanup failed') }
  try {
    if (Test-Path -LiteralPath $task) {
      Remove-Item -LiteralPath $task -Recurse -Force
    }
    if (Test-Path -LiteralPath $task) {
      $cleanupErrors.Add('task root cleanup failed')
    }
  } catch { $cleanupErrors.Add('task root cleanup failed') }
  try {
    if (-not $succeeded -and (Test-Path -LiteralPath $evidencePath)) {
      Remove-Item -LiteralPath $evidencePath -Force
    }
  } catch { $cleanupErrors.Add('partial evidence cleanup failed') }
  if ($cleanupErrors.Count -ne 0) {
    throw ('GT-20 finalizer: ' + ($cleanupErrors -join '; '))
  }
}

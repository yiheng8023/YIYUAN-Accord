#requires -Version 7.0
# Private pipe source for observe_claude_entry.py. No saved receipt is authority.
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

function Reply($value) { [Console]::WriteLine(($value | ConvertTo-Json -Depth 30 -Compress)) }
function Ordinary-Directory([string]$path) {
  $item = Get-Item -LiteralPath $path -Force
  if (-not $item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw 'nonordinary-directory'
  }
  return $item.FullName
}
function Route-Environment {
  # The trusted caller supplies an already authorized route through inherited
  # environment. No private-config fallback, new authentication or route switch.
  $route = [Collections.Generic.Dictionary[string,string]]::new()
  foreach ($name in @('ANTHROPIC_AUTH_TOKEN', 'ANTHROPIC_API_KEY', 'ANTHROPIC_BASE_URL',
      'ANTHROPIC_MODEL', 'ANTHROPIC_DEFAULT_SONNET_MODEL', 'ANTHROPIC_DEFAULT_OPUS_MODEL',
      'ANTHROPIC_DEFAULT_HAIKU_MODEL')) {
    $value = [Environment]::GetEnvironmentVariable($name)
    if ($value) { $route[$name] = [string]$value }
  }
  if (-not $route.ContainsKey('ANTHROPIC_BASE_URL') -or
      (-not $route.ContainsKey('ANTHROPIC_AUTH_TOKEN') -and -not $route.ContainsKey('ANTHROPIC_API_KEY'))) {
    throw 'existing-route-unavailable'
  }
  return ,$route
}
function Same-Route($left, $right) {
  if ($left.Count -ne $right.Count) { return $false }
  foreach ($entry in $left.GetEnumerator()) {
    if (-not $right.ContainsKey($entry.Key) -or $right[$entry.Key] -cne $entry.Value) { return $false }
  }
  return $true
}
function Host-Profile {
  $hostProfile = [Collections.Generic.Dictionary[string,string]]::new()
  foreach ($name in @('USERPROFILE','HOME','APPDATA','LOCALAPPDATA','CLAUDE_CONFIG_DIR')) {
    $value = [Environment]::GetEnvironmentVariable($name)
    if ($value) { $hostProfile[$name] = $value }
  }
  return ,$hostProfile
}

function Invoke-OwnedCapture($application, $arguments, $workspace, $environment, $inputText,
    [int]$seconds, [int]$outputLimit = 2097152, [int]$errorLimit = 262144) {
  $job = [AccordProcessJob]::new()
  $child = $null; $forced = $false; $beforeCleanup = $null; $capture = $null
  $watch = [Diagnostics.Stopwatch]::StartNew()
  try {
    $child = [AccordSuspendedProcess]::Start($application, $arguments, $workspace, $environment, $job)
    $output = [AccordSuspendedProcess]::ReadBoundedAsync($child.StandardOutput, $outputLimit)
    $errors = [AccordSuspendedProcess]::ReadBoundedAsync($child.StandardError, $errorLimit)
    # Writing stdin belongs to the same deadline; a non-reading child must not
    # block the monitor before it can enforce timeout and close its whole job.
    $writing = [AccordEntryInput]::Resume($child, $inputText)
    while (-not $child.Process.WaitForExit(100)) {
      if ($watch.Elapsed.TotalSeconds -gt $seconds -or $output.IsFaulted -or
          $errors.IsFaulted -or $writing.IsFaulted) {
        $forced = $true; $beforeCleanup = $job.ActiveProcessCount
        $job.Terminate(124); break
      }
    }
    if (-not $child.Process.WaitForExit(5000)) { throw 'termination-unverified' }
    if ($null -eq $beforeCleanup) { $beforeCleanup = $job.ActiveProcessCount }
    if ($job.ActiveProcessCount -ne 0) { $forced = $true; $job.Terminate(124) }
    if (-not $output.Wait(5000) -or -not $errors.Wait(5000) -or -not $writing.Wait(5000)) {
      throw 'capture-unclosed'
    }
    if (-not $writing.Result) { $forced = $true }
    $capture = @{stdout=$output.Result; exitCode=$child.Process.ExitCode; forced=$forced;
      childrenBeforeCleanup=$beforeCleanup; stderrBytes=[Text.Encoding]::UTF8.GetByteCount($errors.Result);
      elapsedSeconds=[Math]::Round($watch.Elapsed.TotalSeconds,3)}
  } finally {
    if ($job.ActiveProcessCount -ne 0) { $job.Terminate(125) }
    $settle = [Diagnostics.Stopwatch]::StartNew()
    while ($job.ActiveProcessCount -ne 0 -and $settle.Elapsed.TotalSeconds -lt 5) { Start-Sleep -Milliseconds 50 }
    $afterCleanup = $job.ActiveProcessCount
    try { if ($child) { $child.Dispose() } } finally { $job.Dispose() }
  }
  if ($afterCleanup -ne 0) { throw 'residue-unclosed' }
  $capture.evaluatorChildrenAfterCleanup = $afterCleanup
  return $capture
}

try {
  $bound = [Console]::ReadLine() | ConvertFrom-Json -AsHashtable
  if (-not $IsWindows -or $bound.schema -ne 'accord-live-cli-source/v1' -or
      $bound.episode -notmatch '^[0-9a-f]{32}$' -or $bound.timeout -lt 1 -or $bound.timeout -gt 180 -or
      -not $bound.repository -or -not $bound.taskRoot -or -not $bound.executable -or -not $bound.prompt) {
    throw 'unbound'
  }
  $routeMode = if ($bound.ContainsKey('routeMode')) { $bound.routeMode } else { 'inherited' }
  if ($routeMode -notin @('inherited', 'host-user-settings')) { throw 'unbound-route-mode' }
  $repository = Ordinary-Directory $bound.repository
  $taskRoot = Ordinary-Directory $bound.taskRoot
  if ([IO.Path]::GetDirectoryName($taskRoot).TrimEnd('\') -ne [IO.Path]::GetTempPath().TrimEnd('\') -or
      [IO.Path]::GetFileName($taskRoot) -notlike 'accord-entry-*' -or
      (Get-Content -LiteralPath (Join-Path $taskRoot 'owner') -Raw).Trim() -ne $bound.episode) { throw 'unbound' }
  $executable = (Get-Item -LiteralPath $bound.executable).FullName
  $binaryHash = (Get-FileHash -LiteralPath $executable -Algorithm SHA256).Hash.ToLowerInvariant()
} catch {
  Reply @{error='unbound-observation-request'}
  exit 2
}

try {
  # Compile only the reviewed declaration, never dot-source lifecycle execution.
  $tokens = $null; $parseErrors = $null
  $ast = [Management.Automation.Language.Parser]::ParseFile(
    (Join-Path $repository 'scripts/run-gt20-exact-package.ps1'), [ref]$tokens, [ref]$parseErrors)
  $declaration = $ast.FindAll({param($node)
    $node -is [Management.Automation.Language.CommandAst] -and $node.GetCommandName() -eq 'Add-Type'
  }, $true) | Select-Object -First 1
  $literal = $declaration.CommandElements | Where-Object {
    $_ -is [Management.Automation.Language.StringConstantExpressionAst] -and $_.Value.Contains('class AccordProcessJob')
  } | Select-Object -First 1
  if ($parseErrors.Count -or -not $literal) { throw 'process-boundary-unavailable' }
  $inputHelper = @'
public static class AccordEntryInput {
  public static System.Threading.Tasks.Task<bool> Resume(AccordSuspendedProcess child, string input) {
    return System.Threading.Tasks.Task.Run(() => {
      try { child.Resume(input); return true; }
      catch (System.IO.IOException) {
        // A child killed while not reading closes the pipe. Keep that failure
        // distinct from normal execution while still releasing the writer.
        try { child.CloseInput(); } catch (System.IO.IOException) { }
        return false;
      }
    });
  }
}
'@
  Add-Type -TypeDefinition ($literal.Value + [Environment]::NewLine + $inputHelper)
  $versionEnvironment = [Collections.Generic.Dictionary[string,string]]::new()
  foreach ($name in @('COMSPEC', 'PATH', 'PATHEXT', 'SystemRoot', 'WINDIR', 'TEMP', 'TMP')) {
    $value = [Environment]::GetEnvironmentVariable($name)
    if ($value) { $versionEnvironment[$name] = $value }
  }
  $versionCapture = Invoke-OwnedCapture $executable @('--version') $taskRoot $versionEnvironment '' ([Math]::Min(10, $bound.timeout)) 4096 4096
  if ($versionCapture.forced -or $versionCapture.exitCode -ne 0 -or -not $versionCapture.stdout.Trim()) {
    Reply @{error='version-query-not-completed'; forced=$versionCapture.forced;
      evaluatorChildrenAfterCleanup=$versionCapture.evaluatorChildrenAfterCleanup}
    exit 3
  }
  $version = $versionCapture.stdout.Trim()
  $route = $null
  $ran = [Collections.Generic.HashSet[string]]::new()
  Reply @{ready=$true; binarySha256=$binaryHash; version=$version; episode=$bound.episode}
  while ($line = [Console]::ReadLine()) {
    $request = $line | ConvertFrom-Json -AsHashtable
    if ($request.op -eq 'close') { break }
    if ($request.op -eq 'recheck') {
      Reply @{binaryUnchanged=((Get-FileHash -LiteralPath $executable -Algorithm SHA256).Hash.ToLowerInvariant() -eq $binaryHash);
        routeUnchanged=$(if ($routeMode -eq 'inherited') {
          $null -ne $route -and (Same-Route $route (Route-Environment))
        } else { $null });
        profileUnchanged=($routeMode -eq 'host-user-settings' -and $null -ne $route -and
          (Same-Route $route (Host-Profile))); episode=$bound.episode}
      continue
    }
    if ($request.op -ne 'run' -or $request.arm -notin @('native', 'accord') -or -not $ran.Add($request.arm)) {
      throw 'invalid-or-repeated-arm'
    }
    if ($null -eq $route) {
      $route = if ($routeMode -eq 'inherited') { Route-Environment } else { Host-Profile }
    }
    $armRoot = Ordinary-Directory (Join-Path $taskRoot $request.arm)
    $workspace = Ordinary-Directory (Join-Path $armRoot 'work')
    $environment = [Collections.Generic.Dictionary[string,string]]::new()
    foreach ($name in @('COMSPEC','PATH','PATHEXT','ProgramData','ProgramFiles','ProgramFiles(x86)',
        'ProgramW6432','SystemDrive','SystemRoot','WINDIR')) {
      $value = [Environment]::GetEnvironmentVariable($name)
      if ($value) { $environment[$name] = $value }
    }
    $localPaths = @{TEMP='temp'; TMP='temp'}
    if ($routeMode -eq 'inherited') {
      $localPaths += @{USERPROFILE='home'; HOME='home'; APPDATA='appdata'; LOCALAPPDATA='localappdata';
        CLAUDE_CONFIG_DIR='config'}
    }
    foreach ($pair in $localPaths.GetEnumerator()) {
      $environment[$pair.Key] = Ordinary-Directory (Join-Path $armRoot $pair.Value)
    }
    foreach ($entry in $route.GetEnumerator()) { $environment[$entry.Key] = $entry.Value }
    $environment['CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC'] = '1'
    $environment['CLAUDE_CODE_DISABLE_OFFICIAL_MARKETPLACE_AUTOINSTALL'] = '1'
    $environment['DISABLE_AUTOUPDATER'] = '1'
    $arguments = @('-p','--verbose','--output-format','stream-json','--no-session-persistence',
      '--strict-mcp-config','--mcp-config','{"mcpServers":{}}','--no-chrome',
      '--permission-mode','acceptEdits','--permission-prompts','none',
      '--tools','Read,Write,Edit,Skill','--allowedTools','Read,Write,Edit,Skill',
      '--model','sonnet','--max-turns','16','--max-budget-usd','1')
    if ($routeMode -eq 'inherited') {
      $arguments += @('--restricted','--setting-sources','','--settings','{"autoMemoryEnabled":false}')
    } else {
      # Claude itself uses its existing configuration. This profile is not a
      # pristine host or restricted filesystem; shared customizations remain.
      $arguments += @('--setting-sources','user','--settings',
        '{"autoMemoryEnabled":false,"disableAllHooks":true,"enabledPlugins":{"yiyuan-accord-claude@yiyuan-accord":false}}')
    }
    if ($request.arm -eq 'accord') {
      $arguments += @('--plugin-dir', (Join-Path $repository 'plugins/yiyuan-accord-claude'))
    }
    $capture = Invoke-OwnedCapture $executable $arguments $workspace $environment $bound.prompt $bound.timeout
    $capture.episode = $bound.episode
    $capture.arm = $request.arm
    Reply $capture
  }
} catch {
  # Never expose route data, stderr, private paths or exception text.
  Reply @{error='live-observation-unavailable'}
  exit 3
}

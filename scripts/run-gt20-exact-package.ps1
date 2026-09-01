#requires -Version 7.0

param(
  [Parameter(Mandatory = $true)][string]$RepositoryRoot,
  [Parameter(Mandatory = $true)][string]$CandidateRevision,
  [Parameter(Mandatory = $true)][string]$TaskRoot,
  [Parameter(Mandatory = $true)][string]$EvidenceOutput
)

$ErrorActionPreference = 'Stop'
$CommandTimeoutSeconds = 60
$CommandEndToEndTimeoutSeconds = 70
$CommandOutputLimitBytes = 4194304

if (-not $IsWindows) {
  throw 'GT-20 exact package lifecycle evaluator requires Windows.'
}

Add-Type -TypeDefinition @'
using System;
using System.Collections;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using Microsoft.Win32.SafeHandles;

public sealed class AccordProcessJob : IDisposable {
  private const uint JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000;
  private SafeFileHandle handle;

  [StructLayout(LayoutKind.Sequential)]
  private struct IO_COUNTERS {
    public ulong ReadOperationCount, WriteOperationCount, OtherOperationCount;
    public ulong ReadTransferCount, WriteTransferCount, OtherTransferCount;
  }

  [StructLayout(LayoutKind.Sequential)]
  private struct JOBOBJECT_BASIC_LIMIT_INFORMATION {
    public long PerProcessUserTimeLimit, PerJobUserTimeLimit;
    public uint LimitFlags;
    public UIntPtr MinimumWorkingSetSize, MaximumWorkingSetSize;
    public uint ActiveProcessLimit;
    public UIntPtr Affinity;
    public uint PriorityClass, SchedulingClass;
  }

  [StructLayout(LayoutKind.Sequential)]
  private struct JOBOBJECT_EXTENDED_LIMIT_INFORMATION {
    public JOBOBJECT_BASIC_LIMIT_INFORMATION BasicLimitInformation;
    public IO_COUNTERS IoInfo;
    public UIntPtr ProcessMemoryLimit, JobMemoryLimit, PeakProcessMemoryUsed, PeakJobMemoryUsed;
  }

  [StructLayout(LayoutKind.Sequential)]
  private struct JOBOBJECT_BASIC_ACCOUNTING_INFORMATION {
    public long TotalUserTime, TotalKernelTime, ThisPeriodTotalUserTime, ThisPeriodTotalKernelTime;
    public uint TotalPageFaultCount, TotalProcesses, ActiveProcesses, TotalTerminatedProcesses;
  }

  [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
  private static extern SafeFileHandle CreateJobObject(IntPtr attributes, string name);
  [DllImport("kernel32.dll", SetLastError = true)]
  private static extern bool SetInformationJobObject(SafeFileHandle job, int infoClass, IntPtr info, uint length);
  [DllImport("kernel32.dll", SetLastError = true)]
  private static extern bool QueryInformationJobObject(SafeFileHandle job, int infoClass, IntPtr info, uint length, out uint returnedLength);
  [DllImport("kernel32.dll", SetLastError = true)]
  private static extern bool AssignProcessToJobObject(SafeFileHandle job, IntPtr process);
  [DllImport("kernel32.dll", SetLastError = true)]
  private static extern bool TerminateJobObject(SafeFileHandle job, uint exitCode);

  public AccordProcessJob() {
    handle = CreateJobObject(IntPtr.Zero, null);
    if (handle.IsInvalid) throw new Win32Exception(Marshal.GetLastWin32Error());
    var limits = new JOBOBJECT_EXTENDED_LIMIT_INFORMATION();
    limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
    int size = Marshal.SizeOf(limits);
    IntPtr data = Marshal.AllocHGlobal(size);
    try {
      Marshal.StructureToPtr(limits, data, false);
      if (!SetInformationJobObject(handle, 9, data, (uint)size))
        throw new Win32Exception(Marshal.GetLastWin32Error());
    } finally { Marshal.FreeHGlobal(data); }
  }

  public void Add(Process process) {
    if (!AssignProcessToJobObject(handle, process.Handle))
      throw new Win32Exception(Marshal.GetLastWin32Error());
  }

  public uint ActiveProcessCount {
    get {
      var value = new JOBOBJECT_BASIC_ACCOUNTING_INFORMATION();
      int size = Marshal.SizeOf(value);
      IntPtr data = Marshal.AllocHGlobal(size);
      try {
        uint returned;
        if (!QueryInformationJobObject(handle, 1, data, (uint)size, out returned))
          throw new Win32Exception(Marshal.GetLastWin32Error());
        value = Marshal.PtrToStructure<JOBOBJECT_BASIC_ACCOUNTING_INFORMATION>(data);
        return value.ActiveProcesses;
      } finally { Marshal.FreeHGlobal(data); }
    }
  }

  public void Terminate(uint exitCode) {
    if (!TerminateJobObject(handle, exitCode))
      throw new Win32Exception(Marshal.GetLastWin32Error());
  }

  public void Dispose() {
    if (handle != null) { handle.Dispose(); handle = null; }
  }
}

public sealed class AccordSuspendedProcess : IDisposable {
  [StructLayout(LayoutKind.Sequential)]
  private struct SECURITY_ATTRIBUTES {
    public int nLength;
    public IntPtr lpSecurityDescriptor;
    [MarshalAs(UnmanagedType.Bool)] public bool bInheritHandle;
  }

  [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
  private struct STARTUPINFO {
    public int cb;
    public string lpReserved, lpDesktop, lpTitle;
    public int dwX, dwY, dwXSize, dwYSize, dwXCountChars, dwYCountChars;
    public int dwFillAttribute, dwFlags;
    public short wShowWindow, cbReserved2;
    public IntPtr lpReserved2, hStdInput, hStdOutput, hStdError;
  }

  [StructLayout(LayoutKind.Sequential)]
  private struct PROCESS_INFORMATION {
    public IntPtr hProcess, hThread;
    public uint dwProcessId, dwThreadId;
  }

  [DllImport("kernel32.dll", SetLastError = true)]
  private static extern bool CreatePipe(out IntPtr read, out IntPtr write, ref SECURITY_ATTRIBUTES attributes, int size);
  [DllImport("kernel32.dll", SetLastError = true)]
  private static extern bool SetHandleInformation(IntPtr handle, uint mask, uint flags);
  [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
  private static extern bool CreateProcessW(
    string applicationName, StringBuilder commandLine, IntPtr processAttributes,
    IntPtr threadAttributes, bool inheritHandles, uint creationFlags,
    IntPtr environment, string currentDirectory, ref STARTUPINFO startup,
    out PROCESS_INFORMATION processInformation);
  [DllImport("kernel32.dll", SetLastError = true)]
  private static extern uint ResumeThread(IntPtr thread);
  [DllImport("kernel32.dll", SetLastError = true)]
  private static extern bool CloseHandle(IntPtr handle);

  private IntPtr threadHandle;
  private StreamWriter input;
  public Process Process { get; private set; }
  public StreamReader StandardOutput { get; private set; }
  public StreamReader StandardError { get; private set; }

  private AccordSuspendedProcess() { }

  private static string Quote(string value) {
    if (value.Length > 0 && value.IndexOfAny(new[] {' ', '\t', '\n', '\v', '"'}) < 0)
      return value;
    var result = new StringBuilder("\"");
    int slashes = 0;
    foreach (char ch in value) {
      if (ch == '\\') { slashes++; continue; }
      if (ch == '"') {
        result.Append('\\', slashes * 2 + 1).Append(ch);
        slashes = 0;
        continue;
      }
      result.Append('\\', slashes).Append(ch);
      slashes = 0;
    }
    result.Append('\\', slashes * 2).Append('"');
    return result.ToString();
  }

  private static IntPtr EnvironmentBlock(IDictionary<string,string> overrides) {
    var values = new SortedDictionary<string,string>(StringComparer.OrdinalIgnoreCase);
    foreach (DictionaryEntry entry in Environment.GetEnvironmentVariables())
      values[(string)entry.Key] = (string)entry.Value;
    if (overrides != null)
      foreach (var entry in overrides) values[entry.Key] = entry.Value ?? "";
    var block = new StringBuilder();
    foreach (var entry in values)
      block.Append(entry.Key).Append('=').Append(entry.Value).Append('\0');
    block.Append('\0');
    return Marshal.StringToHGlobalUni(block.ToString());
  }

  public static AccordSuspendedProcess Start(
    string executable, string[] arguments, string currentDirectory,
    IDictionary<string,string> environment) {
    const uint HANDLE_FLAG_INHERIT = 1;
    const uint CREATE_SUSPENDED = 0x00000004;
    const uint CREATE_NO_WINDOW = 0x08000000;
    const uint CREATE_UNICODE_ENVIRONMENT = 0x00000400;
    IntPtr stdoutRead = IntPtr.Zero, stdoutWrite = IntPtr.Zero;
    IntPtr stderrRead = IntPtr.Zero, stderrWrite = IntPtr.Zero;
    IntPtr stdinRead = IntPtr.Zero, stdinWrite = IntPtr.Zero;
    IntPtr environmentBlock = IntPtr.Zero;
    var security = new SECURITY_ATTRIBUTES {
      nLength = Marshal.SizeOf<SECURITY_ATTRIBUTES>(), bInheritHandle = true
    };
    PROCESS_INFORMATION pi = new PROCESS_INFORMATION();
    bool created = false;
    try {
      if (!CreatePipe(out stdoutRead, out stdoutWrite, ref security, 0) ||
          !SetHandleInformation(stdoutRead, HANDLE_FLAG_INHERIT, 0) ||
          !CreatePipe(out stderrRead, out stderrWrite, ref security, 0) ||
          !SetHandleInformation(stderrRead, HANDLE_FLAG_INHERIT, 0) ||
          !CreatePipe(out stdinRead, out stdinWrite, ref security, 0) ||
          !SetHandleInformation(stdinWrite, HANDLE_FLAG_INHERIT, 0))
        throw new Win32Exception(Marshal.GetLastWin32Error());
      var startup = new STARTUPINFO {
        cb = Marshal.SizeOf<STARTUPINFO>(), dwFlags = 0x00000100,
        hStdInput = stdinRead, hStdOutput = stdoutWrite, hStdError = stderrWrite
      };
      var commandLine = new StringBuilder(Quote(executable));
      foreach (string argument in arguments ?? Array.Empty<string>())
        commandLine.Append(' ').Append(Quote(argument ?? ""));
      environmentBlock = EnvironmentBlock(environment);
      created = CreateProcessW(
        executable, commandLine, IntPtr.Zero, IntPtr.Zero, true,
        CREATE_SUSPENDED | CREATE_NO_WINDOW | CREATE_UNICODE_ENVIRONMENT,
        environmentBlock, currentDirectory, ref startup, out pi);
      if (!created) throw new Win32Exception(Marshal.GetLastWin32Error());
      var owned = new AccordSuspendedProcess();
      owned.Process = Process.GetProcessById((int)pi.dwProcessId);
      var ignored = owned.Process.Handle;
      owned.threadHandle = pi.hThread;
      pi.hThread = IntPtr.Zero;
      owned.StandardOutput = new StreamReader(new FileStream(
        new SafeFileHandle(stdoutRead, true), FileAccess.Read, 4096, false),
        new UTF8Encoding(false), true);
      stdoutRead = IntPtr.Zero;
      owned.StandardError = new StreamReader(new FileStream(
        new SafeFileHandle(stderrRead, true), FileAccess.Read, 4096, false),
        new UTF8Encoding(false), true);
      stderrRead = IntPtr.Zero;
      owned.input = new StreamWriter(new FileStream(
        new SafeFileHandle(stdinWrite, true), FileAccess.Write, 4096, false),
        new UTF8Encoding(false)) { AutoFlush = true };
      stdinWrite = IntPtr.Zero;
      return owned;
    } finally {
      if (environmentBlock != IntPtr.Zero) Marshal.FreeHGlobal(environmentBlock);
      if (stdoutWrite != IntPtr.Zero) CloseHandle(stdoutWrite);
      if (stderrWrite != IntPtr.Zero) CloseHandle(stderrWrite);
      if (stdinRead != IntPtr.Zero) CloseHandle(stdinRead);
      if (stdoutRead != IntPtr.Zero) CloseHandle(stdoutRead);
      if (stderrRead != IntPtr.Zero) CloseHandle(stderrRead);
      if (stdinWrite != IntPtr.Zero) CloseHandle(stdinWrite);
      if (pi.hProcess != IntPtr.Zero) CloseHandle(pi.hProcess);
      if (pi.hThread != IntPtr.Zero) CloseHandle(pi.hThread);
    }
  }

  public void Resume(string inputText) {
    if (threadHandle == IntPtr.Zero) throw new InvalidOperationException("Process is not suspended.");
    if (ResumeThread(threadHandle) == UInt32.MaxValue)
      throw new Win32Exception(Marshal.GetLastWin32Error());
    CloseHandle(threadHandle);
    threadHandle = IntPtr.Zero;
    if (!String.IsNullOrEmpty(inputText)) input.Write(inputText);
    input.Dispose();
    input = null;
  }

  public void Dispose() {
    if (threadHandle != IntPtr.Zero) { CloseHandle(threadHandle); threadHandle = IntPtr.Zero; }
    if (input != null) { input.Dispose(); input = null; }
    if (StandardOutput != null) { StandardOutput.Dispose(); StandardOutput = null; }
    if (StandardError != null) { StandardError.Dispose(); StandardError = null; }
    if (Process != null) {
      try { if (!Process.HasExited) Process.Kill(true); } catch { }
      Process.Dispose(); Process = null;
    }
  }
}
'@

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

function ConvertTo-PublicEvidenceText {
  param([AllowEmptyString()][string]$Value)
  $result = $Value
  foreach ($item in @(
    @($script:TaskPathForEvidence, '%TASK_ROOT%'),
    @($script:TemporaryBaseForEvidence, '%TEMP%'),
    @($script:RepositoryForEvidence, '%REPOSITORY_ROOT%')
  )) {
    if ($item[0]) {
      $privateRoot = [string]$item[0]
      $replacement = [string]$item[1]
      foreach ($spelling in @($privateRoot, $privateRoot.Replace('\', '/'))) {
        $result = $result.Replace(
          $spelling, $replacement,
          [System.StringComparison]::OrdinalIgnoreCase
        )
      }
    }
  }
  return $result
}

function Get-TerminalCommandIdentity {
  param([Parameter(Mandatory = $true)]$Command)
  $terminal = $Command.Source
  $manifest = $null
  if ([System.IO.Path]::GetExtension($Command.Source) -eq '.cmd') {
    if ([System.IO.Path]::GetFileName($Command.Source) -ne 'claude.cmd') {
      throw "Unsupported command shim identity: $($Command.Source)"
    }
    $manifest = Join-Path (Split-Path -Parent $Command.Source) 'node_modules/@anthropic-ai/claude-code/package.json'
    $package = Get-Content -Raw -LiteralPath $manifest | ConvertFrom-Json
    $bin = $package.bin.claude
    if (-not $bin -or [System.IO.Path]::IsPathRooted([string]$bin)) {
      throw 'Claude command package manifest has an invalid bin entry.'
    }
    $terminal = [System.IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $manifest) ([string]$bin)))
    if (-not (Test-Path -LiteralPath $terminal -PathType Leaf)) {
      throw 'Claude terminal executable is unavailable.'
    }
  }
  return [ordered]@{
    terminalExecutableRaw = $terminal
    terminalExecutable = ConvertTo-PortablePath $terminal
    terminalExecutableSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $terminal).Hash.ToLowerInvariant()
    packageManifestRaw = $manifest
    packageManifest = if ($manifest) { ConvertTo-PortablePath $manifest } else { $null }
    packageManifestSha256 = if ($manifest) { (Get-FileHash -Algorithm SHA256 -LiteralPath $manifest).Hash.ToLowerInvariant() } else { $null }
  }
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
  $identity = Get-TerminalCommandIdentity $command
  $environmentOverrides = [System.Collections.Generic.Dictionary[string,string]]::new(
    [System.StringComparer]::OrdinalIgnoreCase
  )
  foreach ($entry in $Environment.GetEnumerator()) {
    $environmentOverrides[$entry.Key] = [string]$entry.Value
  }
  $job = [AccordProcessJob]::new()
  $owned = $null
  try {
    $owned = [AccordSuspendedProcess]::Start(
      $identity.terminalExecutableRaw, $Arguments, $WorkingDirectory,
      $environmentOverrides
    )
    $job.Add($owned.Process)
    $owned.Resume($InputText)
    $stdoutTask = $owned.StandardOutput.ReadToEndAsync()
    $stderrTask = $owned.StandardError.ReadToEndAsync()
    $clock = [System.Diagnostics.Stopwatch]::StartNew()
    $executionLimit = [TimeSpan]::FromSeconds($CommandTimeoutSeconds)
    while ($clock.Elapsed -lt $executionLimit -and
        (-not $owned.Process.HasExited -or $job.ActiveProcessCount -ne 0)) {
      Start-Sleep -Milliseconds 50
    }
    $timedOut = -not $owned.Process.HasExited -or $job.ActiveProcessCount -ne 0
    $terminationRequested = $timedOut
    if ($terminationRequested) { $job.Terminate(124) }
    $hardLimit = [TimeSpan]::FromSeconds($CommandEndToEndTimeoutSeconds)
    while ($clock.Elapsed -lt $hardLimit -and
        (-not $owned.Process.HasExited -or $job.ActiveProcessCount -ne 0)) {
      Start-Sleep -Milliseconds 25
    }
    $terminationConfirmed = $owned.Process.HasExited -and $job.ActiveProcessCount -eq 0
    if (-not $terminationConfirmed) {
      throw "Command process tree did not terminate within the hard deadline: $File"
    }
    $remaining = [Math]::Max(1, [int]($hardLimit.TotalMilliseconds - $clock.Elapsed.TotalMilliseconds))
    $outputs = [System.Threading.Tasks.Task[]]@($stdoutTask, $stderrTask)
    $streamsDrained = [System.Threading.Tasks.Task]::WaitAll($outputs, $remaining)
    if (-not $streamsDrained) {
      throw "Command output pipes did not close within the hard deadline: $File"
    }
    $stdoutValue = $stdoutTask.Result
    $stderrValue = $stderrTask.Result
    if ([System.Text.Encoding]::UTF8.GetByteCount($stdoutValue) -gt $CommandOutputLimitBytes -or
        [System.Text.Encoding]::UTF8.GetByteCount($stderrValue) -gt $CommandOutputLimitBytes) {
      throw "Command output exceeded the evidence byte limit: $File"
    }
    $exitCode = if ($timedOut) { 124 } else { $owned.Process.ExitCode }
    return [ordered]@{
      argv = @(@($File) + $Arguments | ForEach-Object { ConvertTo-PublicEvidenceText ([string]$_) })
      resolvedCommand = ConvertTo-PortablePath $command.Source
      resolvedCommandSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $command.Source).Hash.ToLowerInvariant()
      launcher = $identity.terminalExecutable
      launcherSha256 = $identity.terminalExecutableSha256
      terminalExecutable = $identity.terminalExecutable
      terminalExecutableSha256 = $identity.terminalExecutableSha256
      packageManifest = $identity.packageManifest
      packageManifestSha256 = $identity.packageManifestSha256
      environmentKeys = @($Environment.Keys | Sort-Object)
      inputSha256 = [Convert]::ToHexString(
        [System.Security.Cryptography.SHA256]::HashData(
          [System.Text.Encoding]::UTF8.GetBytes($InputText)
        )
      ).ToLowerInvariant()
      executionTimeoutSeconds = $CommandTimeoutSeconds
      endToEndTimeoutSeconds = $CommandEndToEndTimeoutSeconds
      outputLimitBytes = $CommandOutputLimitBytes
      timedOut = $timedOut
      terminationRequested = $terminationRequested
      terminationConfirmed = $terminationConfirmed
      streamsDrained = $streamsDrained
      jobActiveProcesses = [int]$job.ActiveProcessCount
      exitCode = $exitCode
      stdout = ConvertTo-PublicEvidenceText $stdoutValue
      stderr = ConvertTo-PublicEvidenceText $stderrValue
    }
  } finally {
    if ($null -ne $owned) { $owned.Dispose() }
    $job.Dispose()
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

function Assert-ExactOrphanCacheVersion {
  param(
    [Parameter(Mandatory = $true)][string]$ExpectedPackageRoot,
    [Parameter(Mandatory = $true)][string]$CacheVersionRoot,
    [Parameter(Mandatory = $true)][string]$Label
  )
  if (-not (Test-Path -LiteralPath $CacheVersionRoot -PathType Container)) {
    throw "$Label cache version root is absent."
  }
  $reparse = @(Get-ChildItem -LiteralPath $CacheVersionRoot -Recurse -Force |
    Where-Object { $_.Attributes -band [System.IO.FileAttributes]::ReparsePoint })
  if ($reparse.Count -ne 0) { throw "$Label cache contains a reparse point." }
  $expected = Get-FileMap $ExpectedPackageRoot
  $actual = Get-FileMap $CacheVersionRoot
  if (-not $actual.Contains('.orphaned_at')) {
    throw "$Label cache has no orphan marker."
  }
  [void]$actual.Remove('.orphaned_at')
  if (($expected | ConvertTo-Json -Compress) -ne ($actual | ConvertTo-Json -Compress)) {
    throw "$Label cache bytes are outside the exact package allowlist."
  }
  $marker = Get-Content -Raw -LiteralPath (Join-Path $CacheVersionRoot '.orphaned_at')
  $parsed = 0L
  if (-not [long]::TryParse($marker.Trim(), [ref]$parsed) -or $parsed -lt 0) {
    throw "$Label cache orphan marker is invalid."
  }
  return $parsed
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
  $resolvedTask = [System.IO.Path]::GetFullPath($TaskPath)
  $runnerProcesses = @(Get-RunnerProcessIds)
  return @(Get-CimInstance -ClassName Win32_Process |
    Where-Object {
      $_.CommandLine -and ([string]$_.CommandLine).IndexOf(
        $resolvedTask, [System.StringComparison]::OrdinalIgnoreCase
      ) -ge 0 -and [int]$_.ProcessId -notin $runnerProcesses
    } | ForEach-Object { [int]$_.ProcessId })
}

function Stop-TaskProcesses {
  param([Parameter(Mandatory = $true)][string]$TaskPath)
  # Every launched command is assigned while suspended to a no-breakaway Job.
  # A remaining literal task-root reference has no proven ownership after that
  # Job closes, so report it but never terminate an external process by guess.
  return @(Get-TaskProcessIds $TaskPath)
}

$repository = [System.IO.Path]::GetFullPath($RepositoryRoot)
$task = [System.IO.Path]::GetFullPath($TaskRoot)
$evidencePath = [System.IO.Path]::GetFullPath($EvidenceOutput)
$temporaryBase = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
if (-not $task.StartsWith($temporaryBase, [System.StringComparison]::OrdinalIgnoreCase) -or
    ([System.IO.Path]::GetFileName($task)) -notmatch '^yiyuan-accord-gt20-formal-[a-z0-9-]+$') {
  throw 'TaskRoot must be a specifically named temporary directory.'
}
if ($task.StartsWith($repository, [System.StringComparison]::OrdinalIgnoreCase)) {
  throw 'TaskRoot must be outside the repository.'
}
if (-not $evidencePath.StartsWith($temporaryBase, [System.StringComparison]::OrdinalIgnoreCase) -or
    ([System.IO.Path]::GetFileName($evidencePath)) -notmatch '^yiyuan-accord-gt20-formal-evidence-[a-z0-9-]+\.json$' -or
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
$script:TaskPathForEvidence = $task
$script:TemporaryBaseForEvidence = $temporaryBase
$script:RepositoryForEvidence = $repository
$commands = [System.Collections.Generic.List[object]]::new()
$succeeded = $false
try {
$commitCheck = Invoke-Captured git @('-C', $repository, 'rev-parse', '--verify', "$CandidateRevision`^{commit}") $repository
$commands.Add($commitCheck)
Assert-Exit $commitCheck 0 'candidate commit validation'
if ($commitCheck.stdout.Trim() -ne $CandidateRevision) {
  throw 'CandidateRevision is not an exact commit.'
}
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
$claudeManifest = Get-Content -Raw -LiteralPath $claudeVersion.packageManifest.Replace(
  '%APPDATA%', $env:APPDATA, [System.StringComparison]::OrdinalIgnoreCase
) | ConvertFrom-Json
if ($claudeManifest.name -ne '@anthropic-ai/claude-code' -or
    -not $claudeVersion.stdout.Trim().StartsWith(
      "$($claudeManifest.version) ", [System.StringComparison]::Ordinal
    )) {
  throw 'Claude shim, package manifest and reported version do not agree.'
}
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
if ($matchingProcesses.Count -ne 0) {
  throw 'Task-owned process remains.'
}
$codexCache = @(Get-ChildItem -LiteralPath (Join-Path $codexRoot 'plugins/cache/yiyuan-accord') -Recurse -File -ErrorAction SilentlyContinue |
  Sort-Object FullName | ForEach-Object {
  [System.IO.Path]::GetRelativePath($codexRoot, $_.FullName).Replace('\', '/')
})
$claudeCache = @(Get-ChildItem -LiteralPath (Join-Path $claudeRoot 'plugins/cache/yiyuan-accord') -Recurse -File -ErrorAction SilentlyContinue |
  Sort-Object FullName | ForEach-Object {
  [System.IO.Path]::GetRelativePath($claudeRoot, $_.FullName).Replace('\', '/')
})
if ($codexCache.Count -ne 0) {
  throw 'Codex retained package cache outside the declared zero-cache contract.'
}

$claudeCacheRoot = Join-Path $claudeRoot 'plugins/cache/yiyuan-accord/yiyuan-accord-claude'
$claudeOldCache = Join-Path $claudeCacheRoot '3.0.1'
$claudeCandidateCache = Join-Path $claudeCacheRoot '3.1.0'
$retentionMilliseconds = 1209600000L
$clockMilliseconds = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
$youngAgeMilliseconds = $retentionMilliseconds - 3600000L
$expiredAgeMilliseconds = $retentionMilliseconds + 3600000L
[void](Assert-ExactOrphanCacheVersion (Join-Path $oldSource 'plugins/yiyuan-accord-claude') $claudeOldCache 'Claude old')
$candidateOrphanedAt = Assert-ExactOrphanCacheVersion (Join-Path $candidateSource 'plugins/yiyuan-accord-claude') $claudeCandidateCache 'Claude candidate'
$candidateAgeMilliseconds = $clockMilliseconds - $candidateOrphanedAt
if ($candidateAgeMilliseconds -lt 0 -or $candidateAgeMilliseconds -ge $retentionMilliseconds) {
  throw 'Claude candidate orphan cache is not inside the fresh retention boundary.'
}
Set-Content -LiteralPath (Join-Path $claudeOldCache '.orphaned_at') -Encoding ascii -NoNewline -Value ($clockMilliseconds - $youngAgeMilliseconds)
$youngSweepCommandIndex = $commands.Count
$claudeYoungSweep = Invoke-Captured claude @('plugin', 'list', '--json') $task $claudeEnvironment
$commands.Add($claudeYoungSweep)
Assert-Exit $claudeYoungSweep 0 'Claude young orphan sweep'
if (-not (Test-Path -LiteralPath $claudeOldCache -PathType Container)) {
  throw 'Claude removed a younger-than-contract orphan cache.'
}
[void](Assert-ExactOrphanCacheVersion (Join-Path $oldSource 'plugins/yiyuan-accord-claude') $claudeOldCache 'Claude young')
Set-Content -LiteralPath (Join-Path $claudeOldCache '.orphaned_at') -Encoding ascii -NoNewline -Value ($clockMilliseconds - $expiredAgeMilliseconds)
$expiredSweepCommandIndex = $commands.Count
$claudeExpiredSweep = Invoke-Captured claude @('plugin', 'list', '--json') $task $claudeEnvironment
$commands.Add($claudeExpiredSweep)
Assert-Exit $claudeExpiredSweep 0 'Claude expired orphan sweep'
if (Test-Path -LiteralPath $claudeOldCache) {
  throw 'Claude retained an older-than-contract orphan cache.'
}
[void](Assert-ExactOrphanCacheVersion (Join-Path $candidateSource 'plugins/yiyuan-accord-claude') $claudeCandidateCache 'Claude retained candidate')
$claudeCache = @(Get-ChildItem -LiteralPath (Join-Path $claudeRoot 'plugins/cache/yiyuan-accord') -Recurse -File -ErrorAction SilentlyContinue |
  Sort-Object FullName | ForEach-Object {
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
$commandPlan = @($commands | ForEach-Object {
  [ordered]@{
    argv = $_.argv
    endToEndTimeoutSeconds = $_.endToEndTimeoutSeconds
    environmentKeys = $_.environmentKeys
    executionTimeoutSeconds = $_.executionTimeoutSeconds
    inputSha256 = $_.inputSha256
    outputLimitBytes = $_.outputLimitBytes
  }
})
$commandPlanJson = $commandPlan | ConvertTo-Json -Depth 8 -Compress
$commandPlanSha256 = [Convert]::ToHexString(
  [System.Security.Cryptography.SHA256]::HashData(
    [System.Text.Encoding]::UTF8.GetBytes($commandPlanJson)
  )
).ToLowerInvariant()
$record = [ordered]@{
  schema = 'yiyuan-accord-gt20-exact-package-evidence/v3'
  taskId = 'GT-20'
  evaluatedRevision = $CandidateRevision
  runnerSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $PSCommandPath).Hash.ToLowerInvariant()
  commandPlanSha256 = $commandPlanSha256
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
  claimLimit = 'Bounded zero-model Windows lifecycle, command privacy and end-to-end process termination, plus Claude host-owned 14-day inert-cache cleanup evidence for exact Commit A Codex and Claude package bytes in disposable non-empty scopes; production, unmanaged or cross-OS hosts, live-session cache behavior, ordinary model behavior, product value and release readiness remain unclaimed.'
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
    claudePackageManifest = $claudeVersion.packageManifest
    claudePackageManifestSha256 = $claudeVersion.packageManifestSha256
    claudeTerminalExecutable = $claudeVersion.terminalExecutable
    claudeTerminalExecutableSha256 = $claudeVersion.terminalExecutableSha256
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
  hostCacheDisposition = [ordered]@{
    codex = [ordered]@{
      classification = 'no-retained-accord-package-cache'
      hostCallable = $false
    }
    claude = [ordered]@{
      classification = 'host-dispatch-inert-bounded-orphan-cache'
      observedVersions = @('3.0.1', '3.1.0')
      retainedVersions = @('3.1.0')
      exactAllowlistVerified = $true
      listedOrEnabled = $false
      hostCallable = $false
      dataStatePresent = $false
      cleanupTrigger = 'plugin-list'
      retentionMilliseconds = $retentionMilliseconds
      retainedCandidateAgeMilliseconds = $candidateAgeMilliseconds
      youngBoundaryAgeMilliseconds = $youngAgeMilliseconds
      youngBoundaryRetained = $true
      expiredBoundaryAgeMilliseconds = $expiredAgeMilliseconds
      expiredBoundaryRemoved = $true
      youngSweepCommandIndex = $youngSweepCommandIndex
      expiredSweepCommandIndex = $expiredSweepCommandIndex
      liveSessionBehavior = 'unverified'
      claudePackageManifestSha256 = $claudeVersion.packageManifestSha256
      claudeTerminalExecutableSha256 = $claudeVersion.terminalExecutableSha256
    }
  }
}

Remove-Item -LiteralPath $task -Recurse -Force
if (Test-Path -LiteralPath $task) { throw 'TaskRoot cleanup failed.' }
$evidenceDirectory = Split-Path -Parent $evidencePath
if (-not (Test-Path -LiteralPath $evidenceDirectory)) {
  New-Item -ItemType Directory -Path $evidenceDirectory | Out-Null
}
$evidenceJson = $record | ConvertTo-Json -Depth 20
foreach ($privateRoot in @($task, $temporaryBase, $repository, $env:LOCALAPPDATA, $env:APPDATA, $env:USERPROFILE)) {
  if ($privateRoot) {
    $resolvedPrivateRoot = [System.IO.Path]::GetFullPath($privateRoot)
    foreach ($spelling in @($resolvedPrivateRoot, $resolvedPrivateRoot.Replace('\', '/'))) {
      if ($evidenceJson.Contains(
          $spelling, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'Evidence serialization retained a private or task-local root.'
      }
    }
  }
}
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

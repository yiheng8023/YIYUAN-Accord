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
$ChildEnvironmentNames = @(
  'COMSPEC', 'PATH', 'PATHEXT', 'ProgramData', 'ProgramFiles',
  'ProgramFiles(x86)', 'ProgramW6432', 'SystemDrive', 'SystemRoot',
  'TEMP', 'TMP', 'WINDIR'
)

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
using System.Threading.Tasks;
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

  public void Add(IntPtr processHandle) {
    if (!AssignProcessToJobObject(handle, processHandle))
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
  [DllImport("kernel32.dll", SetLastError = true)]
  private static extern bool TerminateProcess(IntPtr process, uint exitCode);
  [DllImport("kernel32.dll", SetLastError = true)]
  private static extern uint WaitForSingleObject(IntPtr handle, uint milliseconds);

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
    IDictionary<string,string> environment, AccordProcessJob job) {
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
    bool assigned = false;
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
      job.Add(pi.hProcess);
      assigned = true;
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
    } catch {
      if (created && !assigned && pi.hProcess != IntPtr.Zero) {
        TerminateProcess(pi.hProcess, 125);
        WaitForSingleObject(pi.hProcess, 5000);
      }
      throw;
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

  public static async Task<string> ReadBoundedAsync(
    StreamReader reader, int maximumBytes) {
    var result = new StringBuilder();
    var buffer = new char[4096];
    int bytes = 0;
    while (true) {
      int count = await reader.ReadAsync(buffer, 0, buffer.Length);
      if (count == 0) break;
      bytes = checked(bytes + Encoding.UTF8.GetByteCount(buffer, 0, count));
      if (bytes > maximumBytes)
        throw new InvalidDataException("Command output exceeded the evidence byte limit.");
      result.Append(buffer, 0, count);
    }
    return result.ToString();
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

function Get-PrivateRootPattern {
  param([Parameter(Mandatory = $true)][string]$Path)
  $resolved = [System.IO.Path]::GetFullPath($Path).TrimEnd('\', '/')
  $segments = @($resolved -split '[\\/]+')
  return (($segments | ForEach-Object {
    [System.Text.RegularExpressions.Regex]::Escape($_)
  }) -join '[\\/]+')
}

function ConvertTo-PublicEvidenceText {
  param([AllowEmptyString()][string]$Value)
  $result = $Value
  foreach ($item in $script:PrivateRootsForEvidence) {
    if ($item.path) {
      $result = [System.Text.RegularExpressions.Regex]::Replace(
        $result, (Get-PrivateRootPattern $item.path),
        [string]$item.replacement,
        [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
      )
    }
  }
  return $result
}

function Test-PrivateEvidenceText {
  param([AllowEmptyString()][string]$Value)
  foreach ($item in $script:PrivateRootsForEvidence) {
    if ($item.path -and [System.Text.RegularExpressions.Regex]::IsMatch(
        $Value, (Get-PrivateRootPattern $item.path),
        [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)) {
      return $true
    }
  }
  return $Value -match '(?i)[a-z]:(?:[\\/]+)(?:users|documents and settings)(?:[\\/]+)'
}

function Assert-NoPrivateEvidenceValue {
  param([Parameter(Mandatory = $true)]$Value)
  $pending = [System.Collections.Generic.Stack[object]]::new()
  $pending.Push($Value)
  while ($pending.Count -ne 0) {
    $current = $pending.Pop()
    if ($current -is [string]) {
      if (Test-PrivateEvidenceText $current) {
        throw 'Evidence retained a private or task-local root.'
      }
    } elseif ($current -is [System.Collections.IDictionary]) {
      foreach ($item in $current.Values) { $pending.Push($item) }
    } elseif ($current -is [pscustomobject]) {
      foreach ($property in $current.PSObject.Properties) {
        $pending.Push($property.Value)
      }
    } elseif ($current -is [System.Collections.IEnumerable]) {
      foreach ($item in $current) { $pending.Push($item) }
    }
  }
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
    [string]$InputText = '',
    [int]$ExecutionTimeoutSeconds = $CommandTimeoutSeconds,
    [int]$EndToEndTimeoutSeconds = $CommandEndToEndTimeoutSeconds,
    [int]$OutputLimitBytes = $CommandOutputLimitBytes
  )
  $clock = [System.Diagnostics.Stopwatch]::StartNew()
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
  foreach ($name in $ChildEnvironmentNames) {
    $value = [System.Environment]::GetEnvironmentVariable($name)
    if ($null -ne $value) { $environmentOverrides[$name] = $value }
  }
  foreach ($entry in $Environment.GetEnumerator()) {
    $environmentOverrides[$entry.Key] = [string]$entry.Value
  }
  $taskEnvironmentReady = (
    $script:TaskPathForEvidence -and
    (Test-Path -LiteralPath $script:TaskPathForEvidence -PathType Container)
  )
  if ($taskEnvironmentReady) {
    $commandTemp = Join-Path $script:TaskPathForEvidence 'command-temp'
    [void][System.IO.Directory]::CreateDirectory($commandTemp)
    $environmentOverrides['TEMP'] = $commandTemp
    $environmentOverrides['TMP'] = $commandTemp
  }
  $job = [AccordProcessJob]::new()
  $owned = $null
  try {
    $owned = [AccordSuspendedProcess]::Start(
      $identity.terminalExecutableRaw, $Arguments, $WorkingDirectory,
      $environmentOverrides, $job
    )
    $owned.Resume($InputText)
    $stdoutTask = [AccordSuspendedProcess]::ReadBoundedAsync(
      $owned.StandardOutput, $OutputLimitBytes
    )
    $stderrTask = [AccordSuspendedProcess]::ReadBoundedAsync(
      $owned.StandardError, $OutputLimitBytes
    )
    $executionLimit = [TimeSpan]::FromSeconds($ExecutionTimeoutSeconds)
    while ($clock.Elapsed -lt $executionLimit -and
        (-not $owned.Process.HasExited -or $job.ActiveProcessCount -ne 0) -and
        -not $stdoutTask.IsFaulted -and -not $stderrTask.IsFaulted) {
      Start-Sleep -Milliseconds 50
    }
    $timedOut = -not $owned.Process.HasExited -or $job.ActiveProcessCount -ne 0
    $outputFaulted = $stdoutTask.IsFaulted -or $stderrTask.IsFaulted
    $terminationRequested = $timedOut -or $outputFaulted
    if ($terminationRequested) { $job.Terminate(124) }
    $hardLimit = [TimeSpan]::FromSeconds($EndToEndTimeoutSeconds)
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
    if ($stdoutTask.IsFaulted -or $stderrTask.IsFaulted) {
      throw "Command output exceeded the evidence byte limit: $File"
    }
    $stdoutValue = $stdoutTask.Result
    $stderrValue = $stderrTask.Result
    $stdoutBytes = [System.Text.Encoding]::UTF8.GetByteCount($stdoutValue)
    $stderrBytes = [System.Text.Encoding]::UTF8.GetByteCount($stderrValue)
    $exitCode = if ($timedOut) { 124 } else { $owned.Process.ExitCode }
    $environmentProfile = if ($Environment.ContainsKey('CODEX_HOME')) {
      'isolated-codex'
    } elseif ($Environment.ContainsKey('CLAUDE_CONFIG_DIR')) {
      'isolated-claude'
    } elseif ($taskEnvironmentReady) {
      'isolated-base'
    } else {
      'preflight-base'
    }
    $environmentBindings = [ordered]@{}
    foreach ($name in @('CODEX_HOME', 'CLAUDE_CONFIG_DIR', 'TEMP', 'TMP')) {
      if ($environmentOverrides.ContainsKey($name)) {
        $environmentBindings[$name] = (
          ConvertTo-PublicEvidenceText ([string]$environmentOverrides[$name])
        ).Replace('\', '/')
      }
    }
    return [ordered]@{
      argv = @(@($File) + $Arguments | ForEach-Object {
        (ConvertTo-PublicEvidenceText ([string]$_)).Replace('\', '/')
      })
      resolvedCommand = ConvertTo-PortablePath $command.Source
      resolvedCommandSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $command.Source).Hash.ToLowerInvariant()
      launcher = $identity.terminalExecutable
      launcherSha256 = $identity.terminalExecutableSha256
      terminalExecutable = $identity.terminalExecutable
      terminalExecutableSha256 = $identity.terminalExecutableSha256
      packageManifest = $identity.packageManifest
      packageManifestSha256 = $identity.packageManifestSha256
      environmentProfile = $environmentProfile
      environmentKeys = @($environmentOverrides.Keys | Sort-Object)
      environmentBindings = $environmentBindings
      inputSha256 = [Convert]::ToHexString(
        [System.Security.Cryptography.SHA256]::HashData(
          [System.Text.Encoding]::UTF8.GetBytes($InputText)
        )
      ).ToLowerInvariant()
      executionTimeoutSeconds = $ExecutionTimeoutSeconds
      endToEndTimeoutSeconds = $EndToEndTimeoutSeconds
      outputLimitBytes = $OutputLimitBytes
      elapsedMilliseconds = [Math]::Round($clock.Elapsed.TotalMilliseconds)
      stdoutBytes = $stdoutBytes
      stderrBytes = $stderrBytes
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
  $reparse = @(Get-ChildItem -LiteralPath $resolved -Recurse -Force |
    Where-Object { $_.Attributes -band [System.IO.FileAttributes]::ReparsePoint })
  if ($reparse.Count -ne 0) { throw "File map root contains a reparse point: $Root" }
  foreach ($file in Get-ChildItem -LiteralPath $resolved -Recurse -File -Force |
      Sort-Object FullName) {
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

function Set-OrphanMarkerAge {
  param(
    [Parameter(Mandatory = $true)][string]$CacheVersionRoot,
    [Parameter(Mandatory = $true)][long]$ClockMilliseconds,
    [Parameter(Mandatory = $true)][long]$AgeMilliseconds
  )
  $marker = Join-Path $CacheVersionRoot '.orphaned_at'
  if (-not (Test-Path -LiteralPath $marker -PathType Leaf)) {
    throw 'Claude orphan marker is absent.'
  }
  $targetMilliseconds = $ClockMilliseconds - $AgeMilliseconds
  $target = [DateTimeOffset]::FromUnixTimeMilliseconds($targetMilliseconds)
  Set-Content -LiteralPath $marker -Encoding ascii -NoNewline -Value $targetMilliseconds
  [System.IO.File]::SetLastWriteTimeUtc($marker, $target.UtcDateTime)
  $observedMilliseconds = [DateTimeOffset]::new(
    (Get-Item -LiteralPath $marker).LastWriteTimeUtc
  ).ToUnixTimeMilliseconds()
  if ([Math]::Abs($observedMilliseconds - $targetMilliseconds) -gt 2000) {
    throw 'Claude orphan marker mtime could not be set at the requested boundary.'
  }
}

function Read-JsonOutput {
  param([System.Collections.IDictionary]$Result, [string]$Label)
  try {
    return $Result.stdout | ConvertFrom-Json
  } catch {
    throw "$Label did not return JSON"
  }
}

function Get-InstalledInventory {
  param(
    [System.Collections.IDictionary]$Result,
    [ValidateSet('codex', 'claude')][string]$HostId,
    [string]$Label
  )
  $value = Read-JsonOutput $Result $Label
  if ($HostId -eq 'codex') { return @($value.installed) }
  return @($value)
}

function Assert-PluginInventory {
  param(
    [System.Collections.IDictionary]$Result,
    [ValidateSet('codex', 'claude')][string]$HostId,
    [string]$PluginId,
    [AllowNull()][string]$ExpectedVersion,
    [bool]$Present,
    [string]$Label
  )
  $items = @(Get-InstalledInventory $Result $HostId $Label)
  $matches = @($items | Where-Object {
    $actualId = if ($HostId -eq 'codex') { $_.pluginId } else { $_.id }
    $actualId -eq $PluginId
  })
  if (-not $Present) {
    if ($matches.Count -ne 0) { throw "$Label retained $PluginId." }
    return
  }
  if ($matches.Count -ne 1 -or $matches[0].version -ne $ExpectedVersion -or
      -not $matches[0].enabled) {
    throw "$Label inventory is invalid for $PluginId."
  }
}

function Get-MarketplaceInventory {
  param(
    [System.Collections.IDictionary]$Result,
    [ValidateSet('codex', 'claude')][string]$HostId,
    [string]$Label
  )
  $value = Read-JsonOutput $Result $Label
  if ($HostId -eq 'codex') { return @($value.marketplaces) }
  return @($value)
}

function Assert-MarketplaceInventory {
  param(
    [System.Collections.IDictionary]$Result,
    [ValidateSet('codex', 'claude')][string]$HostId,
    [string]$MarketplaceName,
    [bool]$Present,
    [string]$Label
  )
  $matches = @(Get-MarketplaceInventory $Result $HostId $Label |
    Where-Object { $_.name -eq $MarketplaceName })
  if (($Present -and $matches.Count -ne 1) -or
      (-not $Present -and $matches.Count -ne 0)) {
    throw "$Label marketplace state is invalid for $MarketplaceName."
  }
}

function Add-CommandRecord {
  param(
    [Parameter(Mandatory = $true)][string]$Role,
    [Parameter(Mandatory = $true)][System.Collections.IDictionary]$Command,
    [AllowNull()][string]$FailureCategory = $null
  )
  if ($Command.Contains('role')) { throw "Command role already assigned: $Role" }
  $Command.Insert(0, 'role', $Role)
  $Command.Insert(1, 'failureCategory', $FailureCategory)
  [void]$commands.Add($Command)
}

function Get-ContractArgument {
  param(
    [Parameter(Mandatory = $true)][string]$Value,
    [Parameter(Mandatory = $true)][string]$Candidate,
    [Parameter(Mandatory = $true)][string]$PriorRelease
  )
  return $Value.Replace('%CANDIDATE_REVISION%', $Candidate).
    Replace('%PRIOR_RELEASE_REVISION%', $PriorRelease)
}

function Assert-CommandContract {
  param(
    [Parameter(Mandatory = $true)]$Contract,
    [Parameter(Mandatory = $true)]$ObservedCommands,
    [Parameter(Mandatory = $true)][string]$Candidate,
    [Parameter(Mandatory = $true)][string]$PriorRelease
  )
  if ($Contract.schema -ne 'yiyuan-accord-gt20-command-contract/v1' -or
      $Contract.priorRelease.tag -ne 'v3.0.1' -or
      $Contract.priorRelease.revision -ne $PriorRelease) {
    throw 'GT-20 command contract identity is invalid.'
  }
  $expected = @($Contract.commands)
  if ($expected.Count -ne $ObservedCommands.Count) {
    throw "GT-20 command count $($ObservedCommands.Count) differs from contract $($expected.Count)."
  }
  $profiles = $Contract.environmentProfiles
  $baseAllowed = @($profiles.base.allowedKeys)
  $baseRequired = @($profiles.base.requiredKeys)
  for ($index = 0; $index -lt $expected.Count; $index++) {
    $spec = $expected[$index]
    $command = $ObservedCommands[$index]
    $argv = @($spec.argv | ForEach-Object {
      Get-ContractArgument ([string]$_) $Candidate $PriorRelease
    })
    $expectedBudgets = if ($null -ne $spec.budgets) {
      $spec.budgets
    } else {
      $Contract.budgets
    }
    $expectedExit = if ($spec.expectedExit -eq 'zero') { 0 } else { $null }
    $expectedTimedOut = $spec.expectedExit -eq 'timeout'
    if ($command.role -ne $spec.role -or
        (($command.argv | ConvertTo-Json -Compress) -ne ($argv | ConvertTo-Json -Compress)) -or
        $command.environmentProfile -ne $spec.environmentProfile -or
        $command.failureCategory -ne $spec.expectedFailureCategory -or
        $command.inputSha256 -ne $spec.inputSha256 -or
        $command.executionTimeoutSeconds -ne $expectedBudgets.executionTimeoutSeconds -or
        $command.endToEndTimeoutSeconds -ne $expectedBudgets.endToEndTimeoutSeconds -or
        $command.outputLimitBytes -ne $expectedBudgets.outputLimitBytes -or
        $command.timedOut -ne $expectedTimedOut -or
        $command.terminationRequested -ne $expectedTimedOut -or
        $command.terminationConfirmed -ne $true -or
        $command.streamsDrained -ne $true -or
        $command.jobActiveProcesses -ne 0 -or
        ($spec.expectedExit -eq 'zero' -and $command.exitCode -ne $expectedExit) -or
        ($spec.expectedExit -eq 'nonzero' -and $command.exitCode -eq 0) -or
        ($spec.expectedExit -eq 'timeout' -and $command.exitCode -ne 124)) {
      throw "GT-20 command contract mismatch at index $index ($($spec.role))."
    }
    $profile = $profiles.($spec.environmentProfile)
    $allowed = @($baseAllowed + @($profile.additionalKeys) | Sort-Object -Unique)
    $required = @($baseRequired + @($profile.requiredAdditionalKeys) | Sort-Object -Unique)
    if (@($command.environmentKeys | Where-Object { $_ -notin $allowed }).Count -ne 0 -or
        @($required | Where-Object { $_ -notin $command.environmentKeys }).Count -ne 0) {
      throw "GT-20 command environment contract mismatch at index $index ($($spec.role))."
    }
    $expectedBindings = $profile.bindings
    if (($command.environmentBindings | ConvertTo-Json -Compress) -ne
        ($expectedBindings | ConvertTo-Json -Compress)) {
      throw "GT-20 command environment binding mismatch at index $index ($($spec.role))."
    }
  }
  $claudeCommands = @($ObservedCommands | Where-Object { $_.argv[0] -eq 'claude' })
  $claudeIdentity = @($claudeCommands | ForEach-Object {
    "$($_.resolvedCommandSha256):$($_.terminalExecutableSha256):$($_.packageManifestSha256)"
  } | Sort-Object -Unique)
  if ($claudeCommands.Count -eq 0 -or $claudeIdentity.Count -ne 1) {
    throw 'Claude command identity drifted during GT-20.'
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
$script:PrivateRootsForEvidence = @(
  [pscustomobject]@{path = $task; replacement = '%TASK_ROOT%'},
  [pscustomobject]@{path = $repository; replacement = '%REPOSITORY_ROOT%'},
  [pscustomobject]@{path = $env:LOCALAPPDATA; replacement = '%LOCALAPPDATA%'},
  [pscustomobject]@{path = $env:APPDATA; replacement = '%APPDATA%'},
  [pscustomobject]@{path = $env:USERPROFILE; replacement = '%USERPROFILE%'},
  [pscustomobject]@{path = $temporaryBase; replacement = '%TEMP%'}
) | Where-Object path | Sort-Object { ([string]$_.path).Length } -Descending
$commands = [System.Collections.Generic.List[object]]::new()
$succeeded = $false
try {
$commitCheck = Invoke-Captured git @('-C', $repository, 'rev-parse', '--verify', "$CandidateRevision`^{commit}") $repository
Add-CommandRecord 'candidateCommitCheck' $commitCheck
Assert-Exit $commitCheck 0 'candidate commit validation'
if ($commitCheck.stdout.Trim() -ne $CandidateRevision) {
  throw 'CandidateRevision is not an exact commit.'
}
$priorReleaseTag = 'v3.0.1'
$expectedPriorReleaseRevision = '24cf9f3750ecd700944988e81a519db54b67b8e8'
$priorReleaseCheck = Invoke-Captured git @(
  '-C', $repository, 'rev-parse', '--verify', "$priorReleaseTag`^{commit}"
) $repository
Add-CommandRecord 'priorReleaseRevision' $priorReleaseCheck
Assert-Exit $priorReleaseCheck 0 'prior release commit validation'
$priorReleaseRevision = $priorReleaseCheck.stdout.Trim()
if ($priorReleaseRevision -ne $expectedPriorReleaseRevision) {
  throw 'The v3.0.1 tag no longer resolves to the admitted prior release revision.'
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
Add-CommandRecord 'gitVersion' $gitVersion
Assert-Exit $gitVersion 0 'Git version'
$tarVersion = Invoke-Captured tar @('--version') $task
Add-CommandRecord 'tarVersion' $tarVersion
Assert-Exit $tarVersion 0 'tar version'

$oldArchive = Join-Path $task 'old.tar'
$candidateArchive = Join-Path $task 'candidate.tar'
$archiveOld = Invoke-Captured git @('-C', $repository, 'archive', '--format=tar', "--output=$oldArchive", $priorReleaseRevision) $repository
Add-CommandRecord 'archivePriorRelease' $archiveOld
Assert-Exit $archiveOld 0 'archive old release'
$archiveCandidate = Invoke-Captured git @('-C', $repository, 'archive', '--format=tar', "--output=$candidateArchive", $CandidateRevision) $repository
Add-CommandRecord 'archiveCandidate' $archiveCandidate
Assert-Exit $archiveCandidate 0 'archive candidate'
$extractOld = Invoke-Captured tar @('-xf', $oldArchive, '-C', $oldSource) $task
Add-CommandRecord 'extractPriorRelease' $extractOld
Assert-Exit $extractOld 0 'extract old release'
$extractCandidate = Invoke-Captured tar @('-xf', $candidateArchive, '-C', $candidateSource) $task
Add-CommandRecord 'extractCandidate' $extractCandidate
Assert-Exit $extractCandidate 0 'extract candidate'
Copy-Item -LiteralPath $oldSource -Destination $mutableSource -Recurse

$neighborSource = Join-Path $task 'neighbor-marketplace'
$neighborCodexPackage = Join-Path $neighborSource 'plugins/lifecycle-neighbor-codex'
$neighborClaudePackage = Join-Path $neighborSource 'plugins/lifecycle-neighbor-claude'
foreach ($path in @(
  (Join-Path $neighborSource '.agents/plugins'),
  (Join-Path $neighborSource '.claude-plugin'),
  (Join-Path $neighborCodexPackage '.codex-plugin'),
  (Join-Path $neighborCodexPackage 'skills/lifecycle-neighbor-marker'),
  (Join-Path $neighborClaudePackage '.claude-plugin'),
  (Join-Path $neighborClaudePackage 'skills/lifecycle-neighbor-marker')
)) {
  New-Item -ItemType Directory -Path $path -Force | Out-Null
}
$neighborCodexMarketplace = [ordered]@{
  name = 'lifecycle-neighbor'
  interface = [ordered]@{displayName = 'Lifecycle Neighbor Fixture'}
  plugins = @([ordered]@{
    name = 'lifecycle-neighbor-codex'
    source = [ordered]@{
      source = 'local'
      path = './plugins/lifecycle-neighbor-codex'
    }
    policy = [ordered]@{
      installation = 'AVAILABLE'
      authentication = 'ON_INSTALL'
    }
    category = 'Developer Tools'
  })
}
$neighborClaudeMarketplace = [ordered]@{
  name = 'lifecycle-neighbor'
  description = 'Isolated lifecycle preservation fixture.'
  owner = [ordered]@{name = 'GT20 Evaluator'}
  plugins = @([ordered]@{
    name = 'lifecycle-neighbor-claude'
    source = './plugins/lifecycle-neighbor-claude'
    description = 'Passive independent plugin used only for lifecycle preservation verification.'
    version = '1.0.0'
  })
}
$neighborCodexManifest = [ordered]@{
  name = 'lifecycle-neighbor-codex'
  version = '1.0.0'
  description = 'Passive independent plugin used only for isolated lifecycle preservation verification.'
  skills = './skills/'
}
$neighborClaudeManifest = [ordered]@{
  name = 'lifecycle-neighbor-claude'
  version = '1.0.0'
  description = 'Passive independent plugin used only for isolated lifecycle preservation verification.'
  skills = './skills/'
}
$utf8 = [System.Text.UTF8Encoding]::new($false)
foreach ($entry in @(
  @((Join-Path $neighborSource '.agents/plugins/marketplace.json'), $neighborCodexMarketplace),
  @((Join-Path $neighborSource '.claude-plugin/marketplace.json'), $neighborClaudeMarketplace),
  @((Join-Path $neighborCodexPackage '.codex-plugin/plugin.json'), $neighborCodexManifest),
  @((Join-Path $neighborClaudePackage '.claude-plugin/plugin.json'), $neighborClaudeManifest)
)) {
  [System.IO.File]::WriteAllText(
    $entry[0], ($entry[1] | ConvertTo-Json -Depth 10) + [System.Environment]::NewLine,
    $utf8
  )
}
$neighborSkill = @'
---
name: lifecycle-neighbor-marker
description: Passive marker for isolated host lifecycle preservation verification.
---

# Lifecycle Neighbor Marker

This evaluator-owned fixture has no hooks, executables, dependencies or active behavior.
'@
[System.IO.File]::WriteAllText(
  (Join-Path $neighborCodexPackage 'skills/lifecycle-neighbor-marker/SKILL.md'),
  $neighborSkill + [System.Environment]::NewLine, $utf8
)
[System.IO.File]::WriteAllText(
  (Join-Path $neighborClaudePackage 'skills/lifecycle-neighbor-marker/SKILL.md'),
  $neighborSkill + [System.Environment]::NewLine, $utf8
)

$codexAgents = Join-Path $codexRoot 'AGENTS.md'
$codexConfig = Join-Path $codexRoot 'config.toml'
$claudeInstructions = Join-Path $claudeRoot 'CLAUDE.md'
$claudeSettings = Join-Path $claudeRoot 'settings.json'
Set-Content -LiteralPath $codexAgents -Encoding utf8 -NoNewline -Value "USER_CODEX_INSTRUCTIONS`n"
Set-Content -LiteralPath $codexConfig -Encoding utf8 -NoNewline -Value "# USER_CODEX_CONFIG`n"
Set-Content -LiteralPath $claudeInstructions -Encoding utf8 -NoNewline -Value "USER_CLAUDE_INSTRUCTIONS`n"
Set-Content -LiteralPath $claudeSettings -Encoding utf8 -NoNewline -Value "{`"permissions`":{`"allow`":[]},`"userSentinel`":`"USER_CLAUDE_SETTINGS`"}`n"
Set-Content -LiteralPath (Join-Path $codexRoot 'unmanaged-user-state.txt') -Encoding utf8 -NoNewline -Value 'UNMANAGED_CODEX'
Set-Content -LiteralPath (Join-Path $claudeRoot 'unmanaged-user-state.txt') -Encoding utf8 -NoNewline -Value 'UNMANAGED_CLAUDE'

$codexEnvironment = @{CODEX_HOME = $codexRoot}
$claudeEnvironment = @{CLAUDE_CONFIG_DIR = $claudeRoot}
$codexVersion = Invoke-Captured codex @('--version') $task $codexEnvironment
Add-CommandRecord 'codexVersion' $codexVersion
Assert-Exit $codexVersion 0 'Codex version'
$claudeVersion = Invoke-Captured claude @('--version') $task $claudeEnvironment
Add-CommandRecord 'claudeVersion' $claudeVersion
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
Add-CommandRecord 'nodeVersion' $nodeVersion
Assert-Exit $nodeVersion 0 'Node version'
$terminationProbeSource = "const {spawn}=require('node:child_process');spawn(process.execPath,['-e','setInterval(()=>{},1000)'],{stdio:['ignore','inherit','inherit']});setInterval(()=>{},1000);"
$terminationProbe = Invoke-Captured node @(
  '-e', $terminationProbeSource
) $task @{} '' 2 8 65536
Add-CommandRecord 'processTreeTerminationProbe' $terminationProbe 'owned-tree-timeout'
if ($terminationProbe.exitCode -ne 124 -or
    $terminationProbe.timedOut -ne $true -or
    $terminationProbe.terminationRequested -ne $true -or
    $terminationProbe.terminationConfirmed -ne $true -or
    $terminationProbe.streamsDrained -ne $true -or
    $terminationProbe.jobActiveProcesses -ne 0) {
  throw 'Owned process-tree termination probe did not close exactly.'
}

$neighborCodexMarketplaceAdd = Invoke-Captured codex @(
  'plugin', 'marketplace', 'add', $neighborSource, '--json'
) $neighborSource $codexEnvironment
Add-CommandRecord 'neighborCodexMarketplaceAdd' $neighborCodexMarketplaceAdd
Assert-Exit $neighborCodexMarketplaceAdd 0 'Codex neighbor marketplace add'
$neighborClaudeMarketplaceAdd = Invoke-Captured claude @(
  'plugin', 'marketplace', 'add', $neighborSource, '--scope', 'user'
) $neighborSource $claudeEnvironment
Add-CommandRecord 'neighborClaudeMarketplaceAdd' $neighborClaudeMarketplaceAdd
Assert-Exit $neighborClaudeMarketplaceAdd 0 'Claude neighbor marketplace add'
$neighborCodexInstall = Invoke-Captured codex @(
  'plugin', 'add', 'lifecycle-neighbor-codex@lifecycle-neighbor', '--json'
) $neighborSource $codexEnvironment
Add-CommandRecord 'neighborCodexInstall' $neighborCodexInstall
Assert-Exit $neighborCodexInstall 0 'Codex neighbor install'
$neighborClaudeInstall = Invoke-Captured claude @(
  'plugin', 'install', 'lifecycle-neighbor-claude@lifecycle-neighbor',
  '--scope', 'user', '-y'
) $neighborSource $claudeEnvironment
Add-CommandRecord 'neighborClaudeInstall' $neighborClaudeInstall
Assert-Exit $neighborClaudeInstall 0 'Claude neighbor install'
$neighborCodexInventory = Invoke-Captured codex @('plugin', 'list', '--json') $neighborSource $codexEnvironment
Add-CommandRecord 'neighborCodexInventory' $neighborCodexInventory
Assert-Exit $neighborCodexInventory 0 'Codex neighbor inventory'
$neighborClaudeInventory = Invoke-Captured claude @('plugin', 'list', '--json') $neighborSource $claudeEnvironment
Add-CommandRecord 'neighborClaudeInventory' $neighborClaudeInventory
Assert-Exit $neighborClaudeInventory 0 'Claude neighbor inventory'
Assert-PluginInventory $neighborCodexInventory codex 'lifecycle-neighbor-codex@lifecycle-neighbor' '1.0.0' $true 'Codex neighbor'
Assert-PluginInventory $neighborClaudeInventory claude 'lifecycle-neighbor-claude@lifecycle-neighbor' '1.0.0' $true 'Claude neighbor'
$neighborCodexInstalled = Join-Path $codexRoot 'plugins/cache/lifecycle-neighbor/lifecycle-neighbor-codex/1.0.0'
$neighborClaudeInstalled = Join-Path $claudeRoot 'plugins/cache/lifecycle-neighbor/lifecycle-neighbor-claude/1.0.0'
$neighborCodexFileCount = Assert-FileMapsEqual $neighborCodexPackage $neighborCodexInstalled 'Codex neighbor initial'
$neighborClaudeFileCount = Assert-FileMapsEqual $neighborClaudePackage $neighborClaudeInstalled 'Claude neighbor initial'

$codexMarketplace = Invoke-Captured codex @('plugin', 'marketplace', 'add', $mutableSource, '--json') $mutableSource $codexEnvironment
Add-CommandRecord 'accordCodexMarketplaceAdd' $codexMarketplace
Assert-Exit $codexMarketplace 0 'Codex marketplace add'
$claudeMarketplace = Invoke-Captured claude @('plugin', 'marketplace', 'add', $mutableSource, '--scope', 'user') $mutableSource $claudeEnvironment
Add-CommandRecord 'accordClaudeMarketplaceAdd' $claudeMarketplace
Assert-Exit $claudeMarketplace 0 'Claude marketplace add'
$codexInstall = Invoke-Captured codex @('plugin', 'add', 'yiyuan-accord-codex@yiyuan-accord', '--json') $mutableSource $codexEnvironment
Add-CommandRecord 'accordCodexInstallPrior' $codexInstall
Assert-Exit $codexInstall 0 'Codex install'
$claudeInstall = Invoke-Captured claude @('plugin', 'install', 'yiyuan-accord-claude@yiyuan-accord', '--scope', 'user', '-y') $mutableSource $claudeEnvironment
Add-CommandRecord 'accordClaudeInstallPrior' $claudeInstall
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
  (Join-Path $codexRoot 'unmanaged-user-state.txt'),
  (Join-Path $claudeRoot 'unmanaged-user-state.txt'))
$sentinelHashes = [ordered]@{}
foreach ($path in $sentinels) {
  $sentinelHashes[$path] = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
}

Move-Item -LiteralPath (Join-Path $mutableSource 'plugins/yiyuan-accord-codex') -Destination (Join-Path $mutableSource 'plugins/yiyuan-accord-codex.failed-update-source')
Move-Item -LiteralPath (Join-Path $mutableSource 'plugins/yiyuan-accord-claude') -Destination (Join-Path $mutableSource 'plugins/yiyuan-accord-claude.failed-update-source')
if ((Test-Path -LiteralPath (Join-Path $mutableSource 'plugins/yiyuan-accord-codex')) -or
    (Test-Path -LiteralPath (Join-Path $mutableSource 'plugins/yiyuan-accord-claude'))) {
  throw 'Failed-update source paths were not removed.'
}
$codexFailedUpdate = Invoke-Captured codex @('plugin', 'add', 'yiyuan-accord-codex@yiyuan-accord', '--json') $mutableSource $codexEnvironment
Add-CommandRecord 'accordCodexFailedUpdate' $codexFailedUpdate 'source-path-absent'
if ($codexFailedUpdate.exitCode -eq 0) { throw 'Codex failed update unexpectedly succeeded' }
$claudeFailedUpdate = Invoke-Captured claude @('plugin', 'update', 'yiyuan-accord-claude@yiyuan-accord', '--scope', 'user', '-y') $mutableSource $claudeEnvironment
Add-CommandRecord 'accordClaudeFailedUpdate' $claudeFailedUpdate 'source-path-absent'
if ($claudeFailedUpdate.exitCode -eq 0) { throw 'Claude failed update unexpectedly succeeded' }
[void](Assert-FileMapsEqual (Join-Path $oldSource 'plugins/yiyuan-accord-codex') $codexOldInstalled 'Codex rollback')
[void](Assert-FileMapsEqual (Join-Path $oldSource 'plugins/yiyuan-accord-claude') $claudeOldInstalled 'Claude rollback')
$codexRollbackList = Invoke-Captured codex @('plugin', 'list', '--json') $mutableSource $codexEnvironment
Add-CommandRecord 'rollbackCodexInventory' $codexRollbackList
Assert-Exit $codexRollbackList 0 'Codex rollback list'
$claudeRollbackList = Invoke-Captured claude @('plugin', 'list', '--json') $mutableSource $claudeEnvironment
Add-CommandRecord 'rollbackClaudeInventory' $claudeRollbackList
Assert-Exit $claudeRollbackList 0 'Claude rollback list'
Assert-PluginInventory $codexRollbackList codex 'yiyuan-accord-codex@yiyuan-accord' '3.0.1' $true 'Codex rollback'
Assert-PluginInventory $claudeRollbackList claude 'yiyuan-accord-claude@yiyuan-accord' '3.0.1' $true 'Claude rollback'
Assert-PluginInventory $codexRollbackList codex 'lifecycle-neighbor-codex@lifecycle-neighbor' '1.0.0' $true 'Codex neighbor after rollback'
Assert-PluginInventory $claudeRollbackList claude 'lifecycle-neighbor-claude@lifecycle-neighbor' '1.0.0' $true 'Claude neighbor after rollback'
[void](Assert-FileMapsEqual $neighborCodexPackage $neighborCodexInstalled 'Codex neighbor after rollback')
[void](Assert-FileMapsEqual $neighborClaudePackage $neighborClaudeInstalled 'Claude neighbor after rollback')

Copy-Item -LiteralPath (Join-Path $candidateSource 'plugins/yiyuan-accord-codex') -Destination (Join-Path $mutableSource 'plugins/yiyuan-accord-codex') -Recurse
Copy-Item -LiteralPath (Join-Path $candidateSource 'plugins/yiyuan-accord-claude') -Destination (Join-Path $mutableSource 'plugins/yiyuan-accord-claude') -Recurse
Copy-Item -LiteralPath (Join-Path $candidateSource '.agents/plugins/marketplace.json') -Destination (Join-Path $mutableSource '.agents/plugins/marketplace.json') -Force
Copy-Item -LiteralPath (Join-Path $candidateSource '.claude-plugin/marketplace.json') -Destination (Join-Path $mutableSource '.claude-plugin/marketplace.json') -Force
$codexUpdate = Invoke-Captured codex @('plugin', 'add', 'yiyuan-accord-codex@yiyuan-accord', '--json') $mutableSource $codexEnvironment
Add-CommandRecord 'accordCodexUpdateCandidate' $codexUpdate
Assert-Exit $codexUpdate 0 'Codex successful update'
$claudeUpdate = Invoke-Captured claude @('plugin', 'update', 'yiyuan-accord-claude@yiyuan-accord', '--scope', 'user', '-y') $mutableSource $claudeEnvironment
Add-CommandRecord 'accordClaudeUpdateCandidate' $claudeUpdate
Assert-Exit $claudeUpdate 0 'Claude successful update'

$codexInstalled = Join-Path $codexRoot 'plugins/cache/yiyuan-accord/yiyuan-accord-codex/3.1.0'
$claudeInstalled = Join-Path $claudeRoot 'plugins/cache/yiyuan-accord/yiyuan-accord-claude/3.1.0'
$codexFileCount = Assert-FileMapsEqual (Join-Path $candidateSource 'plugins/yiyuan-accord-codex') $codexInstalled 'Codex candidate'
$claudeFileCount = Assert-FileMapsEqual (Join-Path $candidateSource 'plugins/yiyuan-accord-claude') $claudeInstalled 'Claude candidate'
$codexList = Invoke-Captured codex @('plugin', 'list', '--json') $mutableSource $codexEnvironment
Add-CommandRecord 'candidateCodexInventory' $codexList
Assert-Exit $codexList 0 'Codex list'
$claudeList = Invoke-Captured claude @('plugin', 'list', '--json') $mutableSource $claudeEnvironment
Add-CommandRecord 'candidateClaudeInventory' $claudeList
Assert-Exit $claudeList 0 'Claude list'
Assert-PluginInventory $codexList codex 'yiyuan-accord-codex@yiyuan-accord' '3.1.0' $true 'Codex list'
Assert-PluginInventory $claudeList claude 'yiyuan-accord-claude@yiyuan-accord' '3.1.0' $true 'Claude list'
Assert-PluginInventory $codexList codex 'lifecycle-neighbor-codex@lifecycle-neighbor' '1.0.0' $true 'Codex neighbor after update'
Assert-PluginInventory $claudeList claude 'lifecycle-neighbor-claude@lifecycle-neighbor' '1.0.0' $true 'Claude neighbor after update'
[void](Assert-FileMapsEqual $neighborCodexPackage $neighborCodexInstalled 'Codex neighbor after update')
[void](Assert-FileMapsEqual $neighborClaudePackage $neighborClaudeInstalled 'Claude neighbor after update')

$startup = '{"hook_event_name":"SessionStart","source":"startup"}'
$resume = '{"hook_event_name":"SessionStart","source":"resume","model":"model-variable","permission_mode":"default"}'
foreach ($runtimeCase in @(
  [pscustomobject]@{Host = 'codex'; Path = (Join-Path $codexInstalled 'runtime/accord-hook.cjs')},
  [pscustomobject]@{Host = 'claude'; Path = (Join-Path $claudeInstalled 'runtime/accord-hook.cjs')}
)) {
  $startupResult = Invoke-Captured node @($runtimeCase.Path) $task @{} $startup
  Add-CommandRecord "$($runtimeCase.Host)HookStartup" $startupResult
  Assert-Exit $startupResult 0 'Hook startup'
  if ($startupResult.stdout.Length -ne 0 -or $startupResult.stderr.Length -ne 0) { throw 'Hook startup was not silent.' }
  $resumeResult = Invoke-Captured node @($runtimeCase.Path) $task @{} $resume
  Add-CommandRecord "$($runtimeCase.Host)HookResume" $resumeResult
  Assert-Exit $resumeResult 0 'Hook resume'
  if (-not $resumeResult.stdout.Contains('yiyuan-accord-hook-context/v1')) { throw 'Hook resume did not emit typed context.' }
}

# Claude's public cache contract runs its approximately 14-day orphan sweep
# during plugin initialization, and only while at least one plugin remains
# installed. The real, evaluator-owned neighbor stays installed while both the
# prior and candidate Accord orphan boundaries are probed.
$claudeCacheRoot = Join-Path $claudeRoot 'plugins/cache/yiyuan-accord/yiyuan-accord-claude'
$claudeOldCache = Join-Path $claudeCacheRoot '3.0.1'
$claudeCandidateCache = Join-Path $claudeCacheRoot '3.1.0'
$retentionMilliseconds = 1209600000L
$clockMilliseconds = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
$youngAgeMilliseconds = $retentionMilliseconds - 3600000L
$expiredAgeMilliseconds = $retentionMilliseconds + 3600000L
[void](Assert-ExactOrphanCacheVersion (Join-Path $oldSource 'plugins/yiyuan-accord-claude') $claudeOldCache 'Claude old')
Set-OrphanMarkerAge $claudeOldCache $clockMilliseconds $youngAgeMilliseconds
$claudeOldYoungSweep = Invoke-Captured claude @('--init-only') $task $claudeEnvironment
Add-CommandRecord 'claudeOldYoungSweep' $claudeOldYoungSweep
Assert-Exit $claudeOldYoungSweep 0 'Claude old young orphan sweep'
if (-not (Test-Path -LiteralPath $claudeOldCache -PathType Container)) {
  throw 'Claude removed a younger-than-contract orphan cache.'
}
[void](Assert-ExactOrphanCacheVersion (Join-Path $oldSource 'plugins/yiyuan-accord-claude') $claudeOldCache 'Claude young')
Set-OrphanMarkerAge $claudeOldCache $clockMilliseconds $expiredAgeMilliseconds
$claudeOldExpiredSweep = Invoke-Captured claude @('--init-only') $task $claudeEnvironment
Add-CommandRecord 'claudeOldExpiredSweep' $claudeOldExpiredSweep
Assert-Exit $claudeOldExpiredSweep 0 'Claude old expired orphan sweep'
$expiredSweepDeadline = [DateTimeOffset]::UtcNow.AddSeconds(5)
while ((Test-Path -LiteralPath $claudeOldCache) -and
       [DateTimeOffset]::UtcNow -lt $expiredSweepDeadline) {
  Start-Sleep -Milliseconds 100
}
if (Test-Path -LiteralPath $claudeOldCache) {
  throw 'Claude retained an older-than-contract orphan cache.'
}
[void](Assert-FileMapsEqual (Join-Path $candidateSource 'plugins/yiyuan-accord-claude') $claudeCandidateCache 'Claude retained installed candidate')

$codexRemove = Invoke-Captured codex @('plugin', 'remove', 'yiyuan-accord-codex@yiyuan-accord', '--json') $mutableSource $codexEnvironment
Add-CommandRecord 'accordCodexRemove' $codexRemove
Assert-Exit $codexRemove 0 'Codex remove'
$claudeRemove = Invoke-Captured claude @('plugin', 'uninstall', 'yiyuan-accord-claude@yiyuan-accord', '--scope', 'user', '-y') $mutableSource $claudeEnvironment
Add-CommandRecord 'accordClaudeRemove' $claudeRemove
Assert-Exit $claudeRemove 0 'Claude remove'
$codexMarketplaceRemove = Invoke-Captured codex @('plugin', 'marketplace', 'remove', 'yiyuan-accord', '--json') $mutableSource $codexEnvironment
Add-CommandRecord 'accordCodexMarketplaceRemove' $codexMarketplaceRemove
Assert-Exit $codexMarketplaceRemove 0 'Codex marketplace remove'
$claudeMarketplaceRemove = Invoke-Captured claude @('plugin', 'marketplace', 'remove', 'yiyuan-accord', '--scope', 'user') $mutableSource $claudeEnvironment
Add-CommandRecord 'accordClaudeMarketplaceRemove' $claudeMarketplaceRemove
Assert-Exit $claudeMarketplaceRemove 0 'Claude marketplace remove'
[void](Assert-ExactOrphanCacheVersion (Join-Path $candidateSource 'plugins/yiyuan-accord-claude') $claudeCandidateCache 'Claude candidate')
$candidateClockMilliseconds = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
Set-OrphanMarkerAge $claudeCandidateCache $candidateClockMilliseconds $youngAgeMilliseconds
$claudeCandidateYoungSweep = Invoke-Captured claude @('--init-only') $task $claudeEnvironment
Add-CommandRecord 'claudeCandidateYoungSweep' $claudeCandidateYoungSweep
Assert-Exit $claudeCandidateYoungSweep 0 'Claude candidate young orphan sweep'
if (-not (Test-Path -LiteralPath $claudeCandidateCache -PathType Container)) {
  throw 'Claude removed the younger-than-contract candidate orphan cache.'
}
[void](Assert-ExactOrphanCacheVersion (Join-Path $candidateSource 'plugins/yiyuan-accord-claude') $claudeCandidateCache 'Claude candidate young')
Set-OrphanMarkerAge $claudeCandidateCache $candidateClockMilliseconds $expiredAgeMilliseconds
$claudeCandidateExpiredSweep = Invoke-Captured claude @('--init-only') $task $claudeEnvironment
Add-CommandRecord 'claudeCandidateExpiredSweep' $claudeCandidateExpiredSweep
Assert-Exit $claudeCandidateExpiredSweep 0 'Claude candidate expired orphan sweep'
$candidateSweepDeadline = [DateTimeOffset]::UtcNow.AddSeconds(5)
while ((Test-Path -LiteralPath $claudeCandidateCache) -and
       [DateTimeOffset]::UtcNow -lt $candidateSweepDeadline) {
  Start-Sleep -Milliseconds 100
}
if (Test-Path -LiteralPath $claudeCandidateCache) {
  throw 'Claude retained the older-than-contract candidate orphan cache.'
}
$afterRemoveCodexInventory = Invoke-Captured codex @('plugin', 'list', '--json') $task $codexEnvironment
Add-CommandRecord 'afterRemoveCodexInventory' $afterRemoveCodexInventory
Assert-Exit $afterRemoveCodexInventory 0 'Codex after-Accord-removal inventory'
$afterRemoveClaudeInventory = Invoke-Captured claude @('plugin', 'list', '--json') $task $claudeEnvironment
Add-CommandRecord 'afterRemoveClaudeInventory' $afterRemoveClaudeInventory
Assert-Exit $afterRemoveClaudeInventory 0 'Claude after-Accord-removal inventory'
$afterRemoveCodexMarketplaces = Invoke-Captured codex @(
  'plugin', 'marketplace', 'list', '--json'
) $task $codexEnvironment
Add-CommandRecord 'afterRemoveCodexMarketplaces' $afterRemoveCodexMarketplaces
Assert-Exit $afterRemoveCodexMarketplaces 0 'Codex after-Accord-removal marketplaces'
$afterRemoveClaudeMarketplaces = Invoke-Captured claude @(
  'plugin', 'marketplace', 'list', '--json'
) $task $claudeEnvironment
Add-CommandRecord 'afterRemoveClaudeMarketplaces' $afterRemoveClaudeMarketplaces
Assert-Exit $afterRemoveClaudeMarketplaces 0 'Claude after-Accord-removal marketplaces'
Assert-PluginInventory $afterRemoveCodexInventory codex 'yiyuan-accord-codex@yiyuan-accord' $null $false 'Codex Accord removal'
Assert-PluginInventory $afterRemoveClaudeInventory claude 'yiyuan-accord-claude@yiyuan-accord' $null $false 'Claude Accord removal'
Assert-PluginInventory $afterRemoveCodexInventory codex 'lifecycle-neighbor-codex@lifecycle-neighbor' '1.0.0' $true 'Codex neighbor after Accord removal'
Assert-PluginInventory $afterRemoveClaudeInventory claude 'lifecycle-neighbor-claude@lifecycle-neighbor' '1.0.0' $true 'Claude neighbor after Accord removal'
Assert-MarketplaceInventory $afterRemoveCodexMarketplaces codex 'yiyuan-accord' $false 'Codex Accord removal'
Assert-MarketplaceInventory $afterRemoveClaudeMarketplaces claude 'yiyuan-accord' $false 'Claude Accord removal'
Assert-MarketplaceInventory $afterRemoveCodexMarketplaces codex 'lifecycle-neighbor' $true 'Codex neighbor after Accord removal'
Assert-MarketplaceInventory $afterRemoveClaudeMarketplaces claude 'lifecycle-neighbor' $true 'Claude neighbor after Accord removal'
[void](Assert-FileMapsEqual $neighborCodexPackage $neighborCodexInstalled 'Codex neighbor after Accord removal')
[void](Assert-FileMapsEqual $neighborClaudePackage $neighborClaudeInstalled 'Claude neighbor after Accord removal')

foreach ($entry in $sentinelHashes.GetEnumerator()) {
  if (-not (Test-Path -LiteralPath $entry.Key) -or
      (Get-FileHash -Algorithm SHA256 -LiteralPath $entry.Key).Hash.ToLowerInvariant() -ne $entry.Value) {
    throw "User or unmanaged sentinel changed: $($entry.Key)"
  }
}
$afterRemoveCodexConfig = Get-Content -Raw -LiteralPath $codexConfig
if (-not $afterRemoveCodexConfig.Contains('# USER_CODEX_CONFIG') -or
    -not $afterRemoveCodexConfig.Contains('# CONCURRENT_CODEX_CONFIG_EDIT') -or
    $afterRemoveCodexConfig.Contains('yiyuan-accord')) {
  throw 'Codex user configuration was not preserved or Accord configuration remains.'
}
$afterRemoveClaudeSettings = Get-Content -Raw -LiteralPath $claudeSettings | ConvertFrom-Json
if ($afterRemoveClaudeSettings.userSentinel -ne 'USER_CLAUDE_SETTINGS' -or
    $afterRemoveClaudeSettings.concurrentSentinel -ne 'CONCURRENT_CLAUDE_SETTINGS' -or
    @($afterRemoveClaudeSettings.permissions.allow).Count -ne 0 -or
    ((Get-Content -Raw -LiteralPath $claudeSettings).Contains('yiyuan-accord'))) {
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
if ($claudeCache.Count -ne 0) {
  throw 'Claude retained Accord package cache after the bounded host sweep.'
}

$afterAccordRemoval = [ordered]@{
  codexAccordInstalledEntries = 0
  claudeAccordInstalledEntries = 0
  codexNeighborInstalledEntries = 1
  claudeNeighborInstalledEntries = 1
  codexAccordMarketplaceEntries = 0
  claudeAccordMarketplaceEntries = 0
  codexNeighborMarketplaceEntries = 1
  claudeNeighborMarketplaceEntries = 1
  taskProcesses = 0
  codexAccordCacheFiles = $codexCache
  claudeAccordCacheFiles = $claudeCache
  neighborInstalledBytesPreserved = $true
  unmanagedSentinelsPreserved = $true
  concurrentUserEditsPreserved = $true
}

# The neighbor is evaluator-owned. Remove it only after the Accord poststate is
# captured, through the same supported host lifecycle, before deleting TaskRoot.
$cleanupCodexNeighborRemove = Invoke-Captured codex @(
  'plugin', 'remove', 'lifecycle-neighbor-codex@lifecycle-neighbor', '--json'
) $neighborSource $codexEnvironment
Add-CommandRecord 'cleanupCodexNeighborRemove' $cleanupCodexNeighborRemove
Assert-Exit $cleanupCodexNeighborRemove 0 'Codex neighbor cleanup'
$cleanupClaudeNeighborRemove = Invoke-Captured claude @(
  'plugin', 'uninstall', 'lifecycle-neighbor-claude@lifecycle-neighbor',
  '--scope', 'user', '-y'
) $neighborSource $claudeEnvironment
Add-CommandRecord 'cleanupClaudeNeighborRemove' $cleanupClaudeNeighborRemove
Assert-Exit $cleanupClaudeNeighborRemove 0 'Claude neighbor cleanup'
$cleanupCodexNeighborMarketplace = Invoke-Captured codex @(
  'plugin', 'marketplace', 'remove', 'lifecycle-neighbor', '--json'
) $neighborSource $codexEnvironment
Add-CommandRecord 'cleanupCodexNeighborMarketplaceRemove' $cleanupCodexNeighborMarketplace
Assert-Exit $cleanupCodexNeighborMarketplace 0 'Codex neighbor marketplace cleanup'
$cleanupClaudeNeighborMarketplace = Invoke-Captured claude @(
  'plugin', 'marketplace', 'remove', 'lifecycle-neighbor', '--scope', 'user'
) $neighborSource $claudeEnvironment
Add-CommandRecord 'cleanupClaudeNeighborMarketplaceRemove' $cleanupClaudeNeighborMarketplace
Assert-Exit $cleanupClaudeNeighborMarketplace 0 'Claude neighbor marketplace cleanup'
$cleanupCodexInventory = Invoke-Captured codex @('plugin', 'list', '--json') $task $codexEnvironment
Add-CommandRecord 'cleanupCodexInventory' $cleanupCodexInventory
Assert-Exit $cleanupCodexInventory 0 'Codex cleanup inventory'
$cleanupClaudeInventory = Invoke-Captured claude @('plugin', 'list', '--json') $task $claudeEnvironment
Add-CommandRecord 'cleanupClaudeInventory' $cleanupClaudeInventory
Assert-Exit $cleanupClaudeInventory 0 'Claude cleanup inventory'
$cleanupCodexMarketplaces = Invoke-Captured codex @(
  'plugin', 'marketplace', 'list', '--json'
) $task $codexEnvironment
Add-CommandRecord 'cleanupCodexMarketplaces' $cleanupCodexMarketplaces
Assert-Exit $cleanupCodexMarketplaces 0 'Codex cleanup marketplaces'
$cleanupClaudeMarketplaces = Invoke-Captured claude @(
  'plugin', 'marketplace', 'list', '--json'
) $task $claudeEnvironment
Add-CommandRecord 'cleanupClaudeMarketplaces' $cleanupClaudeMarketplaces
Assert-Exit $cleanupClaudeMarketplaces 0 'Claude cleanup marketplaces'
Assert-PluginInventory $cleanupCodexInventory codex 'lifecycle-neighbor-codex@lifecycle-neighbor' $null $false 'Codex neighbor cleanup'
Assert-PluginInventory $cleanupClaudeInventory claude 'lifecycle-neighbor-claude@lifecycle-neighbor' $null $false 'Claude neighbor cleanup'
Assert-PluginInventory $cleanupCodexInventory codex 'yiyuan-accord-codex@yiyuan-accord' $null $false 'Codex Accord cleanup'
Assert-PluginInventory $cleanupClaudeInventory claude 'yiyuan-accord-claude@yiyuan-accord' $null $false 'Claude Accord cleanup'
Assert-MarketplaceInventory $cleanupCodexMarketplaces codex 'lifecycle-neighbor' $false 'Codex neighbor cleanup'
Assert-MarketplaceInventory $cleanupClaudeMarketplaces claude 'lifecycle-neighbor' $false 'Claude neighbor cleanup'
Assert-MarketplaceInventory $cleanupCodexMarketplaces codex 'yiyuan-accord' $false 'Codex Accord cleanup'
Assert-MarketplaceInventory $cleanupClaudeMarketplaces claude 'yiyuan-accord' $false 'Claude Accord cleanup'

$afterEvaluatorCleanup = [ordered]@{
  codexInstalledEntries = @(Get-InstalledInventory $cleanupCodexInventory codex 'Codex cleanup inventory').Count
  claudeInstalledEntries = @(Get-InstalledInventory $cleanupClaudeInventory claude 'Claude cleanup inventory').Count
  codexMarketplaceEntries = @(Get-MarketplaceInventory $cleanupCodexMarketplaces codex 'Codex cleanup marketplaces').Count
  claudeMarketplaceEntries = @(Get-MarketplaceInventory $cleanupClaudeMarketplaces claude 'Claude cleanup marketplaces').Count
  taskProcesses = @(Get-TaskProcessIds $task).Count
  taskRootRemoved = $false
}
if ($afterEvaluatorCleanup.codexInstalledEntries -ne 0 -or
    $afterEvaluatorCleanup.claudeInstalledEntries -ne 0 -or
    $afterEvaluatorCleanup.codexMarketplaceEntries -ne 0 -or
    $afterEvaluatorCleanup.claudeMarketplaceEntries -ne 0 -or
    $afterEvaluatorCleanup.taskProcesses -ne 0) {
  throw 'Evaluator-owned fixture cleanup is incomplete.'
}
$finalCodexConfig = Get-Content -Raw -LiteralPath $codexConfig
if (-not $finalCodexConfig.Contains('# USER_CODEX_CONFIG') -or
    -not $finalCodexConfig.Contains('# CONCURRENT_CODEX_CONFIG_EDIT') -or
    $finalCodexConfig.Contains('yiyuan-accord') -or
    $finalCodexConfig.Contains('lifecycle-neighbor')) {
  throw 'Codex evaluator cleanup changed user configuration or retained a test registration.'
}
$finalClaudeSettingsRaw = Get-Content -Raw -LiteralPath $claudeSettings
$finalClaudeSettings = $finalClaudeSettingsRaw | ConvertFrom-Json
if ($finalClaudeSettings.userSentinel -ne 'USER_CLAUDE_SETTINGS' -or
    $finalClaudeSettings.concurrentSentinel -ne 'CONCURRENT_CLAUDE_SETTINGS' -or
    @($finalClaudeSettings.permissions.allow).Count -ne 0 -or
    @($finalClaudeSettings.enabledPlugins.PSObject.Properties).Count -ne 0 -or
    @($finalClaudeSettings.extraKnownMarketplaces.PSObject.Properties).Count -ne 0 -or
    $finalClaudeSettingsRaw.Contains('yiyuan-accord') -or
    $finalClaudeSettingsRaw.Contains('lifecycle-neighbor')) {
  throw 'Claude evaluator cleanup changed user configuration or retained a test registration.'
}

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
$commandContractLocator = 'evals/contracts/gt20-v3-command-contract.json'
$commandContractPath = Join-Path $candidateSource $commandContractLocator
$commandContractBytes = [System.IO.File]::ReadAllBytes($commandContractPath)
$commandContract = [System.Text.Encoding]::UTF8.GetString($commandContractBytes) |
  ConvertFrom-Json -Depth 20
Assert-CommandContract $commandContract $commands $CandidateRevision $priorReleaseRevision
$commandContractSha256 = [Convert]::ToHexString(
  [System.Security.Cryptography.SHA256]::HashData($commandContractBytes)
).ToLowerInvariant()
$record = [ordered]@{
  schema = 'yiyuan-accord-gt20-exact-package-evidence/v3'
  taskId = 'GT-20'
  evaluatedRevision = $CandidateRevision
  runnerSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $PSCommandPath).Hash.ToLowerInvariant()
  commandContractLocator = $commandContractLocator
  commandContractSha256 = $commandContractSha256
  packageSha256 = $packages
  behaviorSubject = $behaviorSubject
  lifecycle = [ordered]@{
    install = 'verified'
    failedUpdateRollback = 'verified'
    successfulUpdate = 'verified'
    activation = 'verified'
    remove = 'verified'
    postState = 'verified'
    cleanup = 'pending'
  }
  claimLimit = 'Bounded zero-model Windows lifecycle, exact command-contract execution, command privacy and end-to-end process termination for exact subject Codex and Claude package bytes in disposable non-empty scopes containing a real evaluator-owned unrelated plugin and unmanaged sentinels; Claude host-owned approximately-14-day orphan cleanup was probed for prior and candidate Accord versions while the unrelated plugin remained installed, leaving zero Accord cache. Production, real unmanaged or cross-OS hosts, live-session cache behavior, ordinary model behavior, product value and release readiness remain unclaimed.'
  fixture = [ordered]@{
    platform = 'windows'
    priorVersion = '3.0.1'
    priorRevision = $priorReleaseRevision
    targetVersion = '3.1.0'
    userStatePreserved = $true
    concurrentEditsPreserved = $true
    unrelatedPluginStatePreserved = $true
    unrelatedPluginOwnership = 'evaluator-owned-fixture'
    unmanagedSentinelsPreserved = $true
    credentialEnvironmentInherited = $false
    hostConfigRootsIsolated = $true
    sessionInputsProvided = $false
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
    neighborCodexInstalledFileCount = $neighborCodexFileCount
    neighborClaudeInstalledFileCount = $neighborClaudeFileCount
  }
  commands = $commands
  postState = [ordered]@{
    afterAccordRemoval = $afterAccordRemoval
    afterEvaluatorCleanup = $afterEvaluatorCleanup
  }
  hostCacheDisposition = [ordered]@{
    codex = [ordered]@{
      classification = 'no-retained-accord-package-cache'
      hostCallable = $false
    }
    claude = [ordered]@{
      classification = 'host-owned-orphan-cache-swept-to-zero-with-installed-neighbor'
      observedVersions = @('3.0.1', '3.1.0')
      retainedVersions = @()
      exactAllowlistVerified = $true
      listedOrEnabled = $false
      hostCallable = $false
      dataStatePresent = $false
      hostIdentity = [ordered]@{
        cliVersion = $claudeVersion.stdout.Trim()
        packageManifestSha256 = $claudeVersion.packageManifestSha256
        terminalExecutableSha256 = $claudeVersion.terminalExecutableSha256
      }
      officialContract = [ordered]@{
        source = 'https://code.claude.com/docs/en/plugins-reference#plugin-caching-and-file-resolution'
        gracePeriod = 'roughly-14-days'
        requiresInstalledPlugin = $true
      }
      exactHostProbe = [ordered]@{
        ageSignal = 'orphan-marker-filesystem-mtime'
        observedGracePeriodMilliseconds = $retentionMilliseconds
        trigger = 'plugin-initialization'
        priorVersion = [ordered]@{
          young = [ordered]@{
            ageMilliseconds = $youngAgeMilliseconds
            disposition = 'retained'
            commandRole = 'claudeOldYoungSweep'
          }
          expired = [ordered]@{
            ageMilliseconds = $expiredAgeMilliseconds
            disposition = 'removed'
            commandRole = 'claudeOldExpiredSweep'
          }
        }
        candidateVersion = [ordered]@{
          young = [ordered]@{
            ageMilliseconds = $youngAgeMilliseconds
            disposition = 'retained'
            commandRole = 'claudeCandidateYoungSweep'
          }
          expired = [ordered]@{
            ageMilliseconds = $expiredAgeMilliseconds
            disposition = 'removed'
            commandRole = 'claudeCandidateExpiredSweep'
          }
        }
        liveSessionBehavior = 'unverified'
      }
    }
  }
}

Remove-Item -LiteralPath $task -Recurse -Force
if (Test-Path -LiteralPath $task) { throw 'TaskRoot cleanup failed.' }
$record.lifecycle.cleanup = 'verified'
$record.postState.afterEvaluatorCleanup.taskRootRemoved = $true
Assert-NoPrivateEvidenceValue $record
$evidenceJson = $record | ConvertTo-Json -Depth 20
Assert-NoPrivateEvidenceValue ($evidenceJson | ConvertFrom-Json -Depth 30)
$succeeded = $true
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
    $succeeded = $false
    throw ('GT-20 finalizer: ' + ($cleanupErrors -join '; '))
  }
}
if (-not $succeeded -or $null -eq $evidenceJson) {
  throw 'GT-20 did not reach an evidence publication state.'
}
$evidenceDirectory = Split-Path -Parent $evidencePath
$createdEvidenceDirectory = $false
if (-not (Test-Path -LiteralPath $evidenceDirectory)) {
  New-Item -ItemType Directory -Path $evidenceDirectory | Out-Null
  $createdEvidenceDirectory = $true
}
$pendingEvidencePath = Join-Path $evidenceDirectory (
  ([System.IO.Path]::GetFileName($evidencePath)) + ".pending-$PID-" +
  [Guid]::NewGuid().ToString('N')
)
try {
  [System.IO.File]::WriteAllText(
    $pendingEvidencePath,
    $evidenceJson + [System.Environment]::NewLine,
    [System.Text.UTF8Encoding]::new($false)
  )
  $stream = [System.IO.FileStream]::new(
    $pendingEvidencePath, [System.IO.FileMode]::Open,
    [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::Read
  )
  try { $stream.Flush($true) } finally { $stream.Dispose() }
  [System.IO.File]::Move($pendingEvidencePath, $evidencePath, $false)
} finally {
  if (Test-Path -LiteralPath $pendingEvidencePath) {
    Remove-Item -LiteralPath $pendingEvidencePath -Force
  }
  if (
    $createdEvidenceDirectory -and
    -not (Test-Path -LiteralPath $evidencePath) -and
    (Test-Path -LiteralPath $evidenceDirectory) -and
    @(Get-ChildItem -LiteralPath $evidenceDirectory -Force).Count -eq 0
  ) {
    Remove-Item -LiteralPath $evidenceDirectory -Force
  }
}
Write-Output $evidencePath

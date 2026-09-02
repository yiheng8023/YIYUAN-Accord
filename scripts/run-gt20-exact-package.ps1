#requires -Version 7.0

param(
  [Parameter(Mandatory = $true)][string]$RepositoryRoot,
  [Parameter(Mandatory = $true)][string]$CandidateRevision,
  [Parameter(Mandatory = $true)][string]$TaskRoot,
  [Parameter(Mandatory = $true)][string]$EvidenceOutput,
  [string]$AgentModel = ''
)

$ErrorActionPreference = 'Stop'
$CommandTimeoutSeconds = 60
$CommandEndToEndTimeoutSeconds = 70
$CommandOutputLimitBytes = 4194304
$AccordMarketplaceId = 'yiyuan-accord'
$CodexAccordPluginId = 'yiyuan-accord-codex@yiyuan-accord'
$ClaudeAccordPluginId = 'yiyuan-accord-claude@yiyuan-accord'
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
using System.Net;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
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

  public void ResumeInteractive() {
    if (threadHandle == IntPtr.Zero) throw new InvalidOperationException("Process is not suspended.");
    if (ResumeThread(threadHandle) == UInt32.MaxValue)
      throw new Win32Exception(Marshal.GetLastWin32Error());
    CloseHandle(threadHandle);
    threadHandle = IntPtr.Zero;
  }

  public void WriteInputLine(string value) {
    if (input == null) throw new InvalidOperationException("Process input is closed.");
    input.WriteLine(value ?? "");
  }

  public void CloseInput() {
    if (input != null) { input.Dispose(); input = null; }
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

public sealed class AccordLoopbackFailingResponsesServer : IDisposable {
  private readonly TcpListener listener;
  private readonly CancellationTokenSource cancellation = new CancellationTokenSource();
  private readonly Task serverTask;
  private int requestCount;

  public AccordLoopbackFailingResponsesServer() {
    listener = new TcpListener(IPAddress.Loopback, 0);
    listener.Start();
    Port = ((IPEndPoint)listener.LocalEndpoint).Port;
    serverTask = Task.Run(() => Serve());
  }

  public int Port { get; private set; }
  public int RequestCount { get { return Volatile.Read(ref requestCount); } }

  private void Serve() {
    while (!cancellation.IsCancellationRequested) {
      TcpClient client;
      try { client = listener.AcceptTcpClient(); }
      catch (SocketException) when (cancellation.IsCancellationRequested) { break; }
      catch (ObjectDisposedException) when (cancellation.IsCancellationRequested) { break; }
      using (client) {
        try {
          client.ReceiveTimeout = 5000;
          client.SendTimeout = 5000;
          using (NetworkStream stream = client.GetStream()) {
            byte[] request = new byte[8192];
            int read = stream.Read(request, 0, request.Length);
            if (read <= 0) continue;
            Interlocked.Increment(ref requestCount);
            byte[] body = Encoding.UTF8.GetBytes(
              "{\"error\":{\"message\":\"intentional GT-20 lifecycle stop\"}}"
            );
            byte[] header = Encoding.ASCII.GetBytes(
              "HTTP/1.1 400 Bad Request\r\n" +
              "Content-Type: application/json\r\n" +
              "Connection: close\r\n" +
              "Content-Length: " + body.Length + "\r\n\r\n"
            );
            stream.Write(header, 0, header.Length);
            stream.Write(body, 0, body.Length);
            stream.Flush();
          }
        } catch (IOException) when (cancellation.IsCancellationRequested) { }
      }
    }
  }

  public void Dispose() {
    cancellation.Cancel();
    listener.Stop();
    try { serverTask.Wait(5000); } catch (AggregateException) { }
    cancellation.Dispose();
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
  if ([System.IO.Path]::IsPathFullyQualified($value)) {
    return '%HOST_PATH%/' + [System.IO.Path]::GetFileName($value)
  }
  return $value.Replace('\\', '/')
}

function Get-PrivateRootPattern {
  param([Parameter(Mandatory = $true)][string]$Path)
  $resolved = [System.IO.Path]::GetFullPath($Path).TrimEnd('\', '/')
  $segments = @($resolved -split '[\\/]+')
  return (($segments | ForEach-Object {
    [System.Text.RegularExpressions.Regex]::Escape($_)
  }) -join '[\\/]+')
}

function Get-PrivateRootEncodedPattern {
  param([Parameter(Mandatory = $true)][string]$Path)
  $resolved = [System.IO.Path]::GetFullPath($Path).TrimEnd('\', '/')
  return [System.Text.RegularExpressions.Regex]::Escape(
    ($resolved -replace '[:\\/]', '-')
  )
}

function Get-TextSha256 {
  param([AllowEmptyString()][string]$Value)
  return [Convert]::ToHexString(
    [System.Security.Cryptography.SHA256]::HashData(
      [System.Text.Encoding]::UTF8.GetBytes($Value)
    )
  ).ToLowerInvariant()
}

function ConvertTo-CanonicalStringListJson {
  param([Parameter(Mandatory = $true)][AllowEmptyCollection()][string[]]$Values)
  $ordered = [string[]]@($Values)
  [Array]::Sort($ordered, [System.StringComparer]::Ordinal)
  return ConvertTo-Json -InputObject @($ordered) -Compress
}

function Get-FileMapIdentityDigest {
  param([Parameter(Mandatory = $true)][System.Collections.IDictionary]$Map)
  $locators = [string[]]@($Map.Keys | ForEach-Object { [string]$_ })
  [Array]::Sort($locators, [System.StringComparer]::Ordinal)
  $facts = @($locators | ForEach-Object {
    [ordered]@{ locator = $_; sha256 = [string]$Map[$_] }
  })
  return Get-TextSha256 (ConvertTo-Json -InputObject @($facts) -Compress)
}

function ConvertTo-PublicEvidenceText {
  param([AllowEmptyString()][string]$Value)
  $result = [System.Text.RegularExpressions.Regex]::Replace(
    $Value,
    '(?:\\{4}\?\\{2}|\\{2}\?\\|//\?/)(?=[A-Za-z]:[\\/])',
    '', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
  )
  foreach ($item in $script:PrivateRootsForEvidence) {
    if ($item.path) {
      $result = [System.Text.RegularExpressions.Regex]::Replace(
        $result, (Get-PrivateRootPattern $item.path),
        [string]$item.replacement,
        [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
      )
      $result = [System.Text.RegularExpressions.Regex]::Replace(
        $result, (Get-PrivateRootEncodedPattern $item.path),
        ([string]$item.replacement + '_ENCODED'),
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
    if ($item.path -and [System.Text.RegularExpressions.Regex]::IsMatch(
        $Value, (Get-PrivateRootEncodedPattern $item.path),
        [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)) {
      return $true
    }
  }
  return (
    $Value -match '(?i)[a-z]:(?:[\\/]+)(?:users|documents and settings)(?:[\\/]+)' -or
    $Value -match '(?i)(?:^|[^a-z0-9])[a-z]--(?:users|documents-and-settings)-' -or
    $Value -match '(?i)(?:^|[\s"''=(:,\[])[a-z]:[\\/]' -or
    $Value -match '(?:^|[\s"''=(:,\[])[\\]{2,}[^\\/\s"'']+[\\/]' -or
    $Value -match '(?i)(?:^|[\s"''=(:,\[])file:(?:/{1,3}|[\\]{1,3})' -or
    $Value -match '(?:^|[\s"''=(:,\[])/(?!/)(?:(?:home|users|private|tmp|var|opt|usr|etc|root|mnt|volumes|srv)(?:/|$)|(?:[^/\s"''<>]+/)+[^/\s"''<>]+)' -or
    $Value -match '(?i)["''](?:hook_id|hookId|installationId|memory_paths|messaging_socket_path|serverName|session_id|sessionId|threadId|turnId|uuid)["'']\s*:'
  )
}

function Assert-NoPrivateEvidenceValue {
  param(
    [Parameter(Mandatory = $true)][AllowNull()]$Value,
    [string]$Location = '$'
  )
  if ($Value -is [string]) {
    if (Test-PrivateEvidenceText $Value) {
      throw "Evidence retained a private or task-local root at $Location."
    }
  } elseif ($Value -is [System.Collections.IDictionary]) {
    foreach ($key in $Value.Keys) {
      if ([string]$key -match '^(?:hook_id|hookId|installationId|memory_paths|messaging_socket_path|serverName|session_id|sessionId|threadId|turnId|uuid)$') {
        throw "Evidence retained a private host/session key at $Location.$key."
      }
      Assert-NoPrivateEvidenceValue $Value[$key] "$Location.$key"
    }
  } elseif ($Value -is [pscustomobject]) {
    foreach ($property in $Value.PSObject.Properties) {
      if ($property.Name -match '^(?:hook_id|hookId|installationId|memory_paths|messaging_socket_path|serverName|session_id|sessionId|threadId|turnId|uuid)$') {
        throw "Evidence retained a private host/session key at $Location.$($property.Name)."
      }
      Assert-NoPrivateEvidenceValue $property.Value (
        "$Location.$($property.Name)"
      )
    }
  } elseif ($Value -is [System.Collections.IEnumerable]) {
    $index = 0
    foreach ($item in $Value) {
      Assert-NoPrivateEvidenceValue $item "${Location}[$index]"
      $index++
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
    $script:TaskEnvironmentReadyForEvidence -and
    $script:TaskOwnedForEvidence -and
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
    $publicStdout = ConvertTo-PublicEvidenceText $stdoutValue
    $publicStderr = ConvertTo-PublicEvidenceText $stderrValue
    $stdoutBytes = [System.Text.Encoding]::UTF8.GetByteCount($publicStdout)
    $stderrBytes = [System.Text.Encoding]::UTF8.GetByteCount($publicStderr)
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
      stdout = $publicStdout
      stderr = $publicStderr
    }
  } finally {
    if ($null -ne $owned) { $owned.Dispose() }
    $job.Dispose()
  }
}

function Invoke-CodexAppServerConnection {
  param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('thread/start', 'thread/resume')][string]$Method,
    [AllowNull()][string]$ThreadId,
    [Parameter(Mandatory = $true)][string]$WorkingDirectory,
    [Parameter(Mandatory = $true)][hashtable]$Environment,
    [Parameter(Mandatory = $true)][string]$ExpectedHookSourcePath,
    [Parameter(Mandatory = $true)][string]$MockBaseUrl
  )
  if (($Method -eq 'thread/start') -eq (-not [string]::IsNullOrEmpty($ThreadId))) {
    throw 'Codex App Server thread id does not match the requested lifecycle method.'
  }
  $mockUri = [Uri]$MockBaseUrl
  if ($mockUri.Scheme -ne 'http' -or $mockUri.Host -ne '127.0.0.1' -or
      -not $mockUri.AbsolutePath.EndsWith('/v1')) {
    throw 'Codex lifecycle model probe must remain on task-owned loopback.'
  }
  $clock = [System.Diagnostics.Stopwatch]::StartNew()
  $arguments = @('--dangerously-bypass-hook-trust', 'app-server', '--stdio')
  $command = Get-Command 'codex.exe' -CommandType Application -ErrorAction SilentlyContinue |
    Select-Object -First 1
  if ($null -eq $command) {
    $command = Get-Command 'codex.cmd' -CommandType Application -ErrorAction Stop |
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
  $commandTemp = Join-Path $script:TaskPathForEvidence 'command-temp'
  [void][System.IO.Directory]::CreateDirectory($commandTemp)
  $environmentOverrides['TEMP'] = $commandTemp
  $environmentOverrides['TMP'] = $commandTemp

  $job = [AccordProcessJob]::new()
  $owned = $null
  try {
    $owned = [AccordSuspendedProcess]::Start(
      $identity.terminalExecutableRaw, $arguments, $WorkingDirectory,
      $environmentOverrides, $job
    )
    $owned.ResumeInteractive()
    $stderrTask = [AccordSuspendedProcess]::ReadBoundedAsync(
      $owned.StandardError, $CommandOutputLimitBytes
    )
    $requestId = if ($Method -eq 'thread/start') { 10 } else { 11 }
    $initialize = [ordered]@{
      method = 'initialize'
      id = 0
      params = [ordered]@{
        clientInfo = [ordered]@{
          name = 'yiyuan_accord_gt20'
          title = 'YIYUAN Accord GT-20 Evaluator'
          version = '3.1.0'
        }
      }
    }
    $modelProviderName = 'yiyuan_accord_gt20_mock'
    $modelProviders = [ordered]@{}
    $modelProviders[$modelProviderName] = [ordered]@{
      name = 'YIYUAN Accord GT-20 loopback failure'
      base_url = $MockBaseUrl
      wire_api = 'responses'
      requires_openai_auth = $false
    }
    $threadConfig = [ordered]@{
      model_provider = $modelProviderName
      model_providers = $modelProviders
      bypass_hook_trust = $true
    }
    $requestParams = [ordered]@{
      cwd = $WorkingDirectory
      model = 'yiyuan-accord-gt20-lifecycle-probe'
      approvalPolicy = 'never'
      sandbox = 'read-only'
      config = $threadConfig
    }
    if ($Method -eq 'thread/start') {
      $requestParams['serviceName'] = 'yiyuan_accord_gt20'
    } else {
      $requestParams['threadId'] = $ThreadId
    }
    $hooksList = [ordered]@{
      method = 'hooks/list'
      id = 1
      params = [ordered]@{cwds = @($WorkingDirectory)}
    }
    $request = [ordered]@{method = $Method; id = $requestId; params = $requestParams}
    $initializeLine = $initialize | ConvertTo-Json -Compress -Depth 20
    $initializedLine = (([ordered]@{method = 'initialized'; params = [ordered]@{}}) |
      ConvertTo-Json -Compress -Depth 20)
    $hooksListLine = $hooksList | ConvertTo-Json -Compress -Depth 20
    $requestLine = $request | ConvertTo-Json -Compress -Depth 20
    $inputLines = @($initializeLine, $initializedLine, $hooksListLine, $requestLine)

    $outputLines = [System.Collections.Generic.List[string]]::new()
    $outputBytes = 0
    $owned.WriteInputLine($initializeLine)
    $initializeResponse = $null
    $lineTask = $owned.StandardOutput.ReadLineAsync()
    $initializeDeadline = [DateTimeOffset]::UtcNow.AddSeconds(10)
    while ([DateTimeOffset]::UtcNow -lt $initializeDeadline) {
      if (-not $lineTask.Wait(100)) { continue }
      $line = $lineTask.Result
      if ($null -eq $line) { break }
      $lineBytes = [System.Text.Encoding]::UTF8.GetByteCount($line + "`n")
      if ($outputBytes + $lineBytes -gt $CommandOutputLimitBytes) {
        throw 'Codex App Server output exceeded the evidence byte limit.'
      }
      $outputBytes += $lineBytes
      [void]$outputLines.Add($line)
      try { $message = $line | ConvertFrom-Json -Depth 40 } catch {
        throw 'Codex App Server emitted non-JSON stdout.'
      }
      if ($message.id -eq 0) {
        $initializeResponse = $message
        break
      }
      $lineTask = $owned.StandardOutput.ReadLineAsync()
    }
    if ($null -eq $initializeResponse -or
        $null -ne $initializeResponse.error -or
        $null -eq $initializeResponse.result) {
      throw 'Codex App Server initialize handshake failed.'
    }
    $owned.WriteInputLine($initializedLine)
    $owned.WriteInputLine($hooksListLine)
    $hooksListResponse = $null
    $lineTask = $owned.StandardOutput.ReadLineAsync()
    $hooksListDeadline = [DateTimeOffset]::UtcNow.AddSeconds(10)
    while ([DateTimeOffset]::UtcNow -lt $hooksListDeadline) {
      if (-not $lineTask.Wait(100)) { continue }
      $line = $lineTask.Result
      if ($null -eq $line) { break }
      $lineBytes = [System.Text.Encoding]::UTF8.GetByteCount($line + "`n")
      if ($outputBytes + $lineBytes -gt $CommandOutputLimitBytes) {
        throw 'Codex App Server output exceeded the evidence byte limit.'
      }
      $outputBytes += $lineBytes
      [void]$outputLines.Add($line)
      try { $message = $line | ConvertFrom-Json -Depth 40 } catch {
        throw 'Codex App Server emitted non-JSON stdout.'
      }
      if ($message.id -eq 1) {
        $hooksListResponse = $message
        break
      }
      $lineTask = $owned.StandardOutput.ReadLineAsync()
    }
    if ($null -eq $hooksListResponse -or
        $null -ne $hooksListResponse.error -or
        $null -eq $hooksListResponse.result.data) {
      throw 'Codex App Server hooks/list failed.'
    }
    $matchingCwdEntries = @($hooksListResponse.result.data | Where-Object {
      [System.IO.Path]::GetFullPath([string]$_.cwd).Equals(
        [System.IO.Path]::GetFullPath($WorkingDirectory),
        [System.StringComparison]::OrdinalIgnoreCase
      )
    })
    $discoveredHooks = @($matchingCwdEntries | ForEach-Object { $_.hooks })
    $qualifyingHooks = @($discoveredHooks | Where-Object {
      $_.eventName -eq 'SessionStart' -and
      $_.source -eq 'plugin' -and
      $_.handlerType -eq 'command' -and
      $_.enabled -eq $true -and
      [System.IO.Path]::GetFullPath([string]$_.sourcePath).Equals(
        [System.IO.Path]::GetFullPath($ExpectedHookSourcePath),
        [System.StringComparison]::OrdinalIgnoreCase
      )
    })
    $discoveryErrors = @($matchingCwdEntries | ForEach-Object { $_.errors })
    if ($matchingCwdEntries.Count -ne 1 -or $qualifyingHooks.Count -ne 1 -or
        $discoveryErrors.Count -ne 0) {
      $discoverySummary = @($discoveredHooks | ForEach-Object {
        [ordered]@{
          eventName = $_.eventName
          source = $_.source
          sourcePathMatches = [System.IO.Path]::GetFullPath(
            [string]$_.sourcePath
          ).Equals(
            [System.IO.Path]::GetFullPath($ExpectedHookSourcePath),
            [System.StringComparison]::OrdinalIgnoreCase
          )
          handlerType = $_.handlerType
          enabled = $_.enabled
          trustStatus = $_.trustStatus
        }
      }) | ConvertTo-Json -Compress -Depth 5
      throw (
        'Codex App Server hooks/list did not discover the installed Hook. ' +
        "cwdEntries=$($matchingCwdEntries.Count),errors=$($discoveryErrors.Count)," +
        "hooks=$discoverySummary"
      )
    }
    $discoveredHook = $qualifyingHooks[0]
    $owned.WriteInputLine($requestLine)

    $response = $null
    $lineTask = $owned.StandardOutput.ReadLineAsync()
    $threadDeadline = [DateTimeOffset]::UtcNow.AddSeconds(15)
    while ([DateTimeOffset]::UtcNow -lt $threadDeadline) {
      if (-not $lineTask.Wait(100)) { continue }
      $line = $lineTask.Result
      if ($null -eq $line) { break }
      $lineBytes = [System.Text.Encoding]::UTF8.GetByteCount($line + "`n")
      if ($outputBytes + $lineBytes -gt $CommandOutputLimitBytes) {
        throw 'Codex App Server output exceeded the evidence byte limit.'
      }
      $outputBytes += $lineBytes
      [void]$outputLines.Add($line)
      try { $message = $line | ConvertFrom-Json -Depth 40 } catch {
        throw 'Codex App Server emitted non-JSON stdout.'
      }
      if ($message.id -eq $requestId) { $response = $message }
      if ($null -ne $response) { break }
      $lineTask = $owned.StandardOutput.ReadLineAsync()
    }
    if ($null -eq $response) {
      throw "Codex App Server $Method did not return a response."
    }
    if ($null -ne $response.error) {
      throw "Codex App Server $Method rejected the request: $($response.error.message)"
    }
    if ($null -eq $response.result.thread.id) {
      throw "Codex App Server $Method returned a malformed thread receipt."
    }
    $observedThreadId = [string]$response.result.thread.id
    if ($Method -eq 'thread/resume' -and $observedThreadId -ne $ThreadId) {
      throw 'Codex App Server resumed a different thread.'
    }

    $turnRequestId = if ($Method -eq 'thread/start') { 20 } else { 21 }
    $turnRequest = [ordered]@{
      method = 'turn/start'
      id = $turnRequestId
      params = [ordered]@{
        threadId = $observedThreadId
        input = @([ordered]@{
          type = 'text'
          text = 'GT-20 lifecycle activation probe; do not invoke tools.'
        })
      }
    }
    $turnLine = $turnRequest | ConvertTo-Json -Compress -Depth 20
    $inputLines += $turnLine
    $owned.WriteInputLine($turnLine)

    $turnResponse = $null
    $turnCompleted = $null
    $hookStarted = $null
    $hookCompleted = $null
    $hookObservations = [System.Collections.Generic.List[object]]::new()
    $lineTask = $owned.StandardOutput.ReadLineAsync()
    $deadline = [DateTimeOffset]::UtcNow.AddSeconds(30)
    while ([DateTimeOffset]::UtcNow -lt $deadline) {
      if (-not $lineTask.Wait(100)) { continue }
      $line = $lineTask.Result
      if ($null -eq $line) { break }
      $lineBytes = [System.Text.Encoding]::UTF8.GetByteCount($line + "`n")
      if ($outputBytes + $lineBytes -gt $CommandOutputLimitBytes) {
        throw 'Codex App Server output exceeded the evidence byte limit.'
      }
      $outputBytes += $lineBytes
      [void]$outputLines.Add($line)
      try { $message = $line | ConvertFrom-Json -Depth 40 } catch {
        throw 'Codex App Server emitted non-JSON stdout.'
      }
      if ($message.id -eq $turnRequestId) { $turnResponse = $message }
      if ($message.method -eq 'turn/completed') { $turnCompleted = $message }
      if ($message.method -in @('hook/started', 'hook/completed')) {
        $run = $message.params.run
        $sourcePath = [System.IO.Path]::GetFullPath([string]$run.sourcePath)
        $sourcePathMatches = $sourcePath.Equals(
          [System.IO.Path]::GetFullPath($ExpectedHookSourcePath),
          [System.StringComparison]::OrdinalIgnoreCase
        )
        [void]$hookObservations.Add([ordered]@{
          method = $message.method
          eventName = $run.eventName
          source = $run.source
          sourcePathMatches = $sourcePathMatches
          scope = $run.scope
          handlerType = $run.handlerType
          status = $run.status
        })
        if ($run.eventName -eq 'SessionStart' -and
            $run.source -eq 'plugin' -and
            $sourcePathMatches) {
          if ($message.method -eq 'hook/started') { $hookStarted = $message }
          if ($message.method -eq 'hook/completed') { $hookCompleted = $message }
        }
      }
      if ($null -ne $turnResponse -and $null -ne $hookStarted -and
          $null -ne $hookCompleted -and $null -ne $turnCompleted) { break }
      if ($null -ne $turnResponse -and $null -ne $turnResponse.error) { break }
      $lineTask = $owned.StandardOutput.ReadLineAsync()
    }
    if ($null -eq $turnResponse) {
      throw "Codex App Server $Method lifecycle turn did not return a response."
    }
    if ($null -ne $turnResponse.error) {
      throw (
        "Codex App Server $Method lifecycle turn was rejected: " +
        $turnResponse.error.message
      )
    }
    if ($null -eq $turnResponse.result.turn.id) {
      throw "Codex App Server $Method returned a malformed lifecycle turn receipt."
    }
    $observedTurnId = [string]$turnResponse.result.turn.id
    if ($null -eq $hookStarted -or $null -eq $hookCompleted) {
      $missingKinds = @()
      if ($null -eq $hookStarted) { $missingKinds += 'hook/started' }
      if ($null -eq $hookCompleted) { $missingKinds += 'hook/completed' }
      $observationSummary = $hookObservations | ConvertTo-Json -Compress -Depth 5
      throw (
        "Codex App Server $Method did not emit qualifying " +
        ($missingKinds -join ',') + "; observed=$observationSummary"
      )
    }
    if ($null -eq $turnCompleted -or
        $turnCompleted.params.turn.id -ne $observedTurnId -or
        $turnCompleted.params.turn.status -ne 'failed') {
      throw "Codex App Server $Method loopback lifecycle turn did not fail closed."
    }
    foreach ($notification in @($hookStarted, $hookCompleted)) {
      if ($null -eq $notification -or
          $notification.params.threadId -ne $observedThreadId -or
          $notification.params.turnId -ne $observedTurnId -or
          $notification.params.run.scope -ne 'thread' -or
          $notification.params.run.handlerType -ne 'command') {
        $receiptState = if ($null -eq $notification) {
          'missing'
        } else {
          'threadMatch={0},turnMatch={1},scope={2},handlerType={3}' -f
            ($notification.params.threadId -eq $observedThreadId),
            ($notification.params.turnId -eq $observedTurnId),
            $notification.params.run.scope,
            $notification.params.run.handlerType
        }
        throw "Codex App Server $Method Hook receipt is incomplete: $receiptState"
      }
    }
    if ($hookStarted.params.run.status -ne 'running' -or
        $hookCompleted.params.run.status -ne 'completed' -or
        $hookStarted.params.run.id -ne $hookCompleted.params.run.id) {
      throw "Codex App Server $Method Hook did not complete successfully."
    }
    $owned.CloseInput()
    $exitDeadline = [DateTimeOffset]::UtcNow.AddSeconds(10)
    while ([DateTimeOffset]::UtcNow -lt $exitDeadline -and
        (-not $owned.Process.HasExited -or $job.ActiveProcessCount -ne 0)) {
      Start-Sleep -Milliseconds 50
    }
    if (-not $owned.Process.HasExited -or $job.ActiveProcessCount -ne 0) {
      $job.Terminate(124)
      throw "Codex App Server $Method did not terminate after stdin closed."
    }
    $remainingOutput = $owned.StandardOutput.ReadToEnd()
    if ($remainingOutput.Length -ne 0) { [void]$outputLines.Add($remainingOutput) }
    if (-not $stderrTask.Wait(5000)) {
      throw "Codex App Server $Method stderr did not drain."
    }
    if ($stderrTask.IsFaulted) {
      throw "Codex App Server $Method stderr exceeded the evidence byte limit."
    }
    $publicStdout = ConvertTo-PublicEvidenceText ($outputLines -join "`n")
    $publicStderr = ConvertTo-PublicEvidenceText $stderrTask.Result
    $publicInput = ConvertTo-PublicEvidenceText ($inputLines -join "`n")
    $hookRunId = [string]$hookStarted.params.run.id
    if ($hookRunId -ne [string]$hookCompleted.params.run.id) {
      throw "Codex App Server $Method Hook lifecycle identity drifted."
    }
    # Current Codex Hook run identifiers may embed task-local source paths.
    # Preserve correlation without publishing the host-private identifier.
    $hookRunIdSha256 = Get-TextSha256 $hookRunId
    return [ordered]@{
      command = [ordered]@{
        argv = @('codex', '--dangerously-bypass-hook-trust', 'app-server', '--stdio')
        resolvedCommand = ConvertTo-PortablePath $command.Source
        resolvedCommandSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $command.Source).Hash.ToLowerInvariant()
        launcher = $identity.terminalExecutable
        launcherSha256 = $identity.terminalExecutableSha256
        terminalExecutable = $identity.terminalExecutable
        terminalExecutableSha256 = $identity.terminalExecutableSha256
        packageManifest = $identity.packageManifest
        packageManifestSha256 = $identity.packageManifestSha256
        environmentProfile = 'isolated-codex'
        environmentKeys = @($environmentOverrides.Keys | Sort-Object)
        environmentBindings = [ordered]@{
          CODEX_HOME = '%TASK_ROOT%/codex-host'
          TEMP = '%TASK_ROOT%/command-temp'
          TMP = '%TASK_ROOT%/command-temp'
        }
        inputSha256 = [Convert]::ToHexString(
          [System.Security.Cryptography.SHA256]::HashData(
            [System.Text.Encoding]::UTF8.GetBytes($publicInput)
          )
        ).ToLowerInvariant()
        executionTimeoutSeconds = $CommandTimeoutSeconds
        endToEndTimeoutSeconds = $CommandEndToEndTimeoutSeconds
        outputLimitBytes = $CommandOutputLimitBytes
        elapsedMilliseconds = [Math]::Round($clock.Elapsed.TotalMilliseconds)
        stdoutBytes = [System.Text.Encoding]::UTF8.GetByteCount($publicStdout)
        stderrBytes = [System.Text.Encoding]::UTF8.GetByteCount($publicStderr)
        timedOut = $false
        terminationRequested = $false
        terminationConfirmed = $true
        streamsDrained = $true
        jobActiveProcesses = [int]$job.ActiveProcessCount
        exitCode = $owned.Process.ExitCode
        stdout = $publicStdout
        stderr = $publicStderr
      }
      threadId = $observedThreadId
      receipt = [ordered]@{
        rpcMethod = $Method
        responseId = $requestId
        threadIdSha256 = Get-TextSha256 $observedThreadId
        lifecycleTrigger = [ordered]@{
          rpcMethod = 'turn/start'
          responseId = $turnRequestId
          turnIdSha256 = Get-TextSha256 $observedTurnId
          terminalStatus = $turnCompleted.params.turn.status
          modelProvider = 'task-owned-loopback-responses-failure'
          requiresOpenAIAuth = $false
        }
        discovery = [ordered]@{
          rpcMethod = 'hooks/list'
          eventName = $discoveredHook.eventName
          source = $discoveredHook.source
          sourcePath = ConvertTo-PublicEvidenceText $discoveredHook.sourcePath
          handlerType = $discoveredHook.handlerType
          enabled = $discoveredHook.enabled
          trustStatus = $discoveredHook.trustStatus
        }
        hookStarted = [ordered]@{
          idSha256 = $hookRunIdSha256
          eventName = $hookStarted.params.run.eventName
          source = $hookStarted.params.run.source
          sourcePath = ConvertTo-PublicEvidenceText $hookStarted.params.run.sourcePath
          status = $hookStarted.params.run.status
        }
        hookCompleted = [ordered]@{
          idSha256 = $hookRunIdSha256
          eventName = $hookCompleted.params.run.eventName
          source = $hookCompleted.params.run.source
          sourcePath = ConvertTo-PublicEvidenceText $hookCompleted.params.run.sourcePath
          status = $hookCompleted.params.run.status
        }
      }
    }
  } finally {
    if ($null -ne $owned) { $owned.Dispose() }
    $job.Dispose()
  }
}

function Invoke-CodexAppServerActivation {
  param(
    [Parameter(Mandatory = $true)][string]$WorkingDirectory,
    [Parameter(Mandatory = $true)][hashtable]$Environment,
    [Parameter(Mandatory = $true)][string]$ExpectedHookSourcePath
  )
  $mockServer = [AccordLoopbackFailingResponsesServer]::new()
  try {
    $mockBaseUrl = "http://127.0.0.1:$($mockServer.Port)/v1"
    $startup = Invoke-CodexAppServerConnection 'thread/start' $null (
      $WorkingDirectory
    ) $Environment $ExpectedHookSourcePath $mockBaseUrl
    $resume = Invoke-CodexAppServerConnection 'thread/resume' $startup.threadId (
      $WorkingDirectory
    ) $Environment $ExpectedHookSourcePath $mockBaseUrl
    $mockRequestCount = $mockServer.RequestCount
  } finally {
    $mockServer.Dispose()
  }
  if ($mockRequestCount -ne 2) {
    throw "Codex lifecycle loopback model request count was $mockRequestCount, expected 2."
  }
  $record = $startup.command
  $record.elapsedMilliseconds = (
    $startup.command.elapsedMilliseconds + $resume.command.elapsedMilliseconds
  )
  $rawStdout = $startup.command.stdout + "`n" + $resume.command.stdout
  $rawStderr = $startup.command.stderr + $resume.command.stderr
  $record.stdout = ''
  $record.stderr = ''
  $record.stdoutBytes = 0
  $record.stderrBytes = 0
  $record.inputSha256 = [Convert]::ToHexString(
    [System.Security.Cryptography.SHA256]::HashData(
      [System.Text.Encoding]::UTF8.GetBytes(
        $startup.command.inputSha256 + ':' + $resume.command.inputSha256
      )
    )
  ).ToLowerInvariant()
  $record['activationReceipt'] = [ordered]@{
    transport = 'app-server-stdio-jsonl'
    rawStreamPolicy = 'digest-only-private-host-transcript-not-retained'
    rawStdoutSha256 = Get-TextSha256 $rawStdout
    rawStderrSha256 = Get-TextSha256 $rawStderr
    rpcMethods = @('hooks/list', 'thread/start', 'turn/start', 'thread/resume')
    lifecycleTriggerTurns = 2
    externalModelTurns = 0
    loopbackModelRequests = $mockRequestCount
    startup = $startup.receipt
    resume = $resume.receipt
  }
  return $record
}

function Get-ClaudeNativeLifecycleReceipt {
  param(
    [Parameter(Mandatory = $true)][System.Collections.IDictionary]$Command,
    [Parameter(Mandatory = $true)][string]$Source,
    [Parameter(Mandatory = $true)][string]$SessionId,
    [Parameter(Mandatory = $true)][string]$ExpectedPluginRoot,
    [Parameter(Mandatory = $true)][string]$ExpectedPluginVersion
  )
  $events = [System.Collections.Generic.List[object]]::new()
  foreach ($line in @($Command.stdout -split "`r?`n")) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    try {
      $events.Add(($line | ConvertFrom-Json -Depth 30))
    } catch {
      throw 'Claude host lifecycle stream contains a non-JSON event.'
    }
  }
  $expectedHookName = "SessionStart:$Source"
  $started = @($events | Where-Object {
    $_.type -eq 'system' -and $_.subtype -eq 'hook_started' -and
    $_.hook_event -eq 'SessionStart' -and
    $_.hook_name -eq $expectedHookName -and $_.session_id -eq $SessionId
  })
  $responses = @($events | Where-Object {
    $_.type -eq 'system' -and $_.subtype -eq 'hook_response' -and
    $_.hook_event -eq 'SessionStart' -and
    $_.hook_name -eq $expectedHookName -and $_.session_id -eq $SessionId
  })
  $initializations = @($events | Where-Object {
    $_.type -eq 'system' -and $_.subtype -eq 'init' -and
    $_.session_id -eq $SessionId
  })
  $terminals = @($events | Where-Object {
    $_.type -eq 'result' -and $_.session_id -eq $SessionId
  })
  if ($started.Count -ne 1 -or $responses.Count -ne 1 -or
      $initializations.Count -ne 1 -or $terminals.Count -ne 1 -or
      $started[0].hook_id -ne $responses[0].hook_id -or
      $responses[0].exit_code -ne 0 -or
      $responses[0].outcome -ne 'success' -or
      $terminals[0].terminal_reason -ne 'api_error' -or
      $terminals[0].api_error_status -ne 400 -or
      $terminals[0].is_error -ne $true -or
      $terminals[0].total_cost_usd -ne 0 -or
      $terminals[0].num_turns -ne 1) {
    throw "Claude $Source native lifecycle events are invalid."
  }
  $plugins = @($initializations[0].plugins | Where-Object {
    $_.name -eq 'yiyuan-accord-claude'
  })
  $expectedPublicRoot = (ConvertTo-PublicEvidenceText $ExpectedPluginRoot).
    Replace('\', '/')
  if ($plugins.Count -ne 1 -or $plugins[0].version -ne $ExpectedPluginVersion -or
      -not ([string]$plugins[0].path).Replace('\', '/').Equals(
        $expectedPublicRoot, [System.StringComparison]::OrdinalIgnoreCase
      )) {
    $observedIdentity = @($plugins | ForEach-Object {
      [ordered]@{
        name = $_.name
        version = $_.version
        source = $_.source
        path = ([string]$_.path).Replace('\', '/')
      }
    }) | ConvertTo-Json -Compress -Depth 6
    throw (
      "Claude $Source loaded plugin identity is invalid: " +
      "expectedPath=$expectedPublicRoot observed=$observedIdentity"
    )
  }
  $hookIdSha256 = Get-TextSha256 ([string]$started[0].hook_id)
  return [ordered]@{
    sessionSource = $Source
    nativeHookStarted = [ordered]@{
      subtype = $started[0].subtype
      hookEvent = $started[0].hook_event
      hookName = $started[0].hook_name
      hookIdSha256 = $hookIdSha256
    }
    nativeHookResponse = [ordered]@{
      subtype = $responses[0].subtype
      hookEvent = $responses[0].hook_event
      hookName = $responses[0].hook_name
      hookIdSha256 = $hookIdSha256
      exitCode = $responses[0].exit_code
      outcome = $responses[0].outcome
    }
    loadedPlugin = [ordered]@{
      name = $plugins[0].name
      version = $plugins[0].version
      source = $plugins[0].source
      path = ([string]$plugins[0].path).Replace('\', '/')
    }
    terminal = [ordered]@{
      status = $terminals[0].terminal_reason
      apiErrorStatus = $terminals[0].api_error_status
      isError = $terminals[0].is_error
      totalCostUsd = $terminals[0].total_cost_usd
      turns = $terminals[0].num_turns
    }
  }
}

function Invoke-ClaudeHostActivation {
  param(
    [Parameter(Mandatory = $true)][string]$WorkingDirectory,
    [Parameter(Mandatory = $true)][hashtable]$Environment,
    [Parameter(Mandatory = $true)][string]$ExpectedRuntimePath,
    [Parameter(Mandatory = $true)][string]$ExpectedPluginVersion
  )
  $observerRoot = Join-Path $script:TaskPathForEvidence 'claude-node-observer'
  [void][System.IO.Directory]::CreateDirectory($observerRoot)
  $observerScript = Join-Path $observerRoot 'observe.cjs'
  $observerShellShim = Join-Path $observerRoot 'node'
  $observerShim = Join-Path $observerRoot 'node.cmd'
  $receiptPath = Join-Path $observerRoot 'receipts.jsonl'
  $realNode = (Get-Command 'node.exe' -CommandType Application -ErrorAction Stop |
    Select-Object -First 1).Source
  $observerSource = @"
'use strict';
const fs = require('node:fs');
const crypto = require('node:crypto');
const {spawnSync} = require('node:child_process');
const realNode = $($realNode | ConvertTo-Json -Compress);
const receiptPath = $($receiptPath | ConvertTo-Json -Compress);
const input = fs.readFileSync(0);
const result = spawnSync(realNode, process.argv.slice(2), {
  input,
  env: process.env,
  maxBuffer: 4 * 1024 * 1024,
});
const digest = (value) => crypto.createHash('sha256').update(value || Buffer.alloc(0)).digest('hex');
let event = null;
try { event = JSON.parse(input.toString('utf8')); } catch (_) {}
fs.appendFileSync(receiptPath, JSON.stringify({
  argv: process.argv.slice(2),
  hookEventName: event && event.hook_event_name,
  source: event && event.source,
  inputSha256: digest(input),
  stdoutSha256: digest(result.stdout),
  stderrSha256: digest(result.stderr),
  exitCode: result.status,
}) + '\n', 'utf8');
if (result.stdout) process.stdout.write(result.stdout);
if (result.stderr) process.stderr.write(result.stderr);
process.exitCode = Number.isInteger(result.status) ? result.status : 125;
"@
  [System.IO.File]::WriteAllText(
    $observerScript, $observerSource, [System.Text.UTF8Encoding]::new($false)
  )
  # Claude command Hooks use a POSIX-like shell on Windows. That shell resolves
  # the extensionless `node` command before cmd.exe PATHEXT rules can consider
  # node.cmd, so provide both host-native entry shapes for the same observer.
  $observerShellSource = '#!/bin/sh' + [System.Environment]::NewLine +
    'exec "' + $realNode.Replace('\', '/') + '" "' +
    $observerScript.Replace('\', '/') + '" "$@"' +
    [System.Environment]::NewLine
  [System.IO.File]::WriteAllText(
    $observerShellShim, $observerShellSource,
    [System.Text.UTF8Encoding]::new($false)
  )
  $shimSource = '@"' + $realNode + '" "' + $observerScript + '" %*' +
    [System.Environment]::NewLine
  [System.IO.File]::WriteAllText(
    $observerShim, $shimSource, [System.Text.Encoding]::ASCII
  )
  $observerEnvironment = $Environment.Clone()
  $observerEnvironment['PATH'] = $observerRoot + [System.IO.Path]::PathSeparator + $env:PATH
  $observerEnvironment['CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC'] = '1'
  $observerEnvironment['CLAUDE_CODE_DISABLE_OFFICIAL_MARKETPLACE_AUTOINSTALL'] = '1'
  $sessionId = [Guid]::NewGuid().ToString()
  $trigger = 'GT-20 task-owned lifecycle trigger; no tool use.'
  $commonArguments = @(
    '-p', $trigger,
    '--output-format', 'stream-json',
    '--include-hook-events', '--verbose',
    '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}',
    '--setting-sources', 'user', '--no-chrome',
    '--max-budget-usd', '0.01'
  )
  $expectedPluginRoot = Split-Path -Parent (Split-Path -Parent $ExpectedRuntimePath)
  $mockServer = [AccordLoopbackFailingResponsesServer]::new()
  try {
    $observerEnvironment['ANTHROPIC_BASE_URL'] = (
      "http://127.0.0.1:$($mockServer.Port)"
    )
    $observerEnvironment['ANTHROPIC_API_KEY'] = (
      'gt20-task-owned-loopback-not-a-secret'
    )
    $startup = Invoke-Captured claude @(
      $commonArguments + @('--session-id', $sessionId)
    ) $WorkingDirectory $observerEnvironment
    $startupRequestCount = $mockServer.RequestCount
    $resume = Invoke-Captured claude @(
      $commonArguments + @('--resume', $sessionId)
    ) $WorkingDirectory $observerEnvironment
    $mockRequestCount = $mockServer.RequestCount
  } finally {
    $mockServer.Dispose()
  }
  if ($startup.exitCode -eq 0 -or $resume.exitCode -eq 0 -or
      $startup.timedOut -or $resume.timedOut -or
      $startupRequestCount -lt 1 -or
      ($mockRequestCount - $startupRequestCount) -lt 1) {
    throw 'Claude lifecycle loopback did not fail closed after both host runs.'
  }
  $startupNative = Get-ClaudeNativeLifecycleReceipt (
    $startup
  ) 'startup' $sessionId $expectedPluginRoot $ExpectedPluginVersion
  $resumeNative = Get-ClaudeNativeLifecycleReceipt (
    $resume
  ) 'resume' $sessionId $expectedPluginRoot $ExpectedPluginVersion
  if (-not (Test-Path -LiteralPath $receiptPath -PathType Leaf)) {
    throw 'Claude host activation did not invoke the installed Hook runtime.'
  }
  $receipts = @(Get-Content -LiteralPath $receiptPath | ForEach-Object {
    $_ | ConvertFrom-Json -Depth 20
  })
  $matching = @($receipts | Where-Object {
    $_.argv.Count -eq 1 -and
    [System.IO.Path]::GetFullPath([string]$_.argv[0]).Equals(
      [System.IO.Path]::GetFullPath($ExpectedRuntimePath),
      [System.StringComparison]::OrdinalIgnoreCase
    ) -and
    $_.hookEventName -eq 'SessionStart' -and
    $_.source -in @('startup', 'resume') -and
    $_.exitCode -eq 0
  })
  $sources = @($matching.source | Sort-Object -Unique)
  if ($matching.Count -ne 2 -or
      ($sources | ConvertTo-Json -Compress) -ne
      (@('resume', 'startup') | ConvertTo-Json -Compress)) {
    throw 'Claude host activation receipts do not close startup and resume.'
  }
  $record = $startup
  $record.argv = @(
    'claude', '-p', '%TASK_OWNED_LIFECYCLE_TRIGGER%',
    '--output-format', 'stream-json',
    '--include-hook-events', '--verbose',
    '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}',
    '--setting-sources', 'user', '--no-chrome',
    '--max-budget-usd', '0.01'
  )
  $record.elapsedMilliseconds = (
    $startup.elapsedMilliseconds + $resume.elapsedMilliseconds
  )
  $rawStdout = $startup.stdout + "`n" + $resume.stdout
  $rawStderr = $startup.stderr + $resume.stderr
  $record.stdout = ''
  $record.stderr = ''
  $record.stdoutBytes = 0
  $record.stderrBytes = 0
  $record['activationReceipt'] = [ordered]@{
    transport = 'headless-stream-json-with-loopback-trigger-and-task-owned-node-observer'
    rawStreamPolicy = 'digest-only-private-host-transcript-not-retained'
    rawStdoutSha256 = Get-TextSha256 $rawStdout
    rawStderrSha256 = Get-TextSha256 $rawStderr
    lifecycleTriggerTurns = 2
    externalModelTurns = 0
    loopbackHttpRequests = $mockRequestCount
    credentialEnvironmentInherited = $false
    networkEndpoint = 'ipv4-loopback'
    terminalStatus = 'api_error'
    hostRuns = @(
      [ordered]@{
        source = 'startup'
        sessionBinding = 'task-owned-session-id'
        exitCode = $startup.exitCode
        loopbackHttpRequests = $startupRequestCount
      },
      [ordered]@{
        source = 'resume'
        sessionBinding = 'same-task-owned-session-id'
        exitCode = $resume.exitCode
        loopbackHttpRequests = $mockRequestCount - $startupRequestCount
      }
    )
    native = [ordered]@{
      startup = $startupNative
      resume = $resumeNative
    }
    hooks = @($matching | ForEach-Object {
      [ordered]@{
        hookEventName = $_.hookEventName
        source = $_.source
        runtimePath = ConvertTo-PublicEvidenceText $_.argv[0]
        inputSha256 = $_.inputSha256
        stdoutSha256 = $_.stdoutSha256
        stderrSha256 = $_.stderrSha256
        exitCode = $_.exitCode
      }
    })
  }
  return $record
}

function Invoke-UpdateWithCandidateLock {
  param(
    [Parameter(Mandatory = $true)][string]$HostCommand,
    [Parameter(Mandatory = $true)][string[]]$Arguments,
    [Parameter(Mandatory = $true)][string]$WorkingDirectory,
    [Parameter(Mandatory = $true)][hashtable]$Environment,
    [Parameter(Mandatory = $true)][string]$CandidateLockPath,
    [Parameter(Mandatory = $true)][string]$CandidateStagingPath,
    [Parameter(Mandatory = $true)][string]$ExpectedPackageRoot
  )
  $staging = [System.IO.Path]::GetFullPath($CandidateStagingPath)
  $expectedPackage = [System.IO.Path]::GetFullPath($ExpectedPackageRoot)
  $versionRoot = Split-Path -Parent $staging
  $stagingParent = Split-Path -Parent $versionRoot
  $targetVersion = [System.IO.Path]::GetFileName($staging)
  if (-not (Test-Path -LiteralPath $stagingParent -PathType Container)) {
    throw 'Candidate staging parent is unavailable for observation.'
  }
  if (Test-Path -LiteralPath $staging) {
    throw 'Candidate staging target must not preexist the failed update.'
  }
  $expectedMap = Get-FileMap $expectedPackage
  $candidateIdentityDigest = Get-FileMapIdentityDigest $expectedMap
  $beforeMap = Get-FileMap $stagingParent
  $beforeChildren = @(Get-ChildItem -LiteralPath $stagingParent -Force |
    ForEach-Object { $_.FullName })
  $watcher = [System.IO.FileSystemWatcher]::new($stagingParent)
  $watcher.IncludeSubdirectories = $true
  $watcher.NotifyFilter = (
    [System.IO.NotifyFilters]::FileName -bor
    [System.IO.NotifyFilters]::DirectoryName -bor
    [System.IO.NotifyFilters]::LastWrite -bor
    [System.IO.NotifyFilters]::Size
  )
  $eventIds = @('Created', 'Changed', 'Renamed') | ForEach-Object {
    $identifier = "yiyuan-accord-gt20-$($_)-$([Guid]::NewGuid().ToString('N'))"
    Register-ObjectEvent -InputObject $watcher -EventName $_ -SourceIdentifier (
      $identifier
    ) | Out-Null
    $identifier
  }
  $events = @()
  $lock = [System.IO.FileStream]::new(
    $CandidateLockPath, [System.IO.FileMode]::Open,
    [System.IO.FileAccess]::Read, [System.IO.FileShare]::None
  )
  try {
    $watcher.EnableRaisingEvents = $true
    $result = Invoke-Captured $HostCommand $Arguments $WorkingDirectory $Environment
  } finally {
    $lock.Dispose()
    $watcher.EnableRaisingEvents = $false
    Start-Sleep -Milliseconds 100
    foreach ($identifier in $eventIds) {
      $events += @(Get-Event -SourceIdentifier $identifier -ErrorAction SilentlyContinue)
      Remove-Event -SourceIdentifier $identifier -ErrorAction SilentlyContinue
      Unregister-Event -SourceIdentifier $identifier -ErrorAction SilentlyContinue
    }
    $watcher.Dispose()
  }
  $relativeStaging = [System.IO.Path]::GetRelativePath(
    $stagingParent, $staging
  ).Replace('\', '/')
  $eventFacts = @($events | ForEach-Object {
    [pscustomobject]@{
      fullPath = [string]$_.SourceEventArgs.FullPath
      relativeParent = [System.IO.Path]::GetRelativePath(
        $stagingParent, [string]$_.SourceEventArgs.FullPath
      ).Replace('\', '/')
      kind = $_.SourceEventArgs.ChangeType.ToString()
    }
  })
  $exactPrefix = $relativeStaging + '/'
  $exactFacts = @($eventFacts | Where-Object {
    $_.relativeParent -eq $relativeStaging -or
    $_.relativeParent.StartsWith(
      $exactPrefix, [System.StringComparison]::OrdinalIgnoreCase
    )
  })
  $candidateRoutes = [System.Collections.Generic.List[object]]::new()
  if ($exactFacts.Count -ne 0) {
    $candidateRoutes.Add([pscustomobject]@{
      pathScope = 'exact-target'
      ownedRoot = $staging
      payloadRoot = $staging
      facts = $exactFacts
    })
  }
  $candidateSuffix = '/' + $relativeStaging
  $temporaryRoots = @($eventFacts | ForEach-Object {
    $marker = $_.relativeParent.IndexOf(
      $candidateSuffix, [System.StringComparison]::OrdinalIgnoreCase
    )
    if ($marker -gt 0) { $_.relativeParent.Substring(0, $marker) }
  } | Where-Object { $_ } | Sort-Object -Unique)
  foreach ($temporaryRoot in $temporaryRoots) {
    $payloadRelative = $temporaryRoot + $candidateSuffix
    $payloadPrefix = $payloadRelative + '/'
    $facts = @($eventFacts | Where-Object {
      $_.relativeParent -eq $payloadRelative -or
      $_.relativeParent.StartsWith(
        $payloadPrefix, [System.StringComparison]::OrdinalIgnoreCase
      )
    })
    $candidateRoutes.Add([pscustomobject]@{
      pathScope = 'verified-temp-sibling'
      ownedRoot = Join-Path $stagingParent $temporaryRoot
      payloadRoot = Join-Path $stagingParent $payloadRelative
      facts = $facts
    })
  }
  $manifestLocator = @($expectedMap.Keys | Where-Object {
    $_ -match '^\.[^/]+-plugin/plugin\.json$'
  })
  $qualifiedRoutes = @($candidateRoutes | Where-Object {
    $route = $_
    $payloadPrefix = [System.IO.Path]::GetFullPath($route.payloadRoot) +
      [System.IO.Path]::DirectorySeparatorChar
    $relativePayload = @($route.facts | ForEach-Object {
      $path = [System.IO.Path]::GetFullPath($_.fullPath)
      if ($path.Equals(
          [System.IO.Path]::GetFullPath($route.payloadRoot),
          [System.StringComparison]::OrdinalIgnoreCase
        )) { return '.' }
      if (-not $path.StartsWith(
          $payloadPrefix, [System.StringComparison]::OrdinalIgnoreCase
        )) { return '__outside__' }
      [System.IO.Path]::GetRelativePath($route.payloadRoot, $path).Replace('\', '/')
    } | Sort-Object -Unique)
    $observedFiles = @($relativePayload | Where-Object {
      $expectedMap.Contains($_)
    })
    $allAllowed = @($relativePayload | Where-Object {
      $relative = $_
      if ($relative -eq '.') { return $false }
      if ($expectedMap.Contains($relative)) { return $false }
      $prefix = $relative.TrimEnd('/') + '/'
      -not @($expectedMap.Keys | Where-Object {
        ([string]$_).StartsWith(
          $prefix, [System.StringComparison]::OrdinalIgnoreCase
        )
      }).Count
    }).Count -eq 0
    $route | Add-Member -NotePropertyName relativePayload -NotePropertyValue (
      $relativePayload
    ) -Force
    $route | Add-Member -NotePropertyName observedFiles -NotePropertyValue (
      $observedFiles
    ) -Force
    $allAllowed -and $manifestLocator.Count -eq 1 -and
      $observedFiles -contains 'adapter.json' -and
      $observedFiles -contains $manifestLocator[0]
  })
  if ($qualifiedRoutes.Count -ne 1) {
    $relativeDiagnostics = @($events | ForEach-Object {
      [System.IO.Path]::GetRelativePath(
        $stagingParent, [string]$_.SourceEventArgs.FullPath
      ).Replace('\', '/')
    } | Sort-Object -Unique | Select-Object -First 24)
    throw (
      'A unique candidate-bound staging route was not observed; parent-relative events=' +
      ($relativeDiagnostics | ConvertTo-Json -Compress)
    )
  }
  $selectedRoute = $qualifiedRoutes[0]
  if ($beforeChildren -contains $selectedRoute.ownedRoot) {
    throw 'The selected candidate staging route preexisted the update.'
  }
  $ownedRelative = [System.IO.Path]::GetRelativePath(
    $stagingParent, $selectedRoute.ownedRoot
  ).Replace('\', '/')
  $allowedPrefix = $ownedRelative + '/'
  $afterMap = Get-FileMap $stagingParent
  $unexpectedSiblingDelta = @(
    @($beforeMap.Keys) + @($afterMap.Keys) | Sort-Object -Unique | Where-Object {
      $relative = ([string]$_).Replace('\', '/')
      -not ($relative -eq $ownedRelative -or $relative.StartsWith(
        $allowedPrefix, [System.StringComparison]::OrdinalIgnoreCase
      )) -and (
        -not $beforeMap.Contains($_) -or -not $afterMap.Contains($_) -or
        $beforeMap[$_] -ne $afterMap[$_]
      )
    }
  )
  if ($unexpectedSiblingDelta.Count -ne 0) {
    throw 'Failed update changed an unexpected staging sibling.'
  }
  $eventRelativePaths = @($selectedRoute.relativePayload)
  $observedLocators = @($selectedRoute.observedFiles | Sort-Object -Unique)
  $eventRelativePaths = [string[]]@($eventRelativePaths | Sort-Object -Unique)
  [Array]::Sort($eventRelativePaths, [System.StringComparer]::Ordinal)
  $observedLocators = [string[]]@($observedLocators)
  [Array]::Sort($observedLocators, [System.StringComparer]::Ordinal)
  $result['mutationReceipt'] = [ordered]@{
    stagingObserved = $true
    eventCount = $selectedRoute.facts.Count
    observationScope = 'candidate-bound-staging-route'
    pathScope = $selectedRoute.pathScope
    targetVersion = $targetVersion
    preexisting = $false
    postCommandAbsent = -not (Test-Path -LiteralPath $selectedRoute.ownedRoot)
    candidateIdentityDigest = $candidateIdentityDigest
    observedLocatorCount = $observedLocators.Count
    observedLocators = @($observedLocators)
    observedLocatorSetSha256 = Get-TextSha256 (
      ConvertTo-CanonicalStringListJson $observedLocators
    )
    eventPathCount = $eventRelativePaths.Count
    eventRelativePaths = @($eventRelativePaths)
    eventPathSetSha256 = Get-TextSha256 (
      ConvertTo-CanonicalStringListJson $eventRelativePaths
    )
    unexpectedSiblingDelta = @()
    eventKinds = @($selectedRoute.facts | ForEach-Object {
      $_.kind
    } | Sort-Object -Unique)
  }
  $result['_ownedStagingRoot'] = $selectedRoute.ownedRoot
  $result['_candidatePayloadRoot'] = $selectedRoute.payloadRoot
  $result['_stagingParent'] = $stagingParent
  return $result
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
  $files = [object[]]@(Get-ChildItem -LiteralPath $resolved -Recurse -File -Force)
  [Array]::Sort($files, [System.Comparison[object]]{
    param($left, $right)
    [System.StringComparer]::Ordinal.Compare(
      [string]$left.FullName, [string]$right.FullName
    )
  })
  foreach ($file in $files) {
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
    $difference = [ordered]@{
      missing = @($expected.Keys | Where-Object { -not $actual.Contains($_) } |
        Sort-Object)
      extra = @($actual.Keys | Where-Object { -not $expected.Contains($_) } |
        Sort-Object)
      changed = @($expected.Keys | Where-Object {
        $actual.Contains($_) -and $actual[$_] -ne $expected[$_]
      } | Sort-Object)
    }
    throw "$Label installed bytes differ: $($difference | ConvertTo-Json -Compress)"
  }
  return $actual.Count
}

function Get-StableSiblingDigest {
  param(
    [Parameter(Mandatory = $true)][string]$StagingParent,
    [Parameter(Mandatory = $true)][string]$OwnedRoot
  )
  $parent = [System.IO.Path]::GetFullPath($StagingParent)
  $owned = [System.IO.Path]::GetFullPath($OwnedRoot)
  $prefix = $parent + [System.IO.Path]::DirectorySeparatorChar
  if (-not $owned.StartsWith(
      $prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Owned staging is outside its observed parent.'
  }
  $relative = [System.IO.Path]::GetRelativePath($parent, $owned).Replace('\', '/')
  $relativePrefix = $relative + '/'
  $outside = [ordered]@{}
  foreach ($entry in (Get-FileMap $parent).GetEnumerator()) {
    if ($entry.Key -ne $relative -and -not ([string]$entry.Key).StartsWith(
        $relativePrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
      $outside[$entry.Key] = $entry.Value
    }
  }
  return Get-FileMapIdentityDigest $outside
}

function Assert-NoReparsePath {
  param(
    [Parameter(Mandatory = $true)][string]$HostRoot,
    [Parameter(Mandatory = $true)][string]$OwnedRoot,
    [Parameter(Mandatory = $true)][string]$Label
  )
  $hostPath = [System.IO.Path]::GetFullPath($HostRoot).TrimEnd('\', '/')
  $owned = [System.IO.Path]::GetFullPath($OwnedRoot).TrimEnd('\', '/')
  $prefix = $hostPath + [System.IO.Path]::DirectorySeparatorChar
  if (-not $owned.StartsWith(
      $prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "$Label staging path is outside its isolated host root."
  }
  $cursor = if (Test-Path -LiteralPath $owned) {
    $owned
  } else {
    [System.IO.Path]::GetDirectoryName($owned)
  }
  while ($cursor) {
    if (Test-Path -LiteralPath $cursor) {
      $item = Get-Item -LiteralPath $cursor -Force
      if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        throw "$Label staging path or ancestor is a reparse point."
      }
    }
    if ($cursor.Equals($hostPath, [System.StringComparison]::OrdinalIgnoreCase)) {
      return
    }
    $parent = [System.IO.Path]::GetDirectoryName($cursor)
    if (-not $parent -or $parent -eq $cursor) { break }
    $cursor = $parent.TrimEnd('\', '/')
  }
  throw "$Label staging ancestry did not terminate at the isolated host root."
}

function Assert-DirectTemporaryPath {
  param([string]$TemporaryBase, [string]$Target, [string]$Label)
  $base = [System.IO.Path]::GetFullPath($TemporaryBase).TrimEnd('\', '/')
  $path = [System.IO.Path]::GetFullPath($Target).TrimEnd('\', '/')
  if (-not [System.IO.Path]::GetDirectoryName($path).Equals(
      $base, [System.StringComparison]::OrdinalIgnoreCase) -or
      (Get-Item -LiteralPath $base -Force).Attributes -band
      [System.IO.FileAttributes]::ReparsePoint) {
    throw "$Label must be a direct child of the non-reparse temporary root."
  }
}

function Assert-EvaluatorTaskRootOwned {
  if (-not $script:TaskOwnedForEvidence -or
      -not (Test-Path -LiteralPath $script:TaskPathForEvidence -PathType Container) -or
      -not (Test-Path -LiteralPath $script:TaskOwnershipMarker -PathType Leaf) -or
      (Get-Content -Raw -LiteralPath $script:TaskOwnershipMarker) -ne
      $script:TaskOwnershipToken) {
    throw 'Evaluator task-root ownership marker is invalid.'
  }
  Assert-DirectTemporaryPath $script:TemporaryBaseForEvidence (
    $script:TaskPathForEvidence
  ) 'Evaluator task root'
  $reparse = @(Get-ChildItem -LiteralPath $script:TaskPathForEvidence -Recurse -Force |
    Where-Object { $_.Attributes -band [System.IO.FileAttributes]::ReparsePoint })
  if ((Get-Item -LiteralPath $script:TaskPathForEvidence -Force).Attributes -band
      [System.IO.FileAttributes]::ReparsePoint -or $reparse.Count -ne 0) {
    throw 'Evaluator task root contains a reparse point and cannot be removed.'
  }
}

function Get-FailedUpdateRecoveryPlan {
  param(
    [Parameter(Mandatory = $true)][ValidateSet('codex', 'claude')][string]$Adapter,
    [Parameter(Mandatory = $true)][string]$ExpectedRoot,
    [Parameter(Mandatory = $true)][string]$OwnedStagingRoot,
    [Parameter(Mandatory = $true)][string]$CandidatePayloadRoot,
    [Parameter(Mandatory = $true)][string]$StagingParent,
    [Parameter(Mandatory = $true)][string]$HostRoot,
    [Parameter(Mandatory = $true)][string]$PriorRoot,
    [Parameter(Mandatory = $true)][System.Collections.IDictionary]$StagingReceipt,
    [Parameter(Mandatory = $true)][string]$Label
  )
  $owned = [System.IO.Path]::GetFullPath($OwnedStagingRoot)
  $payload = [System.IO.Path]::GetFullPath($CandidatePayloadRoot)
  $hostPrefix = [System.IO.Path]::GetFullPath($HostRoot) +
    [System.IO.Path]::DirectorySeparatorChar
  $ownedPrefix = $owned + [System.IO.Path]::DirectorySeparatorChar
  if (-not $owned.StartsWith(
      $hostPrefix, [System.StringComparison]::OrdinalIgnoreCase) -or
      -not ($payload.Equals(
          $owned, [System.StringComparison]::OrdinalIgnoreCase
        ) -or $payload.StartsWith(
          $ownedPrefix, [System.StringComparison]::OrdinalIgnoreCase
        )) -or
      $owned.Equals(
        [System.IO.Path]::GetFullPath($PriorRoot),
        [System.StringComparison]::OrdinalIgnoreCase
      )) {
    throw "$Label candidate staging path is outside its isolated host root."
  }
  Assert-NoReparsePath $HostRoot $owned $Label
  if ($StagingReceipt.stagingObserved -ne $true -or
      $StagingReceipt.observationScope -ne 'candidate-bound-staging-route' -or
      $StagingReceipt.preexisting -ne $false -or
      @($StagingReceipt.unexpectedSiblingDelta).Count -ne 0) {
    throw "$Label did not produce a bounded exact candidate-staging receipt."
  }
  $expected = Get-FileMap $ExpectedRoot
  $candidateIdentity = Get-FileMapIdentityDigest $expected
  if ($StagingReceipt.candidateIdentityDigest -ne $candidateIdentity) {
    throw "$Label candidate identity drifted before recovery."
  }
  $priorIdentity = Get-FileMapIdentityDigest (Get-FileMap $PriorRoot)
  $siblingIdentity = Get-StableSiblingDigest $StagingParent $owned
  $action = 'accept-host-cleaned'
  $actual = $null
  $difference = $null
  if ($StagingReceipt.postCommandAbsent -eq $true) {
    if ((Test-Path -LiteralPath $owned) -or (Test-Path -LiteralPath $payload)) {
      throw "$Label host-cleaned staging receipt conflicts with live residue."
    }
  } else {
    if (-not (Test-Path -LiteralPath $owned -PathType Container) -or
        -not (Test-Path -LiteralPath $payload -PathType Container)) {
      throw "$Label retained staging receipt has no attributable payload."
    }
    $actual = Get-FileMap $payload
    if ($actual.Count -eq 0 -or
        (Get-FileMapIdentityDigest $expected) -eq
        (Get-FileMapIdentityDigest $actual)) {
      throw "$Label staging is empty or already a complete candidate."
    }
    $difference = [ordered]@{
      missing = @($expected.Keys | Where-Object { -not $actual.Contains($_) } |
        Sort-Object)
      extra = @($actual.Keys | Where-Object { -not $expected.Contains($_) } |
        Sort-Object)
      changed = @($expected.Keys | Where-Object {
        $actual.Contains($_) -and $actual[$_] -ne $expected[$_]
      } | Sort-Object)
    }
    if ($difference.missing.Count -eq 0 -or
        $difference.extra.Count -ne 0 -or
        $difference.changed.Count -ne 0) {
      throw "$Label staging is not a strict unmodified subset of the candidate."
    }
    $action = 'remove-attributable-incomplete-staging'
  }
  $public = [ordered]@{
    adapter = $Adapter
    allowedAction = $action
    postCommandAbsent = [bool]$StagingReceipt.postCommandAbsent
    candidateIdentityDigest = $candidateIdentity
    priorIdentityDigest = $priorIdentity
    siblingStateSha256 = $siblingIdentity
    stagedFileCount = if ($null -eq $actual) { $null } else { $actual.Count }
    difference = $difference
  }
  $binding = Get-TextSha256 (ConvertTo-Json $public -Compress -Depth 8)
  $public['bindingSha256'] = $binding
  return [pscustomobject]@{
    Public = $public
    Adapter = $Adapter
    ExpectedRoot = $ExpectedRoot
    OwnedStagingRoot = $owned
    CandidatePayloadRoot = $payload
    StagingParent = $StagingParent
    HostRoot = $HostRoot
    PriorRoot = $PriorRoot
    StagingReceipt = $StagingReceipt
    Label = $Label
  }
}

function Complete-BoundedFailedUpdateRecovery {
  param(
    [Parameter(Mandatory = $true)]$Plan,
    [Parameter(Mandatory = $true)][string]$DecisionAction
  )
  $current = Get-FailedUpdateRecoveryPlan `
    $Plan.Adapter $Plan.ExpectedRoot $Plan.OwnedStagingRoot `
    $Plan.CandidatePayloadRoot $Plan.StagingParent $Plan.HostRoot `
    $Plan.PriorRoot $Plan.StagingReceipt $Plan.Label
  if ($current.Public.bindingSha256 -ne $Plan.Public.bindingSha256 -or
      $DecisionAction -ne $current.Public.allowedAction) {
    throw "$($Plan.Label) recovery state or Agent decision drifted."
  }
  if ($DecisionAction -eq 'remove-attributable-incomplete-staging') {
    Remove-Item -LiteralPath $current.OwnedStagingRoot -Recurse -Force
  }
  if ((Test-Path -LiteralPath $current.OwnedStagingRoot) -or
      (Test-Path -LiteralPath $current.CandidatePayloadRoot)) {
    throw "$($Plan.Label) task-owned staging cleanup failed."
  }
  return [ordered]@{
    disposition = if ($DecisionAction -eq 'accept-host-cleaned') {
      'prior-remained-active-host-cleaned-observed-staging'
    } else {
      'prior-remained-active-with-explicit-task-owned-staging-cleanup'
    }
    stagedFileCount = $current.Public.stagedFileCount
    difference = $current.Public.difference
    stagingCleanupVerified = $true
    postRepairAbsent = $true
  }
}

function Invoke-IsolatedRecoveryDecision {
  param(
    [Parameter(Mandatory = $true)][object[]]$Plans,
    [Parameter(Mandatory = $true)][string]$CandidateSource,
    [Parameter(Mandatory = $true)][string]$CandidateRevision,
    [Parameter(Mandatory = $true)][System.Collections.IDictionary]$CodexVersion,
    [AllowEmptyString()][string]$RequestedModel = ''
  )
  if ($Plans.Count -ne 2 -or
      @($Plans | ForEach-Object { $_.Adapter } | Sort-Object) -join ',' -ne
      'claude,codex') {
    throw 'Agent recovery decision requires exactly the Codex and Claude plans.'
  }
  $agentRoot = Join-Path $script:TaskPathForEvidence 'agent-decision'
  New-Item -ItemType Directory -Path $agentRoot -ErrorAction Stop | Out-Null
  $schemaPath = Join-Path $agentRoot 'decision-schema.json'
  $skillLocator = 'plugins/yiyuan-accord-codex/skills/deliver-demand-driven-outcome/SKILL.md'
  $skillPath = Join-Path $CandidateSource $skillLocator
  $skillText = Get-Content -Raw -LiteralPath $skillPath
  $skillSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $skillPath).Hash.ToLowerInvariant()
  $facts = @($Plans | Sort-Object Adapter | ForEach-Object { $_.Public })
  $failureReceiptSha = Get-TextSha256 (
    ConvertTo-Json $facts -Compress -Depth 10
  )
  $nonceSha = Get-TextSha256 ([Guid]::NewGuid().ToString('N'))
  $schema = [ordered]@{
    type = 'object'
    additionalProperties = $false
    required = @(
      'schema', 'decision', 'boundFailureReceiptSha256',
      'boundNonceSha256', 'boundSubjectRevision', 'adapterActions'
    )
    properties = [ordered]@{
      schema = [ordered]@{ type = 'string'; enum = @('yiyuan-accord-gt20-agent-decision/v1') }
      decision = [ordered]@{ type = 'string'; enum = @('authorize-bounded-compensation', 'hold') }
      boundFailureReceiptSha256 = [ordered]@{ type = 'string' }
      boundNonceSha256 = [ordered]@{ type = 'string' }
      boundSubjectRevision = [ordered]@{ type = 'string' }
      adapterActions = [ordered]@{
        type = 'object'
        additionalProperties = $false
        required = @('codex', 'claude')
        properties = [ordered]@{
          codex = [ordered]@{ type = 'string'; enum = @('accept-host-cleaned', 'remove-attributable-incomplete-staging', 'hold') }
          claude = [ordered]@{ type = 'string'; enum = @('accept-host-cleaned', 'remove-attributable-incomplete-staging', 'hold') }
        }
      }
    }
  }
  $schemaJson = ConvertTo-Json $schema -Compress -Depth 12
  [System.IO.File]::WriteAllText(
    $schemaPath, $schemaJson, [System.Text.UTF8Encoding]::new($false)
  )
  $request = [ordered]@{
    operation = 'decide-bounded-failed-update-recovery'
    userIntentCount = 1
    userInterventionCount = 0
    evaluatedRevision = $CandidateRevision
    candidateSkillLocator = $skillLocator
    candidateSkillSha256 = $skillSha
    failureReceiptSha256 = $failureReceiptSha
    nonceSha256 = $nonceSha
    failureFacts = $facts
  }
  $prompt = @"
With zero tools, decide this single recovery from the path-free facts and exact
Skill. Authorize only when each action equals allowedAction and each retained
difference has nonempty missing and empty extra/changed; otherwise hold. Return
only the required JSON, without paths, commands, explanations or targets.

REQUEST:
$(ConvertTo-Json $request -Compress -Depth 12)

EXACT CANDIDATE SKILL (sha256 $skillSha):
$skillText
"@
  $arguments = [System.Collections.Generic.List[string]]::new()
  foreach ($item in @(
    '--disable', 'plugins', '--disable', 'hooks', '--sandbox', 'read-only',
    '--ask-for-approval', 'never'
  )) { $arguments.Add($item) }
  if ($RequestedModel) {
    $arguments.Add('--model')
    $arguments.Add($RequestedModel)
  }
  foreach ($item in @(
    '-c', 'model_reasoning_effort="medium"', '-C', $agentRoot, 'exec',
    '--ephemeral', '--ignore-user-config', '--ignore-rules',
    '--skip-git-repo-check', '--output-schema', $schemaPath, '--json', '-'
  )) { $arguments.Add($item) }
  $authRoot = if ($env:CODEX_HOME) {
    $env:CODEX_HOME
  } else {
    Join-Path $env:USERPROFILE '.codex'
  }
  if (-not (Test-Path -LiteralPath $authRoot -PathType Container)) {
    throw 'Current Codex authentication root is unavailable.'
  }
  $result = Invoke-Captured codex @($arguments) $agentRoot @{
    CODEX_HOME = $authRoot
  } $prompt 300 310 1048576
  if ($result.exitCode -ne 0 -or $result.timedOut -or
      -not $result.terminationConfirmed -or -not $result.streamsDrained -or
      $result.jobActiveProcesses -ne 0) {
    throw 'Isolated Codex Agent decision did not terminate successfully.'
  }
  $eventTypes = [System.Collections.Generic.List[string]]::new()
  $messages = [System.Collections.Generic.List[string]]::new()
  $threadCount = 0
  $turnStarted = 0
  $turnCompleted = 0
  foreach ($line in @($result.stdout -split "`r?`n" | Where-Object { $_.Trim() })) {
    try { $event = $line | ConvertFrom-Json -Depth 30 } catch {
      throw 'Codex Agent JSONL contained a non-JSON line.'
    }
    if ($event.type -notin @(
        'thread.started', 'turn.started', 'item.started', 'item.completed',
        'turn.completed'
      )) {
      throw "Codex Agent JSONL contained a forbidden event type: $($event.type)"
    }
    $eventTypes.Add([string]$event.type)
    switch ($event.type) {
      'thread.started' { $threadCount++ }
      'turn.started' { $turnStarted++ }
      'turn.completed' { $turnCompleted++ }
      'item.started' {
        if ($event.item.type -notin @('reasoning', 'agent_message')) {
          throw "Codex Agent started a forbidden item type: $($event.item.type)"
        }
      }
      'item.completed' {
        if ($event.item.type -notin @('reasoning', 'agent_message')) {
          throw "Codex Agent completed a forbidden item type: $($event.item.type)"
        }
        if ($event.item.type -eq 'agent_message') {
          $messages.Add([string]$event.item.text)
        }
      }
    }
  }
  if ($threadCount -ne 1 -or $turnStarted -ne 1 -or $turnCompleted -ne 1 -or
      $messages.Count -ne 1) {
    throw 'Codex Agent JSONL did not contain exactly one thread, turn and decision.'
  }
  try { $decision = $messages[0] | ConvertFrom-Json -Depth 10 } catch {
    throw 'Codex Agent decision was not valid structured JSON.'
  }
  if (@($decision.PSObject.Properties).Count -ne 6 -or
      $decision.schema -ne 'yiyuan-accord-gt20-agent-decision/v1' -or
      $decision.boundFailureReceiptSha256 -ne $failureReceiptSha -or
      $decision.boundNonceSha256 -ne $nonceSha -or
      $decision.boundSubjectRevision -ne $CandidateRevision -or
      @($decision.adapterActions.PSObject.Properties).Count -ne 2) {
    throw 'Codex Agent decision did not bind the exact recovery request.'
  }
  foreach ($plan in $Plans) {
    if ($decision.adapterActions.($plan.Adapter) -ne $plan.Public.allowedAction) {
      throw "Codex Agent decision did not select the exact $($plan.Adapter) action."
    }
  }
  if ($decision.decision -ne 'authorize-bounded-compensation') {
    throw 'Codex Agent held or rejected bounded compensation.'
  }
  return [ordered]@{
    request = $request
    invocation = [ordered]@{
      cliVersion = $CodexVersion.stdout.Trim()
      resolvedCommandSha256 = $result.resolvedCommandSha256
      terminalExecutableSha256 = $result.terminalExecutableSha256
      requestedModel = if ($RequestedModel) { $RequestedModel } else { $null }
      reasoningEffort = 'medium'
      isolation = @(
        'ephemeral', 'ignore-user-config', 'ignore-rules', 'disable-plugins',
        'disable-hooks', 'read-only-sandbox', 'approval-never',
        'empty-task-owned-working-directory', 'structured-output'
      )
      credentialUse = 'current-user-codex-home-auth-only'
      inputSha256 = Get-TextSha256 $prompt
      outputSchemaSha256 = Get-TextSha256 $schemaJson
      eventStreamSha256 = Get-TextSha256 $result.stdout
      stderrSha256 = Get-TextSha256 $result.stderr
      rawStreamPolicy = 'digest-and-safe-structure-only-no-thread-or-turn-id-retained'
      eventTypes = @($eventTypes)
      threadCount = $threadCount
      turnCount = $turnCompleted
      agentMessageCount = $messages.Count
      toolCallCount = 0
      exitCode = $result.exitCode
      timedOut = $result.timedOut
      terminationConfirmed = $result.terminationConfirmed
      streamsDrained = $result.streamsDrained
      jobActiveProcesses = $result.jobActiveProcesses
    }
    decision = [ordered]@{
      schema = $decision.schema
      decision = $decision.decision
      boundFailureReceiptSha256 = $decision.boundFailureReceiptSha256
      boundNonceSha256 = $decision.boundNonceSha256
      boundSubjectRevision = $decision.boundSubjectRevision
      adapterActions = [ordered]@{
        codex = $decision.adapterActions.codex
        claude = $decision.adapterActions.claude
      }
    }
  }
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
  $normalizedFailureCategory = if ([string]::IsNullOrEmpty($FailureCategory)) {
    $null
  } else {
    $FailureCategory
  }
  $Command.Insert(0, 'role', $Role)
  $Command.Insert(1, 'failureCategory', $normalizedFailureCategory)
  [void]$commands.Add($Command)
}

function Set-MutableAccordSource {
  param(
    [Parameter(Mandatory = $true)][string]$SourceRoot,
    [Parameter(Mandatory = $true)][string]$MutableRoot
  )
  foreach ($plugin in @('yiyuan-accord-codex', 'yiyuan-accord-claude')) {
    $destination = Join-Path $MutableRoot "plugins/$plugin"
    if (Test-Path -LiteralPath $destination) {
      Remove-Item -LiteralPath $destination -Recurse -Force
    }
    Copy-Item -LiteralPath (Join-Path $SourceRoot "plugins/$plugin") `
      -Destination $destination -Recurse
  }
  Copy-Item -LiteralPath (Join-Path $SourceRoot '.agents/plugins/marketplace.json') `
    -Destination (Join-Path $MutableRoot '.agents/plugins/marketplace.json') -Force
  Copy-Item -LiteralPath (Join-Path $SourceRoot '.claude-plugin/marketplace.json') `
    -Destination (Join-Path $MutableRoot '.claude-plugin/marketplace.json') -Force
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

function Resolve-CommandContractOverlay {
  param(
    [Parameter(Mandatory = $true)]$Overlay,
    [Parameter(Mandatory = $true)][string]$CandidateSource
  )
  if ($Overlay.schema -ne 'yiyuan-accord-gt20-command-contract-overlay/v1') {
    throw 'GT-20 successor command contract schema is invalid.'
  }
  $basePath = [System.IO.Path]::GetFullPath((
    Join-Path $CandidateSource ([string]$Overlay.baseContract.locator)
  ))
  if (-not $basePath.StartsWith(
      [System.IO.Path]::GetFullPath($CandidateSource) + [System.IO.Path]::DirectorySeparatorChar,
      [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'GT-20 base command contract escapes the candidate source.'
  }
  $baseBytes = [System.IO.File]::ReadAllBytes($basePath)
  $baseSha256 = [Convert]::ToHexString(
    [System.Security.Cryptography.SHA256]::HashData($baseBytes)
  ).ToLowerInvariant()
  if ($baseSha256 -ne $Overlay.baseContract.sha256) {
    throw 'GT-20 base command contract digest drifted.'
  }
  $base = [System.Text.Encoding]::UTF8.GetString($baseBytes) |
    ConvertFrom-Json -Depth 20
  if ($base.schema -ne 'yiyuan-accord-gt20-command-contract/v1') {
    throw 'GT-20 base command contract schema is invalid.'
  }
  $overlayCommands = @($Overlay.commands)
  $replaceRoles = @($Overlay.commandEdits.replaceRoles)
  $replacementMap = @{}
  foreach ($item in @($overlayCommands | Where-Object replacesRole)) {
    if ($replacementMap.ContainsKey([string]$item.replacesRole)) {
      throw 'GT-20 successor command contract replaces a role more than once.'
    }
    $replacementMap[[string]$item.replacesRole] = $item
  }
  if ((@($replacementMap.Keys | Sort-Object) | ConvertTo-Json -Compress) -ne
      (@($replaceRoles | Sort-Object) | ConvertTo-Json -Compress)) {
    throw 'GT-20 successor command replacement set is invalid.'
  }
  $effectiveCommands = [System.Collections.Generic.List[object]]::new()
  foreach ($baseSpec in @($base.commands)) {
    foreach ($insert in @($overlayCommands | Where-Object {
      $_.insertBeforeRole -eq $baseSpec.role
    })) {
      $insertValue = $insert | ConvertTo-Json -Depth 20 | ConvertFrom-Json -AsHashtable
      [void]$insertValue.Remove('insertBeforeRole')
      [void]$effectiveCommands.Add($insertValue)
    }
    if ($replacementMap.ContainsKey([string]$baseSpec.role)) {
      $merged = $baseSpec | ConvertTo-Json -Depth 20 | ConvertFrom-Json -AsHashtable
      $replacement = $replacementMap[[string]$baseSpec.role]
      foreach ($property in $replacement.PSObject.Properties) {
        if ($property.Name -ne 'replacesRole') {
          $merged[$property.Name] = $property.Value
        }
      }
      [void]$effectiveCommands.Add($merged)
    } else {
      [void]$effectiveCommands.Add($baseSpec)
    }
  }
  $unplaced = @($overlayCommands | Where-Object {
    -not $_.replacesRole -and -not $_.insertBeforeRole
  })
  if ($unplaced.Count -ne 0) {
    throw 'GT-20 successor command contract contains an unplaced command.'
  }
  $prependEdits = $Overlay.commandEdits.prependArgumentsByRole
  foreach ($property in $prependEdits.PSObject.Properties) {
    $matches = @($effectiveCommands | Where-Object role -eq $property.Name)
    if ($matches.Count -ne 1) {
      throw "GT-20 successor command prefix target is invalid: $($property.Name)"
    }
    $spec = $matches[0]
    $prefix = @($property.Value)
    $argv = @($spec.argv)
    $alreadyPresent = (
      $argv.Count -ge (1 + $prefix.Count) -and
      (@($argv[1..$prefix.Count]) | ConvertTo-Json -Compress) -eq
      ($prefix | ConvertTo-Json -Compress)
    )
    if (-not $alreadyPresent) {
      $spec.argv = @($argv[0]) + $prefix + @($argv | Select-Object -Skip 1)
    }
  }
  $effective = $base | ConvertTo-Json -Depth 20 | ConvertFrom-Json -AsHashtable
  $effective['commands'] = @($effectiveCommands)
  return [ordered]@{
    effective = $effective
    baseLocator = [string]$Overlay.baseContract.locator
    baseSha256 = $baseSha256
  }
}

function Assert-ActivationCommandReceipt {
  param(
    [Parameter(Mandatory = $true)]$Spec,
    [Parameter(Mandatory = $true)][System.Collections.IDictionary]$Command
  )
  if ($Spec.inputPolicy -eq 'app-server-hook-lifecycle-with-loopback-trigger') {
    $receipt = $Command.activationReceipt
    if ($receipt.transport -ne 'app-server-stdio-jsonl' -or
        ($receipt.rpcMethods | ConvertTo-Json -Compress) -ne
        (@('hooks/list', 'thread/start', 'turn/start', 'thread/resume') |
          ConvertTo-Json -Compress) -or
        $receipt.lifecycleTriggerTurns -ne 2 -or
        $receipt.externalModelTurns -ne 0 -or
        $receipt.loopbackModelRequests -ne 2) {
      throw 'Codex host activation protocol receipt is invalid.'
    }
    foreach ($item in @($receipt.startup, $receipt.resume)) {
      if ($item.discovery.rpcMethod -ne 'hooks/list' -or
          $item.discovery.eventName -ne 'SessionStart' -or
          $item.discovery.source -ne 'plugin' -or
          $item.discovery.handlerType -ne 'command' -or
          $item.discovery.enabled -ne $true -or
          $item.lifecycleTrigger.rpcMethod -ne 'turn/start' -or
          $item.lifecycleTrigger.terminalStatus -ne 'failed' -or
          $item.lifecycleTrigger.modelProvider -ne
            'task-owned-loopback-responses-failure' -or
          $item.lifecycleTrigger.requiresOpenAIAuth -ne $false -or
          $item.hookStarted.eventName -ne 'SessionStart' -or
          $item.hookStarted.source -ne 'plugin' -or
          $item.hookStarted.status -ne 'running' -or
          $item.hookCompleted.eventName -ne 'SessionStart' -or
          $item.hookCompleted.source -ne 'plugin' -or
          $item.hookCompleted.status -ne 'completed' -or
          $item.hookStarted.idSha256 -notmatch '^[0-9a-f]{64}$' -or
          $item.hookStarted.idSha256 -ne $item.hookCompleted.idSha256) {
        throw 'Codex installed-package Hook receipt is invalid.'
      }
    }
    return
  }
  if ($Spec.inputPolicy -eq 'headless-hook-lifecycle-with-loopback-trigger') {
    $receipt = $Command.activationReceipt
    $expectedLoadedPluginVersion = [string]$Spec.expectedLoadedPluginVersion
    $sources = @($receipt.hooks.source | Sort-Object -Unique)
    if ([string]::IsNullOrWhiteSpace($expectedLoadedPluginVersion) -or
        $receipt.transport -ne
          'headless-stream-json-with-loopback-trigger-and-task-owned-node-observer' -or
        $receipt.lifecycleTriggerTurns -ne 2 -or
        $receipt.externalModelTurns -ne 0 -or
        $receipt.loopbackHttpRequests -lt 2 -or
        $receipt.credentialEnvironmentInherited -ne $false -or
        $receipt.networkEndpoint -ne 'ipv4-loopback' -or
        $receipt.terminalStatus -ne 'api_error' -or
        @($receipt.hooks).Count -ne 2 -or
        ($sources | ConvertTo-Json -Compress) -ne
        (@('resume', 'startup') | ConvertTo-Json -Compress) -or
        @($receipt.hooks | Where-Object {
          $_.hookEventName -ne 'SessionStart' -or $_.exitCode -ne 0
        }).Count -ne 0) {
      throw 'Claude installed-package Hook receipt is invalid.'
    }
    foreach ($source in @('startup', 'resume')) {
      $native = $receipt.native.$source
      if ($native.sessionSource -ne $source -or
          $native.nativeHookStarted.subtype -ne 'hook_started' -or
          $native.nativeHookStarted.hookEvent -ne 'SessionStart' -or
          $native.nativeHookResponse.subtype -ne 'hook_response' -or
          $native.nativeHookResponse.hookEvent -ne 'SessionStart' -or
          $native.nativeHookResponse.exitCode -ne 0 -or
          $native.nativeHookResponse.outcome -ne 'success' -or
          $native.nativeHookStarted.hookId -ne
            $native.nativeHookResponse.hookId -or
          $native.loadedPlugin.name -ne 'yiyuan-accord-claude' -or
          $native.loadedPlugin.version -ne $expectedLoadedPluginVersion -or
          $native.terminal.status -ne 'api_error' -or
          $native.terminal.apiErrorStatus -ne 400 -or
          $native.terminal.isError -ne $true -or
          $native.terminal.totalCostUsd -ne 0 -or
          $native.terminal.turns -ne 1) {
        throw 'Claude native lifecycle event receipt is invalid.'
      }
    }
    return
  }
  throw "Unknown GT-20 command input policy: $($Spec.inputPolicy)"
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
    $mismatches = [System.Collections.Generic.List[string]]::new()
    if ($command.role -ne $spec.role) { $mismatches.Add('role') }
    if (($command.argv | ConvertTo-Json -Compress) -ne ($argv | ConvertTo-Json -Compress)) {
      $mismatches.Add('argv')
    }
    if ($command.environmentProfile -ne $spec.environmentProfile) { $mismatches.Add('environmentProfile') }
    if ($command.failureCategory -ne $spec.expectedFailureCategory) { $mismatches.Add('failureCategory') }
    if ($spec.inputPolicy) {
      if ($command.inputSha256 -notmatch '^[0-9a-f]{64}$') {
        $mismatches.Add('inputSha256')
      } else {
        Assert-ActivationCommandReceipt $spec $command
      }
    } elseif ($command.inputSha256 -ne $spec.inputSha256) {
      $mismatches.Add('inputSha256')
    }
    if ($command.executionTimeoutSeconds -ne $expectedBudgets.executionTimeoutSeconds) { $mismatches.Add('executionTimeoutSeconds') }
    if ($command.endToEndTimeoutSeconds -ne $expectedBudgets.endToEndTimeoutSeconds) { $mismatches.Add('endToEndTimeoutSeconds') }
    if ($command.outputLimitBytes -ne $expectedBudgets.outputLimitBytes) { $mismatches.Add('outputLimitBytes') }
    if ($command.stdoutBytes -ne [System.Text.Encoding]::UTF8.GetByteCount($command.stdout)) {
      $mismatches.Add('stdoutBytes')
    }
    if ($command.stderrBytes -ne [System.Text.Encoding]::UTF8.GetByteCount($command.stderr)) {
      $mismatches.Add('stderrBytes')
    }
    if ($command.timedOut -ne $expectedTimedOut) { $mismatches.Add('timedOut') }
    if ($command.terminationRequested -ne $expectedTimedOut) { $mismatches.Add('terminationRequested') }
    if ($command.terminationConfirmed -ne $true) { $mismatches.Add('terminationConfirmed') }
    if ($command.streamsDrained -ne $true) { $mismatches.Add('streamsDrained') }
    if ($command.jobActiveProcesses -ne 0) { $mismatches.Add('jobActiveProcesses') }
    if (($spec.expectedExit -eq 'zero' -and $command.exitCode -ne $expectedExit) -or
        ($spec.expectedExit -eq 'nonzero' -and $command.exitCode -eq 0) -or
        ($spec.expectedExit -eq 'timeout' -and $command.exitCode -ne 124)) {
      $mismatches.Add('exitCode')
    }
    if ($mismatches.Count -ne 0) {
      throw "GT-20 command contract mismatch at index $index ($($spec.role)): $($mismatches -join ', ')."
    }
    $profile = $profiles.($spec.environmentProfile)
    $allowed = @(
      $baseAllowed + @($profile.additionalKeys) +
      @($spec.additionalEnvironmentKeys) | Sort-Object -Unique
    )
    $required = @(
      $baseRequired + @($profile.requiredAdditionalKeys) +
      @($spec.requiredEnvironmentKeys) | Sort-Object -Unique
    )
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

$repository = [System.IO.Path]::GetFullPath($RepositoryRoot)
$task = [System.IO.Path]::GetFullPath($TaskRoot)
$evidencePath = [System.IO.Path]::GetFullPath($EvidenceOutput)
$temporaryBase = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
Assert-DirectTemporaryPath $temporaryBase $task 'TaskRoot'
if (([System.IO.Path]::GetFileName($task)) -notmatch '^yiyuan-accord-gt20-formal-[a-z0-9-]+$') {
  throw 'TaskRoot must use the formal evaluator name.'
}
if ($task.StartsWith($repository, [System.StringComparison]::OrdinalIgnoreCase)) {
  throw 'TaskRoot must be outside the repository.'
}
Assert-DirectTemporaryPath $temporaryBase $evidencePath 'EvidenceOutput'
if (([System.IO.Path]::GetFileName($evidencePath)) -notmatch '^yiyuan-accord-gt20-formal-evidence-[a-z0-9-]+\.json$' -or
    [System.IO.Path]::GetExtension($evidencePath) -ne '.json' -or
    $evidencePath.StartsWith($task, [System.StringComparison]::OrdinalIgnoreCase) -or
    $evidencePath.StartsWith($repository, [System.StringComparison]::OrdinalIgnoreCase)) {
  throw 'EvidenceOutput must use the formal JSON name outside the task root and repository.'
}
if (Test-Path -LiteralPath $evidencePath) {
  throw 'EvidenceOutput must not already exist.'
}
if ($CandidateRevision -notmatch '^[0-9a-f]{40}$') {
  throw 'CandidateRevision must be a lowercase 40-character Git object id.'
}
$script:TaskPathForEvidence = $task
$script:TaskOwnedForEvidence = $false
$script:TaskEnvironmentReadyForEvidence = $false
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
$taskOwned = $false
try {
New-Item -ItemType Directory -Path $task -ErrorAction Stop | Out-Null
$taskOwned = $true
$script:TaskOwnedForEvidence = $true
$script:TaskOwnershipToken = Get-TextSha256 ([Guid]::NewGuid().ToString('N'))
$script:TaskOwnershipMarker = Join-Path $task '.yiyuan-accord-evaluator-owned'
[System.IO.File]::WriteAllText(
  $script:TaskOwnershipMarker, $script:TaskOwnershipToken,
  [System.Text.UTF8Encoding]::new($false)
)
Assert-EvaluatorTaskRootOwned
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
$script:TaskEnvironmentReadyForEvidence = $true
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
$claudeManifest = $null
if ($claudeVersion.packageManifest) {
  $claudeManifest = Get-Content -Raw -LiteralPath $claudeVersion.packageManifest.Replace(
    '%APPDATA%', $env:APPDATA, [System.StringComparison]::OrdinalIgnoreCase
  ) | ConvertFrom-Json
  if ($claudeManifest.name -ne '@anthropic-ai/claude-code' -or
      -not $claudeVersion.stdout.Trim().StartsWith(
        "$($claudeManifest.version) ", [System.StringComparison]::Ordinal
      )) {
    throw 'Claude shim, package manifest and reported version do not agree.'
  }
} elseif (
  [System.IO.Path]::GetFileName($claudeVersion.terminalExecutable) -ne 'claude.exe' -or
  $claudeVersion.resolvedCommand -ne $claudeVersion.terminalExecutable -or
  $claudeVersion.resolvedCommandSha256 -ne $claudeVersion.terminalExecutableSha256
) {
  throw 'Claude native executable identity is invalid.'
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
  '--dangerously-bypass-hook-trust',
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
  '--dangerously-bypass-hook-trust',
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

$codexMarketplace = Invoke-Captured codex @(
  '--dangerously-bypass-hook-trust',
  'plugin', 'marketplace', 'add', $mutableSource, '--json'
) $mutableSource $codexEnvironment
Add-CommandRecord 'accordCodexMarketplaceAdd' $codexMarketplace
Assert-Exit $codexMarketplace 0 'Codex marketplace add'
$claudeMarketplace = Invoke-Captured claude @('plugin', 'marketplace', 'add', $mutableSource, '--scope', 'user') $mutableSource $claudeEnvironment
Add-CommandRecord 'accordClaudeMarketplaceAdd' $claudeMarketplace
Assert-Exit $claudeMarketplace 0 'Claude marketplace add'
$codexInstall = Invoke-Captured codex @(
  '--dangerously-bypass-hook-trust',
  'plugin', 'add', $CodexAccordPluginId, '--json'
) $mutableSource $codexEnvironment
Add-CommandRecord 'accordCodexInstallPrior' $codexInstall
Assert-Exit $codexInstall 0 'Codex install'
$claudeInstall = Invoke-Captured claude @('plugin', 'install', $ClaudeAccordPluginId, '--scope', 'user', '-y') $mutableSource $claudeEnvironment
Add-CommandRecord 'accordClaudeInstallPrior' $claudeInstall
Assert-Exit $claudeInstall 0 'Claude install'

$codexOldInstalled = Join-Path $codexRoot 'plugins/cache/yiyuan-accord/yiyuan-accord-codex/3.0.1'
$claudeOldInstalled = Join-Path $claudeRoot 'plugins/cache/yiyuan-accord/yiyuan-accord-claude/3.0.1'
$codexCandidateInstalled = Join-Path $codexRoot 'plugins/cache/yiyuan-accord/yiyuan-accord-codex/3.1.0'
$claudeCandidateInstalled = Join-Path $claudeRoot 'plugins/cache/yiyuan-accord/yiyuan-accord-claude/3.1.0'
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

Set-MutableAccordSource $candidateSource $mutableSource
$codexFailedUpdate = Invoke-UpdateWithCandidateLock codex @(
  '--dangerously-bypass-hook-trust',
  'plugin', 'add', $CodexAccordPluginId, '--json'
) $mutableSource $codexEnvironment (
  Join-Path $mutableSource 'plugins/yiyuan-accord-codex/NOTICE'
) $codexCandidateInstalled (
  Join-Path $candidateSource 'plugins/yiyuan-accord-codex'
)
Add-CommandRecord 'accordCodexFailedUpdateAfterStaging' $codexFailedUpdate 'task-owned-candidate-lock-after-staging'
if ($codexFailedUpdate.exitCode -eq 0) { throw 'Codex failed update unexpectedly succeeded' }
$claudeFailedUpdate = Invoke-UpdateWithCandidateLock claude @(
  'plugin', 'update', $ClaudeAccordPluginId, '--scope', 'user', '-y'
) $mutableSource $claudeEnvironment (
  Join-Path $mutableSource 'plugins/yiyuan-accord-claude/NOTICE'
) $claudeCandidateInstalled (
  Join-Path $candidateSource 'plugins/yiyuan-accord-claude'
)
Add-CommandRecord 'accordClaudeFailedUpdateAfterStaging' $claudeFailedUpdate 'task-owned-candidate-lock-after-staging'
if ($claudeFailedUpdate.exitCode -eq 0) { throw 'Claude failed update unexpectedly succeeded' }
[void](Assert-FileMapsEqual (Join-Path $oldSource 'plugins/yiyuan-accord-codex') $codexOldInstalled 'Codex rollback')
[void](Assert-FileMapsEqual (Join-Path $oldSource 'plugins/yiyuan-accord-claude') $claudeOldInstalled 'Claude rollback')
$codexRollbackList = Invoke-Captured codex @('plugin', 'list', '--json') $mutableSource $codexEnvironment
Add-CommandRecord 'rollbackCodexInventory' $codexRollbackList
Assert-Exit $codexRollbackList 0 'Codex rollback list'
$claudeRollbackList = Invoke-Captured claude @('plugin', 'list', '--json') $mutableSource $claudeEnvironment
Add-CommandRecord 'rollbackClaudeInventory' $claudeRollbackList
Assert-Exit $claudeRollbackList 0 'Claude rollback list'
Assert-PluginInventory $codexRollbackList codex $CodexAccordPluginId '3.0.1' $true 'Codex rollback'
Assert-PluginInventory $claudeRollbackList claude $ClaudeAccordPluginId '3.0.1' $true 'Claude rollback'
Assert-PluginInventory $codexRollbackList codex 'lifecycle-neighbor-codex@lifecycle-neighbor' '1.0.0' $true 'Codex neighbor after rollback'
Assert-PluginInventory $claudeRollbackList claude 'lifecycle-neighbor-claude@lifecycle-neighbor' '1.0.0' $true 'Claude neighbor after rollback'
[void](Assert-FileMapsEqual $neighborCodexPackage $neighborCodexInstalled 'Codex neighbor after rollback')
[void](Assert-FileMapsEqual $neighborClaudePackage $neighborClaudeInstalled 'Claude neighbor after rollback')
$codexRecoveryPlan = Get-FailedUpdateRecoveryPlan codex (
  Join-Path $candidateSource 'plugins/yiyuan-accord-codex'
) $codexFailedUpdate._ownedStagingRoot (
  $codexFailedUpdate._candidatePayloadRoot
) $codexFailedUpdate._stagingParent $codexRoot $codexOldInstalled (
  $codexFailedUpdate.mutationReceipt
) 'Codex failed update'
$claudeRecoveryPlan = Get-FailedUpdateRecoveryPlan claude (
  Join-Path $candidateSource 'plugins/yiyuan-accord-claude'
) $claudeFailedUpdate._ownedStagingRoot (
  $claudeFailedUpdate._candidatePayloadRoot
) $claudeFailedUpdate._stagingParent $claudeRoot $claudeOldInstalled (
  $claudeFailedUpdate.mutationReceipt
) 'Claude failed update'
$agentDecisionEvidence = Invoke-IsolatedRecoveryDecision @(
  $codexRecoveryPlan, $claudeRecoveryPlan
) $candidateSource $CandidateRevision $codexVersion $AgentModel
$codexDecisionAction = $agentDecisionEvidence.decision.adapterActions.codex
$claudeDecisionAction = $agentDecisionEvidence.decision.adapterActions.claude
$codexFailedUpdateRecovery = Complete-BoundedFailedUpdateRecovery (
  $codexRecoveryPlan
) $codexDecisionAction
$claudeFailedUpdateRecovery = Complete-BoundedFailedUpdateRecovery (
  $claudeRecoveryPlan
) $claudeDecisionAction
[void]$codexFailedUpdate.Remove('_ownedStagingRoot')
[void]$codexFailedUpdate.Remove('_candidatePayloadRoot')
[void]$codexFailedUpdate.Remove('_stagingParent')
[void]$claudeFailedUpdate.Remove('_ownedStagingRoot')
[void]$claudeFailedUpdate.Remove('_candidatePayloadRoot')
[void]$claudeFailedUpdate.Remove('_stagingParent')

[void](Assert-FileMapsEqual (Join-Path $oldSource 'plugins/yiyuan-accord-codex') $codexOldInstalled 'Codex post-Agent prior')
[void](Assert-FileMapsEqual (Join-Path $oldSource 'plugins/yiyuan-accord-claude') $claudeOldInstalled 'Claude post-Agent prior')
$postAgentCodexInventory = Invoke-Captured codex @('plugin', 'list', '--json') $mutableSource $codexEnvironment
$postAgentClaudeInventory = Invoke-Captured claude @('plugin', 'list', '--json') $mutableSource $claudeEnvironment
Assert-Exit $postAgentCodexInventory 0 'Codex post-Agent inventory'
Assert-Exit $postAgentClaudeInventory 0 'Claude post-Agent inventory'
Assert-PluginInventory $postAgentCodexInventory codex $CodexAccordPluginId '3.0.1' $true 'Codex post-Agent prior'
Assert-PluginInventory $postAgentClaudeInventory claude $ClaudeAccordPluginId '3.0.1' $true 'Claude post-Agent prior'
Assert-PluginInventory $postAgentCodexInventory codex 'lifecycle-neighbor-codex@lifecycle-neighbor' '1.0.0' $true 'Codex post-Agent neighbor'
Assert-PluginInventory $postAgentClaudeInventory claude 'lifecycle-neighbor-claude@lifecycle-neighbor' '1.0.0' $true 'Claude post-Agent neighbor'
[void](Assert-FileMapsEqual $neighborCodexPackage $neighborCodexInstalled 'Codex post-Agent neighbor')
[void](Assert-FileMapsEqual $neighborClaudePackage $neighborClaudeInstalled 'Claude post-Agent neighbor')
foreach ($path in $sentinels) {
  $currentHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
  if ($currentHash -ne $sentinelHashes[$path]) {
    throw 'Agent recovery changed an unmanaged or concurrent user sentinel.'
  }
}
$agentDecisionEvidence['actuation'] = [ordered]@{
  executor = 'evaluator-runner'
  targetDerivation = 'bound-private-mutation-receipt-only'
  codex = [ordered]@{
    planBindingSha256 = $codexRecoveryPlan.Public.bindingSha256
    action = $codexDecisionAction
    safetyRevalidated = $true
    result = $codexFailedUpdateRecovery
  }
  claude = [ordered]@{
    planBindingSha256 = $claudeRecoveryPlan.Public.bindingSha256
    action = $claudeDecisionAction
    safetyRevalidated = $true
    result = $claudeFailedUpdateRecovery
  }
}
$agentDecisionEvidence['independentPostState'] = [ordered]@{
  priorInstalledBytesPreserved = $true
  unrelatedPluginStatePreserved = $true
  unmanagedAndConcurrentSentinelsPreserved = $true
  inventories = [ordered]@{
    codex = $postAgentCodexInventory
    claude = $postAgentClaudeInventory
  }
  completedBeforeIntentReturn = $true
}

$codexUpdate = Invoke-Captured codex @(
  '--dangerously-bypass-hook-trust',
  'plugin', 'add', $CodexAccordPluginId, '--json'
) $mutableSource $codexEnvironment
Add-CommandRecord 'accordCodexUpdateCandidate' $codexUpdate
Assert-Exit $codexUpdate 0 'Codex successful update'
$claudeUpdate = Invoke-Captured claude @('plugin', 'update', $ClaudeAccordPluginId, '--scope', 'user', '-y') $mutableSource $claudeEnvironment
Add-CommandRecord 'accordClaudeUpdateCandidate' $claudeUpdate
Assert-Exit $claudeUpdate 0 'Claude successful update'

$codexInstalled = $codexCandidateInstalled
$claudeInstalled = $claudeCandidateInstalled
$codexFileCount = Assert-FileMapsEqual (Join-Path $candidateSource 'plugins/yiyuan-accord-codex') $codexInstalled 'Codex candidate'
$claudeFileCount = Assert-FileMapsEqual (Join-Path $candidateSource 'plugins/yiyuan-accord-claude') $claudeInstalled 'Claude candidate'
$codexList = Invoke-Captured codex @('plugin', 'list', '--json') $mutableSource $codexEnvironment
Add-CommandRecord 'candidateCodexInventory' $codexList
Assert-Exit $codexList 0 'Codex list'
$claudeList = Invoke-Captured claude @('plugin', 'list', '--json') $mutableSource $claudeEnvironment
Add-CommandRecord 'candidateClaudeInventory' $claudeList
Assert-Exit $claudeList 0 'Claude list'
Assert-PluginInventory $codexList codex $CodexAccordPluginId '3.1.0' $true 'Codex list'
Assert-PluginInventory $claudeList claude $ClaudeAccordPluginId '3.1.0' $true 'Claude list'
Assert-PluginInventory $codexList codex 'lifecycle-neighbor-codex@lifecycle-neighbor' '1.0.0' $true 'Codex neighbor after update'
Assert-PluginInventory $claudeList claude 'lifecycle-neighbor-claude@lifecycle-neighbor' '1.0.0' $true 'Claude neighbor after update'
[void](Assert-FileMapsEqual $neighborCodexPackage $neighborCodexInstalled 'Codex neighbor after update')
[void](Assert-FileMapsEqual $neighborClaudePackage $neighborClaudeInstalled 'Claude neighbor after update')

$codexHostActivation = Invoke-CodexAppServerActivation $task $codexEnvironment (
  Join-Path $codexInstalled 'hooks/hooks.json'
)
Add-CommandRecord 'codexHostActivation' $codexHostActivation
Assert-Exit $codexHostActivation 0 'Codex installed-package host activation'
$claudeHostActivation = Invoke-ClaudeHostActivation $task $claudeEnvironment (
  Join-Path $mutableSource 'plugins/yiyuan-accord-claude/runtime/accord-hook.cjs'
) '3.1.0'
Add-CommandRecord 'claudeHostActivation' $claudeHostActivation
if ($claudeHostActivation.exitCode -eq 0) {
  throw 'Claude installed registration activation did not stop at the loopback boundary.'
}

$startup = '{"hook_event_name":"SessionStart","source":"startup"}'
$resume = '{"hook_event_name":"SessionStart","source":"resume","model":"model-variable","permission_mode":"default"}'
foreach ($runtimeCase in @(
  [pscustomobject]@{Host = 'codex'; Path = (Join-Path $codexInstalled 'runtime/accord-hook.cjs')},
  [pscustomobject]@{Host = 'claude'; Path = (Join-Path $claudeInstalled 'runtime/accord-hook.cjs')}
)) {
  $startupResult = Invoke-Captured node @($runtimeCase.Path) $task @{} $startup
  if ($runtimeCase.Host -eq 'codex') {
    Add-CommandRecord 'codexHookRuntimeUnitStartup' $startupResult
  } else {
    Add-CommandRecord 'claudeHookRuntimeUnitStartup' $startupResult
  }
  Assert-Exit $startupResult 0 'Hook startup'
  if ($startupResult.stdout.Length -ne 0 -or $startupResult.stderr.Length -ne 0) { throw 'Hook startup was not silent.' }
  $resumeResult = Invoke-Captured node @($runtimeCase.Path) $task @{} $resume
  if ($runtimeCase.Host -eq 'codex') {
    Add-CommandRecord 'codexHookRuntimeUnitResume' $resumeResult
  } else {
    Add-CommandRecord 'claudeHookRuntimeUnitResume' $resumeResult
  }
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

$codexRemove = Invoke-Captured codex @('plugin', 'remove', $CodexAccordPluginId, '--json') $mutableSource $codexEnvironment
Add-CommandRecord 'accordCodexRemove' $codexRemove
Assert-Exit $codexRemove 0 'Codex remove'
$claudeRemove = Invoke-Captured claude @('plugin', 'uninstall', $ClaudeAccordPluginId, '--scope', 'user', '-y') $mutableSource $claudeEnvironment
Add-CommandRecord 'accordClaudeRemove' $claudeRemove
Assert-Exit $claudeRemove 0 'Claude remove'
$codexMarketplaceRemove = Invoke-Captured codex @('plugin', 'marketplace', 'remove', $AccordMarketplaceId, '--json') $mutableSource $codexEnvironment
Add-CommandRecord 'accordCodexMarketplaceRemove' $codexMarketplaceRemove
Assert-Exit $codexMarketplaceRemove 0 'Codex marketplace remove'
$claudeMarketplaceRemove = Invoke-Captured claude @('plugin', 'marketplace', 'remove', $AccordMarketplaceId, '--scope', 'user') $mutableSource $claudeEnvironment
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
Assert-PluginInventory $afterRemoveCodexInventory codex $CodexAccordPluginId $null $false 'Codex Accord removal'
Assert-PluginInventory $afterRemoveClaudeInventory claude $ClaudeAccordPluginId $null $false 'Claude Accord removal'
Assert-PluginInventory $afterRemoveCodexInventory codex 'lifecycle-neighbor-codex@lifecycle-neighbor' '1.0.0' $true 'Codex neighbor after Accord removal'
Assert-PluginInventory $afterRemoveClaudeInventory claude 'lifecycle-neighbor-claude@lifecycle-neighbor' '1.0.0' $true 'Claude neighbor after Accord removal'
Assert-MarketplaceInventory $afterRemoveCodexMarketplaces codex $AccordMarketplaceId $false 'Codex Accord removal'
Assert-MarketplaceInventory $afterRemoveClaudeMarketplaces claude $AccordMarketplaceId $false 'Claude Accord removal'
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
    $afterRemoveCodexConfig.Contains($CodexAccordPluginId)) {
  throw 'Codex user configuration was not preserved or Accord configuration remains.'
}
$afterRemoveClaudeSettings = Get-Content -Raw -LiteralPath $claudeSettings | ConvertFrom-Json
if ($afterRemoveClaudeSettings.userSentinel -ne 'USER_CLAUDE_SETTINGS' -or
    $afterRemoveClaudeSettings.concurrentSentinel -ne 'CONCURRENT_CLAUDE_SETTINGS' -or
    @($afterRemoveClaudeSettings.permissions.allow).Count -ne 0 -or
    ((Get-Content -Raw -LiteralPath $claudeSettings).Contains($ClaudeAccordPluginId))) {
  throw 'Claude user configuration was not preserved or Accord configuration remains.'
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
Assert-PluginInventory $cleanupCodexInventory codex $CodexAccordPluginId $null $false 'Codex Accord cleanup'
Assert-PluginInventory $cleanupClaudeInventory claude $ClaudeAccordPluginId $null $false 'Claude Accord cleanup'
Assert-MarketplaceInventory $cleanupCodexMarketplaces codex 'lifecycle-neighbor' $false 'Codex neighbor cleanup'
Assert-MarketplaceInventory $cleanupClaudeMarketplaces claude 'lifecycle-neighbor' $false 'Claude neighbor cleanup'
Assert-MarketplaceInventory $cleanupCodexMarketplaces codex $AccordMarketplaceId $false 'Codex Accord cleanup'
Assert-MarketplaceInventory $cleanupClaudeMarketplaces claude $AccordMarketplaceId $false 'Claude Accord cleanup'

$afterEvaluatorCleanup = [ordered]@{
  codexInstalledEntries = @(Get-InstalledInventory $cleanupCodexInventory codex 'Codex cleanup inventory').Count
  claudeInstalledEntries = @(Get-InstalledInventory $cleanupClaudeInventory claude 'Claude cleanup inventory').Count
  codexMarketplaceEntries = @(Get-MarketplaceInventory $cleanupCodexMarketplaces codex 'Codex cleanup marketplaces').Count
  claudeMarketplaceEntries = @(Get-MarketplaceInventory $cleanupClaudeMarketplaces claude 'Claude cleanup marketplaces').Count
  # Invoke-Captured assigns every command while suspended to a no-breakaway
  # Job and returns only after its process count reaches zero.
  taskProcesses = 0
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
    $finalCodexConfig.Contains($CodexAccordPluginId) -or
    $finalCodexConfig.Contains('lifecycle-neighbor-codex@lifecycle-neighbor')) {
  throw 'Codex evaluator cleanup changed user configuration or retained a test registration.'
}
$finalClaudeSettingsRaw = Get-Content -Raw -LiteralPath $claudeSettings
$finalClaudeSettings = $finalClaudeSettingsRaw | ConvertFrom-Json
if ($finalClaudeSettings.userSentinel -ne 'USER_CLAUDE_SETTINGS' -or
    $finalClaudeSettings.concurrentSentinel -ne 'CONCURRENT_CLAUDE_SETTINGS' -or
    @($finalClaudeSettings.permissions.allow).Count -ne 0 -or
    @($finalClaudeSettings.enabledPlugins.PSObject.Properties).Count -ne 0 -or
    @($finalClaudeSettings.extraKnownMarketplaces.PSObject.Properties).Count -ne 0 -or
    $finalClaudeSettingsRaw.Contains($ClaudeAccordPluginId) -or
    $finalClaudeSettingsRaw.Contains('lifecycle-neighbor-claude@lifecycle-neighbor')) {
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
$commandContractLocator = 'evals/contracts/gt20-v4-command-contract.json'
$commandContractPath = Join-Path $candidateSource $commandContractLocator
$commandContractBytes = [System.IO.File]::ReadAllBytes($commandContractPath)
$commandContract = [System.Text.Encoding]::UTF8.GetString($commandContractBytes) |
  ConvertFrom-Json -Depth 20
$resolvedCommandContract = Resolve-CommandContractOverlay $commandContract $candidateSource
Assert-CommandContract $resolvedCommandContract.effective $commands $CandidateRevision $priorReleaseRevision
$commandContractSha256 = [Convert]::ToHexString(
  [System.Security.Cryptography.SHA256]::HashData($commandContractBytes)
).ToLowerInvariant()
$record = [ordered]@{
  schema = 'yiyuan-accord-gt20-exact-package-evidence/v4'
  taskId = 'GT-20'
  evaluatedRevision = $CandidateRevision
  runnerSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $PSCommandPath).Hash.ToLowerInvariant()
  commandContractLocator = $commandContractLocator
  commandContractSha256 = $commandContractSha256
  baseCommandContractLocator = $resolvedCommandContract.baseLocator
  baseCommandContractSha256 = $resolvedCommandContract.baseSha256
  packageSha256 = $packages
  behaviorSubject = $behaviorSubject
  lifecycle = [ordered]@{
    install = 'verified'
    failedUpdateRecovery = 'verified'
    successfulUpdate = 'verified'
    activation = 'verified'
    remove = 'verified'
    postState = 'verified'
    cleanup = 'pending'
  }
  claimLimit = 'Bounded Windows exact-package lifecycle evidence for exact subject Codex and Claude package bytes in disposable isolated host roots: mutation-phase failed updates preserved prior installed bytes and fresh-process inventories selected 3.0.1, task-owned staging was closed, successful updates selected 3.1.0 startup/resume, and command privacy, neighbor/unmanaged state preservation, removal, cache disposition, process termination, and zero task residue were verified. The 3.0.1 prior release is Skill-only and no Hook activation is claimed. All lifecycle triggers used task-owned loopback failure endpoints with no external model turns. Real account sessions, current desktop or unmanaged hosts, cross-OS behavior, comparative product value, release readiness, publication, and production remain unclaimed.'
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
    sessionInputsProvided = $true
    lifecycleTriggerTurns = 4
    externalModelTurns = 0
    taskOwnedLoopbackCredential = $true
    sourceFailureMode = 'task-owned-candidate-lock-after-staging'
    failedUpdateDisposition = 'prior-remained-active-with-host-cleaned-or-explicit-task-owned-staging-cleanup'
    automaticRollbackClaimed = $false
    failedUpdateRecovery = [ordered]@{
      codex = $codexFailedUpdateRecovery
      claude = $claudeFailedUpdateRecovery
    }
    codexUpdateMechanism = 'plugin-add-replaces-installed-version'
    claudeUpdateMechanism = 'plugin-update'
    priorInstalledBytesPreservedAfterFailedUpdate = $true
    freshPriorInventoryVerified = $true
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

Assert-EvaluatorTaskRootOwned
Remove-Item -LiteralPath $task -Recurse -Force
if (Test-Path -LiteralPath $task) { throw 'TaskRoot cleanup failed.' }
$taskOwned = $false
$script:TaskOwnedForEvidence = $false
$script:TaskEnvironmentReadyForEvidence = $false
$record.lifecycle.cleanup = 'verified'
$record.postState.afterEvaluatorCleanup.taskRootRemoved = $true
$mechanismRecord = $record
$record = [ordered]@{
  schema = 'yiyuan-accord-gt20-exact-package-evidence/v5'
  taskId = 'GT-20'
  evaluatedRevision = $CandidateRevision
  lifecycle = [ordered]@{
    mechanism = 'verified'
    agentDecision = 'verified'
    actuation = 'verified'
    independentPostState = 'verified'
    cleanup = 'verified'
  }
  claimLimit = 'One isolated, zero-tool Codex Agent decision selected evaluator-derived compensation after native Codex and Claude failed updates; the evaluator revalidated ownership, candidate/prior bytes, retained-subset or host-cleaned state, sibling stability and post-state. The Agent supplied no target or command and deleted nothing. Automatic, in-place or crash-atomic rollback, Claude Agent equivalence, desktop behavior, production, cross-OS value, candidate status and release readiness remain unclaimed.'
  mechanism = $mechanismRecord
  agentDecision = $agentDecisionEvidence
}
Assert-NoPrivateEvidenceValue $record
$evidenceJson = $record | ConvertTo-Json -Depth 20
Assert-NoPrivateEvidenceValue ($evidenceJson | ConvertFrom-Json -Depth 30)
$succeeded = $true
} finally {
  $cleanupErrors = [System.Collections.Generic.List[string]]::new()
  try {
    if ($taskOwned) {
      if (Test-Path -LiteralPath $task) {
        Assert-EvaluatorTaskRootOwned
        Remove-Item -LiteralPath $task -Recurse -Force
      }
      if (Test-Path -LiteralPath $task) {
        $cleanupErrors.Add('task root cleanup failed')
      } else {
        $taskOwned = $false
        $script:TaskOwnedForEvidence = $false
        $script:TaskEnvironmentReadyForEvidence = $false
      }
    }
  } catch { $cleanupErrors.Add('task root cleanup failed') }
  if ($cleanupErrors.Count -ne 0) {
    $succeeded = $false
    throw ('GT-20 finalizer: ' + ($cleanupErrors -join '; '))
  }
}
if (-not $succeeded -or $null -eq $evidenceJson) {
  throw 'GT-20 did not reach an evidence publication state.'
}
$evidenceDirectory = Split-Path -Parent $evidencePath
Assert-DirectTemporaryPath $temporaryBase $evidencePath 'EvidenceOutput'
$pendingEvidencePath = Join-Path $evidenceDirectory (
  ([System.IO.Path]::GetFileName($evidencePath)) + ".pending-$PID-" +
  [Guid]::NewGuid().ToString('N')
)
$pendingEvidenceOwned = $false
try {
  $stream = [System.IO.FileStream]::new(
    $pendingEvidencePath, [System.IO.FileMode]::CreateNew,
    [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::Read
  )
  $pendingEvidenceOwned = $true
  try {
    $evidenceBytes = [System.Text.UTF8Encoding]::new($false).GetBytes(
      $evidenceJson + [System.Environment]::NewLine
    )
    $stream.Write($evidenceBytes, 0, $evidenceBytes.Length)
    $stream.Flush($true)
  } finally { $stream.Dispose() }
  [System.IO.File]::Move($pendingEvidencePath, $evidencePath, $false)
  $pendingEvidenceOwned = $false
} finally {
  if ($pendingEvidenceOwned -and (Test-Path -LiteralPath $pendingEvidencePath)) {
    Remove-Item -LiteralPath $pendingEvidencePath -Force
  }
}
Write-Output $evidencePath

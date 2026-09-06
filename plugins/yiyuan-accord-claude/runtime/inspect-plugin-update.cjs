'use strict';

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {spawnSync} = require('node:child_process');
const hash = data => crypto.createHash('sha256').update(data).digest('hex');
const parseJson = data => JSON.parse(data.toString('utf8').replace(/^\uFEFF/, ''));
const started = Date.now();
const report = {
  schema: 'yiyuan-accord-update-inspection/v1', status: 'unknown',
  reason: 'input-unavailable', sourceManifestJsonValid: null, nativeCalls: [],
  limits: [
    'inspection-only; no install, update, rollback or command interception',
    'matching snapshots do not establish continuous filesystem immutability',
    'this result is not source approval or permission for a later update',
    'native queries or validation may perform host maintenance writes',
    'the deadline is checked between synchronous filesystem operations',
  ],
};
let stage = 'input';
const fail = code => { const error = new Error(); error.code = code; throw error; };
function withinTime() {
  if (Date.now() - started >= 30000) fail('inspection-time-limit');
}
function regularBytes(file, max) {
  withinTime();
  const stat = fs.lstatSync(file);
  if (!stat.isFile() || stat.isSymbolicLink() || stat.nlink !== 1 || stat.size > max) fail('unsafe-or-large-file');
  return fs.readFileSync(file);
}
function directory(root) {
  if (!path.isAbsolute(root)) fail('nonabsolute-native-path');
  const normalized = path.resolve(root);
  if (fs.realpathSync(normalized) !== normalized || !fs.lstatSync(normalized).isDirectory()) fail('indirect-native-path');
  return normalized;
}
function snapshot(root) {
  root = directory(root);
  const files = [];
  let entries = 0, bytes = 0;
  function visit(folder) {
    for (const name of fs.readdirSync(folder).sort()) {
      withinTime();
      if (++entries > 512) fail('snapshot-entry-limit');
      const file = path.join(folder, name), stat = fs.lstatSync(file);
      if (stat.isSymbolicLink()) fail('indirect-package-entry');
      if (stat.isDirectory()) visit(file);
      else {
        const data = regularBytes(file, 16777216 - bytes);
        bytes += data.length;
        files.push([path.relative(root, file).split(path.sep).join('/'), hash(data)]);
      }
    }
  }
  visit(root);
  const digest = crypto.createHash('sha256');
  for (const [name, value] of files.sort((a, b) => Buffer.compare(Buffer.from(a[0]), Buffer.from(b[0])))) {
    digest.update(name).update('\0').update(Buffer.from(value, 'hex'));
  }
  return {sha256: digest.digest('hex'), files: files.length, bytes};
}
function equal(a, b) { return JSON.stringify(a) === JSON.stringify(b); }
function unique(rows, predicate) {
  if (!Array.isArray(rows)) fail('unexpected-native-list');
  const matches = rows.filter(row => row && typeof row === 'object' && predicate(row));
  if (matches.length !== 1) fail('missing-or-ambiguous-native-target');
  return matches[0];
}

try {
  if (process.argv.length !== 3 || process.argv[2] === '--help') {
    process.stdout.write('Usage: node inspect-plugin-update.cjs REQUEST.json\nRequest: {"cli":["absolute trusted Claude executable"],"plugin":"name@marketplace","scope":"user","expectedSourceSha256":"optional trusted snapshot digest"}\nThe CLI and working directory are caller-bound. Only native-resolved relative-directory sources and user scope are supported. Snapshots are bounded to 512 entries/16 MiB and the inspection to 30 seconds. Digest: SHA-256 of lexically sorted relative path, NUL, and binary SHA-256 per file.\n');
    process.exit(0);
  }
  const input = parseJson(regularBytes(path.resolve(process.argv[2]), 32768));
  const allowed = new Set(['cli', 'plugin', 'scope', 'expectedSourceSha256']);
  if (!input || typeof input !== 'object' || Array.isArray(input) || Object.keys(input).some(k => !allowed.has(k)) ||
      !Array.isArray(input.cli) || !input.cli.length || input.cli.length > 8 ||
      input.cli.some(value => typeof value !== 'string' || !value || value.length > 4096 || value.includes('\0')) ||
      !path.isAbsolute(input.cli[0]) || input.scope !== 'user' ||
      typeof input.plugin !== 'string' || !/^[a-z0-9][a-z0-9-]*@[a-z0-9][a-z0-9-]*$/.test(input.plugin) ||
      (input.expectedSourceSha256 !== undefined && (typeof input.expectedSourceSha256 !== 'string' ||
        !/^[0-9a-f]{64}$/.test(input.expectedSourceSha256)))) fail('unsupported-request');
  report.plugin = input.plugin;
  report.scope = input.scope;
  const [plugin, marketplace] = input.plugin.split('@');
  function native(args) {
    withinTime();
    const result = spawnSync(input.cli[0], [...input.cli.slice(1), ...args], {
      cwd: process.cwd(), timeout: Math.max(1, Math.min(8000, 30000 - (Date.now() - started))),
      maxBuffer: 1048576, windowsHide: true, encoding: null,
    });
    const stdout = result.stdout || Buffer.alloc(0), stderr = result.stderr || Buffer.alloc(0);
    report.nativeCalls.push({arguments: args, exitCode: result.status, signal: result.signal,
      error: result.error?.code || null, stdoutBytes: stdout.length, stderrBytes: stderr.length,
      stdoutSha256: hash(stdout), stderrSha256: hash(stderr)});
    if (result.error || result.signal || result.status === null) fail('native-operation-incomplete');
    return {exitCode: result.status, stdout: stdout.toString('utf8')};
  }
  function query(args) {
    const result = native(args);
    if (result.exitCode !== 0) fail('native-query-failed');
    return parseJson(result.stdout);
  }
  function locate() {
    const market = unique(query(['plugin', 'marketplace', 'list', '--json']), row => row.name === marketplace);
    const installed = unique(query(['plugin', 'list', '--json']), row => row.id === input.plugin && row.scope === input.scope);
    if (!['directory', 'git', 'github'].includes(market.source)) fail('unsupported-marketplace-source');
    if (typeof market.installLocation !== 'string' || typeof installed.installPath !== 'string') fail('native-location-unavailable');
    const marketRoot = directory(market.installLocation);
    const catalogBytes = regularBytes(path.join(marketRoot, '.claude-plugin', 'marketplace.json'), 1048576);
    const catalog = parseJson(catalogBytes);
    if (catalog.name !== marketplace) fail('marketplace-identity-mismatch');
    const entry = unique(catalog.plugins, row => row.name === plugin);
    const metadata = new Set(['name', 'source', 'description', 'version', 'author', 'homepage', 'repository', 'license', 'keywords', 'category', 'tags', 'strict']);
    if (Object.keys(entry).some(key => !metadata.has(key)) || (entry.strict !== undefined && entry.strict !== true)) fail('unsupported-entry-overrides');
    if (typeof entry.source !== 'string' || !entry.source.startsWith('./') || entry.source.includes('\\')) fail('unsupported-plugin-source');
    const parts = entry.source.slice(2).split('/');
    if (parts.some(part => !part || part === '.' || part === '..' || part.includes(':'))) fail('unsafe-plugin-source');
    const source = directory(path.join(marketRoot, ...parts));
    const current = directory(installed.installPath);
    return {market, installed, catalogSha256: hash(catalogBytes), source, current, entryVersion: entry.version};
  }
  stage = 'locate-before';
  const before = locate();
  stage = 'snapshot-before';
  const sourceBefore = snapshot(before.source), targetBefore = snapshot(before.current);
  report.source = {path: before.source, ...sourceBefore};
  report.current = {path: before.current, ...targetBefore};
  report.expectedSourceMatches = input.expectedSourceSha256 === undefined ? null : sourceBefore.sha256 === input.expectedSourceSha256;
  try {
    const manifest = parseJson(regularBytes(path.join(before.source, '.claude-plugin', 'plugin.json'), 1048576));
    report.sourceManifestJsonValid = true;
    report.sourceManifestIdentityMatches = manifest?.name === plugin &&
      (before.entryVersion === undefined || manifest?.version === before.entryVersion);
  } catch (error) {
    if (error instanceof SyntaxError) report.sourceManifestJsonValid = false;
    else throw error;
  }
  const currentManifest = parseJson(regularBytes(path.join(before.current, '.claude-plugin', 'plugin.json'), 1048576));
  report.currentManifestIdentityMatches = currentManifest?.name === plugin &&
    typeof currentManifest?.version === 'string' && currentManifest.version === before.installed.version;
  stage = 'native-validation';
  const validation = native(['plugin', 'validate', before.source, '--json']);
  report.nativeValidationPassed = validation.exitCode === 0;
  let verdict;
  try { verdict = parseJson(validation.stdout); } catch { /* Preserve post-state even when native JSON is absent. */ }
  const manifestPath = path.join(before.source, '.claude-plugin', 'plugin.json');
  report.nativeValidationReportMatches = [0, 1].includes(validation.exitCode) &&
    verdict?.success === report.nativeValidationPassed && verdict?.strict === false &&
    typeof verdict?.target === 'string' && path.resolve(verdict.target) === manifestPath &&
    verdict?.manifest?.type === 'plugin' && typeof verdict?.manifest?.file === 'string' &&
    path.resolve(verdict.manifest.file) === manifestPath && Array.isArray(verdict?.contents);
  stage = 'locate-after';
  const after = locate();
  stage = 'snapshot-after';
  report.poststate = {nativeMappingMatchesBefore: equal(before, after),
    sourceMatchesBefore: equal(sourceBefore, snapshot(after.source)),
    targetMatchesBefore: equal(targetBefore, snapshot(after.current))};
  stage = 'decide';
  if (Object.values(report.poststate).some(value => !value)) fail('observed-state-drift');
  if (report.sourceManifestIdentityMatches === false || !report.currentManifestIdentityMatches) fail('plugin-identity-mismatch');
  if (!report.nativeValidationReportMatches) fail('native-validation-inconclusive');
  if (report.nativeValidationPassed && report.sourceManifestJsonValid === false) fail('conflicting-validation-result');
  report.status = validation.exitCode === 0 && report.expectedSourceMatches !== false ? 'inspection-complete' : 'hold';
  report.reason = validation.exitCode !== 0 ? 'native-validation-rejected' :
    report.expectedSourceMatches === false ? 'expected-source-mismatch' : 'checks-finished-for-observed-snapshot';
} catch (error) {
  report.status = 'unknown';
  report.reason = error.code || (error instanceof SyntaxError ? 'unreadable-structured-input' : 'inspection-failed');
  report.failedStage = stage;
}
report.elapsedMilliseconds = Date.now() - started;
process.stdout.write(JSON.stringify(report) + '\n');

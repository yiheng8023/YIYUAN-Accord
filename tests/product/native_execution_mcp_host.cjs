'use strict';
// Deterministic integration fixture: real MCP stdio plus a fixed native peer.
// This is not a provider, model, GUI or actual human authorization observation.
const path = require('node:path');
const bridge = require('../../plugins/yiyuan-accord-codex/runtime/native-state-mcp.cjs');
const {createOwnedNativeRunner} = require('../../plugins/yiyuan-accord-codex/runtime/external-handoff.cjs');
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
bridge.serve(process.stdin, process.stdout, 'fixed-execution-fixture', {
  nativeFactory: opts => createOwnedNativeRunner({...opts, executable: process.execPath,
    args: [path.join(__dirname, 'external_handoff_host.cjs'), process.argv[2], process.argv[4] || 'normal'],
    hostVersion: 'fixed-native-fixture', cleanupTimeoutMs: 1000}),
  capabilities: process.argv[3] ? {
    inventory: options => require('../../plugins/yiyuan-accord-codex/runtime/codex-capabilities.cjs').inventory({...options, codexPath: process.argv[3]}),
    prepare: (request, options) => require('../../plugins/yiyuan-accord-codex/runtime/codex-capabilities.cjs').prepare(request, {...options, codexPath: process.argv[3]}),
  } : {
    async inventory({cwd}) { await delay(200); return {schema: 'fixed-no-model-inventory', cwd, skills: [], fixture: true}; },
    async prepare(request, {cwd}) { await delay(200); return {schema: 'fixed-no-model-skill-preparation', cwd, request, fixture: true}; },
  },
}).catch(() => { process.stderr.write('fixed execution fixture stopped\n'); process.exitCode = 1; });

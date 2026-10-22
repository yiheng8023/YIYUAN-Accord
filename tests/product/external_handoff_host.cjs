'use strict';
// Fixed local protocol fixture. No model, network, credentials or user settings.
const readline = require('node:readline');
const fs = require('node:fs');
const logPath = process.argv[2], mode = process.argv[3];
if (['owned-tree', 'exited-parent'].includes(mode)) {
  const child = require('node:child_process').spawn(process.execPath, ['-e', 'setInterval(()=>{},1000)'],
    {stdio: mode === 'exited-parent' ? ['ignore', process.stdout, process.stderr] : 'ignore', windowsHide: true, detached: true});
  fs.writeFileSync(logPath + '.child', String(child.pid));
}
let turn = fs.existsSync(logPath) ? fs.readFileSync(logPath, 'utf8').trim().split('\n').filter(line => JSON.parse(line).method === 'turn/start').length : 0;
const historyPath = logPath + '.turns.json';
const history = () => fs.existsSync(historyPath) ? JSON.parse(fs.readFileSync(historyPath, 'utf8')) : [];
const send = value => process.stdout.write(JSON.stringify(value) + '\n');
const rl = readline.createInterface({input: process.stdin});
rl.on('line', line => {
  const request = JSON.parse(line);
  fs.appendFileSync(logPath, JSON.stringify({id: request.id ?? null, method: request.method,
    threadId: request.params?.threadId ?? null, params: request.params}) + '\n');
  if (request.method === 'initialize') return send({id: request.id, result: {platformFamily: 'fixture'}});
  if (request.method === 'initialized') return;
  if (request.method === 'thread/start') return send({id: request.id, result: {
    thread: {id: 'wire-target', ephemeral: false, status: {type: 'idle'}},
    cwd: process.cwd(), model: 'fixture', approvalPolicy: 'never', sandbox: {type: 'readOnly'}}});
  if (request.method === 'configRequirements/read') return send({id: request.id, result: {
    requirements: mode === 'requirements-deny' ? {allowedSandboxModes: ['read-only']} : null}});
  if (request.method === 'thread/resume' && mode === 'resume-ack-loss') return;
  if (request.method === 'thread/resume') return send({id: request.id, result: {
    thread: {id: 'wire-target', ephemeral: false, status: {type: 'idle'}}, cwd: process.cwd(),
    model: 'fixture', approvalPolicy: 'never', sandbox: mode === 'policy-missing' ? undefined : mode === 'policy-readonly' ? {type: 'readOnly'} :
      {type: 'workspaceWrite', writableRoots: mode === 'policy-extra-root' ? [require('node:path').dirname(process.cwd())] : [],
      networkAccess: mode === 'policy-network', excludeSlashTmp: true, excludeTmpdirEnvVar: true}}});
  if (request.method === 'thread/read') return send({id: request.id, result: {
    thread: {id: 'wire-target', ephemeral: false, status: {type: mode === 'target-still-active' ? 'active' : 'idle'},
      ...(request.params.includeTurns ? {turns: history()} : {})}}});
  if (request.method === 'turn/start') {
    if (mode === 'lost-turn-receipt') return; // Unknown dispatch, never a replay fixture.
    const turnId = 'wire-turn-' + (++turn);
    if (['workspace-write', 'write-ack-loss', 'write-interrupted'].includes(mode) && request.params.sandboxPolicy?.type === 'workspaceWrite') {
      fs.writeFileSync(require('node:path').join(process.cwd(), 'review.json'), JSON.stringify({fixture: true, turn}));
    }
    if (mode === 'write-ack-loss' && turn === 2) return;
    send({id: request.id, result: {turn: {id: turnId}}});
    const bytes = Buffer.from(JSON.stringify({method: 'item/completed', params: {
      threadId: 'wire-target', turnId, item: {id: 'item-' + turn, type: 'agentMessage', text: '固定协议测试：未调用模型。'}}}) + '\n');
    // Split inside the first Chinese codepoint, across separate stream writes.
    const split = bytes.indexOf(Buffer.from('固定')) + 1;
    process.stdout.write(bytes.subarray(0, split));
    setTimeout(() => {
      process.stdout.write(bytes.subarray(split));
      const completed = {id: turnId, status: mode === 'write-interrupted' && turn === 2 ? 'interrupted' : 'completed'};
      fs.writeFileSync(historyPath, JSON.stringify([...history(), completed]));
      send({method: 'turn/completed', params: {threadId: 'wire-target', turn: completed}});
    }, 5);
    return;
  }
  send({id: request.id, error: {code: -32601, message: 'unsupported fixture method'}});
});
rl.on('close', () => {
  if (mode === 'exited-parent') process.exit(0);
  if (mode === 'hang-on-eof' || mode === 'owned-tree') setInterval(() => {}, 1000);
});

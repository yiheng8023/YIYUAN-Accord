'use strict';

const fs = require('node:fs');
const path = require('node:path');
const {createHash} = require('node:crypto');
const {TextDecoder} = require('node:util');

const utf8 = new TextDecoder('utf-8', {fatal: true});
const guidance = /* compiled entry guidance */ null;

function entryNote(event) {
  if (event?.hook_event_name === 'SessionStart' && typeof event.source === 'string' &&
      Object.hasOwn(guidance.sessionNotes, event.source)) {
    return guidance.sessionNotes[event.source];
  }
  if (event?.hook_event_name === 'SubagentStart' &&
      [event.agent_id, event.agent_type].every(value =>
        typeof value === 'string' && value.trim() && value.length <= 256)) {
    return guidance.subagentNote;
  }
  throw new Error('unsupported-entry');
}

function readGuidance(file) {
  const info = fs.lstatSync(file);
  if (!info.isFile() || info.size < 1 || info.size > 10000) {
    throw new Error('unavailable-guidance');
  }
  const bytes = fs.readFileSync(file);
  if (bytes.length !== info.size) throw new Error('changed-guidance');
  return utf8.decode(bytes);
}

async function main() {
  const chunks = [];
  let size = 0;
  for await (const chunk of process.stdin) {
    size += chunk.length;
    if (size > 65536) throw new Error('oversized-entry');
    chunks.push(chunk);
  }
  const event = JSON.parse(utf8.decode(Buffer.concat(chunks)));
  const note = entryNote(event);
  const skill = path.join(__dirname, '..', 'skills', 'deliver-demand-driven-outcome', 'SKILL.md');
  const digest = createHash('sha256').update(readGuidance(skill).replace(/\r\n/g, '\n')).digest('hex');
  if (digest !== guidance.skillSha256) throw new Error('changed-guidance');
  const additionalContext = note ? guidance.context + '\n\n' + note : guidance.context;
  if (Buffer.byteLength(additionalContext, 'utf8') > guidance.maxContextBytes) throw new Error('oversized-guidance');
  process.stdout.write(JSON.stringify({hookSpecificOutput: {
    hookEventName: event.hook_event_name, additionalContext,
  }}));
}

main().catch(() => {
  process.stderr.write('YIYUAN Accord: Claude entry guidance unavailable.\n');
  process.exitCode = 1;
});

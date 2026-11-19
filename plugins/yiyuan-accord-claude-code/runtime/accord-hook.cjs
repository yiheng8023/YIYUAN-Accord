'use strict';

const fs = require('node:fs');
const path = require('node:path');
const {TextDecoder} = require('node:util');

const utf8 = new TextDecoder('utf-8', {fatal: true});
const entrySources = new Map([
  ['startup', ''],
  ['clear', 'Accord clear entry: recover any unfinished work only from explicitly retained, applicable evidence.'],
  ['resume', 'Accord resume entry: reconcile the current user instruction, pauses, ownership and observed effects before continuing.'],
  ['compact', 'Accord compact entry: check which task facts survived and recover missing evidence before acting on it.'],
  ['fork', 'Accord fork entry: copied history carries context. Establish this task’s authority and writer before acting.'],
]);

function entryNote(event) {
  if (event?.hook_event_name === 'SessionStart' && entrySources.has(event.source)) {
    return entrySources.get(event.source);
  }
  if (event?.hook_event_name === 'SubagentStart' &&
      [event.agent_id, event.agent_type].every(value =>
        typeof value === 'string' && value.trim() && value.length <= 256)) {
    return 'Accord subagent entry: apply these duties within the delegated scope. Reconcile your own inputs and leave the parent task state to its owner.';
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
  const body = /^---\r?\nname: deliver-demand-driven-outcome\r?\ndescription: [^\r\n]+\r?\n---\r?\n+([\s\S]+)$/
    .exec(readGuidance(skill));
  if (!body || !body[1].trim()) throw new Error('invalid-guidance');
  const paragraphs = body[1].replace(/\r\n/g, '\n').trim().split(/\n\n+/);
  const [scope, action, verification] = [
    'Interpret each input', 'For an authorized outcome', 'Verify the claimed consequence',
  ].map(prefix => {
    const matches = paragraphs.filter(paragraph => paragraph.startsWith(prefix));
    if (matches.length !== 1) throw new Error('changed-guidance-structure');
    return matches[0];
  });
  const additionalContext = [
    'Accord task entry. For material needs, consult the installed yiyuan-accord:deliver-demand-driven-outcome Skill. Reuse equivalent meta-guidance already present.',
    scope,
    action,
    'Retain the goal, authority, pauses, verified results and unfinished work. Check actual effects and writer ownership before retry, recovery or handoff.',
    verification,
    note,
  ].filter(Boolean).join('\n\n');
  // The local Desktop Code route trimmed the previous long context before dispatch.
  if (Buffer.byteLength(additionalContext, 'utf8') > 1800) throw new Error('oversized-guidance');
  process.stdout.write(JSON.stringify({hookSpecificOutput: {
    hookEventName: event.hook_event_name, additionalContext,
  }}));
}

main().catch(() => {
  process.stderr.write('YIYUAN Accord: Claude entry guidance unavailable.\n');
  process.exitCode = 1;
});

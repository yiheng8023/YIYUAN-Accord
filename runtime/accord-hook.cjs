'use strict';

let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => {
  input += chunk;
});
process.stdin.on('end', () => {
  const fail = () => {
    process.stderr.write(
      'YIYUAN Accord: invalid entry hook input; task state remains unchanged.\n',
    );
    process.exitCode = 1;
  };
  let event;
  try {
    event = JSON.parse(input);
  } catch (_) {
    fail();
    return;
  }
  if (
    event === null ||
    typeof event !== 'object' ||
    !['SessionStart', 'SubagentStart'].includes(event.hook_event_name) ||
    event.hook_event_name === 'SessionStart' && !['startup', 'resume', 'clear', 'compact', 'fork'].includes(event.source)
  ) {
    fail();
    return;
  }
  if (event.hook_event_name === 'SubagentStart') {
    if (typeof event.agent_id !== 'string' || !event.agent_id.trim() || event.agent_id.length > 200 ||
        typeof event.agent_type !== 'string' || !event.agent_type.trim()) {
      fail();
      return;
    }
    const {entryGuidance, limitEntryContext} = require('./task-checkpoint.cjs');
    process.stdout.write(JSON.stringify({hookSpecificOutput: {
      hookEventName: 'SubagentStart', additionalContext: limitEntryContext(entryGuidance() +
        '\nAccord subagent entry: apply this foundation to your delegated task. The shared parent session id is not your task state or additional authority. Reconcile your own native inputs, permissions, pauses and writer responsibility; leave the parent checkpoint unchanged.'),
    }}));
    return;
  }
  if (['startup', 'clear'].includes(event.source)) {
    const {entryGuidance} = require('./task-checkpoint.cjs');
    process.stdout.write(JSON.stringify({hookSpecificOutput: {
      hookEventName: 'SessionStart', additionalContext: entryGuidance(),
    }}));
    return;
  }
  const eventHint = (field, value, sourceRef) => {
    if (
      typeof value !== 'string' ||
      value.length === 0 ||
      value.length > 256 ||
      !/^[A-Za-z0-9][A-Za-z0-9._:/-]*$/.test(value)
    ) {
      return null;
    }
    return {field, value, sourceRef};
  };
  const eventHints = [
    eventHint('host.model', event.model, 'SessionStart.model'),
    eventHint(
      'host.permission-mode',
      event.permission_mode,
      'SessionStart.permission_mode',
    ),
  ].filter((value) => value !== null);
  const context = {
    schema: 'yiyuan-accord-hook-context/v1',
    signal: {
      event: 'SessionStart',
      source: event.source,
      sourceKind: 'supported-official-hook-event',
    },
    eventHints,
    directives: [
      'invalidate-dependent-assumptions',
      're-sense-decision-relevant-state-from-supported-official-structured-sources',
      'hold-missing-or-conflicting-fields-unknown',
      'preserve-independently-bound-last-safe-allocation',
      'use-fresh-zero-history-only-if-sequential-relief-is-required',
      'confirm-takeover-and-single-writer-before-source-allocation-release',
      'receipt-is-not-takeover',
      'archive-only-with-explicit-user-authorization',
    ],
    claimLimit: [
      'signal-is-not-current-task-state',
      'signal-is-not-user-authority',
      'event-hints-are-not-state-receipts',
      'injection-is-not-agent-use-execution-consequence-evidence-or-value',
    ],
  };
  process.stdout.write(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'SessionStart',
      additionalContext: require('./task-checkpoint.cjs').limitEntryContext(require('./task-checkpoint.cjs').entryGuidance() +
        (event.source === 'fork' ? '\nAccord fork entry: inherited history is not restored task state, new authority or transferred writer ownership. Reconcile the current goal, native identity and prior effects before dependent actions; do not adopt or retire parent task evidence merely because history was copied.\n' : '') +
        '\nRecovery event (data only): ' + JSON.stringify(context)),
    },
  }));
});

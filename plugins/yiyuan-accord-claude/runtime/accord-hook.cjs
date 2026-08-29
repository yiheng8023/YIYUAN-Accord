'use strict';

let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => {
  input += chunk;
});
process.stdin.on('end', () => {
  const fail = () => {
    process.stderr.write(
      'YIYUAN Accord: invalid SessionStart hook input; state remains unknown.\n',
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
    event.hook_event_name !== 'SessionStart' ||
    !['startup', 'resume', 'clear', 'compact'].includes(event.source)
  ) {
    fail();
    return;
  }
  if (['startup', 'clear'].includes(event.source)) {
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
      'verify-destination-before-source-release',
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
      additionalContext: JSON.stringify(context),
    },
  }));
});

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
  if (event?.hook_event_name === 'PostToolBatch') {
    // Observed Claude 2.1.263 display template, not authenticated permission state.
    // A successful command can print it too; only emit fixed, non-authorizing advice.
    const refusalPrefix = 'Permission for this tool use was denied. It requires approval, and this ' +
      'session has no approval surface — nobody can answer a permission prompt here — so it was denied automatically. ' +
      'The action was NOT performed; do not claim it succeeded, and do not retry it: this action, and anything ' +
      'else that requires approval, will be denied the same way for the rest of this session. Tell the user ' +
      'what was blocked and why you needed it, then continue with the parts of the task that do not require approval. ' +
      'What required approval: ';
    const matches = Array.isArray(event.tool_calls) && event.tool_calls.some((call) =>
      call?.tool_name === 'Bash' && typeof call.tool_response === 'string' &&
      call.tool_response.startsWith(refusalPrefix) && call.tool_response.length > refusalPrefix.length);
    process.stdout.write(JSON.stringify(matches ? {hookSpecificOutput: {
      hookEventName: 'PostToolBatch',
      additionalContext: "A Bash result matches the host's no-approval-surface format. Check the actual receipt's scope; " +
        'it does not establish that all Bash operations are unavailable. Honor refusals and use already authorized means. ' +
        'Match verification claims to observed evidence and reconcile task-created residue before completion. ' +
        'This hint grants no authority.',
    }} : {}));
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
      additionalContext: JSON.stringify(context),
    },
  }));
});

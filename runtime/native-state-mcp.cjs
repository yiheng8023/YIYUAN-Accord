'use strict';

// Repository entry; the packaged adapter owns the implementation.
const path = require('node:path');
const shared = require('../plugins/yiyuan-accord-codex/runtime/native-state-mcp.cjs');
const version = () => shared.runtimeVersion(path.resolve(__dirname, '..'));
module.exports = {...shared,
  createHandler: (value = version()) => shared.createHandler(value),
  serve: (input = process.stdin, output = process.stdout, value = version()) => shared.serve(input, output, value),
};
if (require.main === module) shared.main(version);

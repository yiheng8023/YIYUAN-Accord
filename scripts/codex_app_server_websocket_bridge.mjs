#!/usr/bin/env node

/*
 * Minimal line-oriented bridge for Codex app-server WebSocket probes.
 *
 * Each bridge process owns exactly one WebSocket. JSON-RPC objects arrive as
 * one JSON line on stdin and are forwarded as one text WebSocket message.
 * Incoming text messages are written unchanged as one line on stdout.
 * Lifecycle diagnostics go to stderr so they cannot be mistaken for JSON-RPC.
 */

import readline from "node:readline";

const targetUrl = process.argv[2];
if (!targetUrl || !targetUrl.startsWith("ws://")) {
  process.stderr.write("BRIDGE_FATAL missing-or-invalid-ws-url\n");
  process.exit(2);
}

const maxConnectAttempts = 100;
const retryDelayMilliseconds = 50;
let connectAttempt = 0;
let socket;
let input;
let opened = false;
let closing = false;

function fail(message) {
  process.stderr.write(`BRIDGE_FATAL ${message}\n`);
  process.exitCode = 1;
  if (socket && socket.readyState < WebSocket.CLOSING) {
    socket.close(1011, "bridge failure");
  } else {
    process.exit(1);
  }
}

function beginInput() {
  input = readline.createInterface({
    input: process.stdin,
    crlfDelay: Infinity,
  });
  input.on("line", (line) => {
    if (!line.trim()) return;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      fail("stdin-message-before-open");
      return;
    }
    socket.send(line);
  });
  input.on("close", () => {
    closing = true;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.close(1000, "bridge stdin closed");
      setTimeout(() => process.exit(0), 1000).unref();
    } else if (!socket || socket.readyState === WebSocket.CLOSED) {
      process.exit(0);
    }
  });
}

function connect() {
  connectAttempt += 1;
  let candidate;
  try {
    candidate = new WebSocket(targetUrl);
  } catch (error) {
    if (connectAttempt < maxConnectAttempts) {
      setTimeout(connect, retryDelayMilliseconds);
      return;
    }
    fail(`connect-constructor ${String(error)}`);
    return;
  }
  socket = candidate;

  candidate.addEventListener("open", () => {
    opened = true;
    process.stderr.write(
      `BRIDGE_READY pid=${process.pid} attempt=${connectAttempt} url=${targetUrl}\n`,
    );
    beginInput();
  });

  candidate.addEventListener("message", async (event) => {
    let text;
    if (typeof event.data === "string") {
      text = event.data;
    } else if (event.data instanceof ArrayBuffer) {
      text = Buffer.from(event.data).toString("utf8");
    } else if (event.data && typeof event.data.text === "function") {
      text = await event.data.text();
    } else {
      fail("unsupported-message-type");
      return;
    }
    process.stdout.write(`${text}\n`);
  });

  candidate.addEventListener("error", () => {
    if (!opened && connectAttempt < maxConnectAttempts) {
      return;
    }
    process.stderr.write("BRIDGE_ERROR websocket-error\n");
  });

  candidate.addEventListener("close", (event) => {
    if (!opened && connectAttempt < maxConnectAttempts) {
      setTimeout(connect, retryDelayMilliseconds);
      return;
    }
    process.stderr.write(
      `BRIDGE_CLOSED code=${event.code} clean=${event.wasClean}\n`,
    );
    if (input) input.close();
    process.exit(closing || event.code === 1000 ? 0 : 1);
  });
}

connect();

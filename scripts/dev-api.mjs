#!/usr/bin/env node
/**
 * Cross-platform replacement for dev-api.sh (works on Windows without bash/lsof).
 */
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");

function readEnvValue(key, fallback) {
  for (const file of [join(ROOT, ".env"), join(ROOT, ".env.local")]) {
    if (!existsSync(file)) continue;
    const match = readFileSync(file, "utf8").match(new RegExp(`^${key}=(.+)$`, "m"));
    if (match) {
      return match[1].trim().replace(/^["']|["']$/g, "");
    }
  }
  return fallback;
}

const host = readEnvValue("API_HOST", "127.0.0.1");
const port = readEnvValue("API_PORT", "8000");
const bindHost = host === "0.0.0.0" ? "127.0.0.1" : host;

const child = spawn(
  "uv",
  [
    "run",
    "--python",
    "3.11",
    "--package",
    "gridtrace-api",
    "uvicorn",
    "gridtrace_api.main:app",
    "--reload",
    "--host",
    bindHost,
    "--port",
    port,
  ],
  { cwd: ROOT, stdio: "inherit", shell: process.platform === "win32" },
);

child.on("exit", (code) => process.exit(code ?? 0));

#!/usr/bin/env node
/**
 * Cross-platform replacement for setup-production-csv.sh.
 * Ensures data/raw/production/ has CSVs before ingest-production.
 */
import { cpSync, existsSync, mkdirSync, readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const DIR = join(ROOT, "data", "raw", "production");
const FIXTURES = join(ROOT, "apps", "worker", "tests", "fixtures", "production");

function runExport() {
  console.log("==> Exporting full deterministic demo dataset to data/raw/production/");
  const result = spawnSync(
    "uv",
    [
      "run",
      "--python",
      "3.11",
      "--package",
      "gridtrace-worker",
      "python",
      "-m",
      "gridtrace_worker.main",
      "export-production-csv",
    ],
    { cwd: ROOT, stdio: "inherit", shell: process.platform === "win32" },
  );
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
  console.log("==> Full production CSVs ready (edit files here to load your real operational data)");
}

mkdirSync(DIR, { recursive: true });

const stedinDir = join(ROOT, "data", "raw", "Stedin");
if (existsSync(stedinDir)) {
  const stedinFiles = readdirSync(stedinDir).filter((name) =>
    name.startsWith("Stedin kleinverbruikgegevens ") && name.endsWith(".csv"),
  );
  if (stedinFiles.length > 0) {
    console.log(
      `==> Stedin CSVs detected (${stedinFiles.length} files) — skipping demo export; run pnpm db:ingest-production`,
    );
    process.exit(0);
  }
}

let copied = 0;
for (const name of readdirSync(DIR)) {
  if (!name.endsWith(".csv.example")) continue;
  const example = join(DIR, name);
  const target = join(DIR, name.replace(/\.example$/, ""));
  if (!existsSync(target)) {
    cpSync(example, target);
    console.log(`==> Created ${name.replace(/\.example$/, "")} from example`);
    copied += 1;
  }
}

if (!existsSync(join(DIR, "operators.csv")) && existsSync(FIXTURES)) {
  console.log("==> Copying minimal schema fixtures from tests");
  for (const name of readdirSync(FIXTURES)) {
    if (name.endsWith(".csv")) {
      cpSync(join(FIXTURES, name), join(DIR, name));
    }
  }
}

const forceExport = process.env.FORCE_EXPORT_PRODUCTION === "1";
const meterPath = join(DIR, "meter_readings.csv");
let needsExport = forceExport;

if (!needsExport && !existsSync(meterPath)) {
  needsExport = true;
} else if (!needsExport && existsSync(meterPath)) {
  const lines = readFileSync(meterPath, "utf8").split(/\r?\n/).filter(Boolean).length;
  if (lines < 1000) {
    needsExport = true;
  }
}

if (needsExport) {
  runExport();
  process.exit(0);
}

if (copied > 0) {
  console.log("==> Schema templates copied. Run pnpm db:export-production for the full demo dataset.");
} else {
  console.log("==> Production CSVs already present in data/raw/production/");
}

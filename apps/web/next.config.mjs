/** @type {import('next').NextConfig} */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

/** Load monorepo-root .env into process.env (last value wins, like dotenv). */
function loadRootEnv() {
  const monorepoRoot = path.join(path.dirname(fileURLToPath(import.meta.url)), "../..");
  for (const name of [".env", ".env.local"]) {
    const envPath = path.join(monorepoRoot, name);
    if (!fs.existsSync(envPath)) continue;
    for (const line of fs.readFileSync(envPath, "utf8").split("\n")) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#")) continue;
      const eq = trimmed.indexOf("=");
      if (eq <= 0) continue;
      const key = trimmed.slice(0, eq).trim();
      let value = trimmed.slice(eq + 1).trim();
      if (
        (value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'"))
      ) {
        value = value.slice(1, -1);
      }
      process.env[key] = value;
    }
  }
}

loadRootEnv();

const nextConfig = {
  output: "standalone",
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
    NEXT_PUBLIC_MAP_STYLE_URL: process.env.NEXT_PUBLIC_MAP_STYLE_URL,
    NEXT_PUBLIC_DEMO_MODE: process.env.NEXT_PUBLIC_DEMO_MODE,
  },
  reactStrictMode: true,
  transpilePackages: [
    "@gridtrace/api-client",
    "@gridtrace/charts",
    "@gridtrace/config",
    "@gridtrace/contracts",
    "@gridtrace/domain",
    "@gridtrace/maps",
    "@gridtrace/testing",
    "@gridtrace/ui",
  ],
};

export default nextConfig;

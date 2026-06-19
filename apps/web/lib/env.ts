import { parsePublicEnv, type PublicEnv } from "@gridtrace/config";

/**
 * Next.js statically inlines `process.env.NEXT_PUBLIC_*`, so they must be
 * referenced explicitly (not via a dynamic key) to survive the build.
 */
export function getPublicEnv(): PublicEnv {
  return parsePublicEnv({
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
    NEXT_PUBLIC_MAP_STYLE_URL: process.env.NEXT_PUBLIC_MAP_STYLE_URL,
    NEXT_PUBLIC_DEMO_MODE: process.env.NEXT_PUBLIC_DEMO_MODE,
  });
}

"use client";

import { useEffect, useState, type ReactNode } from "react";
import { getPublicEnv } from "./env";

/**
 * In demo mode we start the MSW browser worker so the whole app runs with no
 * backend. Rendering of API-driven content is gated until the worker is ready.
 * When demo mode is off, any previously registered MSW worker is stopped so real
 * API responses are not intercepted by stale mock handlers.
 */
export function DemoModeGate({ children }: { children: ReactNode }) {
  const { NEXT_PUBLIC_DEMO_MODE } = getPublicEnv();
  const [ready, setReady] = useState(!NEXT_PUBLIC_DEMO_MODE);

  useEffect(() => {
    if (NEXT_PUBLIC_DEMO_MODE) {
      let cancelled = false;
      void (async () => {
        const { startMsw } = await import("@gridtrace/testing/browser");
        await startMsw();
        if (!cancelled) setReady(true);
      })();
      return () => {
        cancelled = true;
      };
    }

    void (async () => {
      const { stopMsw } = await import("@gridtrace/testing/browser");
      await stopMsw();
      setReady(true);
    })();
  }, [NEXT_PUBLIC_DEMO_MODE]);

  if (!ready) {
    return (
      <div className="flex h-screen w-full items-center justify-center text-sm text-muted-foreground">
        Starting GridTrace demo environment…
      </div>
    );
  }
  return <>{children}</>;
}

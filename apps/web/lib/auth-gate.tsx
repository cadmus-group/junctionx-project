"use client";

import { useEffect, useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { getPublicEnv } from "./env";
import { getToken } from "./client";

export function AuthGate({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { NEXT_PUBLIC_DEMO_MODE } = getPublicEnv();
  const [ready, setReady] = useState(NEXT_PUBLIC_DEMO_MODE);

  useEffect(() => {
    if (NEXT_PUBLIC_DEMO_MODE) {
      setReady(true);
      return;
    }
    if (!getToken()) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
      return;
    }
    setReady(true);
  }, [NEXT_PUBLIC_DEMO_MODE, pathname, router]);

  if (!ready) {
    return (
      <div className="flex h-screen w-full items-center justify-center text-sm text-muted-foreground">
        Checking session…
      </div>
    );
  }

  return <>{children}</>;
}

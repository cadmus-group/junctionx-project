import { Suspense, type ReactNode } from "react";
import { AppShell } from "@/components/app-shell";
import { RequireAuth } from "@/lib/auth";

export default function PlatformLayout({ children }: { children: ReactNode }) {
  return (
    <RequireAuth>
      <AppShell>
        <Suspense>{children}</Suspense>
      </AppShell>
    </RequireAuth>
  );
}

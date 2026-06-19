"use client";

import { TooltipProvider } from "@gridtrace/ui";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { ApiProvider } from "@/lib/client";
import { DemoModeGate } from "@/lib/demo";

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60_000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <DemoModeGate>
      <QueryClientProvider client={queryClient}>
        <ApiProvider>
          <TooltipProvider delayDuration={150}>{children}</TooltipProvider>
        </ApiProvider>
      </QueryClientProvider>
    </DemoModeGate>
  );
}

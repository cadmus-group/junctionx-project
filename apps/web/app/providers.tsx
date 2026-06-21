"use client";

import { ApiError } from "@gridtrace/api-client";
import { TooltipProvider } from "@gridtrace/ui";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState, type ReactNode } from "react";
import { AuthProvider, useAuth } from "@/lib/auth";
import { ApiProvider } from "@/lib/client";
import { DemoModeGate } from "@/lib/demo";

function AuthQueryHandler({ queryClient }: { queryClient: QueryClient }) {
  const { logout } = useAuth();

  useEffect(() => {
    const onUnauthorized = (error: unknown) => {
      if (error instanceof ApiError && error.status === 401) logout();
    };

    const unsubQueries = queryClient.getQueryCache().subscribe((event) => {
      if (event.type === "updated" && event.action.type === "error") {
        onUnauthorized(event.query.state.error);
      }
    });
    const unsubMutations = queryClient.getMutationCache().subscribe((event) => {
      if (event.type === "updated" && event.action.type === "error") {
        onUnauthorized(event.mutation.state.error);
      }
    });

    return () => {
      unsubQueries();
      unsubMutations();
    };
  }, [queryClient, logout]);

  return null;
}

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60_000,
            retry: (failureCount, error) =>
              !(error instanceof ApiError && error.status === 401) && failureCount < 1,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <DemoModeGate>
      <QueryClientProvider client={queryClient}>
        <ApiProvider>
          <AuthProvider>
            <AuthQueryHandler queryClient={queryClient} />
            <TooltipProvider delayDuration={150}>{children}</TooltipProvider>
          </AuthProvider>
        </ApiProvider>
      </QueryClientProvider>
    </DemoModeGate>
  );
}

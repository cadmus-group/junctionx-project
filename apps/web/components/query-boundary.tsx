"use client";

import { EmptyState, ErrorState } from "@gridtrace/ui";
import type { UseQueryResult } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { LoadingSkeleton } from "./loading";

interface QueryBoundaryProps<T> {
  query: UseQueryResult<T>;
  children: (data: T) => ReactNode;
  loading?: ReactNode;
  isEmpty?: (data: T) => boolean;
  emptyTitle?: string;
  emptyDescription?: string;
}

export function QueryBoundary<T>({
  query,
  children,
  loading,
  isEmpty,
  emptyTitle = "Nothing to show",
  emptyDescription,
}: QueryBoundaryProps<T>) {
  if (query.isPending) return <>{loading ?? <LoadingSkeleton />}</>;
  if (query.isError) {
    return <ErrorState error={query.error} onRetry={() => void query.refetch()} />;
  }
  if (isEmpty?.(query.data)) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />;
  }
  return <>{children(query.data)}</>;
}

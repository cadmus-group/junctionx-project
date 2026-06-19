"use client";

import {
  filtersFromSearchParams,
  filtersToSearchParams,
  type GlobalFilters,
} from "@gridtrace/domain";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useMemo } from "react";

export function useGlobalFilters() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const filters = useMemo<GlobalFilters>(() => {
    try {
      return filtersFromSearchParams(new URLSearchParams(searchParams.toString()));
    } catch {
      return {};
    }
  }, [searchParams]);

  const setFilters = useCallback(
    (next: Partial<GlobalFilters>, options: { replace?: boolean } = {}) => {
      const merged = { ...filters, ...next };
      for (const [key, value] of Object.entries(next)) {
        if (value === undefined || value === null || value === "") {
          delete (merged as Record<string, unknown>)[key];
        }
      }
      const params = filtersToSearchParams(merged);
      const query = params.toString();
      const url = query ? `${pathname}?${query}` : pathname;
      if (options.replace) router.replace(url, { scroll: false });
      else router.push(url, { scroll: false });
    },
    [filters, pathname, router]
  );

  return { filters, setFilters };
}

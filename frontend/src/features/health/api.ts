import { useQuery } from "@tanstack/react-query";

import { api, unwrap } from "@/lib/api/client";

const HEALTH_POLL_MS = 30_000;

export const healthKeys = { service: ["health"] as const };

/** The messaging service's health and recent message counts, refreshed every 30 s. */
export function useServiceHealth() {
  return useQuery({
    queryKey: healthKeys.service,
    queryFn: ({ signal }) => unwrap(api.GET("/api/v1/providers/health/", { signal })),
    refetchInterval: HEALTH_POLL_MS,
    staleTime: HEALTH_POLL_MS,
  });
}

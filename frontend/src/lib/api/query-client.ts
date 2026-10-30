import { QueryClient } from "@tanstack/react-query";

import { ApiError } from "./errors";

const MAX_QUERY_RETRIES = 2;

export function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // SSE events keep the cache current, so frequent refetching is unnecessary.
        staleTime: 30_000,
        // A 4xx fails the same way again; only network errors and 5xx are retried.
        retry: (failureCount, error) =>
          failureCount < MAX_QUERY_RETRIES && error instanceof ApiError && error.isTransient,
      },
      mutations: {
        // A retried send or delete could repeat the action.
        retry: false,
      },
    },
  });
}

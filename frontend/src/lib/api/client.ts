import createClient from "openapi-fetch";

import { ApiError } from "./errors";
import type { paths } from "./schema";

// Same origin: Next proxies /api/* to Django, so the browser needs no API URL. Requests are
// made from client components only. The page's origin is spelled out because some fetch
// implementations (e.g. Node's, used in tests) reject relative URLs.
export const api = createClient<paths>({
  baseUrl: globalThis.location?.origin ?? "",
  // Looked up on each call rather than captured once, so tests can stub the global fetch.
  fetch: (request) => globalThis.fetch(request),
});

type FetchResult<T> = { data?: T; error?: unknown; response: Response };

/**
 * Await an `api` call and return its data, or throw an ApiError.
 *
 * TanStack Query treats a thrown error as a failed query, so query and mutation
 * functions should always go through this.
 */
export async function unwrap<T>(request: Promise<FetchResult<T>>): Promise<T> {
  let result: FetchResult<T>;
  try {
    result = await request;
  } catch {
    throw new ApiError("network_error", null);
  }
  if (!result.response.ok) {
    throw ApiError.fromResponse(result.response, result.error);
  }
  return result.data as T;
}

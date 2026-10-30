import type { ErrorCode, ErrorResponse } from "./types";

// Failures that never produced an API error envelope.
type ClientErrorCode =
  | "network_error" // The request never reached the server (offline, DNS, CORS).
  | "service_unavailable" // The proxy answered 502/503/504 because the API is down.
  | "unknown_error"; // A response we could not interpret, or a code this build doesn't know.

export type ApiErrorCode = ErrorCode | ClientErrorCode;

const GENERIC = "Something went wrong on our side. Please try again.";

// Every API code must have copy here: the Record type fails the build when the backend
// adds a code and `npm run gen:api` is re-run.
const MESSAGES: Record<ApiErrorCode, string> = {
  validation_error: "Some details need fixing. Check the highlighted fields.",
  bad_request: "That request couldn't be processed. Please try again.",
  parse_error: GENERIC,
  not_authenticated: "Your session has ended. Please sign in again.",
  permission_denied: "You don't have permission to do that.",
  not_found: "We couldn't find that. It may have been deleted.",
  method_not_allowed: GENERIC,
  not_acceptable: GENERIC,
  unsupported_media_type: GENERIC,
  throttled: "Too many requests. Please wait a moment and try again.",
  conflict: "This was changed in the meantime. Refresh and try again.",
  not_retryable: "This message can't be sent again. It may already have been retried.",
  duplicate_candidate: "A candidate with this mobile number or email already exists.",
  duplicate_template: "A template with this name already exists.",
  invalid_webhook_signature: GENERIC,
  invalid_webhook_payload: GENERIC,
  internal_error: GENERIC,
  network_error: "Can't reach the server. Check your connection and try again.",
  service_unavailable: "The service is temporarily unavailable. Please try again shortly.",
  unknown_error: GENERIC,
};

export class ApiError extends Error {
  override readonly name = "ApiError";

  constructor(
    readonly code: ApiErrorCode,
    /** HTTP status, or null when no response arrived. */
    readonly status: number | null,
    /** Field path (e.g. "phone") → messages, for showing errors next to form inputs. */
    readonly fields: Record<string, string[]> = {},
    /** The server's own message, shown only when this build has no copy for the code. */
    readonly serverMessage: string | null = null,
  ) {
    super(serverMessage ?? code);
  }

  /** Errors worth retrying automatically: nothing reached the API, or the API is down. */
  get isTransient(): boolean {
    return this.status === null || this.status >= 500;
  }

  static fromResponse(response: Response, body: unknown): ApiError {
    if (isErrorResponse(body)) {
      const { code, message, fields } = body.error;
      return new ApiError(isKnownCode(code) ? code : "unknown_error", response.status, fields, message);
    }
    // No envelope: the request was answered by the proxy, not by Django.
    if ([502, 503, 504].includes(response.status)) {
      return new ApiError("service_unavailable", response.status);
    }
    return new ApiError("unknown_error", response.status);
  }
}

/** Recruiter-facing copy for any error thrown by an API call. */
export function errorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return GENERIC;
  }
  if (error.code === "unknown_error" && error.serverMessage) {
    return error.serverMessage;
  }
  return MESSAGES[error.code];
}

function isKnownCode(code: string): code is ApiErrorCode {
  return Object.hasOwn(MESSAGES, code);
}

function isErrorResponse(body: unknown): body is ErrorResponse {
  if (typeof body !== "object" || body === null || !("error" in body)) {
    return false;
  }
  const error = (body as { error: unknown }).error;
  if (typeof error !== "object" || error === null) {
    return false;
  }
  const { code, message, fields } = error as Record<string, unknown>;
  return (
    typeof code === "string" &&
    typeof message === "string" &&
    typeof fields === "object" &&
    fields !== null
  );
}

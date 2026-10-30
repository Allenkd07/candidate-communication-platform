import { describe, expect, it } from "vitest";

import { ApiError, errorMessage } from "./errors";

const envelope = (code: string, message = "Server text", fields = {}) => ({ error: { code, message, fields } });

describe("ApiError.fromResponse", () => {
  it("keeps the code and field errors from the API envelope", () => {
    const error = ApiError.fromResponse(
      new Response(null, { status: 409 }),
      envelope("duplicate_candidate", "Taken", { phone: ["Already in use."] }),
    );

    expect(error.code).toBe("duplicate_candidate");
    expect(error.status).toBe(409);
    expect(error.fields).toEqual({ phone: ["Already in use."] });
  });

  it("treats a proxy error page without an envelope as the service being unavailable", () => {
    const error = ApiError.fromResponse(new Response("<html>Bad gateway</html>", { status: 502 }), undefined);

    expect(error.code).toBe("service_unavailable");
    expect(error.isTransient).toBe(true);
  });

  it("does not trust a malformed envelope", () => {
    const error = ApiError.fromResponse(new Response(null, { status: 400 }), { error: "nope" });

    expect(error.code).toBe("unknown_error");
  });
});

describe("errorMessage", () => {
  it("maps known codes to recruiter-facing copy, not the server's text", () => {
    const error = ApiError.fromResponse(new Response(null, { status: 404 }), envelope("not_found", "No Candidate matches."));

    expect(errorMessage(error)).toBe("We couldn't find that. It may have been deleted.");
  });

  it("falls back to the server's message for a code this build doesn't know", () => {
    const error = ApiError.fromResponse(new Response(null, { status: 400 }), envelope("brand_new_code", "Explained here."));

    expect(errorMessage(error)).toBe("Explained here.");
  });

  it("explains network failures and non-API errors", () => {
    expect(errorMessage(new ApiError("network_error", null))).toMatch(/can't reach the server/i);
    expect(errorMessage(new TypeError("boom"))).toMatch(/something went wrong/i);
  });
});

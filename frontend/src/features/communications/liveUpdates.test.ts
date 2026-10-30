import { describe, expect, it } from "vitest";

import type { MessageStatusEvent } from "@/lib/api/types";

import { applyEvent } from "./liveUpdates";

const cached = { id: "m1", status: "read" as const, status_changed_at: "2026-10-30T10:00:05Z" };

function event(status: MessageStatusEvent["status"], at: string): MessageStatusEvent {
  return {
    message_id: "m1",
    batch_id: "b1",
    candidate_id: "c1",
    status,
    status_changed_at: at,
    failure_code: "",
    failure_reason: "",
    is_retryable: false,
    can_retry: false,
  };
}

describe("applyEvent", () => {
  it("ignores an event older than the cached status", () => {
    expect(applyEvent(cached, event("delivered", "2026-10-30T10:00:03Z"))).toBe(cached);
  });

  it("applies a newer event", () => {
    const updated = applyEvent(
      { ...cached, status: "delivered" as const, status_changed_at: "2026-10-30T10:00:03Z" },
      event("read", "2026-10-30T10:00:05Z"),
    );

    expect(updated).toMatchObject({ status: "read", status_changed_at: "2026-10-30T10:00:05Z" });
  });
});

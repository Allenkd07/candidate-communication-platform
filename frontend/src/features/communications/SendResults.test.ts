import { describe, expect, it } from "vitest";

import { summarize } from "./SendResults";

describe("summarize", () => {
  it("lists only the statuses present, furthest along first and failures last", () => {
    const counts = { scheduled: 0, queued: 1, sent: 0, delivered: 3, read: 1, failed: 2 };

    expect(summarize(counts)).toBe("1 read · 3 delivered · 1 queued · 2 failed");
  });
});

import { describe, expect, it } from "vitest";

import { nextSort, parseUrlState } from "./useCandidatesUrlState";

const parse = (query: string) => parseUrlState(new URLSearchParams(query));

describe("parseUrlState", () => {
  it("reads valid filters", () => {
    const state = parse("name=tay&phone=98450%2012&id=A1B&status=read,none&from=2026-10-01&to=2026-10-30");

    expect(state).toMatchObject({
      name: "tay",
      phone: "98450 12",
      code: "A1B",
      status: ["read", "none"],
      from: "2026-10-01",
      to: "2026-10-30",
    });
  });

  it("drops filter values the API would reject", () => {
    const state = parse("phone=98x&id=A1B2C3D&status=pending,failed&from=yesterday&to=2026-13-45");

    expect(state).toMatchObject({ phone: "", code: "", status: ["failed"], from: "", to: "" });
  });

  it("falls back to the first page and default size for bad paging values", () => {
    expect(parse("page=-2&rows=7")).toMatchObject({ page: 1, pageSize: 10 });
  });

  it("reads a known sort and drops an unknown one", () => {
    expect(parse("sort=-last_message").sort).toBe("-last_message");
    expect(parse("sort=created_at").sort).toBe("");
    expect(parse("sort=--name").sort).toBe("");
  });
});

describe("nextSort", () => {
  it("cycles ascending, descending, then newest first", () => {
    expect(nextSort("name", "")).toBe("name");
    expect(nextSort("name", "name")).toBe("-name");
    expect(nextSort("name", "-name")).toBe("");
    expect(nextSort("status", "-name")).toBe("status");
  });
});

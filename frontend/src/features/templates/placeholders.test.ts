import { describe, expect, it } from "vitest";

import { fillIn, hasPlaceholders, toTemplate } from "./placeholders";

const taylor = { id: "1", full_name: "Taylor Swift", code: "A1B2C3" };

describe("placeholders", () => {
  it("fills in each candidate detail and leaves unknown placeholders as typed", () => {
    expect(fillIn("Hi {{ first_name }}, {{full_name}} {{salary}}", taylor)).toBe("Hi Taylor, Taylor Swift {{salary}}");
  });

  it("turns a candidate's name back into placeholders", () => {
    expect(toTemplate("Hi Taylor, Taylor Swift, Taylorville", taylor)).toBe(
      "Hi {{first_name}}, {{full_name}}, Taylorville",
    );
  });

  it("round-trips a template", () => {
    const template = "Hello {{full_name}}, see you soon {{first_name}}";
    expect(toTemplate(fillIn(template, taylor), taylor)).toBe(template);
  });

  it("detects placeholders", () => {
    expect(hasPlaceholders("Hi {{first_name}}")).toBe(true);
    expect(hasPlaceholders("Hi Taylor")).toBe(false);
  });
});

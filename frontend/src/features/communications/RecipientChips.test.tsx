import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithProviders } from "@/test/render";

import { RecipientChips } from "./RecipientChips";

const CHIPS_PER_LINE = 3;
const LINE_HEIGHT = 40;
const NAMES = ["Asha", "Bala", "Chitra", "Dev", "Esha", "Farid", "Gita", "Hari"];

describe("RecipientChips", () => {
  beforeEach(() => {
    // jsdom does no layout: place chips three to a line by their position among siblings.
    vi.spyOn(HTMLElement.prototype, "offsetTop", "get").mockImplementation(function (this: HTMLElement) {
      const index = Array.prototype.indexOf.call(this.parentElement?.children ?? [], this);
      return Math.floor(index / CHIPS_PER_LINE) * LINE_HEIGHT;
    });
  });

  it("shows every chip when they fit on two lines", () => {
    renderWithProviders(<RecipientChips names={NAMES.slice(0, 6)} />);

    expect(screen.getAllByRole("listitem")).toHaveLength(6);
    expect(screen.queryByRole("button", { name: /more recipients/ })).not.toBeInTheDocument();
  });

  it("limits the chips to two lines and expands the rest on request", async () => {
    renderWithProviders(<RecipientChips names={NAMES} />);

    // Six fit on two lines; one makes room for "+ n".
    const more = screen.getByRole("button", { name: "Show 3 more recipients" });
    expect(more).toHaveTextContent("+ 3");
    expect(screen.getAllByRole("listitem")).toHaveLength(6);

    await userEvent.click(more);

    expect(screen.getAllByRole("listitem")).toHaveLength(NAMES.length);
  });
});

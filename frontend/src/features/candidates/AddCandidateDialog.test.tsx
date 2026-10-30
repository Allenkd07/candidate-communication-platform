import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { jsonResponse, renderWithProviders } from "@/test/render";

import { AddCandidateDialog } from "./AddCandidateDialog";

function renderDialog() {
  const onClose = vi.fn();
  const onAdded = vi.fn();
  renderWithProviders(<AddCandidateDialog open onClose={onClose} onAdded={onAdded} />);
  return { onClose, onAdded };
}

async function fillIn(name: string, phone: string, email: string) {
  // The dialog focuses the name field when its open transition ends.
  await waitFor(() => expect(screen.getByLabelText(/candidate name/i)).toHaveFocus());
  await userEvent.type(screen.getByLabelText(/candidate name/i), name);
  await userEvent.type(screen.getByLabelText(/mobile number/i), phone);
  await userEvent.type(screen.getByLabelText(/email/i), email);
}

const addButton = () => screen.getByRole("button", { name: /add candidate/i });

describe("AddCandidateDialog", () => {
  it("keeps the button disabled until every field has a value", async () => {
    renderDialog();
    expect(addButton()).toBeDisabled();

    await fillIn("Taylor Swift", "9876543210", "taylor@example.com");

    expect(addButton()).toBeEnabled();
  });

  it("explains invalid input before calling the API", async () => {
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    renderDialog();

    await fillIn("T", "12", "not-an-email");
    await userEvent.click(addButton());

    expect(await screen.findByText("Enter at least 2 characters.")).toBeInTheDocument();
    expect(screen.getByText("Enter a valid mobile number.")).toBeInTheDocument();
    expect(screen.getByText("Enter a valid email address.")).toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalled();
  });

  it("shows a server field error next to its input", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        jsonResponse(409, {
          error: {
            code: "duplicate_candidate",
            message: "A candidate with this mobile number already exists.",
            fields: { phone: ["A candidate with this mobile number already exists."] },
          },
        }),
      ),
    );
    const { onClose } = renderDialog();

    await fillIn("Taylor Swift", "9876543210", "taylor@example.com");
    await userEvent.click(addButton());

    expect(await screen.findByText("A candidate with this mobile number already exists.")).toBeInTheDocument();
    expect(screen.getByLabelText(/mobile number/i)).toHaveAttribute("aria-invalid", "true");
    expect(onClose).not.toHaveBeenCalled();
  });

  it("closes and announces the new candidate on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        jsonResponse(201, {
          id: "3f1c5a8e-0000-4000-8000-000000000001",
          code: "A1B2C3",
          full_name: "Taylor Swift",
          phone: "+919876543210",
          email: "taylor@example.com",
          created_at: "2026-10-30T10:00:00Z",
        }),
      ),
    );
    const { onClose, onAdded } = renderDialog();

    await fillIn("Taylor Swift", "9876543210", "taylor@example.com");
    await userEvent.click(addButton());

    expect(await screen.findByText("Taylor Swift added successfully")).toBeInTheDocument();
    expect(onAdded).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });
});

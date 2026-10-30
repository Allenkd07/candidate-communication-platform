import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { MessageStatus } from "@/lib/api/types";
import { renderWithProviders } from "@/test/render";

import { StatusChip } from "./StatusChip";

describe("StatusChip", () => {
  it.each<[MessageStatus, string]>([
    ["scheduled", "Scheduled"],
    ["queued", "Queued"],
    ["sent", "Sent"],
    ["delivered", "Delivered"],
    ["read", "Read"],
    ["failed", "Failed"],
  ])("labels %s as %s", (status, label) => {
    renderWithProviders(<StatusChip status={status} />);

    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it("shows the failure reason on hover", async () => {
    renderWithProviders(<StatusChip status="failed" failureReason="Handset unreachable" />);

    await userEvent.hover(screen.getByText("Failed"));

    expect(await screen.findByRole("tooltip")).toHaveTextContent("Handset unreachable");
  });
});

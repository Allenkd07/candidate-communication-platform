import { expect, test } from "@playwright/test";

/** A random Indian mobile number ending in 7, so never a simulator test number (…0000–…4444). */
function uniqueMobile(): string {
  const middle = String(Math.floor(Math.random() * 1e8)).padStart(8, "0");
  return `9${middle}7`;
}

test("add a candidate, message them and see it delivered in their history", async ({ page }) => {
  // Names allow letters only: the timestamp's digits are spelled as letters.
  const suffix = String(Date.now())
    .slice(-6)
    .replace(/\d/g, (digit) => String.fromCharCode(97 + Number(digit)));
  const name = `Playwright Candidate ${suffix}`;
  await page.goto("/");

  await page.getByRole("button", { name: "Add candidate" }).click();
  await page.getByLabel(/Candidate Name/).fill(name);
  await page.getByLabel(/Mobile Number/).fill(uniqueMobile());
  await page.getByLabel(/Email/).fill(`${Date.now()}@e2e.example.com`);
  await page.getByRole("dialog").getByRole("button", { name: "Add candidate" }).click();
  await expect(page.getByText(`${name} added successfully`)).toBeVisible();

  await page.getByRole("checkbox", { name: `Select ${name}` }).check();
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.getByText("1 Recipient")).toBeVisible();
  await page.getByPlaceholder("Type or paste here...").fill("Your interview is confirmed.");
  await page.getByRole("button", { name: "Send message" }).last().click();

  await expect(page.getByText("Message sent to 1 candidate")).toBeVisible();
  await expect(page.getByText("1 read")).toBeVisible();
  await page.getByRole("button", { name: "Done" }).click();

  await page.getByRole("button", { name }).click();
  const history = page.getByRole("presentation").filter({ hasText: "Candidate ID:" });
  await expect(history.getByText("Your interview is confirmed.")).toBeVisible();
  await expect(history.getByText("Read")).toBeVisible();
  await history.getByRole("button", { name: "Close" }).click();

  await page.getByRole("checkbox", { name: `Select ${name}` }).check();
  await page.getByRole("button", { name: "Delete candidate" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Delete candidate" }).click();
  await expect(page.getByText("Candidate deleted successfully")).toBeVisible();
});

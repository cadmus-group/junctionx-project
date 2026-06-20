import { expect, test } from "@playwright/test";

const MISSION_NAME = "E2E Inspection Mission";

test("primary demo flow: dashboard -> map -> transformer -> customer -> mission -> outcome", async ({
  page,
}) => {
  // 0. Sign in as operator (has Command Center, Risk Map & Inspections in nav).
  await page.goto("/login");
  await page.getByLabel("Username").fill("operator");
  await page.getByLabel("Password").fill("demo");
  await page.getByRole("button", { name: "Sign in" }).click();

  // 1. Command Center
  await expect(page.getByRole("heading", { name: "Command Center" })).toBeVisible();
  await expect(page.getByText("Unexplained loss")).toBeVisible();

  // 2. Risk Map (legend confirms the map initialized)
  await page.getByRole("link", { name: "Risk Map" }).click();
  await expect(page).toHaveURL(/\/map/);
  await expect(page.getByText("Risk score")).toBeVisible();

  // 3. Select a transformer via the URL-addressable selection, open its twin.
  await page.goto("/map?selected=tx-001");
  await expect(page.getByText("Transformer digital twin")).toBeVisible();
  await page.getByRole("link", { name: /Open digital twin/i }).click();

  // 4. Transformer reconciliation shows the showcase unexplained loss.
  await expect(page).toHaveURL(/\/assets\/transformers\/tx-001/);
  await expect(page.getByText("Energy reconciliation")).toBeVisible();
  await expect(page.getByText("Unexplained loss")).toBeVisible();

  // 5. Open the critical customer investigation.
  await page.goto("/customers/cust-0001");
  await expect(page.getByText("Why this score")).toBeVisible();
  await expect(page.getByText(/human inspection/i)).toBeVisible();

  // 6. Add the customer to a new inspection mission.
  await page.getByRole("button", { name: /Add to inspection mission/i }).click();
  await page.getByLabel("New mission name").fill(MISSION_NAME);
  await page.getByRole("button", { name: "Add case" }).click();
  await expect(page.getByText(/Case added to the mission queue/i)).toBeVisible();
  await page.getByRole("button", { name: "Close" }).click();

  // 7. Open the mission and submit an outcome for the queued case.
  await page.getByRole("link", { name: "Inspections" }).click();
  await page.getByRole("link", { name: MISSION_NAME }).click();
  await expect(page.getByText("cust-0001")).toBeVisible();

  await page.getByRole("button", { name: "Outcome" }).first().click();
  await page.getByLabel("Outcome").selectOption("confirmed_meter_fault");
  await page.getByLabel("Estimated recovered (kWh)").fill("1230");
  await page.getByRole("button", { name: "Submit outcome" }).click();

  await expect(page.getByText("Resolved")).toBeVisible();
});

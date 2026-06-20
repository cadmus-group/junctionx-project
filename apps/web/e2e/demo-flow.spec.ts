import { expect, test } from "@playwright/test";
import {
  authenticate,
  resolveShowcase,
  TOKEN_STORAGE_KEY,
  type ShowcaseIds,
} from "./fixtures/showcase";

const MISSION_NAME = "E2E Inspection Mission";

let showcase: ShowcaseIds;
let accessToken: string;

test.beforeAll(async ({ request }) => {
  accessToken = await authenticate(request);
  showcase = await resolveShowcase(request, accessToken);
});

test.beforeEach(async ({ page }) => {
  await page.addInitScript(
    ([tokenKey, token, userKey, user]) => {
      window.localStorage.setItem(tokenKey, token);
      // Satisfy the auth gate (RequireAuth reads the stored user + role).
      window.localStorage.setItem(userKey, user);
    },
    [
      TOKEN_STORAGE_KEY,
      accessToken,
      "gridtrace.user",
      JSON.stringify({ id: "demo-operator", name: "Grid Operations Lead", role: "operator" }),
    ] as const
  );
});

test("primary demo flow: dashboard -> map -> transformer -> customer -> mission -> outcome", async ({
  page,
}) => {
  const { transformerId, customerId, externalRef } = showcase;

  // 1. Command Center
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Command Center" })).toBeVisible();
  await expect(page.getByText("Unexplained loss")).toBeVisible();

  // 2. Risk Map (legend confirms the map initialized)
  await page.getByRole("link", { name: "Risk Map" }).click();
  await expect(page).toHaveURL(/\/map/);
  await expect(page.getByText("Risk score")).toBeVisible();

  // 3. Select showcase transformer via URL-addressable selection, open its twin.
  await page.goto(`/map?selected=${transformerId}&selectedType=transformer`);
  await expect(page.getByText("Transformer digital twin")).toBeVisible();
  await page.getByRole("link", { name: /Open digital twin/i }).click();

  // 4. Transformer reconciliation shows the showcase unexplained loss.
  await expect(page).toHaveURL(new RegExp(`/assets/transformers/${transformerId}`));
  await expect(page.getByText("Energy reconciliation")).toBeVisible();
  await expect(page.getByText("Unexplained loss")).toBeVisible();

  // 5. Open the critical customer investigation.
  await page.goto(`/customers/${customerId}`);
  await expect(page.getByText("Why this score")).toBeVisible();
  await expect(page.getByText(externalRef)).toBeVisible();
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
  await expect(page.getByText(customerId)).toBeVisible();

  await page.getByRole("button", { name: "Outcome" }).first().click();
  await page.getByLabel("Outcome").selectOption("confirmed_meter_fault");
  await page.getByLabel("Estimated recovered (kWh)").fill("1230");
  await page.getByRole("button", { name: "Submit outcome" }).click();

  await expect(page.getByText("Resolved")).toBeVisible();
});

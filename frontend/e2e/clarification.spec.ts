import { expect, test, type Page } from "@playwright/test";

const sellerEmail = process.env.E2E_SELLER_EMAIL ?? "";
const sellerPassword = process.env.E2E_SELLER_PASSWORD ?? "";
const clientEmail = process.env.E2E_CLIENT_EMAIL ?? "";
const clientPassword = process.env.E2E_CLIENT_PASSWORD ?? "";

async function signIn(page: Page, seat: "Studio" | "Client", email: string, password: string) {
  await page.goto("/signin");
  await page.getByRole("button", { name: seat, exact: true }).click();
  await page.fill("#account-email", email);
  await page.fill("#account-password", password);
  await page
    .getByRole("button", {
      name: seat === "Studio" ? "Sign in to the studio" : "Sign in as a client",
    })
    .click();
  await page.waitForURL(seat === "Studio" ? "**/console" : "**/briefs");
}

test("manual clarification keeps the quote and payment flow alive without model or PayPal credentials", async ({
  browser,
}) => {
  expect(sellerEmail, "E2E_SELLER_EMAIL must be set").not.toBe("");
  expect(sellerPassword, "E2E_SELLER_PASSWORD must be set").not.toBe("");
  expect(clientEmail, "E2E_CLIENT_EMAIL must be set").not.toBe("");
  expect(clientPassword, "E2E_CLIENT_PASSWORD must be set").not.toBe("");

  const sellerContext = await browser.newContext();
  const clientContext = await browser.newContext();
  const seller = await sellerContext.newPage();
  const client = await clientContext.newPage();

  try {
    await signIn(client, "Client", clientEmail, clientPassword);
    await client.goto("/start");
    await client.fill("#client-name", "Smoke Test Client");
    await client.fill("#client-business", "Smoke Test Studio");
    await client.fill("#client-email", clientEmail);
    await client.fill(
      "#client-brief",
      "We need a one page launch site with a link to our existing ordering tool. " +
        "Our budget is $500 and we would like it live in three weeks. " +
        "We do not have photos or copy ready yet.",
    );
    await client.fill("#client-budget", "500");
    await client.getByRole("button", { name: "Send brief" }).click();

    await client.waitForURL(/\/briefs\/[0-9a-f-]{36}$/);
    const briefId = client.url().split("/").pop() ?? "";
    expect(briefId).not.toBe("");

    await signIn(seller, "Studio", sellerEmail, sellerPassword);
    await seller.goto(`/requirements/${briefId}`);
    await expect(seller.getByText("What the studio needs to clarify")).toBeVisible();

    // Model draft without credentials: explicit error, no crash.
    await seller.getByRole("button", { name: "Draft with the model" }).click();
    await expect(seller.getByText("model_not_configured")).toBeVisible();
    await expect(
      seller.getByText("Set MODEL_API_KEY and MODEL_NAME in .env to draft with the model."),
    ).toBeVisible();

    // Manual clarification is an explicit, persisted exception.
    await seller.fill(
      "#manual-clarification-note",
      "Model is not configured; I checked budget, deadline, pages and features by hand.",
    );
    await seller.selectOption("#manual-clarification-reason", "model_not_configured");
    await seller.getByRole("button", { name: "Record manual clarification" }).click();
    await expect(seller.getByText("Manual, not AI-assisted", { exact: true })).toBeVisible();
    await expect(seller.getByText("Confirmed", { exact: true })).toBeVisible();

    // Re-extraction is gated by an explicit confirmation; Cancel sends nothing.
    let extractionRequests = 0;
    seller.on("request", (request) => {
      if (request.method() === "POST" && request.url().includes("/extractions")) {
        extractionRequests += 1;
      }
    });
    await seller.getByRole("button", { name: "Draft with the model" }).click();
    await expect(seller.getByText(/This revision already has a clarification/)).toBeVisible();
    await seller.getByRole("button", { name: "Cancel", exact: true }).click();
    await expect(seller.getByText(/This revision already has a clarification/)).toHaveCount(0);
    expect(extractionRequests).toBe(0);

    // Price a scope: the confirmed clarification must not block quote creation.
    await seller.fill("#scope-label", "One-page launch with external ordering");
    await seller.getByRole("button", { name: "Price this scope" }).click();
    await expect(seller.getByText("One-page launch with external ordering")).toBeVisible();

    const draftQuote = seller.getByRole("button", { name: "Draft quote" });
    await expect(draftQuote).toBeEnabled();
    await draftQuote.click();
    await seller.waitForURL(/\/quotes\/[0-9a-f-]{36}$/);

    await seller.getByRole("button", { name: "Review and issue" }).click();
    await expect(seller.getByText(/Reviewed .* waiting for the client to confirm/)).toBeVisible();

    // The client confirms the reviewed version.
    await client.goto(`/briefs/${briefId}`);
    await expect(client.getByText("The version you confirm")).toBeVisible();
    await client.getByRole("button", { name: "Confirm this version" }).click();
    await expect(client.locator("article").getByText("Confirmed", { exact: true })).toBeVisible();

    // PayPal is deliberately unconfigured: the UI must say why and keep the
    // quote confirmed instead of showing a blank page or a stuck Verifying.
    await client.getByRole("button", { name: "Continue to PayPal" }).click();
    await expect(client.getByText(/paypal_not_configured/)).toBeVisible();
    await expect(client.locator("article").getByText("Confirmed", { exact: true })).toBeVisible();
    await expect(client.getByText("Verifying")).toHaveCount(0);
  } finally {
    await sellerContext.close();
    await clientContext.close();
  }
});

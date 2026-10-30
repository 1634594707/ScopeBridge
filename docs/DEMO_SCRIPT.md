# Demo script — 3 minutes, two paths

Two recordings, both under three minutes. Path A is the sale that works; Path B is the
failure that does not get stuck. Record them separately so a single mistake does not cost
the whole take.

Numbers below are the real values from the seeded demo, not placeholders.

---

## Path A — brief to paid (2:40)

| Time | Screen | Action | English subtitle |
| --- | --- | --- | --- |
| 0:00–0:15 | `/` | Land on the home page; hover the specimen card, do not scroll | "Freelancers lose money in the gap between a vague request and a signed scope." |
| 0:15–0:40 | `/start` | Submit the coffee-shop brief: budget 500, three weeks, no assets | "The client writes it the way they would in an email. No forms to translate." |
| 0:40–1:05 | `/console` → requirement | Press **Draft with the model**; wait for facts and two options | "The model reads the brief and returns five facts — it never sets a price." |
| 1:05–1:25 | same | Point at "As briefed $700 / cannot deliver" then "One-page launch $500 / deliverable" | "The server prices both options. The over-budget one stays visible with its exact violation." |
| 1:25–1:40 | same | **Use this scope** → **Price this scope** → **Draft quote** | "The studio adopts the narrowed scope and issues a quote line by line." |
| 1:40–1:55 | `/quotes/:id` | Scroll the line items; open the rule sidebar; press **Review and issue** | "Every amount points at the rule that priced it and the message that justified it." |
| 1:55–2:15 | `/r/:token` | Client picks the scope, presses **Confirm this version**, then **Continue to PayPal** | "The client confirms one exact version. Confirming freezes it." |
| 2:15–2:35 | PayPal sandbox → back to `/pay/:id` | Approve as the sandbox buyer; the return page confirms automatically | "Returning is not proof — the server confirms the capture with PayPal, then locks the order." |
| 2:35–2:40 | `/pay/:id` | Show the order summary, then **Back to your brief** | "Amount, order and payer are frozen into one read-only snapshot." |

---

## Path B — the payment that never returned an order id (1:30)

Use a second quote so Path A stays intact.

| Time | Screen | Action | English subtitle |
| --- | --- | --- | --- |
| 0:00–0:15 | `/console` → requirement | Open the second brief, show the quote is confirmed | "Same flow, but this time PayPal never answered." |
| 0:15–0:30 | Payments card | Show `RECONCILING`, `order pending`, `create_unknown` | "The attempt is parked, not guessed. The quote stays locked." |
| 0:30–0:55 | Payments card | Press **Retry create**; the order id appears | "One retry with the same request id: PayPal returns the order it may already have made." |
| 0:55–1:15 | Payments card | Press **Close**; type the note; confirm | "If it still fails, a human checks PayPal and closes the attempt with a written reason." |
| 1:15–1:30 | Requirement page | Quote is `CONFIRMED` again; start a new attempt | "The quote unlocks only after that check. Nothing is refunded, because nothing was charged." |

---

## Talking points for the Devpost text (not spoken)

- PayPal Orders v2 is used for real: create → approve → capture, plus query for recovery.
- The amount is always read from the confirmed quote on the server; the client sends no money.
- The model returns facts only; candidate scopes and prices are computed by the server, and the
  evaluation report compares that against letting the model quote directly.
- 19 fixed cases, one run each (reported with denominator): pipeline parsed 19/19 and produced
  6 original-fit options, 6 narrowed options and 7 honest "no solution" answers; the one-shot
  baseline parsed 18/19 and made 2 claims the rules reject.
- Known limits: sandbox only, no webhooks, recovery is seller-triggered, no refunds.

## Recording notes

- Window 1440×900, browser zoom 100%, hide bookmarks bar.
- Start the API and `vite preview` before recording; `.env` must hold the sandbox credentials.
- Reset the demo data with `uv run python -m app.seed` only if the quote is still `CONFIRMED`;
  do not re-seed after Path A if you want to reuse the same order.
- English captions are burned in; the spoken language can be Chinese.

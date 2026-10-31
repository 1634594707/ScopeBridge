# Agent Note: Seller sessions and client tokens use two non-reusable identity paths, with boundaries fixed by a STRIDE pass

Status: implemented

## Problem

One set of pages serves two kinds of people: the provider manages every requirement, while a client
must only see the one they are authorised to see. If a single middleware "accommodates" both
identities, implicit branches inevitably appear in permission checks, and any missed branch becomes
unauthorised quote access or confirming on someone else's behalf.

## Decision

The two paths are physically separated and share no middleware:

- **Provider**: `POST /api/session` password sign-in (Argon2id verification); the server-side
  `seller_sessions` table stores the SHA-256 digest of the token plus a CSRF token, and the browser
  only receives an HttpOnly + SameSite=Lax cookie; every write goes through `require_csrf`, which
  checks `X-CSRF-Token`. Failed sign-ins are throttled per email at 5 attempts per 15 minutes,
  returning 429 beyond that.
- **Client**: `POST /api/requirements` generates a 32-byte random token; only its SHA-256 digest is
  stored, bound to a single requirement. The client sends it in the `X-Customer-Token` header; the
  token never appears in any API path.
- **Unified error body** `{code, message, details?}` — no raw exceptions, SQL, paths or token
  fragments; database unavailability is a uniform 503; unauthorised is always 403 and missing is
  always 404, never revealing whether a resource exists.
- **Response headers**: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy: no-referrer`, `Cache-Control: no-store`.

STRIDE mapping:

| Category | Scenario | Current state |
| --- | --- | --- |
| Spoofing | Password stuffing | Argon2id + failure throttling 5/15min + constant-time comparison; no MFA (accepted for the demo) |
| Tampering | Front-end amount edits | Amounts are computed only by the server's `price_scope`; the client submits only a scope; quote versions are immutable once created — a change creates a new `quote_number` |
| Tampering | Concurrent overwrite | `expected_revision` CAS; conflicts return 409 |
| Repudiation | Later denial | Messages carry author and revision; quotes carry `reviewed_by/reviewed_at/confirmed_at`; no separate audit table (accepted for the demo) |
| Information disclosure | Client token leak | Only digests stored, bound to one requirement, `Referrer-Policy: no-referrer`; the token still appears briefly in the URL — the front end stores it in sessionStorage after first read and switches to the header |
| Denial of service | Flooding the public intake | Sign-in is throttled; `POST /api/requirements` is not throttled (accepted for a local demo; must be added before any public deployment) |
| Elevation of privilege | Cross-seller reads | `load_for_seller` checks `seller_id`; cross-account access returns 403; client endpoints always resolve the token first, then verify resource ownership |

## Alternatives considered

- **Unified session + role field**: the strongest case is one sign-in covering both user kinds and a
  single auth state on the front end. Rejected because clients should not have accounts at all, and
  the blast radius of a leaked token must be limited to a single requirement; shared middleware
  would turn "can a client call /api/quotes/{id}/review" into a branch you can only confirm by
  reading code.
- **JWT-borne identity**: the strongest case is no lookups and easy horizontal scaling. Rejected
  because tokens cannot be revoked immediately and algorithm confusion plus key rotation must be
  handled; a single-process demo is simpler with a server-side session table, and sign-out is
  effective immediately.
- **Client token as a URL query parameter**: the strongest case is an intuitive shareable link.
  Rejected because the token would land in access logs, Referer headers and browser history; it is
  read from the path once and converted to a header, after which the path no longer appears in
  subsequent API calls.

## Consequences

- Benefit: anyone can tell from the router dependencies which identity a endpoint belongs to;
  unauthorised-access tests (another seller, forged token) are explicit cases.
- Benefit: neither tokens nor passwords exist in plaintext in the database; a database leak is not a
  session leak.
- Cost: the client must send the header on every request, and the front end needs one
  `customerToken` storage helper; deep links other than `/r/{token}` require re-entry.
- Cost: the public intake has no rate limit; this must be added before any public demo — it is
  stated in the README's known limitations.

## Testing

`backend/tests/test_api_auth.py` covers wrong passwords, throttling, session round-trips, missing
CSRF, unknown client tokens and cross-seller reads; `test_api_quote_flow.py` covers unreviewed
quotes cannot be confirmed, duplicate confirmation 409, stale revision writes 409.

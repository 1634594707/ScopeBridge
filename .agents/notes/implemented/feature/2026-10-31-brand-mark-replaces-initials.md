# Agent Note: The brand mark becomes a graphic mark, replacing the "SB" letter monogram

Status: implemented

## Problem

The sidebar, top bar and browser tab had been using the letters "SB" in a pine-green square. The
monogram reads awkwardly and carries no product meaning: it says nothing about "scope being framed"
or "the closing line being locked". A letter mark also needs extra explanation outside English
contexts, while what ScopeBridge actually wants to emphasise is exactly three things — rules price
it, humans review it, the client confirms that exact version.

## Decision

**Replace the letter monogram with a graphic mark, and ship vector geometry rather than a generated
bitmap.**

- Graphic semantics: four drafting corner ticks = the framed working scope (scope); one horizontal
  closing line = the agreement line after pricing; one solid square at the end of the line = the
  single version that was locked and confirmed.
- Assets and placement:
  - `frontend/public/favicon.svg` — pine-green rounded square (rx=5) with a paper-white mark
    reversed out, for the browser tab.
  - `frontend/public/logo-mark.svg` — pine-green mark on a transparent background, for direct
    reference from the README and other documents.
  - `frontend/src/components/BrandMark.tsx` — React components. `BrandMark` follows the text colour
    via `currentColor`; `BrandTile` is the pine-green square version used by the `AppShell` sidebar
    and top bar; the landing page's eyebrow row also switched to `BrandMark`.
- Geometry: one path in a 48-unit coordinate system (corner-tick stroke 5, closing-line stroke 3,
  square 8×8), uniformly inset into a 32-unit canvas with
  `translate(16 16) scale(0.56) translate(-24 -24)`. All three assets share the same coordinates and
  scale, so favicon and UI mark proportions cannot drift.
- Colours reuse the existing tokens: pine green `#0F4C45` and paper white `#FAFAF8`;
  `tailwind.config.js` needed no new colours.
- Concept provenance: candidate bitmaps were first generated for concepts only via the user's
  OpenAI-compatible image endpoint (`https://new.orbitix.site`, models `gpt-image-2.5-flare` and
  `gpt-image-2.5-sunburst`) — 7 candidates exploring bridge arches, keystone, drafting corner ticks,
  document with an arc, doorway arch and similar ideas — then hand-written as vector geometry for
  delivery. The endpoint key passed only through environment variables; the generation script lived
  in the system temp directory and was never committed.

## Alternatives considered

1. **Use one generated bitmap as the logo directly**. Strongest case: effortless, and it "looks
   AI-made". Rejected: PNGs blur at 16–32px, stroke weights are inconsistent, and it cannot follow
   the theme colour; in favicon duty the browser would scale the bitmap into mush.
2. **Bridge arch + keystone (the literal reading of "Bridge" in the name)**. Strongest case: the
   closest semantic fit — the keystone maps exactly to "the single confirmed version holds up the
   whole agreement". Rejected: at large sizes it reads as a tunnel or doorway, and the keystone
   square looks like a chimney; shrunk to 18px it becomes "an n and a dot", clearly weaker
   recognition than the corner-tick option.
3. **Keep the monogram, change only the typeface and layout**. Strongest case: zero change, zero
   risk, favicon and UI stay automatically consistent. Rejected: the user had explicitly rejected
   the monogram, and letters cannot carry the "frame the scope / lock the version" storyline.
4. **Change only the favicon; keep SB in the UI**. Strongest case: smallest possible diff. Rejected:
   two different marks in the tab and in the UI looks more unfinished than not changing at all.

## Consequences

- Benefit: the mark remains legible at 16px; favicon, UI tile and standalone asset share one
  proportion; the mark's semantics map one-to-one onto the product storyline (rules price → human
  review → client confirms).
- Cost: two new static assets and one component; the README's repository map gained a line noting
  where the brand assets live.
- Known limitation: the geometry is written out three times (`favicon.svg`, `logo-mark.svg`,
  `BrandMark.tsx`); any future shape change must sync all three or proportions drift. A true single
  source would import the SVG as `?raw` into the bundle — deliberately not done this time.
- Candidate bitmaps are not committed: the repo is only 3.9 MB while the 7 PNGs are about 7 MB; not
  worth it. The generation recipe is recorded in this note and can be reproduced if needed.

## Verification

- `cd frontend && pnpm exec tsc -b` and `pnpm exec vite build` both pass; `favicon.svg` and
  `logo-mark.svg` are present in the build output.
- Loaded the two real SVG files from the repository in headless Chrome and checked proportions and
  legibility at 128 / 32 / 16 / 18px.
- Served `frontend/dist` statically and screenshotted the real landing-page header, confirming the
  top-bar tile mark and the eyebrow-row small mark render correctly.
- `cd backend && uv run pytest -q` and `uv run ruff check .` pass (the change touches no backend
  code, but the full suite runs per repo rules).
- Note verification: `npx tsx .agents/skills/write-notes-like-deepseek/scripts/verify-agent-note-tree.ts`
  and `verify-agent-note-format.ts` pass.

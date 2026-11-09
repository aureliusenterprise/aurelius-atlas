# 7.23 Webapp Sonar findings: real fixes

- **Status:** in review
- **Pull request:** — (this increment's PR)
- **Records:** DD-428 (the Logout button and the language fieldset: native elements over ARIA roles;
  supersedes DD-153's logout-anchor clause and DD-169's `role="group"` clause), CHT-112 (the CSP
  theme-script hash guard). Relies on DD-153 (the mobile burger chrome, unchanged apart from the
  superseded clause), DD-159 (the theme pre-render, unchanged), DD-336 (the combobox listbox
  deviation, kept as written), SPL-06/SPL-07 (the settings controls), SHC-05 (the account dropdown),
  SRH-02/SRH-04/SDX-04 (the search state).

## Scope

The SonarCloud dashboard for the webapp project holds about twenty open findings. This increment
closes them with real fixes. It adds no `NOSONAR` marker and no rule exclusion (the user's
constraint, recorded in DD-428).

Three groups:

- **Code shape (unit-proven, no behaviour change).** Two router calls float their promises (the
  `void` idiom, already the repo convention). One signal spread drops a redundant empty-object
  fallback. One group-merge guard becomes an optional chain. The PNG metadata module swaps the
  byte-pair APIs (`charCodeAt`/`fromCharCode`) for their code-point siblings, uses
  `String#startsWith`, and drops two redundant checks. Four nested ternaries become named methods
  or a module function (the stats count, the lineage name comparator, the loading-bar state, the
  type-name pick). One parameter default replaces a reassignment. The deprecated
  `DATE_PIPE_DEFAULT_TIMEZONE` provider becomes `DATE_PIPE_DEFAULT_OPTIONS` (the same stored zone,
  the same system-zone fallback).
- **Accessible markup (DD-428).** Logout moves from `a role="button"` with hand-wired Enter/Space
  keys to a native `button` (SHC-05). The settings Language control moves from a
  `div role="group"` to a native `fieldset` that keeps its accessible name (SPL-06, DD-169's goal).
  The three browse screens drop the `nav` element that wrapped a search field and a button (it
  marks navigation blocks, not layout). The theme pre-render writes `dataset.theme` in place of
  `setAttribute("data-theme", …)`.
- **The CSP hash guard (CHT-112).** The theme script rides the nginx CSP as a pinned `sha256`, and
  the byte change moved it. Three files carry the hash (the app template, the chart's copy, the
  e2e config). The hash is only correct while it matches `src/index.html`, and nothing tested that.
  A contract test in `tests/test__charts_webapp.py` recomputes it from the HTML and compares all
  three copies.

It does **not** deliver: a fix for the two editor `role="listbox"` lines (DD-336 documents the
deviation on purpose, and its line stays flagged until the server's S6819 `allowedRoles` parameter
lists `listbox` — that Sonar-side change is the real unflag path), changes to spec files (the
analysis excludes `**/*.spec.ts`), a `.sonarignore` (none exists today, none added), or any new
Suppressed/`NOSONAR` line beyond the ones the repo already carries with DD-reason text.

## Semantics

No new rule ids except CHT-112. The paths this increment pins, as stated:

- **CHT-112** (new, proven by `tests/test__charts_webapp.py`): every copy of the webapp nginx
  configuration (the app's `nginx.conf.template`, the chart's `helm/files/nginx.conf.template`,
  `e2e/config/nginx.conf`) pins the CSP `script-src` hash of the inline theme script in
  `src/index.html`. The test recomputes the hash from the HTML source (sha256 over the script
  element's inner bytes, base64) and fails when any copy drifts. The chart twin already pins that
  the chart's copy is a byte copy of the app template (CHT-24), so the guard covers the pair the
  release ships.
- **Logout (SHC-05, DD-428):** the dropdown's Logout is a native `button type="button"` with no
  ARIA role and no key handlers. Enter and Space activate it as they do any button. The click calls
  `keycloak.logout()` once, as before. The `header.component.spec.ts` pair (call once; a rejecting
  logout stays fire-and-forget) and the two e2e suites (the burger menu's Logout entry; the RSL-03
  logout round-trip) drive the button in place of the anchor.
- **Language group (SPL-06, DD-428):** the locale links sit in a native `fieldset` whose accessible
  name stays the section heading's text (`aria-labelledby` rides the heading id). The settings
  panel's labelled-names test queries the fieldset where it queried `[role="group"]`.
- **Date pipe (SPL-07):** the app provides `DATE_PIPE_DEFAULT_OPTIONS` with the stored zone, and no
  zone when nothing is stored, so `DatePipe` falls back to the system zone — the pair
  `app.config.spec.ts` pins.
- **Search state (SRH-02, SRH-04, SDX-04):** the extracted helpers (`applyUrl`'s default parameter,
  `typeNameFor`) keep the pinned behaviour: the URL leads on arrival, a same-text navigation re-runs
  nothing, the bare URL answers with `_ALL_ENTITY_TYPES`, a selection is the comma-joined
  `typeName`. The existing `search-state.spec.ts` suite (updated to the default-parameter call)
  proves it.
- **PNG metadata (LDG-31):** `png-metadata.spec.ts` already pins the CRC check vector, the chunk
  walk, and the metadata round-trip over real bytes. The API swaps keep those green; the code
  points are one-to-one for the module's binary strings (every code ≤ 0xff).

## Java origin

None. This is a code-quality increment over already-ported Aurelius markup (7.11, 7.12, 7.14,
7.22d) and search state (4.2b, 7.4a). The legacy markup form for Logout (an anchor) was a
documented deviation of DD-153, not an Atlas rule; nothing in the Apache Atlas 2.4.0 sources
depends on it, so no parity scenario changes.

## Deviations

No new deviation and no ledger row: nothing observable to the REST API or the ported screen
semantics changes. DD-336's listbox deviation stands as written.

## Acceptance

Scenarios are reviewed as code; the gate is the standard one:

- `npx nx build aurelius-atlas-webapp` — the TS and template type gate.
- `npx nx test aurelius-atlas-webapp -c ci` — the unit suite (554 tests), with the touched specs
  (`header`, `settings-panel`, `app.config`, `search-state`, `png-metadata`/`save-view-as-image`
  consumers) passing unchanged in count.
- `uv run pytest tests/test__charts_webapp.py` — CHT-112 plus the existing twin/limiter contracts.
- e2e: the burger-menu Logout entry test and the RSL-03 logout round-trip (the button locators),
  and the settings suite (the fieldset, the time-zone pair). The full webapp e2e run is the CI
  gate.

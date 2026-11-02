# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md), moved from the [Design
Log](../../../../docs/architecture/conversion/design-log.md). Its
[rules](../../../../docs/architecture/conversion/design-log.md#rules) still apply: an accepted entry is
never edited except its status line, and a changed decision is a new entry that supersedes the old one.

## Entries

### DD-148. The Aurelius brand lands on Bulma 1 tokens, light-forced, legacy metrics pinned

- **Status:** Accepted
- **Increment:** 7.12
- **Date:** 2026-10-21

**Decision.** The Aurelius palette and the legacy chrome metrics ship as
Bulma 1 CSS custom properties in `@aurelius/atlas-brand` (SHM-01..04): the
Aurelius blue as `primary`/`link`, Bulma 0.9.4's greys (`#f5f5f5` light/navbar
bands, `#363636` invert), the blue footer band, BlinkMacSystemFont-first stack,
16px, 1.5 line-height, `#4a4a4a` ink, 4.25rem navbar. They are emitted after
Bulma's own `:root`, on `:root` for the global tokens and on `.navbar`/
`.footer` for the ones Bulma scopes on its components. Light is forced with
`data-theme="light"` on the document root; the brand tokens live outside the
`:root:not([data-theme])` scheme machinery so a future dark scheme keeps them.
The sticky footer is a flex-column body + `.is-tall-container` band
(`flex: 1 1 auto`), the pinned navbar is `is-fixed-top` +
`has-navbar-fixed-top`, navbar content sits in a Bulma `container` (SHM-05).

**Reason.** The legacy (Bulma 0.9.4) baked its look through SASS variables;
the workspace is on Bulma 1, which reads CSS custom properties and defaults to
a different design (Inter, 1rem, turquoise primary, white footer, 3.25rem
navbar) — without the overrides the app renders the wrong brand entirely. Two
Bulma 1 traps found by measurement against the live demo: component-scoped
tokens (`.navbar`/`.footer` re-declare their own background, shadowing
`:root`), and `hsl(var(--h), …)` requiring degree-unit hues (a percentage hue
silently drops every `has-background-*` rule — the demo's `#f5f5f5` band came
out transparent). Light-forcing is Bulma 1's scheme machinery, one attribute;
the brand colours stay scheme-independent so the switch has nothing to
re-brand. The flex-column footer replaces the legacy's
`.is-tall-container{min-height:100vh}`-inside-fixed-padding trick with the
modern equivalent (DD-145's static-navbar reading is superseded — the pinned
navbar is what the demo ships).

**Alternatives.** Stay on the Bulma-1 defaults and re-skin component by
component (the 7.2 status quo): every new surface drifts from the legacy
brand. Port `@models4insight/styles` (DD-126 reversal): a Bulma 0.9.4 theme
package, the dependency the workspace adopted away from. Pin the legacy
`has-background-*` classes only (no tokens): the demo's own utility CSS, and
the token overrides are the one lever — the utilities read the same HSL
triplets.

**Consequences.** The chrome matches the reference demo on every measured
value (SHM-06's e2e scenarios pin them). The theme switch is a later slice:
one attribute (`data-theme`), no re-brand. Bulma utilities read the brand
colours (`has-background-light` = `#f5f5f5`), so 7.4+ surfaces inherit the
look. The greys are Bulma 0.9.4's pair, not Bootstrap's — the brand library's
`$gray-*` stays for the `is-dark` pair (`#363636`).

### DD-149. Critical-CSS inlining is off: the zoneless CSR app never swaps the print sheet

- **Status:** Accepted
- **Increment:** 7.12
- **Date:** 2026-10-21

**Decision.** The webapp's production build sets
`optimization.styles.inlineCritical: false`. The stylesheet loads as a
normal render-blocking `<link>`; nothing is inlined into `index.html`
and no `media="print"` swap is involved.

**Reason.** Angular's critical-CSS inliner (beasties) rewrites the
stylesheet to `media="print"` and ships a script that swaps it back at
load. In this zoneless CSR app the swap never runs (e2e measurement:
every browser, the sheet stayed on `print`, 3,024 rules inert), so the
app rendered from the ~115 rules the inliner had copied into the HTML —
Bulma base styles applied, brand overrides on `.navbar`/`.footer` and
utilities like `has-background-light` did not (transparent bands, no
blue footer). The inliner has no element to inline _for_ in a CSR shell
— `index.html`'s body is the app root and the router content appears
after boot, so "critical" is meaningless here. Dev mode (`optimization:
false`) never showed this, which is what made the demo-match in dev
coexist with broken e2e.

**Alternatives.** Keep inlining and fix the swap script (it is Angular
generated — no supported knob). Load the sheet with a forced
`media="all"` (build emits the print attribute as part of the inliner's
output — off is the supported switch). Serve with SSR/prerender so the
inliner has real content (7.x is a client-rendered SPA; the dashboard
is a separate app).

**Consequences.** First paint ships the full stylesheet (~770 kB
minified, gzip ~90 kB) — the same payload the legacy demo ships. The
e2e suite now measures the CSS the browser actually applies. If LCP
ever matters, re-measure with the inliner enabled in a browser that
executes the swap script before re-enabling.

### DD-150. The sticky footer is the legacy rule verbatim; page content sits on Bulma's grid

- **Status:** Accepted
- **Increment:** 7.12
- **Date:** 2026-10-21

**Decision.** `.is-tall-container` is ported verbatim — `flex: 1 1 auto`
**and** `min-height: 100vh` (the legacy `shell.component.scss`) — so the
outlet band is a full viewport and the footer begins at the fold, off the
first screen. Page content is inset by Bulma's grid, not hand-rolled
margins: the landing wraps in `section.section > div.container` (the
anatomy every legacy routed page uses — `details`, `domains`,
`create-entity` all start with `div.container`), the footer keeps its
`container` (the legacy footer's own anatomy), and the `#f5f5f5` band
behind the content stays full-bleed. SHM-05/SHM-07.

**Reason.** Measured against the live demo: its footer starts at y=1346
in a 900px viewport (band `min-height: 900px` — the footer is never on
the first screen), while the first-cut port (flex-grow only) filled the
band to exactly the fold, pulling the footer into it. And the demo's
landing content is inset on Bulma's responsive grid (box x=56 at 1280,
the navbar brand's column), while the port rendered edge-to-edge. Both
are the legacy's own rules — the port had read `.is-tall-container`
selectively and had not ported the page wrapper at all.

**Alternatives.** Keep flex-grow-only (footer flush at the fold): it
diverges from the demo on the one axis the user measured — "the footer
should always be below the fold". Hand-rolled page padding
(`.is-tall-container { padding: … }`): invents a grid Bulma already
owns; the `container` is responsive (fixed widths per breakpoint, 32px
margins below desktop), a hand-rolled inset is not. `section.hero`
instead of `section.section` (the demo's landing hero is a hero): the
teal hero is the 7.4 search slice, out of scope here.

**Consequences.** The landing matches the demo's measured insets
(box x≈56 at 1280) and the footer is below the fold at any viewport.
The `section > container` wrapper is the pattern for 7.4+ routed pages
(details, search results) — they inherit the grid from their first
element. `min-height: 100vh` on the band means short pages scroll the
footer into view; that is the legacy behaviour the demo shows.

### DD-151. The brand re-emits Bulma 0.9.4's text ramp, not just the body metrics

- **Status:** Accepted
- **Increment:** 7.12
- **Date:** 2026-10-21

**Decision.** SHM-03 covers the whole type ramp, not only the body. The
brand library emits Bulma 0.9.4's neutral greys on Bulma 1's **channels**
(`--bulma-text-h/s/l`, `--bulma-text-strong-*`, `--bulma-text-weak-*`), so
every derived token — `text`, `text-strong`, `text-weak`, the navbar and
dropdown ink chain — resolves to the legacy ramp: `#4a4a4a` body/box/
content ink, `#363636` headings, `#7a7a7a` weak. The weights Bulma 1 moved
are pinned back on the selectors that scope them (`.title`/`.subtitle`
600, `.button` 400) plus `--bulma-strong-weight: 700` and
`--bulma-navbar-item-color: #4a4a4a` (the demo's navbar ink is the body
ink, links and `strong` alike). `.content` is `#4a4a4a` with `#363636`
600 headings. SHM-03.

**Reason.** Reviewing the font story against the live demo: DD-148 pinned
the body (stack, 16px/1.5, `#4a4a4a`) and the chrome bands, and every
body-level value matched — but Bulma 1 re-tinted its whole grey ramp 221
degrees (`text` `#4a5568`, `text-strong` `#2e333d`) and re-weighted the
ramp (title 600→800, strong 700→600, button 400→500). The app rendered
with a blue-grey cast: titles `rgb(46,51,61)` at 800, box ink
`rgb(64,70,84)`, navbar links `#535353`, dropdown ink `#404654` — none of
them the demo's values. The size scale (`is-2` 40px/45, `is-6` 16/18,
dropdown 14px, the 4.25rem bar) was already identical; only the ramp
diverged. Pinning the channels (not the derived tokens) fixes the entire
chain at once, including selectors the brand file does not enumerate.

**Alternatives.** Override each derived token at every use site
(`.title { color }`, `.box { color }`, …): whack-a-mole across Bulma's
long hsl-composed chains (the navbar dropdown composes `h`/`s` from the
scheme with the `text` lightness — enumerating all compositions misses
them, as the first cut did). Pin only the body (DD-148 as landed): the
user-visible difference is exactly what the review found — a blue-grey
app where the demo is neutral grey.

**Consequences.** Every landing text/weight pair is demo-parity, pinned
by `test__type_ramp_matches_the_legacy_page`. The emission is
scheme-independent (channels live outside Bulma's `data-theme` blocks),
so a future dark scheme inherits Aurelius' neutral ramp machinery
unchanged. `--bulma-text-rgb`-style companions are emitted for
`text`/`text-strong`/`text-weak` (consumers read them raw).

### DD-152. The accent ramp: primary stays Bulma teal, the accents take the Bootstrap map

**Decision.** The brand library overrides the **accent** colours, not
primary. `--bulma-primary` keeps Bulma's own teal `#00d1b2` (identical
in 0.9.4 and 1.x — the demo's landing icons, hero buttons and `.is-primary`
fills are teal, measured `rgb(0,209,178)`, hover `rgb(0,196,167)`), with
only `--bulma-primary-invert-l: 100%` pinned: Bulma 1 derives solid-fill
ink from `primary-05-l` (6 % — near-black) where 0.9.4 and the demo use
white. The Bootstrap map the legacy theme applied to its accents is
re-emitted from `$bulma-accent-overrides`: `link` `#0073dd`, `info`
`#17a2b8`, `success` `#28a745`, `warning` `#ffc107`, `danger` `#dc3545`,
each with its value, `-base`/`-rgb` and `h`/`s`/`l` channels, and its
solid-fill ink pinned white — except `warning`, which keeps Bulma's dark
ink (the demo's `btn-warning` text is `rgba(0,0,0,.7)`). The navbar's
hover/active band renders `#f5f5f5` with `#000` ink (the demo's
`.navbar-link:hover`); Bulma 1 derives it from the hero chain and renders
a blue-tinted plate. The plate composes `hsl(navbar-h/s,
navbar-item-background-l + hover-delta, a)`, so the brand neutralises
the `navbar` hue/saturation channels (the DD-151 pattern) and sets the
hover/active deltas to the band grey's 96 % lightness; Bulma 1 has **no**
hover-ink token at all (0.9.4's `navbar-item-hover-color` is gone), so
the black ink rides on a scoped hover rule mirroring Bulma's plate
triggers. SHM-04.

**Reason.** The 7.12 first cut mapped `"primary": $blue` onto
`--bulma-primary` as a placeholder (the shell chrome is blue-banded, so
primary _looked_ like `#0073dd`). Measuring the demo's landing page
shows the icons the user flagged — the business/technical/governance
card glyphs, `has-text-primary` — are Bulma teal `rgb(0,209,178)`, not
blue: `#0073dd` in the legacy theme is `$link` (anchors) and the footer
band, never `$primary`. Bulma 1's defaults for the untouched accents
(its own cyan/green/yellow/red) are likewise not the demo's — the demo
carries the Bootstrap palette, which the legacy `@models4insight/styles`
theme mapped onto Bulma's accents (the same map SHM-04 already uses for
`link`/footer). Fixing primary and leaving the accents on Bulma's
defaults keeps half the deviation.

**Alternatives.** Keep primary `#0073dd` (as landed): every
`has-text-primary`/`is-primary` surface — the landing icons the user
compared side by side — stays blue where the demo is teal. Port all of
Bulma 0.9.4's derived accent tokens (each family emits ~30 variables):
unnecessary, the channel triple plus `-base`/`-rgb`/`-invert-l` covers
what Bulma 1 composes at runtime.

**Consequences.** The landing page's icon highlights match the demo.
`$bulma-token-overrides` shrinks to the four chrome greys; accents have
their own `$bulma-accent-overrides` map (value + ink lightness). The
navbar hover/active emission joins the navbar block (DD-148's "scope on
`.navbar`" pattern), with the one ink rule outside the token machinery —
the first brand rule that must set a state colour Bulma 1 never tokenised.
Pinned by `test__accent_ramp_matches_the_demo`.

### DD-153. The mobile burger chrome: grey burger, blended dropdowns, legacy logout anchor

**Decision.** The brand carries the legacy theme's mobile navbar on Bulma
1: `--bulma-navbar-burger-color: #4a4a4a` with the burger **channels** set
black (the hover/active plate composes them at 10 %/20 % alpha — 0.9.4's
plate is `rgba($black, .1)` over the band, Bulma 1 tints it from link),
and `--bulma-navbar-dropdown-arrow: #000` (the legacy pins
`$navbar-dropdown-arrow: $black`; Bulma 1 derives it from link). The
selected plate (`.is-active`, the locale's current item) lands on
white/`#000` (the demo's measured pair — 0.9.4's, Bulma 1's default is the
link-blue plate). Under `max-width: 1023px` the burger menu's
`.navbar-dropdown` blends into the band (0.9.4 zeroes its
background/colour/padding — Bulma 1's dropdown-item plate rule is **not**
media-scoped, so its items render as white tiles on the grey band) and the
dropdown chevron is hidden (Bulma 1 regression jgthms/bulma#4173: the
`%arrow` placeholder's `:not(.is-arrowless)` display beats the media
rule's plain `.navbar-link::after`). The Logout item is the legacy
`a.navbar-item[role=button]` — navbar ink, no `has-text-danger` (the
legacy shell has none; the dropdown ink chain styles anchors, a
`<button>` keeps the UA's centred text and the dropdown plate's white
tile). SHM-04/SHC-05.

**Reason.** Reviewing the mobile chrome: the burger and its hover plate
rendered Aurelius blue, the logout item sat centred on a white tile
inside the grey menu, and the menu's dropdowns showed as white panels
with blue chevrons. The legacy theme (`.scratch/aurelius`
`libs/styles/src/styles/_theme.scss`) sets exactly four navbar rules —
height, background, dropdown-arrow black, hover `#f5f5f5`/`#000` (DD-152)
— and inherits 0.9.4's defaults for the rest; every mobile deviation is
Bulma 1 changing those defaults (burger/arrow from link, unscoped
dropdown plates, the chevron regression) or the port deviating from the
legacy markup (Logout as a red `<button>`).

**Alternatives.** Restyle the red logout `button` (padding/background
overrides): the legacy ink is navbar grey, not red — the red was never in
the product; the anchor is the legacy element and rides the dropdown's
own ink chain for free. Ship the blue burger (Bulma 1's default): the
demo's chrome is the greys, and the blue plate on the grey band is the
mismatch the review flagged.

**Consequences.** The mobile menu reads as one grey band with grey ink,
as the demo. The media block is the brand's first responsive emission;
the chevron rule documents the upstream regression it mirrors. Pinned by
`test__burger_menu_matches_the_legacy_mobile_chrome`.

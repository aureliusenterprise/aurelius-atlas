# 7.12 Theme, branding and layout

- **Status:** in progress
- **Pull request:** \#103
- **Records:** ADR 053; DD-059 (the brand theme on Bulma 1), DD-060 (critical-CSS inlining off); relies on ADR 018, DD-037, DD-042, DD-056, SHC rules (7.11), UIC rules (7.2)

Part of the [7.0 umbrella](<https://aureliusenterprise.github.io/feat-webapp-theme/architecture/conversion/increments/7-0-webapp-foundation/index.md>), whose rules WBP-01 to WBP-07 this slice inherits and its Acceptance repeats.

## Scope

Make the 7.11 chrome **look like the legacy Aurelius Atlas** — the live demo at `google.aurelius-atlas.com/demo/atlas` is the reference — without porting the legacy `@models4insight/styles` package (DD-037 stands):

- the Aurelius palette on Bulma 1's tokens: the Aurelius blue as primary/link, the blue footer band, the grey chrome bands (SHM-04)
- the legacy body type: Bulma 0.9.4's system font stack, 16px, line-height 1.5, `#4a4a4a` ink — Bulma 1 ships Inter/1rem and renders the app in the wrong type (SHM-03)
- the Aurelius Atlas logo as the navbar brand, sized by the legacy `.logo` rule (max-width 150px, max-height 50px) (SHM-02)
- the legacy navbar anatomy: pinned to the top (`is-fixed-top` + body padding, the 4.25rem bar), content in a `container` (SHM-05)
- the sticky footer: the content band grows to the fold, so the footer sits at the bottom of the viewport on short pages and at the bottom of the document on tall ones (SHM-05)
- light mode forced: Bulma 1 follows the OS scheme, the legacy (Bulma 0.9.4) was light-only, and the app has no theme switch yet (SHM-01)

This slice does **not** deliver: the theme switch itself (a later slice flips the `data-theme` attribute — the brand tokens deliberately live outside the scheme machinery so both schemes keep the Aurelius colours), the navbar search bar and nav buttons (7.4, DD-056), the legacy hero/title colours beyond what the landing slice 7.5 owns.

## Semantics

| Id | Rule |
| --- | --- |
| SHM-01 | The document root carries `data-theme="light"`: the app renders the light scheme under any OS preference. The Aurelius brand colours are emitted outside Bulma's scheme machinery, so they survive a future dark scheme. |
| SHM-02 | The navbar brand is the Aurelius Atlas logo (`assets/aurelius-atlas-logo.png`, from the legacy `libs/assets`), linking `/`, with the app name as its alt text; the ui-lib `Header` sizes it through its `.logo` rule (max-width 150px, max-height 50px) applied via the `logoCssClass` input (default `logo`). |
| SHM-03 | The body type is the legacy Bulma 0.9.4 set: the BlinkMacSystemFont-first system stack, 16px, line-height 1.5, weight 400, ink `#4a4a4a` on white — the values the live demo renders, pinned on Bulma 1's body tokens. |
| SHM-04 | The Aurelius palette lands on Bulma 1's tokens in the brand library: primary/link `#0073dd`; `light`/navbar band `#f5f5f5` with `#363636` invert; footer `#0073dd` with white text (the legacy footer's `has-text-white`). Bulma scopes the navbar/footer tokens on its components, so the overrides are emitted on `.navbar`/`.footer` too. |
| SHM-05 | The chrome's navbar is pinned (`is-fixed-top`, the body padded by the 4.25rem bar via `has-navbar-fixed-top`), its content sits in a Bulma `container` (the legacy navbar anatomy), and the outlet band is the legacy `.is-tall-container`: body is a 100vh flex column, the band grows (`flex: 1 1 auto`), the footer renders at the bottom of the viewport on short pages. |
| SHM-06 | The webapp's dev/e2e pages keep passing every 7.11 chrome scenario (SHC-02..09): the logo brand supersedes SHC-02's name-only brand (the name stays as the logo's alt); the pinned navbar does not cover the landing's top content; the footer keeps its three config values. |

## Aurelius origin

The legacy sources whose rendering this ports (`.scratch/aurelius`):

- `libs/shell/src/lib/header/header.component.{html,scss}` — the pinned `navbar is-fixed-top` inside a `container`, the `.logo` brand sizing
- `libs/shell/src/lib/footer/footer.component.html` — the `has-text-white` level items on the blue footer band
- `libs/shell/src/lib/shell.component.{html,scss}` — `.is-tall-container` (`flex: 1 1 auto`, the sticky-footer content band) and the `has-background-light` page band
- `libs/assets/src/assets/aurelius-atlas-logo.png` — the brand mark
- `@models4insight/styles` (Bulma 0.9.4 theme) — not ported as a package (DD-037); the metrics it ships (system stack, 16px/1.5, 4.25rem navbar, `#f5f5f5` bands, `#0073dd` primary) are the reference values SHM-03/04 pin

The live demo (`google.aurelius-atlas.com/demo/atlas`, version `0.0.0#aad352f`) is the reference: every measured value in Acceptance reads from it.

## Deviations

Against Apache Atlas: none — this is an Aurelius product frame, Atlas has no UI.

Against the Aurelius product, recorded in [design-log](<https://aureliusenterprise.github.io/feat-webapp-theme/architecture/conversion/design-log/index.md>):

- DD-059: the palette lands on Bulma **1** tokens (the legacy shipped Bulma 0.9.4 with SASS variables; Bulma 1 reads CSS custom properties, some scoped on `.navbar`/`.footer`); the sticky footer uses the modern flex-column body (the legacy achieves the same through `.is-tall-container`'s `min-height: 100vh`); the brand greys are Bulma 0.9.4's `#f5f5f5`/`#363636` pair, not Bootstrap's `#f8f9fa`;
- DD-060: the prod build disables critical-CSS inlining — the zoneless CSR app never swaps beasties' `media="print"` sheet back, so the brand rules on `.navbar`/`.footer` (and Bulma utilities) applied in dev but not in the Docker/e2e build; the full stylesheet ships render-blocking instead;
- the theme switch is not ported — light is forced via `data-theme="light"` (SHM-01), the switch is a later slice;
- the legacy navbar's `is-size-4` name next to the logo is not ported: the logo's alt carries the app name (SHM-02).

## Acceptance

- Vitest (`nx test aurelius-atlas-ui -c ci`, `nx test aurelius-atlas-webapp -c ci`):

  - `header/header.component.spec.ts` — logo brand with routerLink/alt (SHM-02), `logoCssClass` applied (default and custom), `fixed` pins the navbar (SHM-05), `container` wraps the navbar content (SHM-05)
  - `shell/header.component.spec.ts` — the Aurelius logo brand (SHM-02, superseding SHC-02's name-only check), pinned navbar (SHM-05)
  - `app.component.spec.ts` — the root frame gains the `.is-tall-container` band (SHM-05), chrome order kept (SHC-01)
- e2e (`nx e2e aurelius-atlas-webapp`), each measured against the demo values:

  - `test__navbar_carries_the_aurelius_logo` — the brand image, 150px cap, links home (SHM-02)
  - `test__body_uses_the_legacy_type_and_ink` — stack, 16px, 24px line, `#4a4a4a` (SHM-03)
  - `test__chrome_bands_carry_the_aurelius_palette` — navbar `#f5f5f5`, footer `#0073dd` white text, pinned 68px bar (SHM-04, SHM-05)
  - `test__footer_sits_at_the_bottom_of_the_fold` — footer bottom ≥ viewport height on the short landing page (SHM-05)
  - `test__app_stays_light_under_a_dark_os_preference` — an emulated `prefers-color-scheme: dark` context renders the light bands (SHM-01)
  - the SHC-02..09 scenarios stay green (SHM-06)
- The dev build renders the reference: logo, 68px pinned grey bar, `#f5f5f5` content band, blue footer at the fold, system-stack 16px text (verified on `nx serve` at :4300 against the demo).
- Purity gate green; example app untouched.

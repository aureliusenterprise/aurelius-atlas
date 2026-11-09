# 9.5e The standalone stack's sign-in theme

- **Status:** done
- **Pull request:** [#291](https://github.com/aureliusenterprise/aurelius-atlas/pull/291)
- **Records:** DD-414; relies on DD-366 (the demo realm), DD-148 and DD-152 (the webapp's brand, 7.12)

The demo realm's sign-in pages wear the Aurelius look: the legacy m4i theme's page, the Aurelius Atlas logo
over one white box on a light band with a teal sign-in button, in the webapp's type and colours. The theme
restyles Keycloak's own login, so every page of the sign-in flow takes the look without templates of its own.

## Scope

The standalone stack in `apps/aurelius-atlas-server/standalone/`: the theme `aurelius` in
`keycloak-themes/aurelius/login/` (its properties, stylesheet, logo and favicon), its mount into the stack's
Keycloak, and the demo realm's `loginTheme`.

Not in scope: the account console, the admin console and the email theme, which keep Keycloak's own; the dev
Keycloak and the chart's realms.

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                  |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SKT-01 | The stack's Keycloak mounts `keycloak-themes/aurelius` read-only as `/opt/keycloak/themes/aurelius`, apart from the realm import, and the demo realm names `aurelius` its login theme                                                                                 |
| SKT-02 | The theme's login extends Keycloak's `keycloak.v2`, keeps its stylesheet and adds `css/aurelius.css` after it, light only: the system type in `#4a4a4a`, the band `#f5f5f5`, the logo over a white box, a teal (`#00d1b2`) full-width sign-in button, links `#0073dd` |
| SKT-03 | The theme's logo and favicon are byte copies of the webapp's `assets/aurelius-atlas-logo.png` and `favicon.ico`                                                                                                                                                       |

## Aurelius origin

The legacy `docker_keycloak` image's theme `m4i` (Keycloak 16): its `login/template.ftl` lays the page out
as a Bulma `hero is-light is-fullheight`, a centred `column is-4` holding the logo and a `box` with the title
and the form, the sign-in button `is-primary is-fullwidth is-large`. Its FreeMarker pages are not ported
(DD-414).

## Deviations

None against Apache Atlas, which ships no Keycloak theme. Against the legacy theme: the Aurelius Atlas logo in
place of the Models4Insight one, and Keycloak's own form fields and messages in place of the Bulma ones.

## Acceptance

- `tests/test__standalone_keycloak_theme.py`: SKT-01 to SKT-03, read from the compose file, the demo realm, the
  theme's properties and stylesheet, and the webapp's assets.
- By hand, the standalone stack: `https://localhost:9000/` leads to the demo realm's sign-in on the light band,
  the logo over the white box and the teal button, at 1280 and 390 pixels wide; a wrong password shows its error
  in the box; `steward` signs in and lands on `/en-US/`.

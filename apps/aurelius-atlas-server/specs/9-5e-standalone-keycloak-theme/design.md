# Design decisions

The `DD-NNN` entries of the increment specified in [`spec.md`](./spec.md). The
[rules](../../../../docs/architecture/conversion/design-log.md#rules) of the design log apply: an accepted
entry is never edited except its status line, and a changed decision is a new entry that supersedes the old
one.

## Entries

### DD-414. The Aurelius sign-in is a stylesheet over Keycloak's own login, not the m4i templates

- **Status:** Accepted
- **Increment:** 9.5e
- **Date:** 2026-11-07
- **Supersedes:** none

**Decision.** The theme `aurelius` extends Keycloak's `keycloak.v2` login and adds one stylesheet that gives it
the legacy m4i page: the logo over a white box on the light band, the teal sign-in button, the webapp's type
and colours. It keeps Keycloak's templates and form fields, and turns dark mode off. Its logo and favicon are
copies of the webapp's.

**Reason.** The m4i theme's FreeMarker pages were written for Keycloak 16 on the `base` theme. Keycloak 26
renders its sign-in through many more pages (passkeys, recovery codes, profile updates), and a page the theme
does not override would fall back to unstyled markup inside the m4i layout. A stylesheet over the maintained
login styles every page, survives Keycloak upgrades, and carries the look in about sixty lines. Light only
follows the webapp (SHM-01).

**Alternatives.**

- The m4i templates ported to Keycloak 26: a copy of every login page to keep in step with each upgrade.
- The m4i theme copied as it is: its pages use the Keycloak 16 template API and break on 26.
- A theme built with Keycloakify: a Node build and a jar for a stylesheet's worth of change.

**Consequences.** The sign-in looks like the legacy one in layout and colour, but its fields and messages are
Keycloak's PatternFly ones, not Bulma's. A Keycloak upgrade that renames the login's classes may need the
stylesheet adjusted; the hand check of 9.5e covers it. The account and admin consoles keep Keycloak's look.

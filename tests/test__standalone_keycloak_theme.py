"""The standalone stack's sign-in and account theme (SKT-01..05, 9.5e, DD-663).

The compose file, the stack's realm and the theme are read as written; the theme's brand assets against the
webapp's own.
"""

import json
import re
from pathlib import Path
from typing import Any

import pytest
from conftest import WORKSPACE, standalone_compose

STACK = WORKSPACE / "docker"
THEME = WORKSPACE / "infra/keycloak/themes/aurelius/login"
ACCOUNT = WORKSPACE / "infra/keycloak/themes/aurelius/account"
WEBAPP = WORKSPACE / "apps/aurelius-atlas-webapp/public"


def _properties(part: Path = THEME) -> dict[str, str]:
    lines = (part / "theme.properties").read_text().splitlines()
    return dict(line.split("=", 1) for line in lines if line and not line.startswith("#"))


@pytest.mark.covers(rules=["SKT-01"])
def test__the_demo_realm_signs_in_on_the_mounted_theme() -> None:
    """Keycloak mounts the theme read-only, apart from the import; the demo realm names it its login theme (SKT-01)."""
    keycloak: dict[str, Any] = standalone_compose()["services"]["keycloak"]
    assert "infra/keycloak/themes/aurelius:/opt/keycloak/themes/aurelius:ro" in keycloak["volumes"]
    realm = json.loads((STACK / "keycloak/aurelius-atlas.json").read_text())
    assert realm["loginTheme"] == "aurelius"
    assert realm["accountTheme"] == "aurelius"


@pytest.mark.covers(rules=["SKT-02"])
def test__the_theme_restyles_keycloak_s_own_login_in_light_mode() -> None:
    """Keycloak's v2 login is the parent, its styles kept and the Aurelius sheet after them; no dark mode (SKT-02)."""
    properties = _properties()
    assert properties["parent"] == "keycloak.v2"
    assert properties["styles"].split() == ["css/styles.css", "css/aurelius.css"]
    assert properties["darkMode"] == "false"
    sheet = (THEME / "resources/css/aurelius.css").read_text()
    assert re.search(r"--aurelius-primary: #00d1b2;", sheet)
    assert re.search(r"--aurelius-link: #0073dd;", sheet)
    for image in re.findall(r'url\("\.\./img/([^"]+)"\)', sheet):
        assert (THEME / "resources/img" / image).is_file()


@pytest.mark.covers(rules=["SKT-03"])
def test__the_theme_s_logo_and_favicon_are_the_webapp_s() -> None:
    """The logo and favicon of the login and the account parts are byte copies of the webapp's (SKT-03)."""
    for part in (THEME, ACCOUNT):
        images = part / "resources/img"
        logo = (images / "aurelius-atlas-logo.png").read_bytes()
        assert logo == (WEBAPP / "assets/aurelius-atlas-logo.png").read_bytes()
        assert (images / "favicon.ico").read_bytes() == (WEBAPP / "favicon.ico").read_bytes()


@pytest.mark.covers(rules=["SKT-04"])
def test__the_account_console_extends_keycloak_s_own_with_the_webapp_s_logo() -> None:
    """Keycloak's v3 account console is the parent, with the Aurelius sheet, the logo and favicon; light only."""
    properties = _properties(ACCOUNT)
    assert properties["parent"] == "keycloak.v3"
    assert properties["styles"].split() == ["css/aurelius.css"]
    assert properties["darkMode"] == "false"
    # The logo link stays host-free (17.2, SPS-01): the browser resolves "/" against the same origin.
    assert properties["logoUrl"] == "/"
    for key in ("logo", "favIcon"):
        assert (ACCOUNT / "resources" / properties[key].lstrip("/")).is_file(), key


@pytest.mark.covers(rules=["SKT-05"])
def test__the_account_console_wears_the_webapp_s_band_ink_teal_and_blue() -> None:
    """The header takes the navbar band and ink; the sidebar is light; teal primary, blue links (SKT-05)."""
    sheet = (ACCOUNT / "resources/css/aurelius.css").read_text()
    for token in ("--aurelius-band: #f5f5f5;", "--aurelius-ink: #4a4a4a;", "--aurelius-primary: #00d1b2;"):
        assert token in sheet
    assert "--aurelius-link: #0073dd;" in sheet
    assert re.search(r"\.pf-v5-c-masthead \{[^}]*--pf-v5-c-masthead--BackgroundColor: var\(--aurelius-band\)", sheet)
    assert re.search(r"\.pf-v5-c-page__sidebar \{[^}]*--pf-v5-c-page__sidebar--BackgroundColor: #fff", sheet)
    assert re.search(r"--pf-v5-c-nav__link--m-current--after--BorderColor: var\(--aurelius-primary\)", sheet)
    assert re.search(r"--pf-v5-c-button--m-primary--BackgroundColor: var\(--aurelius-primary\)", sheet)

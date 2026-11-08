"""The standalone stack's sign-in theme (SKT-01..03, 9.5e).

The compose file, the demo realm and the theme are read as written; the theme's brand assets against the
webapp's own.
"""

import json
import re
from typing import Any

import pytest
import yaml
from conftest import WORKSPACE

STANDALONE = WORKSPACE / "apps/aurelius-atlas-server/standalone"
THEME = STANDALONE / "keycloak-themes/aurelius/login"
WEBAPP = WORKSPACE / "apps/aurelius-atlas-webapp/public"


def _properties() -> dict[str, str]:
    lines = (THEME / "theme.properties").read_text().splitlines()
    return dict(line.split("=", 1) for line in lines if line and not line.startswith("#"))


@pytest.mark.covers(rules=["SKT-01"])
def test__the_demo_realm_signs_in_on_the_mounted_theme() -> None:
    """Keycloak mounts the theme read-only, apart from the import; the demo realm names it its login theme (SKT-01)."""
    keycloak: dict[str, Any] = yaml.safe_load((STANDALONE / "docker-compose.yaml").read_text())["services"]["keycloak"]
    assert "./keycloak-themes/aurelius:/opt/keycloak/themes/aurelius:ro" in keycloak["volumes"]
    realm = json.loads((STANDALONE / "keycloak/demo.json").read_text())
    assert realm["loginTheme"] == "aurelius"


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
    """The logo and favicon are byte copies of the webapp's (SKT-03)."""
    images = THEME / "resources/img"
    assert (images / "aurelius-atlas-logo.png").read_bytes() == (WEBAPP / "assets/aurelius-atlas-logo.png").read_bytes()
    assert (images / "favicon.ico").read_bytes() == (WEBAPP / "favicon.ico").read_bytes()

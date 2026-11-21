"""Rewrite the webapp's form-rules fixture from the server's own rules (WFE-05, DD-805).

Run this after deliberately changing a rule the server owns and the webapp editor copies
(numeric types, cardinality values, the 18.3 constraint names, the description keys): it
re-derives the fixture the client guard reads. The server test
``test__fixture_is_the_vocabulary_the_server_produces`` fails until you do, and the
webapp's ``form-rules.spec.ts`` fails until the client copy follows.
"""

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "apps/aurelius-atlas-server/tests"))

from test__form_rule_vocabulary import FIXTURE, render_fixture  # noqa: E402


def main() -> None:
    """Write the fixture and say so."""
    FIXTURE.write_bytes(render_fixture())
    print(f"wrote {FIXTURE.relative_to(WORKSPACE)}")


if __name__ == "__main__":
    main()

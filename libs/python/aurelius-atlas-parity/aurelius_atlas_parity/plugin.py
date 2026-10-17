"""The pytest plugin: gives each scenario test its endpoints and deviations as test properties (SCN-14; DD-014).

Loaded into every pytest run through the ``pytest11`` entry point.
"""

import pytest

from aurelius_atlas_parity.scenario import Scenario


def pytest_itemcollected(item: pytest.Item) -> None:
    """Add the properties of every scenario a collected test is parametrised with."""
    callspec = getattr(item, "callspec", None)
    if callspec is None:
        return
    for value in callspec.params.values():
        if isinstance(value, Scenario):
            item.user_properties.extend(value.properties())

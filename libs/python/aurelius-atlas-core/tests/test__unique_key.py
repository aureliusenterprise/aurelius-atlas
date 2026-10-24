"""``UniqueKey`` (ENS-05, DD-045), after Atlas's ``PER_TYPE_UNIQUE`` index on ``__u_`` shadow properties."""

from decimal import Decimal

import pytest
from aurelius_atlas_core.unique_key import UniqueKey


@pytest.mark.covers("aurelius_atlas_core.unique_key.UniqueKey.id", rules=["ENS-05"])
def test__a_key_is_one_value_of_one_attribute_of_one_type() -> None:
    """The id is a SHA-256: the same for equal keys, different per type, attribute or value; any length of value."""
    key = UniqueKey("hive_table", "Referenceable.qualifiedName", "db.t@cm")

    assert key.id == UniqueKey("hive_table", "Referenceable.qualifiedName", "db.t@cm").id
    assert len(key.id) == 64
    assert key.id != UniqueKey("hive_db", "Referenceable.qualifiedName", "db.t@cm").id
    assert key.id != UniqueKey("hive_table", "Referenceable.name", "db.t@cm").id
    assert key.id != UniqueKey("hive_table", "Referenceable.qualifiedName", "db.t@cm2").id
    assert UniqueKey("t", "a", Decimal("1.10")).id != UniqueKey("t", "a", Decimal("1.1")).id
    assert len(UniqueKey("t", "a", "x" * 10_000).id) == 64

"""The reflection: an inspector's answers to the table model (DBS-06, DBS-07, DBS-08).

A fake inspector answers every case from memory, including the ones no SQLite database on
this machine can answer — a dialect that carries comments, a foreign key naming no referred
column — so each rule of DBS-06..08 is checked on the exact answer shape.
"""

from typing import Any

import pytest
from aurelius_atlas_db_scanner.reflect import PRIMARY_KEY_MARK, reflect_table


class FakeInspector:
    """The inspector's four reads, answered from the tables handed to it."""

    def __init__(self, tables: dict[tuple[str, str | None], dict[str, Any]]) -> None:
        self._tables = tables
        self.pk_reads: list[tuple[str, str | None]] = []

    def get_columns(self, table_name: str, *, schema: str | None = None) -> list[dict[str, Any]]:
        """The table's columns, as the fake was built."""
        return self._answer(table_name, schema)["columns"]

    def get_pk_constraint(self, table_name: str, *, schema: str | None = None) -> dict[str, Any]:
        """The table's primary key, counted so a test can see the resolution read."""
        self.pk_reads.append((table_name, schema))
        return self._answer(table_name, schema)["pk"]

    def get_foreign_keys(self, table_name: str, *, schema: str | None = None) -> list[dict[str, Any]]:
        """The table's foreign keys, as the fake was built."""
        return self._answer(table_name, schema)["foreign_keys"]

    def get_table_comment(self, table_name: str, *, schema: str | None = None) -> dict[str, Any]:
        """The table comment, or the refusal the fake carries."""
        answer = self._answer(table_name, schema)["comment"]
        if isinstance(answer, Exception):
            raise answer
        return answer

    def _answer(self, table: str, schema: str | None) -> dict[str, Any]:
        return self._tables[(table, schema)]


def _inspector(**tables: dict[str, Any]) -> FakeInspector:
    """A one-schema fake: each table gets columns, pk, foreign keys, and a comment answer."""
    return FakeInspector({(name, None): table for name, table in tables.items()})


@pytest.mark.covers("aurelius_atlas_db_scanner.reflect.reflect_table", rules=["DBS-06"])
def test_the_columns_become_the_fields_with_their_rendered_types() -> None:
    """DBS-06: every column carries its name and the dialect's own rendered type."""
    inspector = _inspector(
        orders={
            "columns": [
                {"name": "id", "type": "INTEGER", "comment": None},
                {"name": "total", "type": "NUMERIC(12,2)", "comment": None},
            ],
            "pk": {"constrained_columns": []},
            "foreign_keys": [],
            "comment": {},
        }
    )
    info = reflect_table(inspector, "orders", None)
    assert [(c.name, c.field_type, c.definition) for c in info.columns] == [
        ("id", "INTEGER", None),
        ("total", "NUMERIC(12,2)", None),
    ]


@pytest.mark.covers("aurelius_atlas_db_scanner.reflect.reflect_table", rules=["DBS-06"])
def test_a_primary_key_column_without_a_comment_carries_the_mark() -> None:
    """DBS-06: the key's columns are marked; the mark is what tells a reader why they are key."""
    inspector = _inspector(
        orders={
            "columns": [{"name": "id", "type": "INTEGER", "comment": None}],
            "pk": {"constrained_columns": ["id"]},
            "foreign_keys": [],
            "comment": {},
        }
    )
    info = reflect_table(inspector, "orders", None)
    assert info.columns[0].definition == PRIMARY_KEY_MARK


@pytest.mark.covers("aurelius_atlas_db_scanner.reflect.reflect_table", rules=["DBS-06"])
def test_a_column_comment_keeps_its_text_and_beats_the_mark() -> None:
    """DBS-06: the operator's comment is the definition; the primary-key mark never overwrites one."""
    inspector = _inspector(
        orders={
            "columns": [{"name": "id", "type": "INTEGER", "comment": "Order number, assigned on checkout"}],
            "pk": {"constrained_columns": ["id"]},
            "foreign_keys": [],
            "comment": {},
        }
    )
    info = reflect_table(inspector, "orders", None)
    assert info.columns[0].definition == "Order number, assigned on checkout"


@pytest.mark.covers("aurelius_atlas_db_scanner.reflect.reflect_table", rules=["DBS-07"])
def test_the_table_comment_becomes_the_definition() -> None:
    """DBS-07: the table's comment rides as the dataset's definition."""
    inspector = _inspector(
        orders={
            "columns": [],
            "pk": {"constrained_columns": []},
            "foreign_keys": [],
            "comment": {"text": "One row per customer order"},
        }
    )
    assert reflect_table(inspector, "orders", None).definition == "One row per customer order"


@pytest.mark.covers("aurelius_atlas_db_scanner.reflect.reflect_table", rules=["DBS-07"])
def test_a_dialect_that_refuses_comments_answers_no_definition() -> None:
    """DBS-07: SQLite's inspector raises on a table comment — the absence is honest, not a failure."""
    inspector = _inspector(
        orders={
            "columns": [],
            "pk": {"constrained_columns": []},
            "foreign_keys": [],
            "comment": NotImplementedError("get_table_comment is not implemented for this dialect"),
        }
    )
    assert reflect_table(inspector, "orders", None).definition is None


@pytest.mark.covers("aurelius_atlas_db_scanner.reflect.reflect_table", rules=["DBS-08"])
def test_a_foreign_key_names_its_ordered_column_pairs() -> None:
    """DBS-08: the constrained and referred columns ride position-aligned, with the referred schema."""
    inspector = _inspector(
        line={
            "columns": [],
            "pk": {"constrained_columns": []},
            "foreign_keys": [
                {
                    "constrained_columns": ["order_id"],
                    "referred_schema": None,
                    "referred_table": "orders",
                    "referred_columns": ["id"],
                }
            ],
            "comment": {},
        }
    )
    key = reflect_table(inspector, "line", None).foreign_keys[0]
    assert (key.constrained_columns, key.referred_table, key.referred_columns) == (("order_id",), "orders", ("id",))


@pytest.mark.covers("aurelius_atlas_db_scanner.reflect.reflect_table", rules=["DBS-08"])
def test_an_empty_referred_position_resolves_against_the_referred_primary_key() -> None:
    """DBS-08: an empty referred position gets the referred table's real key, by position.

    The starting script's "id" guess, fixed.
    """
    inspector = FakeInspector(
        {
            ("line", None): {
                "columns": [],
                "pk": {"constrained_columns": []},
                "foreign_keys": [
                    {
                        "constrained_columns": ["shop_id", "sku"],
                        "referred_schema": "shop",
                        "referred_table": "shops",
                        "referred_columns": [],
                    }
                ],
                "comment": {},
            },
            ("shops", "shop"): {
                "columns": [],
                "pk": {"constrained_columns": ["code", "region"]},
                "foreign_keys": [],
                "comment": {},
            },
        }
    )
    key = reflect_table(inspector, "line", None).foreign_keys[0]
    assert key.referred_columns == ("code", "region")
    assert ("shops", "shop") in inspector.pk_reads


@pytest.mark.covers("aurelius_atlas_db_scanner.reflect.reflect_table", rules=["DBS-08"])
def test_a_position_the_referred_key_cannot_answer_stays_unset() -> None:
    """DBS-08: no primary key, or a key shorter than the position, answers None — the graph drops it."""

    class Missing(FakeInspector):
        def get_pk_constraint(self, table_name: str, *, schema: str | None = None) -> dict[str, Any]:
            if table_name == "ghosts":
                msg = "the referred table is not readable"
                raise RuntimeError(msg)
            return super().get_pk_constraint(table_name, schema=schema)

    inspector = Missing(
        {
            ("line", None): {
                "columns": [],
                "pk": {"constrained_columns": []},
                "foreign_keys": [
                    {
                        "constrained_columns": ["ghost_id"],
                        "referred_schema": None,
                        "referred_table": "ghosts",
                        "referred_columns": None,
                    }
                ],
                "comment": {},
            }
        }
    )
    assert reflect_table(inspector, "line", None).foreign_keys[0].referred_columns == (None,)


@pytest.mark.covers("aurelius_atlas_db_scanner.reflect.reflect_table", rules=["DBS-04", "DBS-08"])
def test_the_door_schema_normalizer_reaches_the_referred_schema() -> None:
    """The referred schema is renormalized the way the door names schemas (DBS-04, DBS-08).

    SQLite's ``main`` becomes the nameless default, so the pair lines up with the scan.
    """
    inspector = _inspector(
        line={
            "columns": [],
            "pk": {"constrained_columns": []},
            "foreign_keys": [
                {
                    "constrained_columns": ["order_id"],
                    "referred_schema": "main",
                    "referred_table": "orders",
                    "referred_columns": ["id"],
                }
            ],
            "comment": {},
        }
    )
    key = reflect_table(
        inspector, "line", None, normalize_schema=lambda name: None if name == "main" else name
    ).foreign_keys[0]
    assert key.referred_schema is None


@pytest.mark.covers("aurelius_atlas_db_scanner.reflect.reflect_table", rules=["DBS-05", "DBS-07"])
def test_a_table_that_answers_no_columns_reflects_as_a_bare_dataset() -> None:
    """DBS-05/DBS-07: an empty table still reflects whole — the scan decides it is field-less."""
    inspector = _inspector(
        empty={
            "columns": [],
            "pk": {"constrained_columns": []},
            "foreign_keys": [],
            "comment": {"text": "A table with nothing in it yet"},
        }
    )
    info = reflect_table(inspector, "empty", None)
    assert (info.columns, info.primary_key, info.foreign_keys, info.definition) == (
        (),
        (),
        (),
        "A table with nothing in it yet",
    )

"""The reflection: an inspector's table to the scan's table model (13.3, DBS-06..08).

The inspector answers dictionaries — columns with rendered types, the primary key, foreign
keys, a table comment — and this module turns one table's answers into the frozen models the
graph builds from: rendered column types as ``fieldType`` (DBS-06), the column comment or the
primary-key mark as ``definition`` (DBS-06), the table comment as the dataset's future
``definition`` (DBS-07), and every constrained column of every foreign key as an ordered pair
with the referred column resolved by position against the referred table's actual primary key
(DBS-08 — the starting script's ``ref_column or "id"`` guess, fixed).

The inspector is a Protocol, so a test hands a fake and answers every rule from memory;
:class:`~aurelius-atlas-db-scanner.database.SqlDatabase` hands it the real
:func:`sqlalchemy.inspect` result.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

PRIMARY_KEY_MARK = "Primary key"
"""The definition a primary-key column carries when it holds no comment of its own (DBS-06)."""


class Inspector(Protocol):
    """The reflection calls of :func:`sqlalchemy.inspect`, as this door uses them (DD-502)."""

    def get_columns(self, table_name: str, *, schema: str | None = None) -> list[dict[str, Any]]:
        """The table's columns: name, type (a live SQLAlchemy type), comment when the dialect reads one."""
        ...

    def get_pk_constraint(self, table_name: str, *, schema: str | None = None) -> dict[str, Any]:
        """The primary key: ``constrained_columns`` in order."""
        ...

    def get_foreign_keys(self, table_name: str, *, schema: str | None = None) -> list[dict[str, Any]]:
        """The foreign keys: constrained and referred columns, referred schema and table."""
        ...

    def get_table_comment(self, table_name: str, *, schema: str | None = None) -> dict[str, Any]:
        """The table comment's ``text``, when the dialect carries comments at all."""
        ...


@dataclass(frozen=True)
class ColumnInfo:
    """One reflected column (DBS-06): the future field's name, type, and definition."""

    name: str
    """The column's own name — the field's ``name`` and qualified-name component."""

    field_type: str
    """The rendered column type, ``str(column["type"])`` (DBS-06): the dialect's own name reads
    back — ``VARCHAR(255)``, ``INTEGER``."""

    definition: str | None = None
    """The column comment when one exists, else the primary-key mark for a key column, else
    ``None`` (DBS-06): a comment keeps its text; the mark never overwrites one."""


@dataclass(frozen=True)
class ForeignKeyInfo:
    """One reflected foreign key as ordered column pairs (DBS-08): the future processes."""

    constrained_columns: tuple[str, ...]
    """The referring table's constrained columns, in the key's own order."""

    referred_schema: str | None
    """The referred table's schema, normalized like the scan names schemas (``None`` = default)."""

    referred_table: str
    """The referred table's own name."""

    referred_columns: tuple[str | None, ...]
    """The referred columns, position-aligned with ``constrained_columns``; a position the
    dialect left empty is resolved against the referred table's primary key (DBS-08), and
    stays ``None`` only when that resolution failed."""


@dataclass(frozen=True)
class TableInfo:
    """One reflected table (DBS-05..08's input): everything the graph needs, nothing more."""

    schema: str | None
    """The schema the table sits in, normalized; ``None`` is the nameless default (DBS-04)."""

    name: str
    """The table's own name — the dataset's ``name`` (DBS-07)."""

    definition: str | None = None
    """The table comment as the dataset's ``definition``, when one exists (DBS-07)."""

    primary_key: tuple[str, ...] = ()
    """The key's constrained columns, in order (DBS-06's mark, DBS-08's resolution source)."""

    columns: tuple[ColumnInfo, ...] = ()
    """The columns, in the inspector's order — the dataset's fields (DBS-06)."""

    foreign_keys: tuple[ForeignKeyInfo, ...] = ()
    """The foreign keys, as ordered column pairs (DBS-08)."""


def reflect_table(
    inspector: Inspector,
    table: str,
    schema: str | None,
    *,
    normalize_schema: Callable[[str | None], str | None] = lambda name: name,
) -> TableInfo:
    """One table's metadata, read through the inspector (DBS-06..08).

    A dialect that carries no table comments (SQLite's inspector refuses
    ``get_table_comment``) answers no definition — the absence is the dialect's, not a failure.
    A foreign key position the dialect leaves empty names the referred table's primary-key
    column in the same position (DBS-08); an unresolvable position stays ``None`` for the
    graph to drop with a notice.

    Args:
        inspector: The live or faked :class:`Inspector`.
        table: The table name to reflect.
        schema: The schema as the door names it (``None`` = the nameless default).
        normalize_schema: Re-normalizes a referred schema the way the door names schemas, so a
            referred ``main`` on SQLite lines up with the scan's ``None`` (DBS-04, DBS-08).

    Raises:
        Exception: whatever the inspector raises on a refused table — the door wraps it into
            :class:`~aurelius-atlas-db-scanner.database.TableReflectionError` (DBS-05).
    """
    primary_key = tuple(inspector.get_pk_constraint(table, schema=schema).get("constrained_columns") or ())
    columns = tuple(
        ColumnInfo(
            name=column["name"],
            field_type=str(column["type"]),
            definition=column.get("comment") or (PRIMARY_KEY_MARK if column["name"] in primary_key else None),
        )
        for column in inspector.get_columns(table, schema=schema)
    )
    foreign_keys = tuple(
        _reflect_foreign_key(inspector, key, normalize_schema)
        for key in inspector.get_foreign_keys(table, schema=schema)
    )
    return TableInfo(
        schema=schema,
        name=table,
        definition=_table_comment(inspector, table, schema),
        primary_key=primary_key,
        columns=columns,
        foreign_keys=foreign_keys,
    )


def _table_comment(inspector: Inspector, table: str, schema: str | None) -> str | None:
    """The table comment (DBS-07), or ``None`` on a dialect that carries none at all."""
    try:
        return inspector.get_table_comment(table, schema=schema).get("text") or None
    except Exception:  # noqa: BLE001 - a dialect without comment support is the absence, not a failure (DBS-07)
        return None


def _reflect_foreign_key(
    inspector: Inspector,
    key: dict[str, Any],
    normalize_schema: Callable[[str | None], str | None],
) -> ForeignKeyInfo:
    """One key, position-aligned and primary-key-resolved (DBS-08)."""
    constrained = tuple(key.get("constrained_columns") or ())
    referred_schema = normalize_schema(key.get("referred_schema"))
    referred_table = str(key.get("referred_table") or "")
    referred = list(key.get("referred_columns") or ())
    referred += [None] * (len(constrained) - len(referred))
    resolved = tuple(
        name if name is not None else _primary_key_at(inspector, referred_schema, referred_table, position)
        for position, name in enumerate(referred)
    )
    return ForeignKeyInfo(constrained, referred_schema, referred_table, resolved)


def _primary_key_at(inspector: Inspector, schema: str | None, table: str, position: int) -> str | None:
    """The referred table's primary-key column at one position (DBS-08), or None.

    No primary key, a missing table, or a key shorter than the position all answer ``None``;
    the graph drops that pair with a notice, because a process end must name two registered
    datasets and a column the scan cannot name belongs to neither end's proof.
    """
    try:
        key = inspector.get_pk_constraint(table, schema=schema)
    except Exception:  # noqa: BLE001 - an unreadable referred key is the None the graph drops (DBS-08)
        return None
    columns = list(key.get("constrained_columns") or ())
    return columns[position] if position < len(columns) else None

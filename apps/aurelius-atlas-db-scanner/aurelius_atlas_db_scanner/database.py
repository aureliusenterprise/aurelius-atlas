"""The database door: connect, schema names, table names, one reflect (13.3, DBS-01..05).

The scan reads the database through SQLAlchemy Core's inspector — ``get_schema_names``,
``get_table_names``, ``get_columns``, ``get_pk_constraint``, ``get_foreign_keys``,
``get_table_comment`` — and nothing else (DD-502): no ``information_schema`` SQL, no vendor
CLI, no product name in the walk. The branches the reflection honestly needs live here, keyed
by the engine's dialect name: the nameless default schema (DBS-04's SQLite case) and the
fixed system-schema set the scan must never register (DBS-04).

The door is a Protocol the unit tests fake (13.1's idiom), so DBS-02..05 run offline; the
real door, :class:`SqlDatabase`, is what the CLI and the e2e open. A database that answers no
connect fails the run with :class:`DatabaseUnreachableError`, naming the URL's host and
database with the password scrubbed by SQLAlchemy's own rendering (DBS-02, DD-506).
"""

import logging
import re
from typing import Protocol, cast

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import SQLAlchemyError

from aurelius_atlas_db_scanner.reflect import Inspector, TableInfo, reflect_table

logger = logging.getLogger(__name__)

WILDCARD = "*"
"""The filter character that stands for any run of characters (DBS-04, DBS-05, KSC-02's rule)."""

SYSTEM_SCHEMAS = frozenset(
    {
        "pg_catalog",
        "information_schema",
        "pg_toast",
        "mysql",
        "sys",
        "performance_schema",
    }
)
"""The dialect metadata schemas a scan must never register (DBS-04). ``pg_`` names are covered
by the prefix rule, not listed one by one."""

SYSTEM_SCHEMA_PREFIX = "pg_"
"""A name starting with this is a Postgres system schema of some kind (DBS-04)."""

NAMELESS_DIALECTS = frozenset({"sqlite"})
"""Dialects whose one default schema carries no usable name (DBS-04): the scan answers ``None``
for it and :attr:`ScannerSettings.schema_name` names its Collection."""

NAMELESS_DEFAULT_SCHEMA = "main"
"""The name SQLite gives its default schema — the one the scan treats as nameless (DBS-04)."""

CONNECT_TIMEOUT_DIALECTS = frozenset({"postgresql", "mysql", "mariadb", "mssql"})
"""Dialects whose driver takes a ``connect_timeout`` connect argument (DBS-02); SQLite's driver
takes its own ``timeout`` instead, and an unknown dialect is left to its driver's default."""


class DatabaseUnreachableError(RuntimeError):
    """The database answered no connect (DBS-02): a run-level failure naming host and database.

    The message carries the URL rendered with the password hidden — SQLAlchemy's own scrubbing,
    so the rule is one call and no regex (DD-506). The credentials never appear.
    """


class TableReflectionError(RuntimeError):
    """The inspector refused one table (DBS-05): a notice and a field-less dataset, not a failure."""


def compile_patterns(names: str) -> list[re.Pattern[str]]:
    """The schema/table patterns of the settings, compiled for a case-insensitive full match.

    Each comma-separated pattern may hold ``*``, which stands for any run of characters; the
    rest of a pattern is literal text. An empty pattern between commas is dropped (DBS-04,
    DBS-05 — the Kafka scanner's filter rule, KSC-02, applied to database names).
    """
    compiled: list[re.Pattern[str]] = []
    for raw in names.split(","):
        pattern = raw.strip()
        if not pattern:
            continue
        body = "".join(".*" if part == WILDCARD else re.escape(part) for part in re.split(r"(\*)", pattern))
        compiled.append(re.compile(f"^{body}$", re.IGNORECASE))
    return compiled


def matches_any(name: str, patterns: list[re.Pattern[str]]) -> bool:
    """Whether a schema or table name matches any of ``patterns`` (DBS-04, DBS-05). Empty matches nothing."""
    return any(pattern.match(name) for pattern in patterns)


def is_system_schema(name: str) -> bool:
    """Whether a schema name is dialect metadata the scan must never register (DBS-04)."""
    lowered = name.lower()
    return lowered in SYSTEM_SCHEMAS or lowered.startswith(SYSTEM_SCHEMA_PREFIX)


class DatabaseDoor(Protocol):
    """What the scan asks of the database (DBS-02..05): names and one reflect, no SQL.

    A test hands a fake and answers every rule from memory; :class:`SqlDatabase` is the real
    door, opening a SQLAlchemy engine on a DSN.
    """

    def open(self) -> None:
        """Connect once: a database that answers nothing fails the run here (DBS-02)."""
        ...

    def close(self) -> None:
        """Release the connection pool, whatever happened to the scan."""
        ...

    def schema_names(self, patterns: list[re.Pattern[str]]) -> list[str | None]:
        """The schemas to scan (DBS-04): the dialect's own, minus the system set, by the patterns.

        Matching the patterns, minus any the dialect refuses to introspect; ``None`` is the nameless default.
        """
        ...

    def table_names(self, schema: str | None, patterns: list[re.Pattern[str]]) -> list[str]:
        """The table names of one schema that match the patterns (DBS-05). Views are not tables."""
        ...

    def reflect(self, schema: str | None, table: str) -> TableInfo:
        """One table's metadata (DBS-06, DBS-07): columns, keys, comment.

        Raises:
            TableReflectionError: the inspector refused this table (DBS-05) — the scan keeps a
                field-less dataset and a notice, and the run completes.
        """
        ...


class SqlDatabase:
    """The real door: one engine on one DSN, read through the Core inspector (DD-502, DD-503).

    The connect timeout is the settings' (DBS-02), handed to the driver as the connect argument
    its dialect accepts; a dialect that names none is left to its driver's default rather than
    guessed at. One DSN per door, one database per run (DD-503).
    """

    def __init__(self, dsn: str, *, connect_timeout_seconds: float) -> None:
        self._url = make_url(dsn)
        self._timeout_seconds = connect_timeout_seconds
        self._engine: Engine | None = None

    @property
    def safe_url(self) -> str:
        """The DSN with its password hidden (DBS-02, DD-506): the only form the job ever prints."""
        return self._url.render_as_string(hide_password=True)

    def open(self) -> None:
        """Build the engine and prove it answers one connect (DBS-02).

        Raises:
            DatabaseUnreachableError: the database answered nothing within the timeout; the
                message names host and database, never the credentials.
        """
        engine = create_engine(
            self._url,
            connect_args=_connect_args(self._url.get_backend_name(), self._timeout_seconds),
        )
        try:
            with engine.connect():
                pass
        except SQLAlchemyError as cause:
            engine.dispose()
            msg = (
                f"the database at {self.safe_url} answered no connect"
                f" (within {self._timeout_seconds:g}s where the driver honours it): {cause}"
            )
            raise DatabaseUnreachableError(msg) from cause
        self._engine = engine

    def close(self) -> None:
        """Dispose of the pool; safe to call before a successful open."""
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None

    def schema_names(self, patterns: list[re.Pattern[str]]) -> list[str | None]:
        """The admitted schemas (DBS-04): system set out, patterns applied, un-introspectable skipped."""
        inspector = inspect(self._require_engine())
        if self._url.get_backend_name() in NAMELESS_DIALECTS:
            return [None] if matches_any("", patterns) else []
        admitted: list[str | None] = []
        for raw in inspector.get_schema_names():
            name = self._normalize(raw)
            if name is not None and is_system_schema(raw):
                logger.debug("skipping system schema %s", raw)
                continue
            if not matches_any(name or "", patterns):
                continue
            if not self._introspectable(inspector, name):
                continue
            admitted.append(name)
        return admitted

    def table_names(self, schema: str | None, patterns: list[re.Pattern[str]]) -> list[str]:
        """The schema's tables that match the patterns (DBS-05); a view is not in ``get_table_names``."""
        inspector = inspect(self._require_engine())
        return [table for table in inspector.get_table_names(schema=schema) if matches_any(table, patterns)]

    def reflect(self, schema: str | None, table: str) -> TableInfo:
        """One table's metadata through the inspector (DBS-06..08's input), or the refusal notice.

        The door's own schema-normalizer rides along, so a foreign key that names the nameless
        dialect's default schema by its internal name lines up with the scan's ``None`` (DBS-08).
        """
        try:
            with self._require_engine().connect() as connection:
                live = inspect(connection)
                return reflect_table(cast("Inspector", live), table, schema, normalize_schema=self._normalize)
        except Exception as cause:
            raise TableReflectionError(str(cause)) from cause

    def _normalize(self, raw: str | None) -> str | None:
        """The dialect's schema name as the scan names it: the nameless default is ``None`` (DBS-04)."""
        if raw is None or raw == "":
            return None
        if self._url.get_backend_name() in NAMELESS_DIALECTS and raw == NAMELESS_DEFAULT_SCHEMA:
            return None
        return raw

    def _introspectable(self, inspector: object, schema: str | None) -> bool:
        """Whether the dialect can read one schema at all (DBS-04's skip): a refusal is a debug notice."""
        try:
            get_table_names = getattr(inspector, "get_table_names")  # noqa: B009 - the inspector is untyped here; the probe is the point
            get_table_names(schema=schema)
        except Exception:  # noqa: BLE001 - the dialect refused the schema; the scan moves on (DBS-04)
            logger.debug("the dialect cannot introspect schema %s — skipped", schema or "")
            return False
        return True

    def _require_engine(self) -> Engine:
        """The open engine; a door read before :meth:`open` is a programming error."""
        if self._engine is None:
            msg = "the database door is closed: call open() first"
            raise RuntimeError(msg)
        return self._engine


def _connect_args(dialect_name: str, timeout_seconds: float) -> dict[str, object]:
    """The driver's connect timeout, spelled the way that driver spells it (DBS-02).

    The dialect branches are DD-502's, keyed by dialect name: Postgres/MySQL/MariaDB/MSSQL
    drivers take ``connect_timeout``, SQLite's takes ``timeout`` (the busy wait), and any other
    dialect keeps its driver's default rather than an argument that could break the connect.
    """
    if dialect_name == "sqlite":
        return {"timeout": timeout_seconds}
    if dialect_name in CONNECT_TIMEOUT_DIALECTS:
        return {"connect_timeout": max(1, round(timeout_seconds))}
    return {}

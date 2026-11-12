"""The database door: patterns, the system set, the SQLite dialect, a dead connect (DBS-01..05).

The real door opens against SQLite — the one product this job's own driver set carries a
dialect for but the scan names nowhere (DBS-01): its tables are the scan's, and the nameless
default schema is DBS-04's honest case. The system set and the un-introspectable skip are
fakes, because a SQLite database answers no ``pg_catalog``.
"""

import pytest
from aurelius_atlas_db_scanner.database import (
    DatabaseUnreachableError,
    SqlDatabase,
    TableReflectionError,
    compile_patterns,
    is_system_schema,
    matches_any,
)
from sqlalchemy import create_engine, text

SCRUB_CANARY = "sup3r-s3cret"
"""The stand-in password the door must never repeat: it proves the scrubbing (DBS-02, DD-506)."""

DEAD_DSN = f"postgresql+psycopg://atlas:{SCRUB_CANARY}@127.0.0.1:1/warehouse"
"""A Postgres DSN pointing at a port nothing answers on, with a password to prove scrubbing."""


def _sqlite(tmp_path: object, schemas: dict[str | None, list[str]]) -> SqlDatabase:
    """A closed SQLite door holding the named tables, created in files under the tmp dir.

    The caller opens it — as a ``with`` block, the pattern every test here rides — so the
    door's own context management is what closes it.
    """
    path = f"{tmp_path}/scan.db"
    engine = create_engine(f"sqlite:///{path}")
    with engine.begin() as connection:
        for table in schemas.get(None, []):
            connection.execute(text(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY, name TEXT)"))
    engine.dispose()
    return SqlDatabase(f"sqlite:///{path}", connect_timeout_seconds=5.0)


@pytest.mark.covers("aurelius_atlas_db_scanner.database.compile_patterns", rules=["DBS-04", "DBS-05"])
def test_the_patterns_match_case_insensitively_with_the_star_wildcard() -> None:
    """Each comma-separated pattern is a full, case-insensitive match with ``*`` as the wildcard."""
    patterns = compile_patterns(" sales*, ORDERS ,*_hist,")
    assert matches_any("Sales2024", patterns)
    assert matches_any("orders", patterns)
    assert matches_any("audit_hist", patterns)
    assert not matches_any("orders_archive", patterns)


@pytest.mark.covers("aurelius_atlas_db_scanner.database.compile_patterns", rules=["DBS-04", "DBS-05"])
def test_a_lone_star_admits_every_name_and_an_empty_list_admits_none() -> None:
    """The default ``*`` admits everything; a name never matches an empty pattern list."""
    assert matches_any("anything", compile_patterns("*"))
    assert not matches_any("anything", compile_patterns(",, "))


@pytest.mark.covers("aurelius_atlas_db_scanner.database.is_system_schema", rules=["DBS-04"])
def test_the_fixed_system_set_never_enters_a_scan() -> None:
    """The dialect metadata schemas are out of every scan, whatever the patterns say (DBS-04)."""
    for name in ("pg_catalog", "INFORMATION_SCHEMA", "pg_toast", "mysql", "sys", "performance_schema", "pg_temp_7"):
        assert is_system_schema(name)
    assert not is_system_schema("sales")
    assert not is_system_schema("my_syslog")


@pytest.mark.covers("aurelius_atlas_db_scanner.database.SqlDatabase.schema_names", rules=["DBS-01", "DBS-04"])
def test_the_sqlite_door_answers_one_nameless_schema_and_its_tables(tmp_path: pytest.TempPathFactory) -> None:
    """SQLite is DBS-04's nameless case: one schema answered ``None``, and its tables by pattern.

    The door answers the nameless default for SQLite's one schema — no name to match, no
    Collection name of its own — while the table read still names every real table.
    """
    with _sqlite(tmp_path, {None: ["orders", "audit_log"]}) as door:
        assert door.schema_names(compile_patterns("*")) == [None]
        assert sorted(door.table_names(None, compile_patterns("*"))) == ["audit_log", "orders"]
        assert door.table_names(None, compile_patterns("orders")) == ["orders"]


@pytest.mark.covers("aurelius_atlas_db_scanner.database.SqlDatabase.schema_names", rules=["DBS-04"])
def test_the_sqlite_door_admits_nothing_when_the_patterns_miss_the_nameless(tmp_path: pytest.TempPathFactory) -> None:
    """The nameless schema carries no name to match: only ``*`` admits it (DBS-04)."""
    with _sqlite(tmp_path, {None: ["orders"]}) as door:
        assert door.schema_names(compile_patterns("sales*")) == []


@pytest.mark.covers("aurelius_atlas_db_scanner.database.SqlDatabase.reflect", rules=["DBS-01"])
def test_the_sqlite_door_reflects_a_real_table(tmp_path: pytest.TempPathFactory) -> None:
    """The door reads one real table through the inspector: columns, key, and the primary-key mark."""
    with _sqlite(tmp_path, {None: ["orders"]}) as door:
        info = door.reflect(None, "orders")
        assert [column.name for column in info.columns] == ["id", "name"]
        assert info.primary_key == ("id",)
        assert info.columns[0].definition == "Primary key"


@pytest.mark.covers("aurelius_atlas_db_scanner.database.SqlDatabase.reflect", rules=["DBS-05"])
def test_a_table_the_inspector_refuses_raises_the_reflection_error(tmp_path: pytest.TempPathFactory) -> None:
    """One refused table is a :class:`TableReflectionError`, which the scan turns into a notice."""
    with _sqlite(tmp_path, {None: ["orders"]}) as door, pytest.raises(TableReflectionError):
        door.reflect(None, "no_such_table")


@pytest.mark.covers("aurelius_atlas_db_scanner.database.SqlDatabase.open", rules=["DBS-02"])
def test_a_database_that_answers_no_connect_names_host_and_database_not_the_password() -> None:
    """A dead database fails the run naming the URL with its password scrubbed (DBS-02, DD-506)."""
    door = SqlDatabase(DEAD_DSN, connect_timeout_seconds=1.0)
    with pytest.raises(DatabaseUnreachableError) as error:
        door.open()
    message = str(error.value)
    assert "127.0.0.1:1" in message
    assert "warehouse" in message
    assert SCRUB_CANARY not in message


@pytest.mark.covers(
    "aurelius_atlas_db_scanner.database.SqlDatabase.__enter__",
    "aurelius_atlas_db_scanner.database.SqlDatabase.__exit__",
    rules=["DBS-02"],
)
def test_the_with_block_opens_the_door_and_closes_it_again() -> None:
    """The door as a context manager: the block reads it, and the pool is gone after it."""
    door = SqlDatabase(DEAD_DSN, connect_timeout_seconds=1.0)
    # The connect proof runs at the with: a silent database never reaches the body (DBS-02).
    with pytest.raises(DatabaseUnreachableError), door:
        pytest.fail("the body must not run when the database answers nothing")


@pytest.mark.covers(
    "aurelius_atlas_db_scanner.database.SqlDatabase.__enter__",
    "aurelius_atlas_db_scanner.database.SqlDatabase.__exit__",
    rules=["DBS-02"],
)
def test_the_door_is_closed_after_the_block_even_through_a_body_failure(
    tmp_path: pytest.TempPathFactory,
) -> None:
    """Whatever the body did — even raise — the block leaves the door closed."""
    door = _sqlite(tmp_path, {None: ["orders"]})

    def read_and_fail() -> None:
        door.reflect(None, "orders")  # proves the block opened the door
        msg = "a body that fails"
        raise RuntimeError(msg)

    with pytest.raises(RuntimeError), door:
        read_and_fail()
    with pytest.raises(RuntimeError, match="closed"):
        door.schema_names(compile_patterns("*"))


@pytest.mark.covers("aurelius_atlas_db_scanner.database.SqlDatabase.safe_url", rules=["DBS-02"])
def test_the_safe_url_hides_the_password() -> None:
    """The only form of the DSN the job ever prints, scrubbed by SQLAlchemy's own rendering."""
    assert (
        SqlDatabase(DEAD_DSN, connect_timeout_seconds=1.0).safe_url
        == "postgresql+psycopg://atlas:***@127.0.0.1:1/warehouse"
    )

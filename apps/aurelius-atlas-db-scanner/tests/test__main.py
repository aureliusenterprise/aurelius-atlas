"""The CLI: the exit codes of the failures the run answers itself (DBS-02, DBS-10, DBS-11)."""

import pytest
from aurelius_atlas_db_scanner.__main__ import EXIT_FAILURE, EXIT_OK, MINT_REFUSAL, _tokens, run

NO_DOOR = "a run that must not scan must not open the database door"


def _never_a_door(
    *_args: object, **_kwargs: object
) -> None:  # pragma: no cover - the assertion is that this never runs
    raise AssertionError(NO_DOOR)


@pytest.mark.covers("aurelius_atlas_db_scanner.__main__.run", rules=["DBS-02", "DBS-11"])
def test_an_unknown_flag_fails_the_run_with_no_scan(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The settings model is the CLI: a flag it does not name is a configuration error, exit 1 (DBS-11).

    The identity and the DSN are complete here, so the flag alone is what the run refuses.
    """
    monkeypatch.setenv("AURELIUS_ATLAS_DB_SCANNER_DSN", "sqlite:///:memory:")
    monkeypatch.setenv("AURELIUS_ATLAS_DB_SCANNER_SYSTEM_NAME", "Test Database")
    monkeypatch.setenv("AURELIUS_ATLAS_DB_SCANNER_CLIENT_SECRET", "anything")
    monkeypatch.setattr("aurelius_atlas_db_scanner.__main__.SqlDatabase", _never_a_door)
    assert run(["--not-a-flag"]) == EXIT_FAILURE
    assert "configuration error" in capsys.readouterr().err


@pytest.mark.covers("aurelius_atlas_db_scanner.__main__.run", rules=["DBS-02", "DBS-12"])
def test_a_run_without_a_dsn_fails_with_no_scan(monkeypatch: pytest.MonkeyPatch) -> None:
    """A bad configuration is a run-level failure: exit 1, and no door is ever opened (DBS-02).

    The project's ``.env`` carries the dev identity, but never a DSN — the database is
    named per run, so a run that names none has no configuration to build a scan from.
    """
    monkeypatch.setattr("aurelius_atlas_db_scanner.__main__.SqlDatabase", _never_a_door)
    assert run([]) == EXIT_FAILURE


@pytest.mark.covers("aurelius_atlas_db_scanner.__main__._tokens", rules=["DBS-10"])
def test_a_refused_mint_raises_the_named_error() -> None:
    """The scan does not speak anonymously: a None bearer is the refusal the run fails on (DBS-10)."""

    class Refused:
        def bearer(self) -> str | None:
            return None

    with pytest.raises(RuntimeError, match=MINT_REFUSAL):
        _tokens(Refused())()  # pyright: ignore[reportArgumentType] - the protocol's shape is the point


@pytest.mark.covers("aurelius_atlas_db_scanner.__main__._tokens", rules=["DBS-10"])
def test_a_fresh_mint_answers_the_bearer() -> None:
    """The happy path of the token seam: the source's token, verbatim."""

    class Minted:
        def bearer(self) -> str | None:
            return "jwt-value"

    assert _tokens(Minted())() == "jwt-value"  # pyright: ignore[reportArgumentType]
    assert EXIT_OK == 0

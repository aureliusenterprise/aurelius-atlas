"""The CLI: the arguments, and the exit codes of the failures the run answers itself (KSC-01, KSC-09)."""

import pytest
from aurelius_atlas_kafka_scanner.__main__ import EXIT_FAILURE, EXIT_OK, MINT_REFUSAL, _tokens, parse_args, run

NO_DOOR = "a run without settings must not open a door"


@pytest.mark.covers("aurelius_atlas_kafka_scanner.__main__.parse_args", rules=["KSC-08"])
def test_the_cli_takes_a_dry_run_and_repeatable_topics() -> None:
    """--dry-run and --topic (repeatable) are the whole interface (KSC-08)."""
    args = parse_args(["--dry-run", "--topic", "orders", "--topic", "events-*"])
    assert args.dry_run is True
    assert args.topics == ["orders", "events-*"]
    assert parse_args([]).dry_run is False
    assert parse_args([]).topics is None


@pytest.mark.covers("aurelius_atlas_kafka_scanner.__main__.run", rules=["KSC-01", "KSC-09"])
def test_a_secretless_run_fails_with_no_scan(monkeypatch: pytest.MonkeyPatch) -> None:
    """A bad configuration is a run-level failure: exit 1, and no door is ever opened (KSC-01)."""

    def never_open(
        *_args: object, **_kwargs: object
    ) -> None:  # pragma: no cover - the assertion is that this never runs
        raise AssertionError(NO_DOOR)

    monkeypatch.setattr("aurelius_atlas_kafka_scanner.__main__.KafkaCluster", never_open)
    assert run([]) == EXIT_FAILURE


@pytest.mark.covers("aurelius_atlas_kafka_scanner.__main__._tokens", rules=["KSC-09"])
def test_a_refused_mint_raises_the_named_error() -> None:
    """The scan does not speak anonymously: a None bearer is the refusal the run fails on (KSC-09)."""

    class Refused:
        def bearer(self) -> str | None:
            return None

    with pytest.raises(RuntimeError, match=MINT_REFUSAL):
        _tokens(Refused())()  # pyright: ignore[reportArgumentType] - the protocol's shape is the point


@pytest.mark.covers("aurelius_atlas_kafka_scanner.__main__._tokens", rules=["KSC-09"])
def test_a_fresh_mint_answers_the_bearer() -> None:
    """The happy path of the token seam: the source's token, verbatim."""

    class Minted:
        def bearer(self) -> str | None:
            return "jwt-value"

    assert _tokens(Minted())() == "jwt-value"  # pyright: ignore[reportArgumentType]
    assert EXIT_OK == 0

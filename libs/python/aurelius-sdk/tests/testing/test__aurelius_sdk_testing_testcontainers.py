import logging
from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import MagicMock

from aurelius_sdk.testing.testcontainers import capture_docker_compose_logs
from testcontainers.compose import DockerCompose


def _compose(stdout: str, stderr: str) -> MagicMock:
    compose = MagicMock(spec=DockerCompose)
    compose.get_logs.return_value = (stdout, stderr)
    return compose


def test__capture_logs_logs_stdout_and_stderr_per_line() -> None:
    """Each stdout line is logged at INFO and each stderr line at ERROR."""
    compose = _compose("one\ntwo", "bad\nworse")
    logger = MagicMock(spec=logging.Logger)

    capture_docker_compose_logs(compose, "db", logger=logger)

    info_messages = [call.args[0] for call in logger.info.call_args_list]
    error_messages = [call.args[0] for call in logger.error.call_args_list]
    assert "one" in info_messages
    assert "two" in info_messages
    assert error_messages == ["bad", "worse"]


def test__capture_logs_forwards_service_names() -> None:
    """Service names are passed through to DockerCompose.get_logs."""
    compose = _compose("", "")
    capture_docker_compose_logs(compose, "db", "api", logger=MagicMock(spec=logging.Logger))

    compose.get_logs.assert_called_once_with("db", "api")


def test__capture_logs_without_services_captures_all_logs() -> None:
    """Omitting services calls get_logs with no arguments."""
    compose = _compose("", "")
    capture_docker_compose_logs(compose, logger=MagicMock(spec=logging.Logger))

    compose.get_logs.assert_called_once_with()


def test__capture_logs_defaults_to_module_logger() -> None:
    """Without an explicit logger, the module logger receives the records."""
    compose = _compose("hello", "oops")

    with _capture_records() as records:
        capture_docker_compose_logs(compose)

    messages = [(record.levelno, record.getMessage()) for record in records]
    assert (logging.INFO, "hello") in messages
    assert (logging.ERROR, "oops") in messages
    assert all(record.name == "aurelius_sdk.testing.testcontainers" for record in records)


@contextmanager
def _capture_records() -> Iterator[list[logging.LogRecord]]:
    """Capture log records emitted under the aurelius_sdk logger."""
    records: list[logging.LogRecord] = []
    handler = logging.Handler()
    handler.emit = records.append  # type: ignore[method-assign]
    sdk_logger = logging.getLogger("aurelius_sdk")
    previous_level = sdk_logger.level
    sdk_logger.setLevel(logging.INFO)
    sdk_logger.addHandler(handler)
    try:
        yield records
    finally:
        sdk_logger.removeHandler(handler)
        sdk_logger.setLevel(previous_level)

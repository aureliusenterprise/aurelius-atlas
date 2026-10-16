import threading
from collections.abc import Iterable

import logfire
from opentelemetry.metrics import CallbackOptions, Observation

from aurelius_fastapi_example.globals import LOGGER


class ConnectionCounter:
    """Thread-safe counter of open SSE streams, exposed as an OTel gauge callback.

    The callback gauge reports the current count on every metric collection, so
    the value can never drift: it is read straight from the live counter rather
    than accumulated by add/subtract events.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active = 0

    @property
    def active(self) -> int:
        """Number of currently open streams."""
        with self._lock:
            return self._active

    def add(self, delta: int) -> None:
        """Adjust the counter, clamped at zero (defensive against unbalanced calls)."""
        with self._lock:
            self._active = max(self._active + delta, 0)

    def observation(self, options: CallbackOptions) -> Iterable[Observation]:  # noqa: ARG002
        """Yield the current count as a metric observation (OTel callback)."""
        yield Observation(self.active)


SSE_CONNECTIONS = ConnectionCounter()

_registered = False


def register_sse_metric() -> None:
    """Register the open-SSE-streams gauge on the configured meter provider.

    Idempotent: calling it again (e.g. a second ``create_app`` in the same
    process) does not create a duplicate instrument.
    """
    global _registered  # noqa: PLW0603

    if _registered:
        return

    logfire.metric_gauge_callback(
        "aurelius.sse.connections",
        callbacks=[SSE_CONNECTIONS.observation],
        unit="",
        description="Number of open server-sent-event streams.",
    )
    _registered = True
    LOGGER.debug("Registered SSE connection gauge")

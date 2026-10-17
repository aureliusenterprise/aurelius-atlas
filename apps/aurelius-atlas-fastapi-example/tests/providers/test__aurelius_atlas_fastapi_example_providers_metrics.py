from aurelius_atlas_fastapi_example.providers import metrics as metrics_module


def test__counter_active_tracks_add_calls() -> None:
    """add() accumulates deltas into the live count."""
    counter = metrics_module.ConnectionCounter()
    assert counter.active == 0

    counter.add(1)
    counter.add(1)
    counter.add(-1)

    assert counter.active == 1


def test__counter_clamps_at_zero() -> None:
    """Negative drift is clamped so the gauge can never go below zero."""
    counter = metrics_module.ConnectionCounter()

    counter.add(-5)

    assert counter.active == 0


def test__observation_yields_current_active() -> None:
    """The OTel callback yields a single Observation with the current count."""
    counter = metrics_module.ConnectionCounter()
    counter.add(3)

    observations = list(counter.observation(None))  # type: ignore[arg-type]

    assert len(observations) == 1
    assert observations[0].value == 3


def test__register_sse_metric_is_idempotent() -> None:
    """Registering twice (e.g. a second create_app in one process) must not raise."""
    metrics_module.register_sse_metric()
    first = metrics_module._registered  # noqa: SLF001
    metrics_module.register_sse_metric()

    assert first is True

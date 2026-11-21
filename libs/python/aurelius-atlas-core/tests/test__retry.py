"""The shared version-conflict retry (PAR-01, PAR-02, DD-809, DD-810).

The helper runs a callable again after a lost race; each caller keeps its own budget and its own answer for a
conflict that survives. These tests hold the helper to that: what it reruns, what it returns, and what it lets
through untouched.
"""

import pytest
from aurelius_atlas_core.entity_store import EntityVersionConflictError, EntityWriteError
from aurelius_atlas_core.retry import internal_error, is_version_conflict, retry_race
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode

R = "aurelius_atlas_core.retry.retry_race"
CONFLICT = "changed"
FAILED_WRITE = "failed"


class _Flaky:
    """A race that loses the first ``losses`` times, answers ``answer`` after that, and counts its runs."""

    def __init__(self, answer: str, losses: int) -> None:
        self.answer = answer
        self.losses = losses
        self.runs = 0

    async def __call__(self) -> str:
        self.runs += 1
        if self.runs <= self.losses:
            raise EntityVersionConflictError(CONFLICT)
        return self.answer


@pytest.mark.covers(R, rules=["PAR-01"])
async def test__a_race_that_wins_at_once_answers_once() -> None:
    """One run, its answer; nothing rerun."""
    race = _Flaky("done", losses=0)
    assert await retry_race(race, 2) == "done"
    assert race.runs == 1


@pytest.mark.covers(R, rules=["PAR-01"])
async def test__a_lost_race_is_run_again_and_its_answer_returned() -> None:
    """A conflict runs the race once more, and its second answer comes back."""
    race = _Flaky("done", losses=1)
    assert await retry_race(race, 2) == "done"
    assert race.runs == 2


@pytest.mark.covers(R, rules=["PAR-01", "PAR-02"])
async def test__the_last_attempt_s_conflict_becomes_the_caller_s_answer() -> None:
    """The last conflict goes to the caller's mapping, with the conflict as its cause."""
    race = _Flaky("done", losses=2)
    with pytest.raises(AtlasError) as raised:
        await retry_race(race, 2, lost_race=internal_error)
    assert raised.value.code is AtlasErrorCode.INTERNAL_ERROR
    assert "changed" in str(raised.value)
    assert isinstance(raised.value.__cause__, EntityVersionConflictError)
    assert race.runs == 2


@pytest.mark.covers(R, rules=["PAR-01"])
async def test__a_caller_that_maps_nothing_sees_the_conflict_unchanged() -> None:
    """Without a mapping, the last conflict is raised as it was."""
    race = _Flaky("done", losses=1)
    with pytest.raises(EntityVersionConflictError):
        await retry_race(race, 1)
    assert race.runs == 1


@pytest.mark.covers(R, rules=["PAR-01"])
async def test__an_error_that_is_not_a_lost_race_leaves_after_one_run() -> None:
    """Only a conflict reruns: any other error leaves at once, unmapped."""
    calls = 0

    async def race() -> str:
        nonlocal calls
        calls += 1
        raise EntityWriteError(FAILED_WRITE)

    with pytest.raises(EntityWriteError):
        await retry_race(race, 2, lost_race=internal_error)
    assert calls == 1


@pytest.mark.covers(R, rules=["PAR-02"])
async def test__a_caller_may_allow_more_attempts_than_another() -> None:
    """The budget is the caller's: ten runs where another caller stops at two."""
    race = _Flaky("done", losses=5)
    assert await retry_race(race, 10) == "done"
    assert race.runs == 6


@pytest.mark.covers(R, rules=["PAR-02"])
def test__the_conflict_check_names_only_the_version_conflict() -> None:
    """A lost race is the version conflict, and nothing else."""
    assert is_version_conflict(EntityVersionConflictError(CONFLICT))
    assert not is_version_conflict(EntityWriteError(FAILED_WRITE))
    assert not is_version_conflict(AtlasError(AtlasErrorCode.INTERNAL_ERROR, "other"))

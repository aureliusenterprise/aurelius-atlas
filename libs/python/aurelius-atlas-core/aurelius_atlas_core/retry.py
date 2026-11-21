"""``retry_race``: the version-conflict retry every writer shares (PAR-01, PAR-02, DD-809).

Every store write carries the version it read, and a write whose document changed in between is refused
(``EntityStore.write``, DD-046). Each caller used to write that retry loop itself; the loops were the same
body — run, catch the lost race, run again, and on the last attempt raise the answer the caller owes — copied
with a different attempt budget and a different error. This module holds that body once.

The budget and the error stay with the caller (DD-810): the writers retry twice (DD-052), and a conflict left
after the last attempt is whatever answer that caller gives — the same one as before this helper existed.
"""

from collections.abc import Awaitable, Callable

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode

from aurelius_atlas_core.entity_store import EntityVersionConflictError, EntityWriteError, UniqueValueTakenError


def is_version_conflict(error: BaseException) -> bool:
    """Whether ``error`` is a write refused because the document changed underneath it (DD-046)."""
    return isinstance(error, EntityVersionConflictError)


def internal_error(conflict: BaseException) -> AtlasError:
    """The answer a writer owes when the conflict survives every attempt: ``INTERNAL_ERROR`` (DD-052)."""
    return AtlasError(AtlasErrorCode.INTERNAL_ERROR, str(conflict))


def failed_write[T](race: Callable[[], Awaitable[T]]) -> Callable[[], Awaitable[T]]:
    """``race``, with a write that failed for another reason answered as ``INTERNAL_ERROR`` (DD-052).

    A unique value another entity holds, or a write that failed outright, is no race: no writer reruns it, and
    every writer answers it the way it answers a lost one. Callers that map those wrap their race in this and
    pass the same ``lost_race`` to :func:`retry_race`; callers that let them through, like the propagation
    tasks, do not.
    """

    async def mapped() -> T:
        try:
            return await race()
        except (UniqueValueTakenError, EntityWriteError) as failure:
            raise internal_error(failure) from failure

    return mapped


async def retry_race[T](
    race: Callable[[], Awaitable[T]],
    attempts: int,
    *,
    is_conflict: Callable[[BaseException], bool] = is_version_conflict,
    lost_race: Callable[[BaseException], BaseException] | None = None,
) -> T:
    """Run ``race`` until it succeeds, at most ``attempts`` times, and answer what it answered (PAR-01, PAR-02).

    Only what ``is_conflict`` recognises is run again: any other error leaves at once, unmapped. On the last
    attempt the conflict goes to ``lost_race`` and what it returns is raised, or it is raised unchanged when
    ``lost_race`` is given no answer.

    Args:
        race: The work, run again on each lost race. It builds everything it needs, so an attempt never reads
            what a lost one left behind (WRS-05).
        attempts: How often to run it, at least once — each caller keeps its own budget (DD-810).
        is_conflict: Which error is a lost race.
        lost_race: The answer a surviving conflict turns into.

    Raises:
        Exception: What a lost race answers on the last attempt, or any error that is not a lost race.
    """
    for take in range(1, attempts + 1):
        try:
            return await race()
        except EntityVersionConflictError as conflict:
            if not is_conflict(conflict):
                raise
            if take == attempts:
                if lost_race is None:
                    raise
                raise lost_race(conflict) from conflict
    raise AssertionError  # pragma: no cover - the loop returns or raises

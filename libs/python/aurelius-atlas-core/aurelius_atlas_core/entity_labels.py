"""``EntityLabels``: the labels of entities, set, added and removed (LBL-01 to LBL-05).

The label methods of ``AtlasEntityStoreV2`` (``setLabels``, ``addLabels``, ``removeLabels``) and the mapping
``EntityGraphMapper`` does for them, each request one write, run again once after a lost race (DD-052). Labels keep
the order they were first given (DD-021, DV-116).
"""

from collections.abc import Awaitable, Callable, Sequence

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode

from aurelius_atlas_core.authorization import ALLOW_ALL, AtlasPrivilege, Authorizer
from aurelius_atlas_core.entity_change_notifier import EntityChangeNotifier
from aurelius_atlas_core.entity_discovery import validate_labels
from aurelius_atlas_core.entity_documents import VersionedEntity
from aurelius_atlas_core.entity_store import (
    EntityChange,
    EntityStore,
    EntityVersionConflictError,
    EntityWriteError,
    UniqueValueTakenError,
)

ATTEMPTS = 2
"""A request that loses a race is run once more (DD-052)."""

NO_GUID = "guid is null/empty"
NO_LABELS = "labels is null/empty"

type Change = tuple[list[str], list[str]] | None
"""The labels a write added and removed, or None when nothing was written."""


class EntityLabels:
    """Labels of the entities of ``store``, changed as ``user``; ``notifier`` is told what each change added and
    removed once it is written, and ``authorizer`` checks each label (AUZ-16).
    """  # noqa: D205 - one sentence

    def __init__(
        self,
        store: EntityStore,
        *,
        user: str | None = None,
        notifier: EntityChangeNotifier | None = None,
        authorizer: Authorizer = ALLOW_ALL,
    ) -> None:
        self._store = store
        self._user = user
        self._notifier = notifier
        self._authorizer = authorizer

    async def set_labels(self, guid: str, labels: Sequence[str] | None) -> None:
        """``setLabels``: the entity's labels become ``labels``, none for None or none given (LBL-02, AUZ-16).

        Each label added needs ``ENTITY_ADD_LABEL``, each removed ``ENTITY_REMOVE_LABEL``, once they are validated.
        The entity is written, and its modification time and user set, even when its labels stay.

        Raises:
            AtlasError: ``INVALID_PARAMETERS``, ``INSTANCE_GUID_NOT_FOUND``, ``INVALID_LABEL_LENGTH``,
                ``INVALID_LABEL_CHARACTERS``, ``UNAUTHORIZED_ACCESS``.
        """
        if not guid:
            raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, NO_GUID)
        given = None if labels is None else list(dict.fromkeys(labels))

        async def attempt() -> Change:
            found = await self._entity(guid)
            validate_labels(given)
            current = found.entity.labels or []
            added, removed = _difference(given or [], current)
            for label in added:
                self._verify(AtlasPrivilege.ENTITY_ADD_LABEL, "add label: guid=", guid, label)
            for label in removed:
                self._verify(AtlasPrivilege.ENTITY_REMOVE_LABEL, "remove label: guid=", guid, label)
            await self._write(found, given or [])
            return added, removed

        await self._run(guid, attempt)

    async def add_labels(self, guid: str, labels: Sequence[str] | None) -> None:
        """``addLabels``: the labels the entity does not have yet added to it (LBL-03, AUZ-16).

        Each label needs ``ENTITY_ADD_LABEL`` before the labels are validated. Nothing is written when the entity
        has them all.

        Raises:
            AtlasError: ``INVALID_PARAMETERS``, ``INSTANCE_GUID_NOT_FOUND``, ``UNAUTHORIZED_ACCESS``,
                ``INVALID_LABEL_LENGTH``, ``INVALID_LABEL_CHARACTERS``.
        """
        given = self._given(guid, labels)

        async def attempt() -> Change:
            found = await self._entity(guid)
            for label in given:
                self._verify(AtlasPrivilege.ENTITY_ADD_LABEL, "add/update label: guid=", guid, label)
            validate_labels(given)
            current = found.entity.labels or []
            added = [label for label in given if label not in current]
            if not added:
                return None
            await self._write(found, [*current, *added])
            return added, []

        await self._run(guid, attempt)

    async def remove_labels(self, guid: str, labels: Sequence[str] | None) -> None:
        """``removeLabels``: the labels given taken from the entity (LBL-04, AUZ-16).

        Each label needs ``ENTITY_REMOVE_LABEL`` before the labels are validated. Nothing is written when the
        entity has none of them.

        Raises:
            AtlasError: ``INVALID_PARAMETERS``, ``INSTANCE_GUID_NOT_FOUND``, ``UNAUTHORIZED_ACCESS``,
                ``INVALID_LABEL_LENGTH``, ``INVALID_LABEL_CHARACTERS``.
        """
        given = self._given(guid, labels)

        async def attempt() -> Change:
            found = await self._entity(guid)
            for label in given:
                self._verify(AtlasPrivilege.ENTITY_REMOVE_LABEL, "remove label: guid=", guid, label)
            validate_labels(given)
            current = found.entity.labels or []
            removed = [label for label in current if label in given]
            if not removed:
                return None
            await self._write(found, [label for label in current if label not in given])
            return [], removed

        await self._run(guid, attempt)

    @staticmethod
    def _given(guid: str, labels: Sequence[str] | None) -> list[str]:
        """The labels of an add or remove, each once.

        Raises:
            AtlasError: ``INVALID_PARAMETERS`` for no GUID, or no labels.
        """
        if not guid:
            raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, NO_GUID)
        if not labels:
            raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, NO_LABELS)
        return list(dict.fromkeys(labels))

    def _verify(self, privilege: AtlasPrivilege, verb: str, guid: str, label: str) -> None:
        self._authorizer.verify_access(privilege, verb, guid, ", label=", label)

    async def _entity(self, guid: str) -> VersionedEntity:
        found = await self._store.get(guid)
        if found is None:
            raise AtlasError(AtlasErrorCode.INSTANCE_GUID_NOT_FOUND, guid)
        return found

    async def _write(self, found: VersionedEntity, labels: list[str]) -> None:
        """``updateLabels`` and ``updateModificationMetadata``: the labels, or none, at the request's time."""
        entity = found.entity.touched(now=self._store.now(), user=self._user)
        await self._store.write([EntityChange(entity.model_copy(update={"labels": labels or None}), found.version)])

    async def _run(self, guid: str, attempt: Callable[[], Awaitable[Change]]) -> None:
        """Run once more after a lost race; a second loss or a failed write is ``INTERNAL_ERROR`` (DD-052).

        What the write added and removed is told after it (LBL-05).
        """
        for number in range(1, ATTEMPTS + 1):
            try:
                change = await attempt()
            except EntityVersionConflictError as conflict:
                if number == ATTEMPTS:
                    raise AtlasError(AtlasErrorCode.INTERNAL_ERROR, str(conflict)) from conflict
            except (UniqueValueTakenError, EntityWriteError) as failure:
                raise AtlasError(AtlasErrorCode.INTERNAL_ERROR, str(failure)) from failure
            else:
                if change is not None and self._notifier is not None:
                    await self._notifier.on_labels_updated(guid, *change, user=self._user)
                return


def _difference(labels: list[str], others: list[str]) -> tuple[list[str], list[str]]:
    """The labels not among ``others``, and those among them."""
    return [label for label in labels if label not in others], [label for label in others if label not in labels]

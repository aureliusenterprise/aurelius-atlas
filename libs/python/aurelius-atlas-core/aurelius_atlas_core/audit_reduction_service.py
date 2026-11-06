"""``AtlasAuditReductionService``: the agings of the entity audits a criteria or the configuration asks for, each
queued as a task (AGE-01 to AGE-03).
"""  # noqa: D205 - one sentence

import logging
from dataclasses import dataclass
from typing import Any

from aurelius_atlas_model.audit import EntityAuditActionV2
from aurelius_atlas_model.audit_reduction import (
    AUDIT_AGING_ACTION_TYPES_KEY,
    AUDIT_AGING_COUNT_KEY,
    AUDIT_AGING_ENTITY_TYPES_KEY,
    AUDIT_AGING_SUBTYPES_INCLUDED_KEY,
    AUDIT_AGING_TTL_KEY,
    AUDIT_AGING_TYPE_KEY,
    CREATE_EVENTS_AGEOUT_ALLOWED_KEY,
    AtlasAuditAgingType,
    AuditReductionCriteria,
)
from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.tasks import AtlasTask, TaskStatus

from aurelius_atlas_core.audit_reduction_task import AUDIT_REDUCTION_ENTITY_RETRIEVAL
from aurelius_atlas_core.entity_store import EntityStore, TaskChange
from aurelius_atlas_core.request_context import current_user
from aurelius_atlas_core.stored_task import StoredTask

LOGGER = logging.getLogger(__name__)

VALUE_DELIMITER = ","
ALL_ACTIONS = tuple(action.value for action in EntityAuditActionV2)


@dataclass(frozen=True)
class AuditAgingConfig:
    """The ``atlas.audit.*`` aging settings, at Atlas's defaults (``AtlasConfiguration``)."""

    aging_enabled: bool = False
    default_ageout_enabled: bool = True
    default_ageout_ttl_in_days: int = 90
    default_ageout_count: int = 0
    default_ageout_ignore_ttl: bool = False
    custom_ageout_ttl_in_days: int = 0
    custom_ageout_count: int = 0
    custom_ageout_entity_types: str | None = None
    custom_ageout_action_types: str | None = None
    sweep_out_enabled: bool = False
    sweep_out_entity_types: str | None = None
    sweep_out_action_types: str | None = None
    create_events_ageout_allowed: bool = False
    subtypes_included: bool = True
    min_ttl_to_maintain: int = 7
    min_count_to_maintain: int = 50
    max_pending_tasks: int = 50
    """``atlas.audit.reduction.max.pending.tasks``."""


class AtlasAuditReductionService:
    """``AtlasAuditReductionService`` over the tasks of ``store``, bounded by ``config``."""

    def __init__(self, store: EntityStore, config: AuditAgingConfig) -> None:
        self._store = store
        self._config = config

    def criteria_of_config(self) -> AuditReductionCriteria:
        """``convertConfigToAuditReductionCriteria``: the configured agings, each TTL and count at least the minimum
        kept unless off (AGE-02).
        """  # noqa: D205 - one sentence
        config = self._config
        return AuditReductionCriteria.model_validate(
            {
                "audit_aging_enabled": config.aging_enabled,
                "create_events_ageout_allowed": config.create_events_ageout_allowed,
                "sub_types_included": config.subtypes_included,
                "ignore_default_ageout_ttl": config.default_ageout_ignore_ttl,
                "default_ageout_enabled": config.default_ageout_enabled,
                "default_ageout_ttl_in_days": max(config.default_ageout_ttl_in_days, config.min_ttl_to_maintain),
                "default_ageout_audit_count": self._count(config.default_ageout_count),
                "custom_ageout_ttl_in_days": self._ttl(config.custom_ageout_ttl_in_days),
                "custom_ageout_audit_count": self._count(config.custom_ageout_count),
                "custom_ageout_entity_types": config.custom_ageout_entity_types,
                "custom_ageout_action_types": config.custom_ageout_action_types,
                "audit_sweepout_enabled": config.sweep_out_enabled,
                "sweepout_entity_types": config.sweep_out_entity_types if config.sweep_out_enabled else None,
                "sweepout_action_types": config.sweep_out_action_types if config.sweep_out_enabled else None,
            }
        )

    def build_ageout_criteria(self, criteria: AuditReductionCriteria | None) -> list[dict[str, Any]]:
        """``buildAgeoutCriteriaForAllAgingTypes``: a sweep, a custom and a default aging, each as its task's
        parameters, the types and actions of one left out of those after it (AGE-02).

        Raises:
            AtlasError: ``INTERNAL_ERROR`` for action types of which none names an action.
        """  # noqa: D205 - one sentence
        if criteria is None or not criteria.audit_aging_enabled:
            return []
        found: list[dict[str, Any]] = []
        excluded: set[str] = set()
        default_actions = set(ALL_ACTIONS)
        create, subtypes = criteria.create_events_ageout_allowed, criteria.sub_types_included
        ignore_ttl = criteria.ignore_default_ageout_ttl
        default_ttl = 0 if ignore_ttl else max(criteria.default_ageout_ttl_in_days, self._config.min_ttl_to_maintain)
        default_count = self._count(criteria.default_ageout_audit_count)
        custom_ttl = self._ttl(criteria.custom_ageout_ttl_in_days)
        custom_count = self._count(criteria.custom_ageout_audit_count)
        custom_types = _unique(criteria.custom_ageout_entity_types)
        custom_actions = _valid_actions(AtlasAuditAgingType.CUSTOM, _unique(criteria.custom_ageout_action_types))
        excluded |= custom_types
        if not custom_types:
            default_actions -= custom_actions
        if criteria.audit_sweepout_enabled:
            sweep_types = _unique(criteria.sweepout_entity_types)
            sweep_actions = _valid_actions(AtlasAuditAgingType.SWEEP, _unique(criteria.sweepout_action_types))
            if sweep_types or sweep_actions:
                found.append(_criteria(AtlasAuditAgingType.SWEEP, 0, 0, sweep_types, sweep_actions, create, subtypes))
            else:
                LOGGER.error("Sweepout of audits is skipped: neither entity types nor action types are configured")
            excluded |= sweep_types
            custom_types -= sweep_types
            if not sweep_types:
                default_actions -= sweep_actions
                custom_actions -= sweep_actions
        if (custom_ttl > 0 or custom_count > 0) and (custom_types or custom_actions):
            found.append(
                _criteria(
                    AtlasAuditAgingType.CUSTOM, custom_ttl, custom_count, custom_types, custom_actions, create, subtypes
                )
            )
        elif custom_ttl > 0 or custom_count > 0 or custom_types or custom_actions:
            LOGGER.error("Custom audit aging is skipped: it needs a TTL or a count, and entity or action types")
        if criteria.default_ageout_enabled:
            found += _default(default_ttl, default_count, excluded, default_actions, criteria)
        return found

    async def start_by_criteria(self, criteria: list[dict[str, Any]]) -> list[AtlasTask]:
        """``startAuditAgingByCriteria``: a pending ``AUDIT_REDUCTION_ENTITY_RETRIEVAL`` task of each aging, as the
        current user; once too many are pending, the rest are not queued, the failure logged (AGE-03).
        """  # noqa: D205 - one sentence
        tasks: list[AtlasTask] = []
        try:
            for parameters in criteria:
                tasks.append(await self._queue(parameters))  # noqa: PERF401 - those queued before a refusal stay
        except AtlasError:
            LOGGER.exception("Error while aging out audits by criteria")
        return tasks

    async def start_by_config(self) -> list[AtlasTask]:
        """``startAuditAgingByConfig``: the agings of the configuration queued (AGE-02, AGE-03)."""
        try:
            return await self.start_by_criteria(self.build_ageout_criteria(self.criteria_of_config()))
        except AtlasError:
            LOGGER.exception("Error while aging out audits by configuration")
            return []

    async def _queue(self, parameters: dict[str, Any]) -> AtlasTask:
        """``createAndQueueAuditReductionTask``: refused once more than the allowed tasks of the type are pending.

        Raises:
            AtlasError: ``PENDING_TASKS_ALREADY_IN_PROGRESS``.
        """
        pending = [
            task
            for task, _ in await self._store.list_tasks(open_only=True)
            if task.type == AUDIT_REDUCTION_ENTITY_RETRIEVAL and task.status is TaskStatus.PENDING
        ]
        if len(pending) > self._config.max_pending_tasks:
            raise AtlasError(AtlasErrorCode.PENDING_TASKS_ALREADY_IN_PROGRESS, len(pending))
        now = self._store.now()
        task = StoredTask(
            guid=self._store.new_guid(),
            type=AUDIT_REDUCTION_ENTITY_RETRIEVAL,
            created_by=current_user(),
            created_time=now,
            updated_time=now,
            parameters=parameters,
        )
        await self._store.write([], [], [], [TaskChange(task)])
        return task.to_task()

    def _ttl(self, ttl: int) -> int:
        """A TTL that is on raised to the minimum kept (``getGuaranteedMinValueOf``)."""
        return ttl if ttl <= 0 else max(ttl, self._config.min_ttl_to_maintain)

    def _count(self, count: int) -> int:
        """A count that is on raised to the minimum kept."""
        return count if count <= 0 else max(count, self._config.min_count_to_maintain)


def _criteria(  # noqa: PLR0913, PLR0917 - getAgeoutCriteriaMap's arguments
    aging_type: AtlasAuditAgingType,
    ttl: int,
    count: int,
    entity_types: set[str],
    actions: set[str],
    create_events_ageout_allowed: bool,  # noqa: FBT001
    subtypes_included: bool,  # noqa: FBT001
) -> dict[str, Any]:
    """``getAgeoutCriteriaMap``: an aging's task parameters, its types and actions sorted."""
    return {
        AUDIT_AGING_TYPE_KEY: aging_type.value,
        AUDIT_AGING_TTL_KEY: ttl,
        AUDIT_AGING_COUNT_KEY: count,
        AUDIT_AGING_ENTITY_TYPES_KEY: sorted(entity_types),
        AUDIT_AGING_ACTION_TYPES_KEY: sorted(actions),
        CREATE_EVENTS_AGEOUT_ALLOWED_KEY: create_events_ageout_allowed,
        AUDIT_AGING_SUBTYPES_INCLUDED_KEY: subtypes_included,
    }


def _default(
    ttl: int, count: int, excluded: set[str], actions: set[str], criteria: AuditReductionCriteria
) -> list[dict[str, Any]]:
    """The default aging, of all actions as none; skipped, and logged, when its TTL is ignored and it has no count."""
    if criteria.ignore_default_ageout_ttl and count <= 0:
        LOGGER.error("Default audit aging is skipped: a count is needed when its TTL is ignored")
        return []
    actions = set() if len(actions) == len(ALL_ACTIONS) else actions  # all actions: one listing without an action
    create, subtypes = criteria.create_events_ageout_allowed, criteria.sub_types_included
    return [_criteria(AtlasAuditAgingType.DEFAULT, ttl, count, excluded, actions, create, subtypes)]


def _unique(value: str | None) -> set[str]:
    """``getUniqueListOf``: the comma-separated names, trimmed."""
    return {name.strip() for name in value.split(VALUE_DELIMITER)} if value else set()


def _valid_actions(aging_type: AtlasAuditAgingType, names: set[str]) -> set[str]:
    """``getValidActionTypes``: the actions each name starts (``*`` dropped), the unknown ones logged.

    Raises:
        AtlasError: ``INTERNAL_ERROR`` when names were given but none names an action.
    """
    found: set[str] = set()
    invalid: set[str] = set()
    for name in names:
        prefix = name.replace("*", "")
        matched = {action for action in ALL_ACTIONS if action.startswith(prefix)}
        if matched:
            found |= matched
        else:
            invalid.add(name)
    if names and not found:
        canonical = "org.apache.atlas.model.audit.EntityAuditEventV2.EntityAuditActionV2"
        message = f"No enum constant {canonical}.{VALUE_DELIMITER.join(sorted(invalid))}"
        raise AtlasError.of_message(AtlasErrorCode.INTERNAL_ERROR, message)
    if invalid:
        LOGGER.warning("Invalid action type name(s) %s for aging type %s", ",".join(sorted(invalid)), aging_type)
    return found

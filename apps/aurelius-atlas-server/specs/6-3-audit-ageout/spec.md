# 6.3c4 Entity audit aging

- **Status:** in progress
- **Pull request:** to follow
- **Records:** DD-309, DV-132, DV-133, DV-134; relies on the entity audits (AUD-_) and the tasks (TSK-_)

The entity audits grow with every change. Atlas ages them out: a default aging of every type by age and count,
a custom aging of some types or actions with its own age and count, and a sweep that removes every audit of
some types or actions. `admin/audits/ageout` queues the agings a request asks for, or those of the
configuration; with `audit_aging_enabled` the configuration's run on a schedule. The task worker runs them, so
aging needs `tasks_enabled`.

## Scope

| Endpoint                              | Needs          |
| ------------------------------------- | -------------- |
| `POST /api/atlas/admin/audits/ageout` | `ADMIN_AUDITS` |

In `aurelius-atlas-model`, `audit_reduction` and `PENDING_TASKS_ALREADY_IN_PROGRESS`. In `aurelius-atlas-core`,
`audit_reduction_service`, `audit_reduction_task`, `events_to_age_out` and `delete_events_v2` with the
repositories' `delete_events`, and the task's dispatch in `task_management`. In `aurelius-atlas-server`, the
route in `routes/admin`, the `audit_*` settings and the `AuditAgingScheduler`.

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AGE-01 | `POST admin/audits/ageout` needs `ADMIN_AUDITS`, `Admin Audits Ageout`. With `useAuditConfig=true` it queues the configuration's agings; else it reads `AuditReductionCriteria` (Java's names, `TTL` in capitals) and, unless `auditAgingEnabled`, answers 204. A default TTL of 0 or less is the configured one. It answers the queued tasks, or 204 when none is queued                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| AGE-02 | The criteria make up to three agings, each as its task's parameters (`auditAgingType`, `ttl`, `auditCount`, `entityTypes`, `actionTypes`, `createEventsAgeoutAllowed`, `subTypesIncluded`). A TTL or count that is on is at least `audit_min_ttl_to_maintain` (7) or `audit_min_count_to_maintain` (50); the default TTL always, unless ignored. Action names match every action they start (`*` dropped); names of which none matches fail (`No enum constant …EntityAuditActionV2.<names>`). A sweep (when enabled, of some types or actions) comes first; its types leave the custom and default agings, and without types its actions leave them. A custom aging needs a TTL or count and types or actions; its types leave the default aging, and without types its actions do. The default aging (when enabled) excludes those types; all actions are none; with its TTL ignored it needs a count |
| AGE-03 | Each aging is a pending `AUDIT_REDUCTION_ENTITY_RETRIEVAL` task created by the current user. When more than `audit_reduction_max_pending_tasks` (50) are pending, the rest are not queued and the refusal (`PENDING_TASKS_ALREADY_IN_PROGRESS`) is only logged                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| AGE-04 | The task finds the entities, in any state, of its types (`<prefix>*` all that start so, with their sub types when `subTypesIncluded`), or of every type for none; the default aging takes the types it does not name. A custom aging or sweep none of whose types exists finds none. For each entity, per action asked (or of all), creations left out unless allowed, newest first: past the `auditCount` newest age out when a count is given or the aging sweeps. Of those kept, a default aging or one of all actions keeps the newest `auditCount` of them all, and those older than `ttl` days age out. The task is removed when done                                                                                                                                                                                                                                                             |
| AGE-05 | With `audit_aging_enabled` the configuration's agings are queued `audit_aging_scheduler_initial_delay_in_min` (at least 1) after the start, then every `audit_aging_scheduler_frequency_in_days` (at least 1); a round that fails is only logged                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |

## Java origin

Apache Atlas `release-2.4.0`:

- `webapp/.../web/resources/AdminResource.java`: `ageoutAuditData`, `updateCriteriaWithDefaultValues`
- `repository/.../audit/AtlasAuditReductionService.java`
- `repository/.../store/graph/v2/tasks/AuditReductionTaskFactory.java`, `AuditReductionEntityRetrievalTask.java`,
  `AuditReductionTask.java`
- `repository/.../audit/HBaseBasedAuditRepository.java`: `deleteEventsV2` and its `listEventsV2`
- `repository/.../discovery/EntityDiscoveryService.java`: `createAndQueueAuditReductionTask`,
  `searchEntityGUIDs`
- `intg/.../AtlasConfiguration.java` (`atlas.audit.*`), `intg/.../model/audit/AuditReductionCriteria.java`,
  `common/.../repository/Constants.java` (`AtlasAuditAgingType`, the task keys)

## Deviations

- **DV-132:** an aging finds its entities by type alone; Atlas's search for them also takes the type names
  as a free-text query.
- **DV-133:** every server process schedules the configured aging; Atlas schedules it on its active instance.
  The pending limit bounds the tasks the processes queue.
- **DV-134:** an ageout without a body answers 204; Atlas fails on the missing criteria.

## Acceptance

- `libs/python/aurelius-atlas-core/tests/test__audit_reduction.py` — AGE-01 to AGE-04: what an aging removes,
  the agings the criteria make, their tasks, the entities they find, a task run by the task management.
- `libs/python/aurelius-atlas-core/e2e/test__entity_audit_e2e.py` — AGE-04 on Elasticsearch.
- `libs/python/aurelius-atlas-model/tests/test__audit_reduction_criteria.py` — the criteria.
- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_audit_ageout.py` — AGE-01 to AGE-03 through the
  route, AGE-05 the schedule.
- `apps/aurelius-atlas-server/scenarios/admin/audit-ageout.scenario.yaml`.
- `uv run aurelius-atlas-trace check`.
